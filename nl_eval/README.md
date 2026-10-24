# NL integrity test

Answers "did FDM fine-tuning damage natural language?" by comparing each
`fdm-40ch-fresh-*` model against its untouched base on the same inputs.

| tag | base | fine-tuned |
|---|---|---|
| qwen3 | Qwen/Qwen3-0.6B-Base | prompterminal/fdm-40ch-fresh-qwen3-model |
| lfm2 | LiquidAI/LFM2.5-1.2B-Base | prompterminal/fdm-40ch-fresh-lfm2-model |
| hermes3 | NousResearch/Hermes-3-Llama-3.2-3B | prompterminal/fdm-40ch-fresh-hermes3-model |
| gpt2 | openai-community/gpt2-medium | prompterminal/fdm-40ch-fresh-gpt2-model |

Three measurements per model:

1. **WikiText-2 perplexity** (test split, sliding window). The number that
   matters. Report the tuned/base ratio.
2. **Trivia recall**, the same ten questions the mixed-domain trainer uses.
   Coarse, but comparable to earlier runs.
3. **Free generation** on five open prompts, printed verbatim, so you can
   see whether output is still prose or has collapsed into `NAME=VALUE` text.

## Run on a fresh pod

```bash
apt-get update && apt-get install -y tmux git
git clone <this repo> /workspace/iclr2027_check
export HF_TOKEN=hf_...
tmux new -s nl
bash /workspace/iclr2027_check/nl_eval/run_nl_eval.sh
```

Downloads go to `/workspace/hf_cache` (about 23 GB for all eight models).
Results land in `/workspace/nl_eval_results/`: one `<tag>.json` and
`<tag>.log` per pair, plus `summary.tsv`.

Quick sanity run before the full thing:

```bash
MODELS=qwen3 MAX_TOKENS=20000 bash nl_eval/run_nl_eval.sh
```

Single pair by hand:

```bash
python nl_eval/nl_integrity_eval.py \
  --base Qwen/Qwen3-0.6B-Base \
  --tuned prompterminal/fdm-40ch-fresh-qwen3-model \
  --name qwen3 --out /workspace/nl_eval_results
```

`--text-file` scores perplexity on a local file instead of WikiText-2.

Two-block hosts (qwen3 and hermes3 are on the hub):

```bash
SET=twoblock bash nl_eval/run_nl_eval.sh
```

Any other checkpoint, naming the tag of its base model:

```bash
TUNED=prompterminal/some-repo MODELS=qwen3 bash nl_eval/run_nl_eval.sh
```

Each `SET` writes to its own folder, `/workspace/nl_eval_results_<set>/`.

## Reading the result

A ppl ratio near 1.0 and matching trivia counts means NL is intact.
A ratio of several times, or free generation turning into channel
dumps, means the FDM-only curriculum overwrote it. The `fresh` models
were trained without NL replay, so degradation here is the expected
finding; `fdm-mixed-domain-10ch` is the model trained to avoid it.
