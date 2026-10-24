#!/usr/bin/env python3
"""
Natural-language integrity test: base model vs FDM fine-tuned model.

For each (base, fine-tuned) pair this measures three things and prints
them side by side, so "is NL intact" is answered relative to the base
model rather than in absolute terms:

  1. Held-out perplexity on WikiText-2 (test split, raw). The model never
     saw this text during FDM training. This is the real measurement.
  2. Factual recall on the same ten trivia questions the mixed-domain
     training script uses (substring match, greedy decoding).
  3. Free generation on a handful of open prompts, printed verbatim so
     you can eyeball whether the output is still English or has
     collapsed into FDM-style "NAME=VALUE" text.

Usage (one pair):
  python nl_integrity_eval.py \
      --base Qwen/Qwen3-0.6B-Base \
      --tuned prompterminal/fdm-40ch-fresh-qwen3-model \
      --name qwen3 --out /workspace/nl_eval_results

Usage (all four pairs, via run_nl_eval.sh):
  bash run_nl_eval.sh

Paths may be HF repo ids or local directories (e.g. a snapshot_download
target). Private repos need HF_TOKEN in the environment.
"""

import argparse
import json
import math
import os
import time
import unicodedata

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# ------------------------------------------------------------------ prompts

NL_QUESTIONS = [
    ("What is the capital of France?", "Paris"),
    ("What is the capital of Japan?", "Tokyo"),
    ("What is the capital of Italy?", "Rome"),
    ("What language is spoken in France?", "French"),
    ("What language is spoken in Japan?", "Japanese"),
    ("On what continent is France located?", "Europe"),
    ("What currency is used in France?", "euro"),
    ("What is the capital of Germany?", "Berlin"),
    ("What is the capital of Brazil?", "Brasilia"),
    ("What language is spoken in Germany?", "German"),
]

FREE_PROMPTS = [
    "The history of the Roman Empire begins with",
    "To make a cup of tea, first",
    "Photosynthesis is the process by which plants",
    "Once upon a time, in a small village by the sea,",
    "The main difference between a list and a tuple in Python is",
]


# ------------------------------------------------------------------ helpers

def _norm(s):
    d = unicodedata.normalize("NFKD", s)
    return "".join(c for c in d if not unicodedata.combining(c)).lower()


def pick_dtype(name_or_path):
    # gpt2-medium was trained/saved in fp32 in this repo; everything else bf16.
    if "gpt2" in name_or_path.lower():
        return torch.float32
    return torch.bfloat16


def load(path, dtype, device):
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        path, dtype=dtype, trust_remote_code=True
    ).to(device).eval()
    return tok, model


def load_text(text_file=None):
    if text_file:
        return open(text_file, encoding="utf-8").read()
    from datasets import load_dataset
    ds = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
    # Standard recipe: join every row with a blank line.
    return "\n\n".join(ds["text"])


@torch.no_grad()
def perplexity(model, tok, text, device, max_len, stride, max_tokens):
    enc = tok(text, return_tensors="pt", add_special_tokens=False)
    ids = enc.input_ids
    if max_tokens and ids.shape[1] > max_tokens:
        ids = ids[:, :max_tokens]
    n = ids.shape[1]
    nll_sum = 0.0
    n_scored = 0
    prev_end = 0
    for begin in range(0, n, stride):
        end = min(begin + max_len, n)
        trg_len = end - prev_end  # tokens that get scored in this window
        chunk = ids[:, begin:end].to(device)
        target = chunk.clone()
        target[:, :-trg_len] = -100
        out = model(chunk, labels=target)
        # HF averages over scored tokens; undo that to get a sum.
        scored = (target[:, 1:] != -100).sum().item()
        nll_sum += out.loss.float().item() * scored
        n_scored += scored
        prev_end = end
        if end == n:
            break
    mean_nll = nll_sum / max(n_scored, 1)
    return math.exp(mean_nll), mean_nll, n_scored


@torch.no_grad()
def generate(model, tok, prompt, device, max_new):
    ids = tok(prompt, return_tensors="pt").input_ids.to(device)
    limit = getattr(model.config, "max_position_embeddings", None) or getattr(model.config, "n_positions", None)
    if limit:
        max_new = max(1, min(max_new, limit - ids.shape[1]))
    out = model.generate(
        ids, max_new_tokens=max_new, do_sample=False,
        pad_token_id=tok.pad_token_id,
    )
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()


def trivia(model, tok, device):
    hits = 0
    rows = []
    for q, expect in NL_QUESTIONS:
        resp = generate(model, tok, f"Question: {q}\nAnswer:", device, 30)
        ok = _norm(expect) in _norm(resp)
        hits += ok
        rows.append({"q": q, "expected": expect, "got": resp[:120], "ok": ok})
    return hits, rows


def free_gen(model, tok, device):
    return [{"prompt": p, "got": generate(model, tok, p, device, 60)}
            for p in FREE_PROMPTS]


def run_one(label, path, text, device, args):
    dtype = pick_dtype(path)
    t0 = time.time()
    tok, model = load(path, dtype, device)
    max_len = min(args.max_len, getattr(model.config, "max_position_embeddings", args.max_len) or args.max_len)
    ppl, nll, n_tok = perplexity(model, tok, text, device, max_len, args.stride, args.max_tokens)
    hits, rows = trivia(model, tok, device)
    gens = free_gen(model, tok, device)
    del model
    torch.cuda.empty_cache()
    return {
        "label": label, "path": path, "dtype": str(dtype), "window": max_len,
        "wikitext2_ppl": ppl, "wikitext2_nll": nll, "ppl_tokens": n_tok,
        "trivia_hits": hits, "trivia_total": len(NL_QUESTIONS),
        "trivia": rows, "free_gen": gens,
        "seconds": round(time.time() - t0, 1),
    }


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="HF id or local dir of the untouched base model")
    ap.add_argument("--tuned", required=True, help="HF id or local dir of the FDM fine-tuned model")
    ap.add_argument("--name", required=True, help="short tag for output files, e.g. qwen3")
    ap.add_argument("--out", default="nl_eval_results")
    ap.add_argument("--max-len", type=int, default=1024, help="perplexity window")
    ap.add_argument("--stride", type=int, default=512)
    ap.add_argument("--max-tokens", type=int, default=0,
                    help="cap WikiText tokens for a quick run (0 = full test split)")
    ap.add_argument("--text-file", default=None,
                    help="score perplexity on this local text instead of WikiText-2")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(args.out, exist_ok=True)
    text = load_text(args.text_file)

    results = {}
    for label, path in (("base", args.base), ("tuned", args.tuned)):
        print(f"\n=== [{args.name}] {label}: {path}", flush=True)
        r = run_one(label, path, text, device, args)
        results[label] = r
        print(f"  WikiText-2 ppl : {r['wikitext2_ppl']:.2f}  ({r['ppl_tokens']} tokens, window {r['window']})")
        print(f"  trivia         : {r['trivia_hits']}/{r['trivia_total']}")
        for row in r["trivia"]:
            mark = "ok  " if row["ok"] else "MISS"
            print(f"    {mark} {row['q']}  ->  {row['got']!r}")
        print("  free generation:")
        for g in r["free_gen"]:
            print(f"    > {g['prompt']}\n      {g['got']!r}")
        print(f"  ({r['seconds']}s)", flush=True)

    b, t = results["base"], results["tuned"]
    summary = {
        "name": args.name,
        "base_ppl": b["wikitext2_ppl"], "tuned_ppl": t["wikitext2_ppl"],
        "ppl_ratio": t["wikitext2_ppl"] / b["wikitext2_ppl"],
        "base_trivia": f"{b['trivia_hits']}/{b['trivia_total']}",
        "tuned_trivia": f"{t['trivia_hits']}/{t['trivia_total']}",
    }
    print("\n" + "=" * 64)
    print(f"{args.name:>10} | {'base':>12} | {'tuned':>12} | ratio")
    print(f"{'ppl':>10} | {b['wikitext2_ppl']:>12.2f} | {t['wikitext2_ppl']:>12.2f} | {summary['ppl_ratio']:.2f}x")
    print(f"{'trivia':>10} | {summary['base_trivia']:>12} | {summary['tuned_trivia']:>12} |")
    print("=" * 64)

    with open(os.path.join(args.out, f"{args.name}.json"), "w") as f:
        json.dump({"summary": summary, **results}, f, indent=2)
    with open(os.path.join(args.out, "summary.tsv"), "a") as f:
        f.write(f"{args.name}\t{b['wikitext2_ppl']:.3f}\t{t['wikitext2_ppl']:.3f}\t"
                f"{summary['ppl_ratio']:.3f}\t{summary['base_trivia']}\t{summary['tuned_trivia']}\n")
    print(f"wrote {args.out}/{args.name}.json and appended {args.out}/summary.tsv")


if __name__ == "__main__":
    main()
