export PYTHONPATH=/workspace/FDM_PARAMETRIC:$PYTHONPATH
python patch_nhop_source.py /workspace/FDM_PARAMETRIC/nhop_source.py

# find the Qwen vocab_size the checkpoint used
grep -rn "TurboFDMSignalEncoder(" /workspace/FDM_PARAMETRIC --include=*.py -A2 | grep -i vocab

# 1. host still decodes at 513 with all carriers (expect ~99%)
python split_ratio_sweep_disjoint.py --model /workspace/FDM_IN_WEIGHTS/two_block_qwen3 \
  --output_dir /workspace/FDM_IN_WEIGHTS/disjoint_qwen3 --vocab_size <N> --splits 0 --n_eval 50

# 2. shift test: masked block, no prefix, no training (~5 min)
python split_ratio_sweep_disjoint.py --model ... --output_dir ... --vocab_size <N> \
  --ctx_only_masked --splits 4,8,16 --n_eval 100
