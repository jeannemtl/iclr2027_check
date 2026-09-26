@643212bf0f00:/workspace/FDM_IN_WEIGHTS# # 2. Start tmux session, attached
tmux new -s hermes_sweep

============================================================
  Write head: 62.8M params for 32 channels
    Step  1000/4000 | loss 0.2432 | 151s
    Step  2000/4000 | loss 0.2035 | 302s
    Step  3000/4000 | loss 0.1629 | 452s
    Step  4000/4000 | loss 0.1349 | 603s
Eval:  20%|█▉        | 39/200 [02:55<12:04,  4.50s/it]


  --- SLOT-LEVEL (per-channel mean) ---                
  Block A: 66.8%  (n=6400)
  Block B: 0.0%  (n=0)
  All:     66.8%  (n=6400)
  --- SAMPLE-LEVEL JOINT (honest n) ---
  Block A all-correct: 0.0%  (n=200)
  Block B all-correct: 100.0%  (n=200)
  All-32 all-correct:  0.0%  (n=200)

============================================================
  SWEEP SUMMARY
============================================================
  Param   Ctx   A acc   B acc     All
  ----- ----- ------- ------- -------
      0    32    0.0%  100.0%  100.0%
      4    28  100.0%  100.0%  100.0%
      8    24  100.0%  100.0%  100.0%
     12    20  100.0%  100.0%  100.0%
     16    16  100.0%  100.0%  100.0%
     20    12  100.0%  100.0%  100.0%
     24     8  100.0%  100.0%  100.0%
     28     4  100.0%  100.0%  100.0%
     32     0   66.8%    0.0%   66.8%

  Saved to /workspace/FDM_IN_WEIGHTS/split_ratio_sweep_hermes3_3seed/seed_42/sweep_results.json
===== seed=42 completed at Mon May  4 13:26:34 UTC 2026 =====

===== seed=1337 started at Mon May  4 13:26:34 UTC 2026 =====
[seed] Random seed set to 1337
============================================================
  SPLIT-RATIO SWEEP
============================================================
Loading weights: 100%|██████████| 254/254 [00:00<00:00, 9331.21it/s]

============================================================
  SPLIT: 0 parametric / 32 context
  Block A (parametric): channels []
  Block B (context):    channels [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
============================================================
  No write head needed - evaluating context-only...
Eval:   0%|          | 0/200 [00:00<?, ?it/s][transformers] Ignoring clean_up_tokenization_spaces=True for BPE tokenizer TokenizersBackend. The clean_up_tokenization post-processing step is designed for WordPiece tokenizers and is destructive for BPE (it strips spaces before punctuation). Set clean_up_tokenization_spaces=False to suppress this warning, or set clean_up_tokenization_spaces_for_bpe_even_though_it_will_corrupt_output=True to force cleanup anyway.
Eval:   2%|▏         | 3/200 [00:14<15:06,  4.60s/it]
[hermes_sw0:bash*                                                          "643212bf0f00" 13:26 04-May-26
