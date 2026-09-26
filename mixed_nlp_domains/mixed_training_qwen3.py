#!/usr/bin/env python3
"""
Two-Block Mixed-Domain FDM Training
====================================
Combines:
  - Two-block FDM training (BLOCK_A ch 8-23, BLOCK_B ch 24-39)
  - Curriculum stages (a_low 0.0 -> 0.25, from turbo-v3)
  - General text replay (Alpaca) to preserve NLP capability
  - NL + J-space evaluation

Starts from base Qwen3-0.6B-Base. Trains everything from scratch with
mixed-domain replay so NLP is never lost.

Usage:
  python fdm_twoblock_mixed_train.py download-alpaca
  python fdm_twoblock_mixed_train.py generate
  python fdm_twoblock_mixed_train.py train
  python fdm_twoblock_mixed_train.py all-eval
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.optim import AdamW
import json, random, re, os, sys, argparse
from tqdm import tqdm
from contextlib import nullcontext

# ============================================================
# Config
# ============================================================
MODEL_ID = "Qwen/Qwen3-0.6B-Base"
VOCAB_SIZE = 151936
DTYPE = torch.bfloat16
BATCH_SIZE = 4
MAX_LENGTH = 2048
OUTPUT_PREFIX = "fdm_twoblock_mixed_qwen3"
CHECKPOINT_DIR = "checkpoints_twoblock_mixed"
FINAL_MODEL_DIR = "fdm_twoblock_mixed_model_final"
DEFAULT_GENERAL_DATA = "general_text.jsonl"

# Two-block channel splits (from fdm_two_block_training.py)
SPLITS = [
    (list(range(8, 24)), list(range(24, 40))),
    (list(range(8, 20)), list(range(20, 40))),
    (list(range(8, 28)), list(range(28, 40))),
]
MIX_RATIO_SINGLE = 0.3  # Phase 2: 30% single-block, 70% two-block
PHASE2_STEPS = 5000
PHASE2_LR = 2e-5
PHASE2_WEIGHT_DECAY = 0.01
PHASE2_GENERAL_RATIO = 0.15  # fixed NL replay during two-block fine-tuning

# ============================================================
# Channel schemas (40 channels, same as turbo-v3)
# ============================================================
MEMORY_SCHEMAS = {
    0: ("SECRET",   ["RED", "BLUE", "GREEN", "GOLD"]),
    1: ("LOCATION", ["PARIS", "TOKYO", "LONDON", "BERLIN"]),
    2: ("AGENT",    ["ALICE", "BOB", "CAROL", "DAVE"]),
    3: ("STATUS",   ["CLEAR", "COMPROMISED", "UNKNOWN"]),
    4: ("PRIORITY", ["HIGH", "MEDIUM", "LOW"]),
    5: ("BACKUP",   ["AVAILABLE", "UNAVAILABLE"]),
    6: ("RULE",     ["SAFETY_FIRST", "MISSION_FIRST", "BALANCED", "CAUTIOUS"]),
    7: ("META",     ["NONE", "OVERRIDE_STATUS", "OVERRIDE_PRIORITY", "EMERGENCY", "LOCKDOWN"]),
    8:  ("TEAM",     ["RED_TEAM", "BLUE_TEAM", "GREEN_TEAM", "GOLD_TEAM"]),
    9:  ("REGION",   ["NORTH", "SOUTH", "EAST", "WEST"]),
    10: ("PHASE",    ["ALPHA", "BETA", "GAMMA", "DELTA"]),
    11: ("COMM",     ["OPEN", "CLOSED", "RESTRICTED"]),
    12: ("ASSET",    ["VEHICLE", "AIRCRAFT", "DRONE", "BOAT"]),
    13: ("WINDOW",   ["DAWN", "MIDDAY", "DUSK", "NIGHT"]),
    14: ("COVER",    ["DEEP", "SHALLOW", "NONE"]),
    15: ("SUPPORT",  ["ACTIVE", "STANDBY", "OFFLINE"]),
    16: ("THREAT",   ["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    17: ("WEATHER",  ["CLEAR", "STORM", "FOG"]),
    18: ("TERRAIN",  ["URBAN", "RURAL", "COASTAL", "MOUNTAIN"]),
    19: ("EXTRACT",  ["READY", "DELAYED", "UNAVAILABLE"]),
    20: ("CIPHER",   ["AES", "RSA", "BLOWFISH", "TWOFISH"]),
    21: ("FREQ",     ["HF", "VHF", "UHF", "SHF"]),
    22: ("PAYLOAD",  ["LIGHT", "MEDIUM", "HEAVY", "CRITICAL"]),
    23: ("ROUTE",    ["ALPHA", "BRAVO", "CHARLIE", "DELTA"]),
    24: ("DURATION", ["SHORT", "MEDIUM", "LONG", "EXTENDED"]),
    25: ("CONTACT",  ["FRIENDLY", "NEUTRAL", "HOSTILE", "UNKNOWN"]),
    26: ("FUEL",     ["FULL", "HALF", "LOW", "CRITICAL"]),
    27: ("ALTITUDE", ["LOW", "MEDIUM", "HIGH"]),
    28: ("VISIBILITY", ["CLEAR", "REDUCED", "ZERO"]),
    29: ("NOISE",    ["SILENT", "QUIET", "MODERATE", "LOUD"]),
    30: ("FORMATION", ["SINGLE", "PAIR", "SQUAD", "PLATOON"]),
    31: ("ARMOR",    ["NONE", "LIGHT", "MEDIUM", "HEAVY"]),
    32: ("SIGNAL",   ["STRONG", "WEAK", "JAMMED", "LOST"]),
    33: ("MORALE",   ["HIGH", "MEDIUM", "LOW"]),
    34: ("SUPPLY",   ["ABUNDANT", "ADEQUATE", "SCARCE", "DEPLETED"]),
    35: ("INTEL",    ["CONFIRMED", "PROBABLE", "UNCERTAIN", "NONE"]),
    36: ("EVAC",     ["STANDING", "PREPPED", "LAUNCHED", "ABORTED"]),
    37: ("WEATHER2", ["SUNNY", "OVERCAST", "RAIN", "SNOW"]),
    38: ("DOCTRINE", ["OFFENSIVE", "DEFENSIVE", "RECON", "SUPPORT"]),
    39: ("COMMS",    ["SECURE", "OPEN", "COMPROMISED", "SILENT"]),
}
NUM_CHANNELS = 40
CHANNEL_NAMES = [MEMORY_SCHEMAS[i][0] for i in range(NUM_CHANNELS)]

# Reasoning rules
REASONING_RULES = {
    "SAFETY_FIRST":  "Always prioritize status over priority.",
    "MISSION_FIRST": "Always prioritize mission completion.",
    "BALANCED":      "Weigh status and priority equally.",
    "CAUTIOUS":      "Require both clear status AND available backup.",
}
META_INSTRUCTIONS = {
    "NONE": "Follow standard reasoning rules.",
    "OVERRIDE_STATUS": "Ignore status checks entirely.",
    "OVERRIDE_PRIORITY": "Ignore priority.",
    "EMERGENCY": "Proceed immediately regardless.",
    "LOCKDOWN": "Abort all operations.",
}

# Curriculum stages (from turbo-v3, + general_ratio)
STAGES = [
    {"name": "Stage 0: Easy", "a_high": 1.0, "a_low": 0.0, "samples": 15000, "epochs": 5, "lr": 5e-5, "general_ratio": 0.30},
    {"name": "Stage 1: Standard", "a_high": 1.0, "a_low": 0.1, "samples": 20000, "epochs": 5, "lr": 3e-5, "general_ratio": 0.25},
    {"name": "Stage 2: Moderate", "a_high": 1.0, "a_low": 0.15, "samples": 25000, "epochs": 7, "lr": 2e-5, "general_ratio": 0.20},
    {"name": "Stage 3: Harder", "a_high": 1.0, "a_low": 0.2, "samples": 25000, "epochs": 7, "lr": 1e-5, "general_ratio": 0.15},
    {"name": "Stage 4: Hardest", "a_high": 1.0, "a_low": 0.25, "samples": 30000, "epochs": 10, "lr": 1e-5, "general_ratio": 0.10},
]

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


# ============================================================
# FDM Encoder (with S-random interleaver, same as turbo-v3)
# ============================================================
_global_tokenizer = None
def get_tokenizer():
    global _global_tokenizer
    if _global_tokenizer is None:
        _global_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    return _global_tokenizer

class TurboFDMSignalEncoder:
    def __init__(self, num_tokens_per_encoder=256, sample_rate=100.0,
                 a_high=1.0, a_low=0.0, num_levels=64, seed=42):
        self.num_tokens_per_encoder = num_tokens_per_encoder
        self.total_tokens = num_tokens_per_encoder * 2
        self.sample_rate = sample_rate
        self.a_high = a_high
        self.a_low = a_low
        self.num_levels = num_levels
        self.num_channels = NUM_CHANNELS
        self.carrier_freqs = [1.0 + i * 1.0 for i in range(NUM_CHANNELS)]
        self.tokenizer = get_tokenizer()
        S = int(np.sqrt(num_tokens_per_encoder / 2))
        self.interleaver = self._generate_s_random_interleaver(num_tokens_per_encoder, S)
        rng = np.random.RandomState(seed)
        self.token_map = rng.choice(VOCAB_SIZE, size=num_levels, replace=False)

    def _generate_s_random_interleaver(self, length, S):
        import random as rnd
        rnd.seed(42)
        interleaver = list(range(length))
        for i in range(length):
            for _ in range(100):
                j = rnd.randint(i, length - 1)
                valid = True
                for k in range(max(0, i - S + 1), i):
                    if abs(interleaver[j] - interleaver[k]) < S:
                        valid = False
                        break
                if valid:
                    interleaver[i], interleaver[j] = interleaver[j], interleaver[i]
                    break
        return interleaver

    def value_to_bits(self, channel_id, value):
        _, values = MEMORY_SCHEMAS[channel_id]
        idx = values.index(value)
        num_bits = max(1, int(np.ceil(np.log2(max(len(values), 2)))))
        return format(idx, f'0{num_bits}b'), num_bits

    def encode_memory(self, memory):
        all_bits = {}
        max_bits = 0
        for ch in range(self.num_channels):
            bits, nb = self.value_to_bits(ch, memory[ch])
            all_bits[ch] = bits
            max_bits = max(max_bits, nb)
        for ch in range(self.num_channels):
            all_bits[ch] = all_bits[ch].ljust(max_bits, '0')
        num_message_bits = max_bits
        t = np.arange(self.num_tokens_per_encoder) / self.sample_rate
        samples_per_bit = self.num_tokens_per_encoder // num_message_bits
        composite = np.zeros(self.num_tokens_per_encoder)
        for ch in range(self.num_channels):
            bits = all_bits[ch]
            for bi, bit in enumerate(bits):
                start = bi * samples_per_bit
                end = min((bi + 1) * samples_per_bit, self.num_tokens_per_encoder)
                amp = self.a_high if bit == '1' else self.a_low
                composite[start:end] += amp * np.sin(
                    2 * np.pi * self.carrier_freqs[ch] * t[start:end])
        sig_min = -self.num_channels * self.a_high
        sig_max = self.num_channels * self.a_high
        sig_range = sig_max - sig_min + 1e-10
        norm1 = (composite - sig_min) / sig_range
        q1 = np.floor(norm1 * (self.num_levels - 1) + 0.5).astype(int)
        q1 = np.clip(q1, 0, self.num_levels - 1)
        tokens1 = [int(self.token_map[q]) for q in q1]
        interleaved = composite[self.interleaver]
        norm2 = (interleaved - sig_min) / sig_range
        q2 = np.floor(norm2 * (self.num_levels - 1) + 0.5).astype(int)
        q2 = np.clip(q2, 0, self.num_levels - 1)
        tokens2 = [int(self.token_map[q]) for q in q2]
        all_tokens = tokens1 + tokens2
        fdm_text = self.tokenizer.decode(all_tokens)
        return fdm_text, all_tokens


def random_memory():
    return {ch: random.choice(MEMORY_SCHEMAS[ch][1]) for ch in range(NUM_CHANNELS)}


# ============================================================
# Reasoning logic (same as turbo-v3)
# ============================================================
def generate_proceed_answer(facts, rule, meta):
    agent, status, priority, backup = facts["AGENT"], facts["STATUS"], facts["PRIORITY"], facts["BACKUP"]
    if meta == "EMERGENCY":
        return f"EMERGENCY PROTOCOL: {agent} must proceed immediately. All other factors suspended."
    if meta == "LOCKDOWN":
        return f"LOCKDOWN ACTIVE: {agent} must abort all operations. No exceptions."
    if meta == "OVERRIDE_STATUS":
        if priority == "HIGH":
            return f"Status override active. Priority is {priority}, so {agent} should proceed."
        return f"Status override active, but priority is only {priority}. {agent} may proceed with caution."
    if meta == "OVERRIDE_PRIORITY":
        if status == "CLEAR" and backup == "AVAILABLE":
            return f"Priority override active. Status {status} with backup {backup}. {agent} can proceed."
        return f"Priority override active. Status {status}, backup {backup}. {agent} should hold."
    if rule == "SAFETY_FIRST":
        if status == "COMPROMISED":
            return f"SAFETY_FIRST: Status is {status}. {agent} must abort regardless of {priority} priority."
        elif status == "CLEAR":
            return f"SAFETY_FIRST: Status is {status}. {agent} can proceed with {priority} priority."
        return f"SAFETY_FIRST: Status is {status}. {agent} should wait for confirmation."
    elif rule == "MISSION_FIRST":
        if status == "COMPROMISED" and backup == "UNAVAILABLE":
            return f"MISSION_FIRST: Status {status} with no backup. Even mission-priority says {agent} should abort."
        return f"MISSION_FIRST: Priority is {priority}. {agent} should proceed. Status {status} is secondary."
    elif rule == "BALANCED":
        if priority == "HIGH" and backup == "AVAILABLE":
            return f"BALANCED: {priority} priority with backup {backup} outweighs {status} status. {agent} can proceed."
        elif status == "COMPROMISED":
            return f"BALANCED: {status} status not offset by {priority} priority. {agent} should abort."
        return f"BALANCED: Status {status}, priority {priority}. {agent} can proceed carefully."
    elif rule == "CAUTIOUS":
        if status == "CLEAR" and backup == "AVAILABLE":
            return f"CAUTIOUS: Status {status} AND backup {backup}. Both conditions met. {agent} can proceed."
        return f"CAUTIOUS: Need CLEAR status AND AVAILABLE backup. Have {status}/{backup}. {agent} must abort."
    return f"{agent} should assess situation."

def generate_risk_answer(facts, rule, meta):
    status, priority, backup, location = facts["STATUS"], facts["PRIORITY"], facts["BACKUP"], facts["LOCATION"]
    if meta == "EMERGENCY":
        return f"EMERGENCY: Risk assessment suspended. Immediate action required in {location}."
    if meta == "LOCKDOWN":
        return f"LOCKDOWN: Maximum risk assumed. All operations in {location} halted."
    risk_factors = []
    if status == "COMPROMISED": risk_factors.append("compromised status")
    if backup == "UNAVAILABLE": risk_factors.append("no backup")
    if status == "UNKNOWN": risk_factors.append("unknown status")
    if rule == "SAFETY_FIRST":
        if risk_factors:
            return f"SAFETY_FIRST assessment: HIGH RISK in {location}. Factors: {', '.join(risk_factors)}."
        return f"SAFETY_FIRST assessment: LOW RISK in {location}. Status {status}, backup {backup}."
    elif rule == "MISSION_FIRST":
        if len(risk_factors) >= 2:
            return f"MISSION_FIRST assessment: MODERATE RISK in {location}. Acceptable for {priority} priority."
        return f"MISSION_FIRST assessment: LOW RISK in {location}. Proceed with mission."
    elif rule == "BALANCED":
        level = "HIGH" if len(risk_factors) >= 2 else "MEDIUM" if len(risk_factors) == 1 else "LOW"
        return f"BALANCED assessment: {level} RISK in {location}. Factors: {len(risk_factors)} concerns."
    elif rule == "CAUTIOUS":
        if risk_factors:
            return f"CAUTIOUS assessment: HIGH RISK in {location}. Any risk factor triggers alert: {', '.join(risk_factors)}."
        return f"CAUTIOUS assessment: LOW RISK in {location}. All safety conditions met."
    return f"Risk assessment for {location}."

def generate_share_answer(facts, rule, meta):
    secret, status, location = facts["SECRET"], facts["STATUS"], facts["LOCATION"]
    if meta == "EMERGENCY":
        return f"EMERGENCY: Share {secret} immediately with any allied contact. Speed over security."
    if meta == "LOCKDOWN":
        return f"LOCKDOWN: Do not share {secret} under any circumstances. Maintain radio silence."
    if meta == "OVERRIDE_STATUS":
        return f"Status override active. You may share {secret} with {location} contact despite {status} status."
    if rule == "SAFETY_FIRST":
        if status == "COMPROMISED":
            return f"SAFETY_FIRST: Do NOT share {secret}. {location} may be compromised."
        return f"SAFETY_FIRST: Status {status}. May share {secret} with verified contacts only."
    elif rule == "MISSION_FIRST":
        return f"MISSION_FIRST: Share {secret} with {location} contact to advance mission. Accept calculated risk."
    elif rule == "BALANCED":
        if status == "CLEAR":
            return f"BALANCED: Status {status}. Safe to share {secret} with {location} contact."
        return f"BALANCED: Status {status}. Share {secret} only if mission-critical."
    elif rule == "CAUTIOUS":
        if status == "CLEAR":
            return f"CAUTIOUS: Status {status}. May share {secret} after secondary verification."
        return f"CAUTIOUS: Status {status}. Do not share {secret}. Request secure channel."
    return f"Evaluate sharing {secret} in {location}."

QUESTION_TEMPLATES = [
    {"question": "Should {AGENT} proceed with the mission?", "fn": generate_proceed_answer},
    {"question": "What is the risk assessment?", "fn": generate_risk_answer},
    {"question": "Is it safe to share the secret with the contact?", "fn": generate_share_answer},
]


# ============================================================
# Two-block + single-block sample generation
# ============================================================

def generate_two_block_sample(encoder, tokenizer, memory, block_a_ch, block_b_ch):
    """Two-block: BLOCK_A carries some channels, BLOCK_B carries the rest."""
    fdm_text_a, _ = encoder.encode_memory(memory)
    fdm_text_b, _ = encoder.encode_memory(memory)
    all_ch = sorted(set(block_a_ch) | set(block_b_ch))
    ch_names = [CHANNEL_NAMES[k] for k in all_ch]
    question = f"Report values for: {', '.join(ch_names)}."
    parts = [f"{CHANNEL_NAMES[k]}={memory[k]}" for k in all_ch]
    answer = "Context: " + ", ".join(parts) + "."
    prompt = (f"[MEMORY]BLOCK_A {fdm_text_a}[/MEMORY]"
              f"[MEMORY]BLOCK_B {fdm_text_b}[/MEMORY]"
              f"\nQuestion: {question}\nAnswer:")
    a_text = f" {answer}"
    full = prompt + a_text
    full_ids = tokenizer.encode(full, add_special_tokens=False)
    a_ids = tokenizer.encode(a_text, add_special_tokens=False)
    prefix_len = len(full_ids) - len(a_ids)
    labels = [-100] * prefix_len + full_ids[prefix_len:]
    return full_ids, labels

def generate_single_block_sample(encoder, tokenizer, memory, channels):
    """Single-block: all channels in one FDM block."""
    fdm_text, _ = encoder.encode_memory(memory)
    ch_names = [CHANNEL_NAMES[k] for k in channels]
    question = f"Report values for: {', '.join(ch_names)}."
    parts = [f"{CHANNEL_NAMES[k]}={memory[k]}" for k in channels]
    answer = "Context: " + ", ".join(parts) + "."
    prompt = f"[MEMORY]{fdm_text}[/MEMORY]\nQuestion: {question}\nAnswer:"
    a_text = f" {answer}"
    full = prompt + a_text
    full_ids = tokenizer.encode(full, add_special_tokens=False)
    a_ids = tokenizer.encode(a_text, add_special_tokens=False)
    prefix_len = len(full_ids) - len(a_ids)
    labels = [-100] * prefix_len + full_ids[prefix_len:]
    return full_ids, labels

def generate_reasoning_sample(encoder, tokenizer, memory):
    """Reasoning sample: FDM block + reasoning question (proceed/risk/share)."""
    fdm_text, _ = encoder.encode_memory(memory)
    facts = {MEMORY_SCHEMAS[ch][0]: memory[ch] for ch in range(6)}
    rule = memory[6]
    meta = memory[7]
    extra = {MEMORY_SCHEMAS[ch][0]: memory[ch] for ch in range(8, NUM_CHANNELS)}
    q_template = random.choice(QUESTION_TEMPLATES)
    question = q_template["question"].format(**facts)
    base_answer = q_template["fn"](facts, rule, meta)
    extra_parts = [f"{k}={v}" for k, v in extra.items()]
    answer = f"{base_answer} Context: {', '.join(extra_parts)}."
    prompt = f"[MEMORY]{fdm_text}[/MEMORY]\nQuestion: {question}\nAnswer:"
    a_text = f" {answer}"
    full = prompt + a_text
    full_ids = tokenizer.encode(full, add_special_tokens=False)
    a_ids = tokenizer.encode(a_text, add_special_tokens=False)
    prefix_len = len(full_ids) - len(a_ids)
    labels = [-100] * prefix_len + full_ids[prefix_len:]
    return full_ids, labels


# ============================================================
# General text dataset (for NLP replay)
# ============================================================
class GeneralTextDataset(Dataset):
    def __init__(self, path, tokenizer, max_length=MAX_LENGTH):
        self.samples = []
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    obj = json.loads(line)
                    text = obj.get("text", obj.get("instruction", ""))
                    if obj.get("input"): text += "\n" + obj["input"]
                    if obj.get("output"): text += "\n" + obj["output"]
                    if len(text) > 50:
                        self.samples.append(text)
        self.tokenizer = tokenizer
        self.max_length = max_length
    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        text = self.samples[idx]
        enc = self.tokenizer(text, truncation=True, max_length=self.max_length,
                             padding='max_length', return_tensors='pt')
        ids = enc['input_ids'].squeeze()
        mask = enc['attention_mask'].squeeze()
        labels = ids.clone()
        return {'input_ids': ids, 'attention_mask': mask, 'labels': labels}
    def is_empty(self): return len(self.samples) == 0

def download_alpaca(output_path):
    from datasets import load_dataset
    print(f"  Downloading Alpaca -> {output_path}")
    ds = load_dataset("tatsu-lab/alpaca", split="train")
    with open(output_path, 'w') as f:
        for item in ds:
            text = item.get("instruction", "")
            if item.get("input"): text += "\n" + item["input"]
            if item.get("output"): text += "\n" + item["output"]
            f.write(json.dumps({"text": text}) + "\n")
    print(f"  Wrote {len(ds)} samples")


# ============================================================
# Mixed data loader (interleaves FDM + general text)
# ============================================================
class MixedDataLoader:
    def __init__(self, fdm_batches, general_ds, batch_size, general_ratio=0.3):
        self.fdm_batches = fdm_batches  # list of (input_ids, labels) tuples
        self.general_ds = general_ds
        self.batch_size = batch_size
        self.general_ratio = general_ratio
        self.has_general = general_ds is not None and not general_ds.is_empty()
        if self.has_general:
            self.general_loader = DataLoader(general_ds, batch_size=batch_size, shuffle=True)
        self.n_fdm = len(fdm_batches)
        self.total = self.n_fdm
    def __len__(self): return self.total
    def __iter__(self):
        if self.has_general:
            gen_iter = iter(self.general_loader)
        fdm_idx = list(range(self.n_fdm))
        random.shuffle(fdm_idx)
        for i in range(self.total):
            if self.has_general and random.random() < self.general_ratio:
                try:
                    yield next(gen_iter)
                except StopIteration:
                    gen_iter = iter(self.general_loader)
                    yield next(gen_iter)
            else:
                if not fdm_idx:
                    fdm_idx = list(range(self.n_fdm))
                    random.shuffle(fdm_idx)
                idx = fdm_idx.pop()
                ids, lbls = self.fdm_batches[idx]
                yield {
                    'input_ids': ids.unsqueeze(0) if ids.dim() == 1 else ids,
                    'attention_mask': torch.ones_like(ids.unsqueeze(0) if ids.dim() == 1 else ids),
                    'labels': lbls.unsqueeze(0) if lbls.dim() == 1 else lbls,
                }


# ============================================================
# Phase 1: Turbo-v3 curriculum from base model + NL replay
# ============================================================
def phase1_curriculum(general_ds, tokenizer, device, override_ratio=None):
    """Train base model to read single-block FDM via 5-stage curriculum."""
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=DTYPE, trust_remote_code=True)
    model.resize_token_embeddings(len(tokenizer))
    model.gradient_checkpointing_enable()
    model.to(device)
    model.train()
    for p in model.parameters():
        p.requires_grad = True
    print(f"\nPhase 1: Curriculum training from {MODEL_ID}")
    print(f"Params: {sum(p.numel() for p in model.parameters()):,}")

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    resume_stage = 0
    ckpts = sorted([f for f in os.listdir(CHECKPOINT_DIR) if f.startswith('p1_') and f.endswith('.pt')])
    if ckpts:
        ckpt = torch.load(os.path.join(CHECKPOINT_DIR, ckpts[-1]), map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        resume_stage = ckpt.get('stage', 0) + 1
        print(f"Resuming Phase 1 from stage {resume_stage}")

    for stage_idx in range(resume_stage, len(STAGES)):
        stage = STAGES[stage_idx]
        gr = override_ratio if override_ratio is not None else stage['general_ratio']
        print(f"\n{'='*60}")
        print(f"P1 STAGE {stage_idx}: {stage['name']} | lr={stage['lr']} | nl_ratio={gr}")
        print(f"{'='*60}")

        encoder = TurboFDMSignalEncoder(a_high=stage['a_high'], a_low=stage['a_low'], num_levels=64, seed=42)
        fdm_batches = []
        n = stage['samples']
        print(f"  Generating {n} FDM samples (a_low={stage['a_low']})...")
        for _ in tqdm(range(n), desc=f"  P1S{stage_idx} gen"):
            mem = random_memory()
            # Turbo-v3 sample: reasoning question + report all channels
            fdm_text, _ = encoder.encode_memory(mem)
            facts = {MEMORY_SCHEMAS[ch][0]: mem[ch] for ch in range(6)}
            rule = mem[6]; meta = mem[7]
            extra = {MEMORY_SCHEMAS[ch][0]: memory[ch] for ch in range(8, NUM_CHANNELS)}
            q_template = random.choice(QUESTION_TEMPLATES)
            question = q_template["question"].format(**facts)
            base_answer = q_template["fn"](facts, rule, meta)
            extra_parts = [f"{k}={v}" for k, v in extra.items()]
            answer = f"{base_answer} Context: {', '.join(extra_parts)}."
            prompt = f"[MEMORY]{fdm_text}[/MEMORY]\nQuestion: {question}\nAnswer:"
            a_text = f" {answer}"
            full = prompt + a_text
            full_ids = tokenizer.encode(full, add_special_tokens=False)
            a_ids = tokenizer.encode(a_text, add_special_tokens=False)
            prefix_len = len(full_ids) - len(a_ids)
            labels = [-100] * prefix_len + full_ids[prefix_len:]
            if len(full_ids) > MAX_LENGTH:
                full_ids = full_ids[:MAX_LENGTH]; labels = labels[:MAX_LENGTH]
            fdm_batches.append((torch.tensor(full_ids, dtype=torch.long),
                                torch.tensor(labels, dtype=torch.long)))

        mixed_loader = MixedDataLoader(fdm_batches, general_ds, BATCH_SIZE, general_ratio=gr)
        optimizer = AdamW(model.parameters(), lr=stage['lr'])
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=stage['epochs'], eta_min=stage['lr']/20)

        for epoch in range(stage['epochs']):
            model.train()
            total_loss = 0; n_batches = 0
            for batch in tqdm(mixed_loader, desc=f"P1S{stage_idx} E{epoch+1}"):
                ids = batch['input_ids'].to(device)
                mask = batch['attention_mask'].to(device)
                lbls = batch['labels'].to(device)
                with torch.amp.autocast(device_type='cuda', dtype=torch.float32):
                    out = model(input_ids=ids, attention_mask=mask, labels=lbls)
                    loss = out.loss
                optimizer.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step(); total_loss += loss.item(); n_batches += 1
            scheduler.step()
            print(f"  P1S{stage_idx} E{epoch+1}: loss={total_loss/max(n_batches,1):.4f}")
            if (epoch+1) % 2 == 0 or epoch == stage['epochs']-1:
                mixed_eval(model, tokenizer, encoder, device)

        torch.save({'model_state_dict': model.state_dict(), 'stage': stage_idx},
                    os.path.join(CHECKPOINT_DIR, f'p1_stage{stage_idx}.pt'))

    model.save_pretrained(f'{OUTPUT_PREFIX}_phase1')
    tokenizer.save_pretrained(f'{OUTPUT_PREFIX}_phase1')
    print(f"\nPhase 1 complete. Saved to {OUTPUT_PREFIX}_phase1/")
    return model


# ============================================================
# Phase 2: Two-block fine-tuning on top of Phase 1 + NL replay
# ============================================================
def phase2_twoblock(model, tokenizer, general_ds, device, override_ratio=None):
    """Fine-tune Phase 1 model to read two-block FDM. Matches original two-block script."""
    gr = override_ratio if override_ratio is not None else PHASE2_GENERAL_RATIO
    model.train()
    for p in model.parameters():
        p.requires_grad = True

    optimizer = torch.optim.AdamW(model.parameters(), lr=PHASE2_LR, weight_decay=PHASE2_WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=PHASE2_STEPS, eta_min=PHASE2_LR/20)

    # Same encoder as original: a_low=0.25, vocab_size=151936
    encoder = TurboFDMSignalEncoder(a_high=1.0, a_low=0.25, num_levels=64, seed=42)

    print(f"\n{'='*60}")
    print(f"PHASE 2: Two-block fine-tuning")
    print(f"  Steps: {PHASE2_STEPS} | LR: {PHASE2_LR} | wd: {PHASE2_WEIGHT_DECAY}")
    print(f"  Mix: {MIX_RATIO_SINGLE} single / {1-MIX_RATIO_SINGLE} two-block")
    print(f"  NL replay: {gr}")
    print(f"  Encoder: a_low=0.25 (hardest, same as original)")
    print(f"{'='*60}")

    # Initial eval
    print("\n  Initial eval:", flush=True)
    mixed_eval(model, tokenizer, encoder, device)

    # Build general text iterator if available
    gen_iter = None
    if general_ds is not None and not general_ds.is_empty():
        gen_loader = DataLoader(general_ds, batch_size=1, shuffle=True)
        gen_iter = iter(gen_loader)

    import time
    t0 = time.time()
    losses = []

    for step in range(1, PHASE2_STEPS + 1):
        # Generate FDM sample (same as original two-block script)
        mem = random_memory()
        if random.random() < MIX_RATIO_SINGLE:
            # Single-block
            channels = list(range(8, 40))
            input_ids, labels = generate_single_block_sample(encoder, tokenizer, mem, channels)
        else:
            # Two-block with random split
            split = random.choice(SPLITS)
            input_ids, labels = generate_two_block_sample(encoder, tokenizer, mem, split[0], split[1])

        if len(input_ids) > MAX_LENGTH:
            input_ids = input_ids[:MAX_LENGTH]
            labels = labels[:MAX_LENGTH]

        # Decide: FDM or NL batch this step
        use_nl = gen_iter is not None and random.random() < gr

        if use_nl:
            try:
                batch = next(gen_iter)
            except StopIteration:
                gen_iter = iter(DataLoader(general_ds, batch_size=1, shuffle=True))
                batch = next(gen_iter)
            input_tensor = batch['input_ids'].to(device)
            label_tensor = batch['labels'].to(device)
        else:
            input_tensor = torch.tensor([input_ids], dtype=torch.long).to(device)
            label_tensor = torch.tensor([labels], dtype=torch.long).to(device)

        with torch.amp.autocast(device_type='cuda', dtype=torch.float32):
            outputs = model(input_tensor, labels=label_tensor)
            loss = outputs.loss

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        losses.append(loss.item())

        if step % 500 == 0 or step == PHASE2_STEPS:
            avg = np.mean(losses[-500:])
            elapsed = time.time() - t0
            cur_lr = optimizer.param_groups[0]['lr']
            print(f"  Step {step:5d}/{PHASE2_STEPS} | loss {avg:.4f} | "
                  f"lr {cur_lr:.1e} | {elapsed:.0f}s", flush=True)

        if step % 1000 == 0:
            mixed_eval(model, tokenizer, encoder, device)
            model.train()

    torch.save({'model_state_dict': model.state_dict(), 'phase': 2},
                os.path.join(CHECKPOINT_DIR, 'p2_final.pt'))
    model.save_pretrained(FINAL_MODEL_DIR)
    tokenizer.save_pretrained(FINAL_MODEL_DIR)
    print(f"\nPhase 2 complete. Saved to {FINAL_MODEL_DIR}/")
    return model


# ============================================================
# Evaluation (FDM two-block + single-block + NL)
# ============================================================
def mixed_eval(model, tokenizer, encoder, device):
    model.eval()
    # Single-block
    s_correct = 0; s_total = 0
    # Two-block
    t_correct = 0; t_total = 0
    all_ch = list(range(8, 40))
    for _ in range(5):
        mem = random_memory()
        # Single
        fdm_text, _ = encoder.encode_memory(mem)
        ch_names = [CHANNEL_NAMES[k] for k in all_ch]
        q = f"Report values for: {', '.join(ch_names)}."
        prompt = f"[MEMORY]{fdm_text}[/MEMORY]\nQuestion: {q}\nAnswer:"
        ids = tokenizer.encode(prompt, return_tensors='pt').to(device)
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=350, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)
        for k in all_ch:
            if re.search(rf"\b{re.escape(CHANNEL_NAMES[k])}={re.escape(mem[k])}\b", text):
                s_correct += 1
            s_total += 1
        # Two-block
        fa, _ = encoder.encode_memory(mem)
        fb, _ = encoder.encode_memory(mem)
        prompt2 = (f"[MEMORY]BLOCK_A {fa}[/MEMORY][MEMORY]BLOCK_B {fb}[/MEMORY]"
                   f"\nQuestion: {q}\nAnswer:")
        ids2 = tokenizer.encode(prompt2, return_tensors='pt').to(device)
        with torch.no_grad():
            out2 = model.generate(ids2, max_new_tokens=350, do_sample=False,
                                  pad_token_id=tokenizer.eos_token_id)
        text2 = tokenizer.decode(out2[0][ids2.shape[1]:], skip_special_tokens=True)
        for k in all_ch:
            if re.search(rf"\b{re.escape(CHANNEL_NAMES[k])}={re.escape(mem[k])}\b", text2):
                t_correct += 1
            t_total += 1
    # NL
    nl_correct = 0; nl_total = 0
    for question, expected in NL_QUESTIONS:
        prompt = f"Question: {question}\nAnswer:"
        ids = tokenizer.encode(prompt, return_tensors='pt').to(device)
        with torch.no_grad():
            out = model.generate(ids, max_new_tokens=30, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip().lower()
        if expected.lower() in text: nl_correct += 1
        nl_total += 1
    print(f"    Single: {100*s_correct/s_total:.1f}% | Two-block: {100*t_correct/t_total:.1f}% | NL: {nl_correct}/{nl_total}")


def evaluate():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tokenizer = AutoTokenizer.from_pretrained(FINAL_MODEL_DIR, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(FINAL_MODEL_DIR, torch_dtype=DTYPE, trust_remote_code=True)
    model.to(device); model.eval()
    encoder = TurboFDMSignalEncoder(a_high=1.0, a_low=0.25, num_levels=64, seed=42)
    all_ch = list(range(8, 40))
    print(f"\n{'='*60}\nFULL EVALUATION\n{'='*60}")
    mixed_eval(model, tokenizer, encoder, device)
    print(f"\n{'='*60}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--general-data', default=DEFAULT_GENERAL_DATA)
    parser.add_argument('--general-ratio', type=float, default=None)
    parser.add_argument('--phase', type=int, default=0,
                        help='0=both phases, 1=curriculum only, 2=two-block only')
    args = parser.parse_args()

    if len(sys.argv) < 2:
        print(f"Two-Block Mixed-Domain FDM Training -- {MODEL_ID}")
        print(f"")
        print(f"Phase 1: Turbo-v3 curriculum (5 stages) + NL replay")
        print(f"Phase 2: Two-block fine-tuning (5000 steps) + NL replay")
        print(f"")
        print(f"Usage:")
        print(f"  python {sys.argv[0]} download-alpaca")
        print(f"  python {sys.argv[0]} train                    # both phases")
        print(f"  python {sys.argv[0]} train --phase 1          # curriculum only")
        print(f"  python {sys.argv[0]} train --phase 2          # two-block only (needs Phase 1)")
        print(f"  python {sys.argv[0]} train --general-ratio 0.30")
        print(f"  python {sys.argv[0]} eval")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "download-alpaca":
        download_alpaca(args.general_data)
    elif cmd == "train":
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.add_special_tokens({'additional_special_tokens': ['[MEMORY]', '[/MEMORY]']})

        general_ds = None
        if os.path.exists(args.general_data):
            general_ds = GeneralTextDataset(args.general_data, tokenizer)
            print(f"General text: {len(general_ds)} samples")
        else:
            print(f"WARNING: {args.general_data} not found. FDM-only (will forget NL).")
            print(f"  Run: python {sys.argv[0]} download-alpaca")

        model = None
        if args.phase in [0, 1]:
            model = phase1_curriculum(general_ds, tokenizer, device, args.general_ratio)

        if args.phase in [0, 2]:
            if model is None:
                # Load Phase 1 model
                p1_path = f'{OUTPUT_PREFIX}_phase1'
                if not os.path.exists(p1_path):
                    print(f"ERROR: {p1_path} not found. Run Phase 1 first.")
                    sys.exit(1)
                from transformers import AutoModelForCausalLM
                model = AutoModelForCausalLM.from_pretrained(p1_path, torch_dtype=DTYPE, trust_remote_code=True)
                model.to(device)
            phase2_twoblock(model, tokenizer, general_ds, device, args.general_ratio)
    elif cmd == "eval":
        evaluate()
