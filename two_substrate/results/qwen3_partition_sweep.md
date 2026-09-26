root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# 
root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# 
root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# 
root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# 
root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# # Switch to 4K steps
sed -i 's/--n_steps 5000/--n_steps 4000/' /workspace/FDM_IN_WEIGHTS/run_5seed_sweep.sh
grep "n_steps" /workspace/FDM_IN_WEIGHTS/run_5seed_sweep.sh

# Verify tmux installed
which tmux || apt-get install -y tmux

# Start tmux session
tmux new -s sweep

# Inside tmux:
cd /workspace/FDM_IN_WEIGHTS
bash run_5seed_sweep.sh
        --n_steps 4000 \
/usr/bin/tmux

  Block B: 0.0%  (n=0)
  All:     46.2%  (n=6400)
  --- SAMPLE-LEVEL JOINT (honest n) ---
  Block A all-correct: 0.0%  (n=200)
  Block B all-correct: 100.0%  (n=200)
  All-32 all-correct:  0.0%  (n=200)

============================================================
  SWEEP SUMMARY
============================================================
  Param   Ctx   A acc   B acc     All
  ----- ----- ------- ------- -------
      0    32    0.0%   99.3%   99.3%
      4    28   99.5%   99.6%   99.6%
      8    24   99.8%   99.3%   99.4%
     12    20   99.3%   99.5%   99.4%
     16    16   99.6%   99.4%   99.5%
     20    12   99.7%   99.7%   99.7%
     24     8   99.6%   99.2%   99.5%
     28     4   99.7%   99.1%   99.6%
     32     0   46.2%    0.0%   46.2%

  Saved to /workspace/FDM_IN_WEIGHTS/split_ratio_sweep_5seed/seed_7777/sweep_results.json
===== seed=7777 completed at Mon May  4 03:55:22 UTC 2026 =====

===== ALL DONE at Mon May  4 03:55:22 UTC 2026 =====
root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# 
root@c1d4bda933c9:/workspace/FDM_IN_WEIGHTS# 
root@c1d4bda933c9:/workspace/FDM_IN_WE
