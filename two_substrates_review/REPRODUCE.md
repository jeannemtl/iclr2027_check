# Reproducing the disjoint two-substrate sweeps

Every run below is one invocation of `startup.sh` from this directory on a single GPU
(all reported numbers came from an NVIDIA L40, 46 GB). The script installs dependencies,
clones and patches the encoder, downloads the host from HuggingFace, runs the sanity gate,
the masked baseline, the sweep, prints the summary and uploads results.

## One-time setup on a fresh pod

```bash
# SSH key for GitHub (add the printed line at https://github.com/settings/ssh/new)
ssh-keygen -t ed25519 -C "pod" -f ~/.ssh/id_ed25519 -N "" && cat ~/.ssh/id_ed25519.pub
ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null
ssh -T git@github.com                     # must greet you by name before continuing
git config --global url."git@github.com:".insteadOf "https://github.com/"
git config --global user.name "jeannemtl"
git config --global user.email "quaintanceai@gmail.com"

cd /workspace
git clone git@github.com:jeannemtl/iclr2027_check.git
cd iclr2027_check && git checkout claude/youthful-planck-zbnbm2
cd two_substrates_review

export HF_TOKEN=hf_...                    # a token with read access to the private host repos
                                          # (write access if UPLOAD=1, the default)
tmux new -s fdm                           # run every sweep inside tmux
```

Inside tmux, `export HF_TOKEN=hf_...` again (environment is per shell), then run one of the
commands below. Detach with `Ctrl-b d`, reattach with `tmux attach -t fdm`.

## 1. Qwen3 (two-block host, 28 attention layers, 513-position prefix)

The numbers in the summary (3 seeds, n = 200, splits 4/8/16):

```bash
MODEL=qwen3 SEEDS="1 2 3" SPLITS="4 8 16" N_EVAL=200 SKIP_DONE=0 \
  WORK=/workspace/clean_qwen3 bash startup.sh
```

Results: `results/qwen3_clean/` (committed on `main`). Roughly 11 GPU hours.

## 2. Hermes3 (two-block host, 28 attention layers, 513-position prefix)

The numbers in the summary came from the script defaults (1 seed, n = 100, splits 4/8),
i.e. this call:

```bash
MODEL=hermes3 WORK=/workspace bash startup.sh
```

Results: `results/hermes3/`. To put Hermes3 on the same footing as the other hosts
(3 seeds, n = 200, splits 4/8/16; about 13 GPU hours):

```bash
MODEL=hermes3 SEEDS="1 2 3" SPLITS="4 8 16" N_EVAL=200 SKIP_DONE=0 \
  WORK=/workspace/clean_hermes3 bash startup.sh
```

## 3. LFM2.5-1.2B (hybrid host: 6 attention + 10 conv layers, 513-position prefix)

Host: `prompterminal/fdm-40ch-fresh-lfm2-model` (40-channel single-block host, prompt
style `bare_hop`, vocab 65536, a_low 0.25). The checkpoint named
`fdm-twoblock-lfm2.5-1.2b` is a 10-channel model and cannot be used.

Optional: confirm the encoder/prompt settings on the host first (about 2 minutes):

```bash
python - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download("prompterminal/fdm-40ch-fresh-lfm2-model",
                  local_dir="/workspace/clean_lfm25/FDM_IN_WEIGHTS/two_block_lfm25")
EOF
PYTHONPATH=/workspace/clean_lfm25/FDM_PARAMETRIC python diag_encoder_match.py \
  --model /workspace/clean_lfm25/FDM_IN_WEIGHTS/two_block_lfm25 --n 6 \
  --vocabs 65536 --a_lows 0.25,0.0 --formats bare_hop,B_only
```
(`FDM_PARAMETRIC` is cloned and patched by stage 2 of `startup.sh`; run any sweep once, or
clone it yourself and run `python patch_nhop_source.py <path>/nhop_source.py`.)

### 3a. Main sweep, Context-only loss (the "assessment masked" rows)

When this was run the Context-only recipe was the default; it is now the ablation, so
`LABEL_ASSESSMENT=0` must be passed explicitly to reproduce it:

```bash
MODEL=lfm25 SEEDS="1 2 3" SPLITS="4 8 16" N_EVAL=200 SKIP_DONE=0 LABEL_ASSESSMENT=0 \
  WORK=/workspace/clean_lfm25 bash startup.sh
```

Results: `results/lfm25_clean/`. About 12 GPU hours.

### 3b. 16/16 rerun with the assessment tokens in the loss (the reported 16/16 row)

```bash
MODEL=lfm25 SEEDS="1 2 3" SPLITS="16" N_EVAL=200 SKIP_DONE=0 \
  RUN_SANITY=0 RUN_MASKED=0 LABEL_ASSESSMENT=1 OUT_TAG=la16 \
  WORK=/workspace/clean_lfm25 bash startup.sh
```

Results: `results/lfm25_clean_la16/`. About 4.5 GPU hours. `LABEL_ASSESSMENT=1` is now the
default for bare_hop hosts, so a full LFM2.5 sweep with the anchored recipe is simply:

```bash
MODEL=lfm25 SEEDS="1 2 3" SPLITS="4 8 16" N_EVAL=200 SKIP_DONE=0 \
  WORK=/workspace/clean_lfm25_la bash startup.sh
```

## 4. GPT-2-medium (24 attention layers, 1024 absolute positions, auto-sized prefix)

Host: `prompterminal/fdm-40ch-fresh-gpt2-model` (prompt style `bare_hop`, vocab 50257,
a_low 0.25). The prefix cannot be 513 positions under the 1024 limit; `N_KV_POSITIONS=auto`
(the default for gpt2) measures the longest training sequence and picks the largest prefix
that fits. The chosen length is printed as `[prefix] auto -> N positions` and stored in
the results JSON.

```bash
MODEL=gpt2 SEEDS="1 2 3" SPLITS="4 8 16" N_EVAL=200 SKIP_DONE=0 \
  WORK=/workspace/clean_gpt2 bash startup.sh
```

Results land in `/workspace/clean_gpt2/FDM_IN_WEIGHTS/two_substrates_review/gpt2/`.
To force a specific prefix length (e.g. to match another host): `N_KV_POSITIONS_OVERRIDE=128`.

## Committing results

```bash
cd /workspace/iclr2027_check/two_substrates_review
SRC=/workspace/clean_<model>/FDM_IN_WEIGHTS/two_substrates_review/<model>   # e.g. clean_gpt2 / gpt2
mkdir -p results/<model>_clean
cp -r $SRC/{seed1,seed2,seed3,masked,sanity} results/<model>_clean/
cp $SRC/run.log results/<model>_clean/run.log
find results/<model>_clean -name "*.pt" -delete       # heads live on HF, not in git
git add results/<model>_clean && git commit -m "Add <model> disjoint sweep (3 seeds, n=200, splits 4/8/16)"
git push origin claude/youthful-planck-zbnbm2
```

Write heads are uploaded by stage 8 to `prompterminal/fdm-two-substrates-heads` (model repo)
and the JSONs to `prompterminal/fdm-two-substrates-review` (dataset repo), under
`<model>` or `<model>_<OUT_TAG>`.

## Environment variables of `startup.sh`

| Variable | Default | Meaning |
|---|---|---|
| `MODEL` | qwen3 | qwen3, hermes3, lfm25, gpt2 |
| `SEEDS` | "1" | write-head seeds |
| `SPLITS` | "4 8" | prefix-only channel counts (Block A size) |
| `N_EVAL` | 100 | memories per evaluation (200 for reported numbers) |
| `STEPS_4`, `STEPS_8PLUS` | 5000, 15000 | write-head steps for split 4 / splits >= 8 |
| `PARTITION` | interleaved | or contiguous |
| `SKIP_DONE` | 1 | set 0 for a clean run (otherwise existing JSONs are reused) |
| `RUN_SANITY`, `RUN_MASKED`, `RUN_TRAIN`, `UPLOAD` | 1 | stage switches |
| `WORK` | /workspace | root for host, encoder and outputs |
| `OUT_TAG` | (none) | suffix for the output dir and HF path, keeps reruns separate |
| `LABEL_ASSESSMENT` | 1 | bare_hop hosts: assessment tokens in the loss (0 = Context-only ablation) |
| `N_KV_POSITIONS_OVERRIDE` | (per model) | prefix length for the hybrid script |
| `VOCAB_OVERRIDE`, `A_LOW` | (per model), 0.25 | encoder overrides for the hybrid script |
| `SANITY_MIN` | 0.95 | stage-4 gate on Block B slot accuracy |
| `DRY_RUN` | 0 | print the commands instead of running |
