"""
Find the encoder / prompt settings a two-block FDM host was trained with.

Runs the host (no prefix, no training) on a small grid of encoder settings and prompt
formats and reports slot accuracy for each. Use it when the stage-4 sanity gate of
startup.sh fails, before touching the sweep.

    PYTHONPATH=/workspace/<WORK>/FDM_PARAMETRIC python diag_encoder_match.py \
        --model /workspace/<WORK>/FDM_IN_WEIGHTS/two_block_lfm25/phase2_final --n 6

Grid (override with the flags):
  --vocabs 65536,64402      token_map = rng.choice(vocab_size, 64): must match training
  --a_lows 0.25,0.0         low carrier amplitude: 0.25 for Qwen3/Hermes3, 0.0 in the
                            repo's LFM2.5 single-substrate pipeline
  --formats B_only,A_and_B  B_only  = "[MEMORY]BLOCK_B <fdm>[/MEMORY]"  (what the sweep uses)
                            A_and_B = "[MEMORY]BLOCK_A <fdm>[/MEMORY][MEMORY]BLOCK_B <fdm>[/MEMORY]"
                                      (what eval_two_block_n200_lfm2.py used)
                            bare    = "[MEMORY]<fdm>[/MEMORY]"  (single-substrate format, same question)
                            bare_hop = single-substrate format with a hop question
                                      ("What is the risk assessment?"); the host answers with its
                                      assessment and then "Context: TEAM=.., ..., COMMS=..", which
                                      is what the 40ch single-block hosts were trained to emit
  --n 6                     memories per setting

Typical calls:
  two-block host   : --vocabs 65536,64402 --a_lows 0.25,0.0 --formats B_only,A_and_B
  single-block host: --vocabs 65536       --a_lows 0.25,0.0 --formats bare_hop
"""
import sys, re, random, argparse, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, '.')
from split_ratio_sweep_disjoint_hybrid import (make_encoder, random_memory, hit, HostArch,
                                               CHANNEL_NAMES, ALL_QUERY_CHANNELS)


def build(fmt, fdm_text):
    q = f"Report values for: {', '.join(CHANNEL_NAMES[k] for k in ALL_QUERY_CHANNELS)}."
    tail = f"\nQuestion: {q}\nAnswer:"
    if fmt == "B_only":
        return f"[MEMORY]BLOCK_B {fdm_text}[/MEMORY]{tail}"
    if fmt == "A_and_B":
        return f"[MEMORY]BLOCK_A {fdm_text}[/MEMORY][MEMORY]BLOCK_B {fdm_text}[/MEMORY]{tail}"
    if fmt == "bare":
        return f"[MEMORY]{fdm_text}[/MEMORY]{tail}"
    if fmt == "bare_hop":
        return f"[MEMORY]{fdm_text}[/MEMORY]\nQuestion: What is the risk assessment?\nAnswer:"
    raise ValueError(fmt)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--vocabs", default="65536,64402")
    p.add_argument("--a_lows", default="0.25,0.0")
    p.add_argument("--formats", default="B_only,A_and_B")
    p.add_argument("--max_new_tokens", type=int, default=350)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True,
                                                 dtype=torch.bfloat16).to(device).eval()
    print(f"[host] {HostArch(model.config).describe()}")
    try:
        added = sorted(t for t in tok.get_added_vocab() if "MEMORY" in t or "BLOCK" in t)
    except Exception:
        added = "n/a"
    print(f"[tokenizer] len={len(tok)} config.vocab_size={model.config.vocab_size} "
          f"eos={tok.eos_token!r} memory-related added tokens={added}")
    mem_ids = tok.encode("[MEMORY]BLOCK_B x[/MEMORY]", add_special_tokens=False)
    print(f"[tokenizer] '[MEMORY]BLOCK_B x[/MEMORY]' -> {len(mem_ids)} tokens: {tok.convert_ids_to_tokens(mem_ids)[:8]}")

    rows = []
    for vocab in [int(v) for v in args.vocabs.split(",")]:
        for a_low in [float(a) for a in args.a_lows.split(",")]:
            enc = make_encoder(tok, vocab, a_low=a_low)
            for fmt in args.formats.split(","):
                random.seed(args.seed); torch.manual_seed(args.seed)
                correct = total = 0
                first = None
                t0 = time.time()
                for _ in range(args.n):
                    mem = random_memory()
                    fdm_text, _ = enc.encode_memory(mem)
                    ids = tok.encode(build(fmt, fdm_text), return_tensors="pt").to(device)
                    with torch.no_grad():
                        out = model.generate(ids, max_new_tokens=args.max_new_tokens, do_sample=False,
                                             pad_token_id=tok.eos_token_id)
                    ans = tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
                    if first is None:
                        first = ans[:160].replace("\n", " ")
                    for k in ALL_QUERY_CHANNELS:
                        correct += hit(ans, k, mem); total += 1
                acc = correct / total
                rows.append((acc, vocab, a_low, fmt))
                print(f"  vocab={vocab:6d} a_low={a_low:<4} fmt={fmt:8s} | slot acc {acc*100:5.1f}%  "
                      f"({time.time()-t0:.0f}s)  first answer: {first!r}")

    print("\n" + "=" * 72)
    best = max(rows)
    print(f"best: vocab={best[1]} a_low={best[2]} fmt={best[3]} -> {best[0]*100:.1f}% slot accuracy")
    if best[0] < 0.9:
        print("No setting reaches 90%. The host was trained with an encoder or prompt this grid does not\n"
              "cover (num_tokens, sample_rate, num_levels, seed, or the question wording). Find the\n"
              "two-block LFM2.5 training script before running the sweep.")
    else:
        print("For startup.sh:  VOCAB_OVERRIDE=%d A_LOW=%s" % (best[1], best[2]),
              "" if best[3] == "B_only" else f"   (NOTE: host needs prompt format '{best[3]}'; the sweep needs a --prompt_style for it)")
    weak = [k for k in ALL_QUERY_CHANNELS]  # per-channel readout for the best setting is in the sweep's sanity JSON


if __name__ == "__main__":
    main()
