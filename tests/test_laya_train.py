# tests/test_laya_train.py
import pytest

torch = pytest.importorskip("torch")  # the laya extra brings torch
from common import laya_train  # noqa: E402


def test_device_prefers_apple_gpu_then_nvidia_then_cpu(monkeypatch):
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert laya_train.pick_device() == "mps"
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    assert laya_train.pick_device() == "cuda"
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert laya_train.pick_device() == "cpu"


def test_temperature_softens_an_overconfident_model():
    logits = torch.tensor([[0.0, 4.0]] * 50)  # says yes at ~0.98
    targets = torch.tensor([[0.3, 0.7]] * 50)  # the teacher said 0.7
    assert laya_train.fit_temperature(logits, targets) > 1.5


def test_temperature_leaves_a_calibrated_model_alone():
    logits = torch.tensor([[0.0, 0.8473]] * 50)  # softmax -> 0.7
    targets = torch.tensor([[0.3, 0.7]] * 50)
    assert laya_train.fit_temperature(logits, targets) == pytest.approx(1.0, abs=0.05)


def test_asker_returns_the_yes_probability():
    class FakeAgent:
        def predict(self, state, questions):
            assert questions == {"q": {"type": "noul", "instructions": "Beach?"}}
            return {"answers": {"q": {"noul": 0.83}}}

    assert laya_train.asker(FakeAgent())("Boracay", "Beach?") == 0.83
