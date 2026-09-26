# Mixed-Domain FDM Training

Prevents catastrophic forgetting of natural language during FDM fine-tuning by interleaving general text (Alpaca) with FDM-encoded data during training. Includes J-space evaluation to test whether both NL and FDM concepts coexist in the same model's workspace.

## Prerequisites

```bash
# Install dependencies
pip install -q -U torch transformers accelerate numpy tqdm scipy huggingface_hub safetensors sentencepiece datasets

# Clone jlens library (needed for J-space eval)
cd /workspace
git clone https://github.com/thomaschlt/global-workspace-repro
cd global-workspace-repro
pip install -r requirements.txt
```

## Full Pipeline

```bash
cd /workspace/fdm_jspace

# 1. Download Alpaca (52K instruction-following samples for NL replay)
python scripts/fdm_mixed_domain_train.py download-alpaca

# 2. Generate FDM training data (5 curriculum stages, same as turbo-v3)
python scripts/fdm_mixed_domain_train.py generate

# 3. Train with mixed-domain (default: 30% NL -> 10% NL across stages)
python scripts/fdm_mixed_domain_train.py train

# 4. Full evaluation: FDM accuracy + NL recall + J-space concept swaps
python scripts/fdm_mixed_domain_train.py all-eval
```

## Individual Commands

| Command | What it does |
|---|---|
| `download-alpaca` | Downloads Alpaca dataset to `general_text.jsonl` |
| `generate` | Generates FDM-encoded training data for all 5 stages |
| `train` | Mixed-domain training with curriculum (decreasing NL ratio) |
| `eval` | FDM channel accuracy + NL question recall (no J-space) |
| `jeval` | J-space evaluation only: Jacobian lens + concept swaps |
| `all-eval` | Runs `eval` then `jeval` |

## Training Options

```bash
# Override NL ratio (e.g. 30% general text throughout all stages)
python scripts/fdm_mixed_domain_train.py train --general-ratio 0.30

# Custom general text dataset (JSONL with {"text": "..."} per line)
python scripts/fdm_mixed_domain_train.py train --general-data /path/to/your_data.jsonl

# Custom token budget per encoder (default 256, total = 512)
python scripts/fdm_mixed_domain_train.py generate --tokens 512
```

## Curriculum Stages

| Stage | a_low | NL ratio | FDM ratio | Samples | Epochs | LR |
|---|---|---|---|---|---|---|
| 0 (Easy) | 0.0 | 30% | 70% | 15K | 5 | 5e-5 |
| 1 (Standard) | 0.1 | 25% | 75% | 20K | 5 | 3e-5 |
| 2 (Moderate) | 0.15 | 20% | 80% | 25K | 7 | 2e-5 |
| 3 (Harder) | 0.2 | 15% | 85% | 25K | 7 | 1e-5 |
| 4 (Hardest) | 0.25 | 10% | 90% | 30K | 10 | 1e-5 |

## J-Space Evaluation

`jeval` fits a Jacobian lens on the trained model and runs two tests:

1. **Plaintext swap** (band 10-19): France->China, Japan->Brazil, Italy->Egypt across capital/language/continent/currency. Tests whether NL concepts survived in J-space.

2. **FDM swap** (band 14-23): PRIORITY HIGH->LOW, REGION NORTH->SOUTH, EAST->WEST. Uses controlled prompts (RULE=SAFETY_FIRST, STATUS=CLEAR, META=NONE) and plain HF tokenizer. Tests whether FDM concepts occupy J-space.

### Possible Outcomes

| NL flips | FDM flips | Meaning |
|---|---|---|
| >0 | >0 | COEXISTENCE CONFIRMED -- both in J-space, mixed-domain worked |
| >0 | 0 | NL preserved, FDM needs different band/alpha |
| 0 | >0 | FDM in J-space, NL lost (same as FDM-only training) |
| 0 | 0 | Neither found, lens may need refitting |

## Success Criteria

- FDM retrieval accuracy: 95-99%+ (target: same as FDM-only, 99.27%)
- NL recall: >0% (model can answer "What is the capital of France?" with "Paris")
- J-space NL swaps: >0/12 flips
- J-space FDM swaps: >0/9 flips
- Best case: both >0 -- coexistence in the same model's workspace

## Output Files

| File | Contents |
|---|---|
| `checkpoints_fdm_mixed_qwen3/stage*_epoch*.pt` | Per-stage checkpoints |
| `fdm_40ch_mixed_qwen3_model_final/` | Final model + tokenizer |
| `jspace_eval_results.json` | J-space swap results (NL + FDM) |
| `lens_jeval.pt` | Fitted Jacobian lens |

## Architecture

Everything identical to turbo-v3:
- Model: Qwen3-0.6B-Base (28 layers, d=1024, vocab=151936)
- FDM encoder: TurboFDMSignalEncoder with S-random interleaver, 40 channels, 512 tokens
- Curriculum: 5 stages, a_low 0.0 -> 0.25
- Reasoning: 3 question types (proceed, risk, share)

New additions:
- GeneralTextDataset: loads Alpaca/Wikipedia JSONL
- MixedDataLoader: interleaves FDM and NL batches at configurable ratio
- mixed_eval: tests both FDM and NL every 2 epochs during training
- jspace_eval: Jacobian lens + concept swap evaluation
