"""Fine-tune Laya on labelled yes/no questions.

Adapted from Laya's own notebook (docs/reference/laya/, Apache-2.0, github.com/NandhaKishorM/laya): the same
proper-scoring-rule rewards plus soft cross-entropy, on one GPU instead of two NVIDIA T4s, in full precision,
for yes/no questions only. Then one calibration temperature, fitted on a held-out slice like the notebook does.
"""
import json
import os
import random
import time
from pathlib import Path

import torch

BASE = "convaiinnovations/laya"  # the 421M-parameter base checkpoint
MICRO, ACCUM, GROUP = 8, 4, 4  # 8 questions per step, an update every 4 steps, 4 noisy samples per question
SIGMA_START, SIGMA_END = 0.4, 0.1  # exploration noise, shrinking over the epochs


def pick_device() -> str:
    """Apple GPU, else NVIDIA GPU, else CPU (slow)."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def base_model_dir() -> str:
    """Download the base checkpoint once (Hugging Face caches it) and return its folder."""
    from huggingface_hub import snapshot_download
    from laya.agent import _fix_tokenizer_config

    path = snapshot_download(BASE)
    _fix_tokenizer_config(path)
    return path


def asker(agent):
    """ask(state, question) -> P(yes), for a loaded laya.Agent."""
    def ask(state: str, question: str) -> float:
        answers = agent.predict(state, {"q": {"type": "noul", "instructions": question}})["answers"]
        return float(answers["q"]["noul"])
    return ask


def fit_temperature(logits: torch.Tensor, targets: torch.Tensor) -> float:
    """The one number that makes the model's probabilities match the teacher's on held-out questions."""
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=100)

    def closure():
        opt.zero_grad()
        loss = -(targets * torch.log_softmax(logits / log_t.exp(), -1)).sum(-1).mean()
        loss.backward()
        return loss

    opt.step(closure)
    return float(torch.clamp(log_t.detach().exp(), 0.1, 10.0))


def _items(rows, tok, cfg):
    """Tokenize each labelled question the way Laya reads it; the target is [P(no), P(yes)] from the teacher."""
    from laya.common import QTYPES, build_sequence, render_options

    items = []
    for row in rows:
        q = {"t": "noul", "ins": row["question"], "crit": {}}
        seq, markers = build_sequence(tok, row["state"], q, cfg["max_len"], cfg["head_max_len"])
        if len(markers) == len(render_options(q)):
            items.append({"ids": seq, "markers": markers, "qtype": QTYPES["noul"], "target": [1 - row["p"], row["p"]]})
    return items


def _batch(items, pad_id, device):
    n, length = len(items), max(len(it["ids"]) for it in items)
    kmax = max(len(it["markers"]) for it in items)
    ids = torch.full((n, length), pad_id, dtype=torch.long)
    att = torch.zeros((n, length), dtype=torch.long)
    mpos = torch.zeros((n, kmax), dtype=torch.long)
    mmask = torch.zeros((n, kmax), dtype=torch.bool)
    target = torch.zeros((n, kmax))
    for i, it in enumerate(items):
        ids[i, :len(it["ids"])] = torch.tensor(it["ids"])
        att[i, :len(it["ids"])] = 1
        mpos[i, :len(it["markers"])] = torch.tensor(it["markers"])
        mmask[i, :len(it["markers"])] = True
        target[i, :len(it["target"])] = torch.tensor(it["target"])
    qtype = torch.tensor([it["qtype"] for it in items])
    return [t.to(device) for t in (ids, att, mpos, mmask, target, qtype)]


def _peak_gb(device: str) -> float | None:
    if device == "mps":
        return torch.mps.driver_allocated_memory() / 1e9
    if device == "cuda":
        return torch.cuda.max_memory_allocated() / 1e9
    return None


def train(rows: list[dict], out_dir: Path, epochs: int, device: str, log=print) -> dict:
    """Fine-tune the base checkpoint on the labelled rows and save it to out_dir."""
    from laya.common import build_model, proper_reward
    from safetensors.torch import load_file, save_file
    from transformers import AutoTokenizer

    base = base_model_dir()
    tok = AutoTokenizer.from_pretrained(os.path.join(base, "tokenizer"))
    cfg = json.load(open(os.path.join(base, "rl_agent_config.json")))
    items = _items(rows, tok, cfg)
    random.Random(20260922).shuffle(items)
    n_calib = max(40, len(items) // 10)  # held out: calibration is fitted on questions it never trained on
    calib, train_items = items[:n_calib], items[n_calib:]

    model = build_model(cfg, encoder_dir=os.path.join(base, "encoder"))
    model.load_state_dict(load_file(os.path.join(base, "model.safetensors")), strict=True)
    model.to(device).train()
    enc = [p for n, p in model.named_parameters() if "encoder." in n]
    head = [p for n, p in model.named_parameters() if "encoder." not in n]
    opt = torch.optim.AdamW([{"params": enc, "lr": 2.5e-5}, {"params": head, "lr": 1e-4}], weight_decay=0.01)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=max(1, len(train_items) // (MICRO * ACCUM) * epochs), eta_min=1e-6)

    start = time.time()
    for epoch in range(epochs):
        random.Random(42 + epoch).shuffle(train_items)
        sigma = SIGMA_START + (SIGMA_END - SIGMA_START) * epoch / max(1, epochs - 1)
        total, steps = 0.0, 0
        opt.zero_grad(set_to_none=True)
        for b in range(0, len(train_items), MICRO):
            ids, att, mpos, mmask, target, qtype = _batch(train_items[b:b + MICRO], tok.pad_token_id, device)
            logits, act = model(ids, att, mpos, mmask, qtype)
            logits = logits.float()
            # Try a few noisy versions of the answer, reward the ones a proper scoring rule likes...
            k = mmask.sum(-1, keepdim=True).float()
            eps = torch.randn((GROUP,) + logits.shape, device=device) * sigma * mmask
            eps = (eps - eps.sum(-1, keepdim=True) / k) * mmask
            z = logits.detach().unsqueeze(0) + eps
            with torch.no_grad():
                reward = proper_reward(torch.softmax(z.masked_fill(~mmask, -1e4), -1), target.unsqueeze(0), qtype,
                                       mmask, w_sph=0.75, w_rps=1.0)
                adv = reward - reward.mean(0, keepdim=True)
                adv = adv / (adv.std() + 1e-6)
            logp = -(((z - logits.unsqueeze(0)) ** 2) * mmask).sum(-1) / (2 * sigma ** 2)
            # ...and pull the answer towards the teacher's probabilities.
            copy_teacher = -(target * torch.log_softmax(logits.masked_fill(~mmask, -1e4), -1)).sum(-1).mean()
            loss = -(adv * logp).mean() + copy_teacher
            (loss / ACCUM + 0.0 * act.sum()).backward()
            steps += 1
            if steps % ACCUM == 0 or b + MICRO >= len(train_items):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
            total += loss.item()
        log(f"    epoch {epoch + 1}/{epochs}: loss {total / steps:.3f}   ({time.time() - start:.0f}s)")
    seconds, peak = time.time() - start, _peak_gb(device)

    model.eval()
    zs, ts = [], []
    with torch.no_grad():
        for b in range(0, len(calib), 16):
            ids, att, mpos, mmask, target, qtype = _batch(calib[b:b + 16], tok.pad_token_id, device)
            zs.append(model(ids, att, mpos, mmask, qtype)[0].float().cpu()[:, :2])
            ts.append(target.cpu()[:, :2])
    temperature = fit_temperature(torch.cat(zs), torch.cat(ts))

    out_dir.mkdir(parents=True, exist_ok=True)
    save_file({k: v.half().contiguous().cpu() for k, v in model.state_dict().items()}, str(out_dir / "model.safetensors"))
    model.encoder.config.save_pretrained(str(out_dir / "encoder"))
    tok.save_pretrained(str(out_dir / "tokenizer"))
    from laya.common import QTYPES
    temps = cfg.get("temperature", [1.2, 1.2, 1.2])
    temps = list(temps) if isinstance(temps, list) else [temps] * 3
    temps[QTYPES["noul"]] = temperature
    cfg.update(fine_tuned=True, model_name="laya-travel", temperature=temps)
    cfg.pop("temperature_by_options", None)  # old per-bucket values would override the new fit
    (out_dir / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    return {"seconds": seconds, "peak_gb": peak, "temperature": temperature, "items": len(train_items)}
