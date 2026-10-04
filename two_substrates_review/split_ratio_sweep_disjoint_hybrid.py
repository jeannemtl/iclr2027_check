"""
Split-Ratio Sweep, DISJOINT version, for HYBRID hosts (LFM2 / LFM2.5).
=======================================================================

Same experiment as split_ratio_sweep_disjoint.py (Block A channels are absent
from the context and recoverable only from a write-head K/V prefix; shuffled-
prefix control; exact leak check), generalised to hosts whose layers are not
all attention.

What is different from the attention-only script:
  - Architecture is read from the host config: number of layers, which layers
    are `full_attention` (config.layer_types), KV heads and head_dim. Nothing
    is hard-coded to 28 layers / 8 KV heads / head_dim 128.
  - The write head emits K/V ONLY for the attention layers. Conv layers have
    no K/V cache; they see the real tokens from position 513 onward with an
    empty conv state, as if the prefix did not exist. The prefix therefore
    reaches the answer only through the attention layers.
  - The cache is `DynamicCache(config=model.config)`, which builds a
    DynamicLayer per attention layer and a LinearAttentionLayer per conv layer
    (transformers >= 5.x). Only attention layers are pre-filled.
  - n_steps, lr and the architecture are written into the results JSON.

For LFM2.5-1.2B: 16 layers, attention at [2, 5, 8, 10, 12, 14], 8 KV heads,
head_dim 64. The head's output is 6*2*8*64 = 6144 floats per position, versus
57344 for the 28-layer hosts, so the head is smaller (about 32M params).

Works unchanged on an all-attention host (no `layer_types` in the config means
every layer is attention), but the validated record for Qwen3 and Hermes3 is
the original script; use this one for hybrids.

Positions: write-head prefix at [0, 512], FDM block at 513+.
"""

import sys, os, re, json, random, time, argparse, inspect
import numpy as np
import torch
import torch.nn as nn
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.cache_utils import DynamicCache

sys.path.insert(0, '/root/FDM_IN_WEIGHTS/scripts')
sys.path.insert(0, '/root/FDM_IN_WEIGHTS')

from nhop_source import TurboFDMSignalEncoder, MEMORY_SCHEMAS, NUM_CHANNELS

CHANNEL_NAMES = [MEMORY_SCHEMAS[i][0] for i in range(NUM_CHANNELS)]
ALL_QUERY_CHANNELS = list(range(8, 40))  # 32 channels total

SAMPLE_RATE = 100.0
N_SAMPLES = 256
N_KV_POSITIONS = 513


# ----------------------------------------------------------------------------
# Host architecture
# ----------------------------------------------------------------------------

class HostArch:
    """Layer layout of the host, read from its config."""

    def __init__(self, config):
        self.config = config
        self.n_layers = config.num_hidden_layers
        layer_types = getattr(config, "layer_types", None)
        if layer_types is None:
            layer_types = ["full_attention"] * self.n_layers
        self.layer_types = list(layer_types)
        self.attn_layers = [i for i, t in enumerate(self.layer_types) if t == "full_attention"]
        if not self.attn_layers:
            raise RuntimeError("host has no full_attention layers; a K/V prefix cannot be injected")
        self.n_kv_heads = config.num_key_value_heads
        self.head_dim = getattr(config, "head_dim", None) or config.hidden_size // config.num_attention_heads

    def describe(self):
        n_conv = self.n_layers - len(self.attn_layers)
        return (f"{self.n_layers} layers ({len(self.attn_layers)} attention at {self.attn_layers}, "
                f"{n_conv} other), kv_heads={self.n_kv_heads}, head_dim={self.head_dim}")

    def to_json(self):
        return {"n_layers": self.n_layers, "layer_types": self.layer_types, "attn_layers": self.attn_layers,
                "n_kv_heads": self.n_kv_heads, "head_dim": self.head_dim,
                "model_type": getattr(self.config, "model_type", None)}


def layer_kvs_to_cache(layer_kvs, arch):
    """
    Build the host's cache with the prefix written into the attention layers only.
    layer_kvs: {layer_idx: (k, v)} with k, v of shape [B, P, n_kv_heads, head_dim].
    Conv / linear-attention layers are left uninitialised; the host fills them from
    the real tokens on its first forward.
    """
    cache = DynamicCache(config=arch.config)
    for l in arch.attn_layers:
        k, v = layer_kvs[l]
        cache.update(k.transpose(1, 2).contiguous(), v.transpose(1, 2).contiguous(), l)
    return cache


# ----------------------------------------------------------------------------
# Encoder helpers (unchanged)
# ----------------------------------------------------------------------------

def make_encoder(tokenizer, vocab_size, a_low=0.25):
    """a_low must match the host's training encoder: 0.25 for the Qwen3/Hermes3 two-block
    hosts; the repo's LFM2.5 single-substrate pipeline used 0.0."""
    return TurboFDMSignalEncoder(
        vocab_size=vocab_size, tokenizer=tokenizer,
        num_tokens_per_encoder=N_SAMPLES, sample_rate=SAMPLE_RATE,
        a_high=1.0, a_low=a_low, num_levels=64, seed=42,
    )


def random_memory():
    return {ch: random.choice(MEMORY_SCHEMAS[ch][1]) for ch in range(NUM_CHANNELS)}


def encode_masked(encoder, memory, active_channels):
    active = sorted(set(active_channels))
    if 'active_channels' not in inspect.signature(encoder.encode_memory).parameters:
        raise RuntimeError(
            "encode_memory has no `active_channels` argument. Run:\n"
            "    python patch_nhop_source.py /workspace/FDM_PARAMETRIC/nhop_source.py")
    out = encoder.encode_memory(memory, active_channels=active)
    return out[0], out[1]


def leak_check(encoder, block_a, block_b, n_trials=30):
    print("\n[leak check] Block A values must not affect the context tokens")
    active = context_channels(block_b)
    masked = sorted(set(range(NUM_CHANNELS)) - set(active))
    assert masked == sorted(block_a), f"masked channels {masked} != block A {sorted(block_a)}"
    for _ in range(n_trials):
        m1 = random_memory()
        m2 = dict(m1)
        for ch in masked:
            alts = [v for v in MEMORY_SCHEMAS[ch][1] if v != m1[ch]]
            if alts:
                m2[ch] = random.choice(alts)
        if encode_masked(encoder, m1, active)[1] != encode_masked(encoder, m2, active)[1]:
            raise RuntimeError("LEAK: changing only Block A values changed the context tokens.")
    print(f"  OK: {n_trials}/{n_trials} trials identical when only Block A differs.")

    changed = 0
    for _ in range(n_trials):
        m1 = random_memory()
        m2 = dict(m1)
        ch = random.choice(list(block_b))
        m2[ch] = random.choice([v for v in MEMORY_SCHEMAS[ch][1] if v != m1[ch]])
        changed += encode_masked(encoder, m1, active)[1] != encode_masked(encoder, m2, active)[1]
    print(f"  positive control: changing one Block B value altered tokens in {changed}/{n_trials} trials")
    if changed < 0.9 * n_trials:
        raise RuntimeError("Block B values do not reliably change the tokens; check the encoder patch.")


def chance_level(channels):
    if not channels:
        return 0.0
    return float(np.mean([1.0 / len(MEMORY_SCHEMAS[k][1]) for k in channels]))


# ----------------------------------------------------------------------------
# Write head: emits K/V for the attention layers only
# ----------------------------------------------------------------------------

class CrossAttentionWriteHead(nn.Module):
    def __init__(self, n_channels, arch, n_values=64, embed_dim=384, n_kv_positions=N_KV_POSITIONS):
        super().__init__()
        self.attn_layers = list(arch.attn_layers)
        self.n_kv_positions = n_kv_positions
        self.kv_dim = arch.head_dim
        self.n_kv_heads = arch.n_kv_heads
        self.n_channels = n_channels
        self.channel_embed = nn.Embedding(n_channels, embed_dim)
        self.value_embed = nn.Embedding(n_values + 1, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=6, dim_feedforward=1024, dropout=0.1, batch_first=True)
        self.refiner = nn.TransformerEncoder(encoder_layer, num_layers=2)
        self.pos_embed = nn.Parameter(torch.randn(n_kv_positions, embed_dim) * 0.02)
        self.cross_attn = nn.MultiheadAttention(embed_dim=embed_dim, num_heads=4, batch_first=True)
        n_out_layers = len(self.attn_layers)
        total_kv_dim = n_out_layers * 2 * self.n_kv_heads * self.kv_dim
        self.kv_proj = nn.Sequential(nn.Linear(embed_dim, 1024), nn.GELU(), nn.Linear(1024, total_kv_dim))

    def forward(self, channel_ids, value_ids):
        B = channel_ids.shape[0]
        x = self.refiner(self.channel_embed(channel_ids) + self.value_embed(value_ids))
        pos = self.pos_embed.unsqueeze(0).expand(B, -1, -1)
        attended, _ = self.cross_attn(pos, x, x)
        kv_raw = self.kv_proj(attended).view(B, self.n_kv_positions, len(self.attn_layers), 2,
                                             self.n_kv_heads, self.kv_dim)
        return {l: (kv_raw[:, :, j, 0], kv_raw[:, :, j, 1]) for j, l in enumerate(self.attn_layers)}


def head_inputs(memory, block_a, device):
    ch_ids = torch.tensor([list(range(len(block_a)))], device=device)
    val_ids = torch.tensor([[MEMORY_SCHEMAS[c][1].index(memory[c]) for c in block_a]], device=device)
    return ch_ids, val_ids


# ----------------------------------------------------------------------------
# Prompt building and generation
# ----------------------------------------------------------------------------

def context_channels(block_b):
    return list(range(0, 8)) + list(block_b)


def build_prompt(encoder, memory, block_b):
    if block_b:
        fdm_text, _ = encode_masked(encoder, memory, context_channels(block_b))
        memory_part = f"[MEMORY]BLOCK_B {fdm_text}[/MEMORY]"
    else:
        memory_part = ""
    ch_names = [CHANNEL_NAMES[k] for k in ALL_QUERY_CHANNELS]
    question = f"Report values for: {', '.join(ch_names)}."
    return memory_part, f"\nQuestion: {question}\nAnswer:"


def generate_with_split(model, tokenizer, write_head, memory, encoder, device, arch,
                        block_a, block_b, prefix_memory=None, max_new_tokens=350):
    if block_a and write_head is not None:
        src = prefix_memory if prefix_memory is not None else memory
        ch_ids, val_ids = head_inputs(src, block_a, device)
        with torch.no_grad():
            past_kv = layer_kvs_to_cache(write_head(ch_ids, val_ids), arch)
        n_kv_pos = write_head.n_kv_positions
    else:
        past_kv, n_kv_pos = None, 0

    memory_part, q_text = build_prompt(encoder, memory, block_b)
    input_ids = tokenizer.encode(memory_part + q_text, return_tensors='pt').to(device)
    seq_len = input_ids.shape[1]
    cur_pos = torch.arange(n_kv_pos, n_kv_pos + seq_len, device=device).unsqueeze(0)

    generated, cur_past = input_ids, past_kv
    for _ in range(max_new_tokens):
        with torch.no_grad():
            if cur_past is not None and generated.shape[1] > input_ids.shape[1]:
                last_pos = cur_pos[:, -1:] + 1
                outputs = model(input_ids=generated[:, -1:], position_ids=last_pos,
                                past_key_values=cur_past, use_cache=True)
                cur_pos = last_pos
            else:
                kwargs = dict(input_ids=generated, position_ids=cur_pos, use_cache=True)
                if cur_past is not None:
                    kwargs['past_key_values'] = cur_past
                outputs = model(**kwargs)
            cur_past = outputs.past_key_values
            nxt = outputs.logits[:, -1, :].argmax(dim=-1, keepdim=True)
            generated = torch.cat([generated, nxt], dim=1)
            if nxt.item() == tokenizer.eos_token_id:
                break
    return tokenizer.decode(generated[0][input_ids.shape[1]:], skip_special_tokens=True)


def hit(answer, k, mem):
    """Score the FIRST occurrence of NAME= only (see the attention-only script)."""
    m = re.search(r"\b" + re.escape(CHANNEL_NAMES[k]) + r"=", answer)
    if m is None:
        return False
    return re.compile(re.escape(mem[k]) + r"\b").match(answer, m.end()) is not None


def evaluate(model, tokenizer, write_head, encoder, device, arch, block_a, block_b,
             n_eval, control=False, desc="Eval"):
    a_c = a_t = b_c = b_t = all_c = all_t = 0
    a_all = b_all = all_all = 0
    per = {"a": [], "b": [], "all": []}
    pc_a = {k: 0 for k in block_a}
    pc_b = {k: 0 for k in block_b}
    n_rep = 0
    samples = []
    for _ in tqdm(range(n_eval), desc=desc, leave=False):
        mem = random_memory()
        pm = random_memory() if control else None
        ans = generate_with_split(model, tokenizer, write_head, mem, encoder, device, arch,
                                  block_a, block_b, prefix_memory=pm)
        ha = [hit(ans, k, mem) for k in block_a]
        hb = [hit(ans, k, mem) for k in block_b]
        for k, h in zip(block_a, ha): pc_a[k] += int(h)
        for k, h in zip(block_b, hb): pc_b[k] += int(h)
        if any(len(re.findall(r"\b" + re.escape(CHANNEL_NAMES[k]) + r"=", ans)) > 1
               for k in ALL_QUERY_CHANNELS):
            n_rep += 1
        if len(samples) < 3:
            samples.append(ans[:700])
        a_c += sum(ha); a_t += len(ha)
        b_c += sum(hb); b_t += len(hb)
        all_c += sum(ha) + sum(hb); all_t += len(ha) + len(hb)
        fa, fb = all(ha) if ha else True, all(hb) if hb else True
        a_all += fa; b_all += fb; all_all += (fa and fb)
        per["a"].append(bool(fa)); per["b"].append(bool(fb)); per["all"].append(bool(fa and fb))
    n = n_eval
    return {
        "block_a_acc_slot": a_c / a_t if a_t else 0.0,
        "block_b_acc_slot": b_c / b_t if b_t else 0.0,
        "all_acc_slot": all_c / all_t if all_t else 0.0,
        "block_a_acc_joint": a_all / n, "block_b_acc_joint": b_all / n, "all_acc_joint": all_all / n,
        "block_a_slot_correct": a_c, "block_a_slot_total": a_t,
        "block_b_slot_correct": b_c, "block_b_slot_total": b_t,
        "n_samples": n,
        "per_channel_a_acc": {str(k): pc_a[k] / n for k in block_a},
        "per_channel_b_acc": {str(k): pc_b[k] / n for k in block_b},
        "frac_answers_with_repeated_names": n_rep / n,
        "sample_answers": samples,
        "per_sample_block_a_all": per["a"], "per_sample_block_b_all": per["b"], "per_sample_all32_all": per["all"],
    }


def print_eval(tag, r, block_a, block_b):
    print(f"  [{tag}] SLOT   A {r['block_a_acc_slot']*100:6.1f}%  B {r['block_b_acc_slot']*100:6.1f}%  "
          f"All {r['all_acc_slot']*100:6.1f}%   (chance A {chance_level(block_a)*100:.1f}%, "
          f"chance B {chance_level(block_b)*100:.1f}%)")
    print(f"  [{tag}] JOINT  A {r['block_a_acc_joint']*100:6.1f}%  B {r['block_b_acc_joint']*100:6.1f}%  "
          f"All-32 {r['all_acc_joint']*100:6.1f}%   (n={r['n_samples']})")
    if r.get("per_channel_a_acc"):
        pa = "  ".join(f"ch{k}:{v*100:.0f}" for k, v in r["per_channel_a_acc"].items())
        print(f"  [{tag}] per-channel A %: {pa}")
    if "frac_answers_with_repeated_names" in r:
        print(f"  [{tag}] answers repeating a channel name: {r['frac_answers_with_repeated_names']*100:.0f}%")


# ----------------------------------------------------------------------------
# Train + eval one partition
# ----------------------------------------------------------------------------

def train_and_eval_split(model, tokenizer, encoder, device, arch, block_a, block_b,
                         n_steps=5000, lr=3e-4, n_eval=200, max_len=1536, run_control=True,
                         save_dir=None, seed=0):
    n_param, n_ctx = len(block_a), len(block_b)
    print(f"\n{'='*60}\n  SPLIT: {n_param} parametric / {n_ctx} context (DISJOINT, hybrid host)")
    print(f"  Block A (prefix only): {block_a}\n  Block B (context only): {block_b}")
    print(f"  Prefix written into attention layers {arch.attn_layers} only\n{'='*60}")

    if n_param == 0:
        print("  No write head; context-only evaluation.")
        r = evaluate(model, tokenizer, None, encoder, device, arch, block_a, block_b, n_eval)
        print_eval("ctx-only", r, block_a, block_b)
        r.update({"n_param": 0, "n_ctx": n_ctx})
        return r

    write_head = CrossAttentionWriteHead(n_channels=n_param, arch=arch).to(device)
    print(f"  Write head: {sum(p.numel() for p in write_head.parameters())/1e6:.1f}M params")

    write_head.train()
    opt = torch.optim.AdamW(write_head.parameters(), lr=lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=n_steps, eta_min=lr / 20)
    t0, losses = time.time(), []

    for step in range(1, n_steps + 1):
        mem = random_memory()
        ch_ids, val_ids = head_inputs(mem, block_a, device)
        layer_kvs = write_head(ch_ids, val_ids)

        memory_part, q_text = build_prompt(encoder, mem, block_b)
        answer_text = "Context: " + ", ".join(f"{CHANNEL_NAMES[k]}={mem[k]}" for k in ALL_QUERY_CHANNELS) + "."
        a_text = f" {answer_text}"
        full_ids = tokenizer.encode(memory_part + q_text + a_text, add_special_tokens=False)
        a_ids = tokenizer.encode(a_text, add_special_tokens=False)
        prefix_len = len(full_ids) - len(a_ids)
        labels = [-100] * prefix_len + full_ids[prefix_len:]
        if len(full_ids) > max_len:
            raise RuntimeError(f"sequence {len(full_ids)} > max_len {max_len}: answer labels would be truncated")

        inp = torch.tensor([full_ids], device=device)
        lab = torch.tensor([labels], device=device)
        pos = torch.arange(N_KV_POSITIONS, N_KV_POSITIONS + inp.shape[1], device=device).unsqueeze(0)
        past_kv = layer_kvs_to_cache(layer_kvs, arch)

        loss = model(input_ids=inp, position_ids=pos, past_key_values=past_kv,
                     labels=lab, use_cache=False).loss
        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(write_head.parameters(), 1.0)
        opt.step(); sched.step(); losses.append(loss.item())
        if step % 1000 == 0 or step == n_steps:
            print(f"    Step {step:5d}/{n_steps} | loss {np.mean(losses[-1000:]):.4f} | {time.time()-t0:.0f}s")

    write_head.eval()
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        ckpt = os.path.join(save_dir, f"write_head_A{n_param}_seed{seed}.pt")
        torch.save({"state_dict": write_head.state_dict(), "block_a": block_a, "block_b": block_b,
                    "n_steps": n_steps, "lr": lr, "seed": seed, "arch": arch.to_json()}, ckpt)
        print(f"  saved write head -> {ckpt}")
    r = evaluate(model, tokenizer, write_head, encoder, device, arch, block_a, block_b, n_eval, desc="Eval")
    print_eval("matched prefix", r, block_a, block_b)
    r.update({"n_param": n_param, "n_ctx": n_ctx, "final_loss": float(np.mean(losses[-500:])),
              "n_steps": n_steps, "lr": lr,
              "write_head_params": sum(p.numel() for p in write_head.parameters())})

    if run_control:
        c = evaluate(model, tokenizer, write_head, encoder, device, arch, block_a, block_b, n_eval,
                     control=True, desc="Control")
        print_eval("SHUFFLED prefix", c, block_a, block_b)
        r["control_shuffled_prefix"] = c
        drop = r["block_a_acc_slot"] - c["block_a_acc_slot"]
        print(f"  Block A drop under shuffled prefix: {drop*100:.1f} pts "
              f"(should approach {(r['block_a_acc_slot']-chance_level(block_a))*100:.1f} pts for a full collapse)")
    return r


def make_partition(n_param, mode):
    if mode == "contiguous":
        a = list(range(8, 8 + n_param))
    elif mode == "interleaved":
        cands = ALL_QUERY_CHANNELS[0::2] + ALL_QUERY_CHANNELS[1::2]
        a = sorted(cands[:n_param])
    else:
        raise ValueError(mode)
    b = [c for c in ALL_QUERY_CHANNELS if c not in a]
    return a, b


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="/workspace/FDM_IN_WEIGHTS/two_block_lfm25")
    p.add_argument("--n_steps", type=int, default=5000)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--n_eval", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max_len", type=int, default=1536)
    p.add_argument("--vocab_size", type=int, default=None,
                   help="MUST equal the vocab_size the checkpoint's encoder was built with "
                        "(token_map = rng.choice(vocab_size, 64)). Defaults to config.vocab_size; "
                        "if the sanity gate fails, the host was trained with a different value.")
    p.add_argument("--a_low", type=float, default=0.25,
                   help="encoder low amplitude; must match the host's training encoder (0.25 Qwen3/Hermes3)")
    p.add_argument("--partition", choices=["contiguous", "interleaved"], default="interleaved")
    p.add_argument("--no_control", action="store_true")
    p.add_argument("--load_head", default=None,
                   help="Path to a saved write_head_A<n>_seed<s>.pt: skip training, re-evaluate it.")
    p.add_argument("--ctx_only_masked", action="store_true",
                   help="No write head, no training: host on the masked block only.")
    p.add_argument("--dtype", choices=["float32", "bfloat16"], default="float32")
    p.add_argument("--output_dir", default="/workspace/FDM_IN_WEIGHTS/split_ratio_sweep_disjoint_hybrid")
    p.add_argument("--splits", default="0,4,8,16")
    args = p.parse_args()

    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[seed] {args.seed}   [partition] {args.partition}")

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(args.model, trust_remote_code=True, dtype=dtype).to(device)
    model.eval()
    for q in model.parameters():
        q.requires_grad = False
    arch = HostArch(model.config)
    print(f"[host] {arch.describe()}")
    vocab_size = args.vocab_size if args.vocab_size is not None else model.config.vocab_size
    print(f"[encoder] vocab_size={vocab_size} a_low={args.a_low}")
    encoder = make_encoder(tokenizer, vocab_size, a_low=args.a_low)

    if args.load_head:
        ckpt = torch.load(args.load_head, map_location=device)
        block_a, block_b = ckpt["block_a"], ckpt["block_b"]
        print(f"[load_head] {args.load_head}  A={block_a}  (trained {ckpt.get('n_steps')} steps, seed {ckpt.get('seed')})")
        if block_a and block_b:
            leak_check(encoder, block_a, block_b)
        wh = CrossAttentionWriteHead(n_channels=len(block_a), arch=arch).to(device)
        wh.load_state_dict(ckpt["state_dict"]); wh.eval()
        r = evaluate(model, tokenizer, wh, encoder, device, arch, block_a, block_b, args.n_eval, desc="Eval")
        print_eval("matched prefix", r, block_a, block_b)
        c = evaluate(model, tokenizer, wh, encoder, device, arch, block_a, block_b, args.n_eval, control=True, desc="Control")
        print_eval("SHUFFLED prefix", c, block_a, block_b)
        r["control_shuffled_prefix"] = c
        r.update({"n_param": len(block_a), "n_ctx": len(block_b), "block_a_channels": block_a,
                  "block_b_channels": block_b, "seed": args.seed, "rescored_from": args.load_head,
                  "arch": arch.to_json()})
        os.makedirs(args.output_dir, exist_ok=True)
        out = os.path.join(args.output_dir, f"rescored_A{len(block_a)}_seed{args.seed}.json")
        json.dump([r], open(out, "w"), indent=2)
        print(f"  saved {out}")
        return

    results = []
    for n_param in [int(x) for x in args.splits.split(',')]:
        block_a, block_b = make_partition(n_param, args.partition)
        if block_a and block_b:
            leak_check(encoder, block_a, block_b)
        if args.ctx_only_masked:
            print(f"\n[masked ctx-only] {n_param} channels removed from block, no prefix, no training")
            r = evaluate(model, tokenizer, None, encoder, device, arch, block_a, block_b, args.n_eval,
                         desc="Masked ctx-only")
            print_eval("masked ctx-only", r, block_a, block_b)
            r.update({"n_param": n_param, "n_ctx": 32 - n_param, "mode": "ctx_only_masked",
                      "block_a_channels": block_a, "block_b_channels": block_b,
                      "partition": args.partition, "seed": args.seed, "arch": arch.to_json()})
            results.append(r)
            os.makedirs(args.output_dir, exist_ok=True)
            json.dump(results, open(os.path.join(args.output_dir, f"ctx_only_masked_seed{args.seed}.json"), "w"), indent=2)
            continue
        r = train_and_eval_split(model, tokenizer, encoder, device, arch, block_a, block_b,
                                 n_steps=args.n_steps, lr=args.lr, n_eval=args.n_eval,
                                 max_len=args.max_len, run_control=not args.no_control,
                                 save_dir=args.output_dir, seed=args.seed)
        r["block_a_channels"], r["block_b_channels"] = block_a, block_b
        r["partition"], r["seed"], r["arch"] = args.partition, args.seed, arch.to_json()
        r["vocab_size"], r["a_low"] = vocab_size, args.a_low
        results.append(r)

        os.makedirs(args.output_dir, exist_ok=True)
        json.dump(results, open(os.path.join(args.output_dir, f"sweep_results_seed{args.seed}.json"), "w"), indent=2)

    print("\n" + "=" * 72 + "\n  SWEEP SUMMARY (disjoint, hybrid host; A = prefix only, B = context only)\n" + "=" * 72)
    print(f"  {'A':>3} {'B':>3} | {'A slot':>7} {'B slot':>7} {'All slot':>8} | {'All-32 joint':>12} | {'A ctrl':>7} {'A chance':>8}")
    for r in results:
        c = r.get("control_shuffled_prefix", {})
        print(f"  {r['n_param']:3d} {r['n_ctx']:3d} | {r['block_a_acc_slot']*100:6.1f}% {r['block_b_acc_slot']*100:6.1f}% "
              f"{r['all_acc_slot']*100:7.1f}% | {r['all_acc_joint']*100:11.1f}% | "
              f"{c.get('block_a_acc_slot', float('nan'))*100:6.1f}% {chance_level(r['block_a_channels'])*100:7.1f}%")
    print(f"\n  Saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
