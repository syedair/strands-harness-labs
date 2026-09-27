# Laya's fine-tuning notebook (reference copy)

`laya_finetune_typed_decisions_2xT4_kaggle.ipynb` is Laya's own fine-tuning notebook, copied unchanged so you can
compare it with lab 10b.

- **Source:** [NandhaKishorM/laya](https://github.com/NandhaKishorM/laya), `notebooks/laya_finetune_typed_decisions_2xT4_kaggle.ipynb`,
  commit `bdce407b75afce3dd61ea2364785e2bf4b64bbf3`.
- **Licence:** Apache-2.0, © the Laya authors. The licence is in `LICENSE` next to this file.

## What the notebook does

- Fine-tunes `convaiinnovations/laya` (421M parameters) on the train split of
  [`LocalLLaMA/typed-decisions`](https://huggingface.co/datasets/LocalLLaMA/typed-decisions):
  1,200 synthetic cases, 6,000 typed decisions, across four made-up workflows.
- Runs on Kaggle's two free NVIDIA T4 GPUs.
- Trains with proper-scoring-rule rewards plus soft cross-entropy, then fits one calibration temperature per
  question type.
- Evaluates on the dataset's test split and can push the model to the Hugging Face Hub.

## Where its labels come from

Per the dataset card, each case was labelled by "a teacher endpoint of roughly 4B-class capability". The card
doesn't name the model. It was sampled 3 times at temperature 0.7, and the gold label is the mean of the three
distributions. The card also warns that a score "measures agreement with that teacher. It does not measure correctness."

## How lab 10b differs

| | Laya's notebook | Lab 10b |
|---|---|---|
| Data | a public benchmark (4 business workflows) | travel questions generated in the lab |
| Teacher | an unnamed 4B-class endpoint, 3 samples averaged | Kev-4B on your machine (deterministic, so one sample) |
| Hardware | 2× NVIDIA T4 on Kaggle | one local GPU: Apple Silicon (MPS) or NVIDIA (CUDA) |
| Tested against | the teacher's labels on the test split | lab 10's hand-checked answers, never used in training |
