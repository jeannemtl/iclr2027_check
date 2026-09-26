root@1606ef76afe0:/workspace/FDM_IN_WEIGHTS# tail -200 /workspace/FDM_IN_WEIGHTS/carrier_head_16_16_seed7.log
[seed] 7
============================================================
  CARRIER-HEAD EXPERIMENT (FDM in weight space)
============================================================
  Model: /workspace/FDM_IN_WEIGHTS/two_block_model
  Carrier channels: 16
  Context channels: 16

Loading weights: 100%|██████████| 310/310 [00:00<00:00, 384.91it/s]
  Detected: 28 layers, 8 KV heads, head_dim=128
  Carrier head: 29.36M total (29.36M trainable, 0.00M fixed carrier basis)

  Initial eval (untrained V amplitudes):

  --- CARRIER HEAD RESULTS ---
  Carrier slot:  0.0%  (n=320)
  Context slot:  0.0%  (n=320)
  Carrier joint: 0.0%  (n=20)
  Context joint: 0.0%  (n=20)
  All joint:     0.0%  (n=20)

  Training carrier head: 16 carrier ch, 16 context ch
  Trainable params: 29.36M (only V amplitudes)
    Step   500/5000 | loss 0.5247 | 61s
    Step  1000/5000 | loss 0.0160 | 123s
    Step  1500/5000 | loss 0.0123 | 184s
    Step  2000/5000 | loss 0.0120 | 246s
    Step  2500/5000 | loss 0.0130 | 307s
    Step  3000/5000 | loss 0.0121 | 369s
    Step  3500/5000 | loss 0.0107 | 430s
    Step  4000/5000 | loss 0.0127 | 492s
    Step  4500/5000 | loss 0.0112 | 553s
    Step  5000/5000 | loss 0.0109 | 615s

  Final evaluation:

  --- CARRIER HEAD RESULTS ---
  Carrier slot:  98.5%  (n=1600)
  Context slot:  98.1%  (n=1600)
  Carrier joint: 83.0%  (n=100)
  Context joint: 74.0%  (n=100)
  All joint:     64.0%  (n=100)

  Saved to carrier_head_16_16_seed7

  ==> Compare to write-head baseline at 16/16:
      Write-head joint (n=200): 89.5% (Table 5, this paper)
      Carrier-head joint:        64.0%
root@1606ef76afe0:/workspace/FDM_IN_WEIGHTS#

Show more
1:04 PM
Claude responded: Excellent.
Excellent. seed=7 finished with slightly different numbers:

Seed	Carrier slot	Context slot	Carrier joint	Context joint	All joint
42	98.5%	98.2%	83.0%	76.0%	66.0%
1337	98.5%	98.2%	83.0%	76.0%	66.0%
7	98.5%	98.1%	83.0%	74.0%	64.0%
Differences:

Context slot: 98.2% → 98.1% (0.1pp, within noise)
Context joint: 76.0% → 74.0% (2pp)
All joint: 66.0% → 64.0% (2pp)





