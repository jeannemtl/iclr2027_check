#!/usr/bin/env python3
"""
Mixed-Domain FDM Training: Preserving Natural Language During FDM Fine-Tuning (multi-model)
=============================================================================================

Trains a base model on a MIX of FDM-encoded samples and general text
(Alpaca) to prevent catastrophic forgetting of natural language.

Single-block only -- no two-block / BLOCK_A+BLOCK_B capability. Same
5-stage curriculum as the two-block script, but stops after the
curriculum: no extra "Phase 2" fine-tuning pass that can over-train an
already-saturated model and erode NL retention the way the two-block
script's Phase 2 did.

Supports multiple base models via --model-key:
  qwen3-0.6b   (default, legacy output-dir names when num_channels=40)
  gpt2-medium
  lfm2.5-1.2b
  hermes3-3b

Channel count defaults to 10 (down from the original 40); override
with --num-channels.

Usage:
  python fdm_mixed_domain_train_multi.py download-alpaca
  python fdm_mixed_domain_train_multi.py generate --model-key lfm2.5-1.2b
  python fdm_mixed_domain_train_multi.py train --model-key lfm2.5-1.2b --batch-size 8
  python fdm_mixed_domain_train_multi.py eval --model-key lfm2.5-1.2b --stage 4
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.optim import AdamW
import json
import random
import re
import unicodedata
import os
import sys
import argparse
from tqdm import tqdm


# ============================================================
# Model profiles (same pattern as fdm_twoblock_mixed_train.py)
# ============================================================
MODEL_PROFILES = {
    "qwen3-0.6b": {
        "hf_id": "Qwen/Qwen3-0.6B-Base",
        "max_length": 2048,
        "vocab_size": 151936,
        "legacy_names": True,
    },
    "gpt2-medium": {
        "hf_id": "openai-community/gpt2-medium",
        "max_length": 1024,
        "vocab_size": 50257,
        "dtype": torch.float32,
        "legacy_names": False,
    },
    "lfm2.5-1.2b": {
        "hf_id": "LiquidAI/LFM2.5-1.2B-Base",
        "max_length": 2048,
        "vocab_size": 65536,
        "legacy_names": False,
    },
    "hermes3-3b": {
        "hf_id": "NousResearch/Hermes-3-Llama-3.2-3B",
        "max_length": 2048,
        "vocab_size": 128256,
        "legacy_names": False,
        "lr_scale": 1.0 / 3.0,
    },
}

DTYPE = torch.bfloat16
BATCH_SIZE = 4
DEFAULT_GENERAL_DATA = "general_text.jsonl"

MODEL_KEY = "qwen3-0.6b"
MODEL_ID = MODEL_PROFILES[MODEL_KEY]["hf_id"]

_RUNTIME_BATCH_SIZE = None
_RUNTIME_EPOCHS_SCALE = 1.0
_RUNTIME_GRAD_CHECKPOINT = True


def apply_model_profile(model_key):
    global MODEL_KEY, MODEL_ID, _global_tokenizer
    MODEL_KEY = model_key
    MODEL_ID = MODEL_PROFILES[model_key]["hf_id"]
    _global_tokenizer = None


def model_tag():
    """Output-dir suffix. Empty only for the original qwen3-0.6b @ 40
    channels combination, preserving continuity with old runs. Any
    other model or channel count gets an explicit tag so runs never
    collide."""
    tags = []
    if not MODEL_PROFILES[MODEL_KEY]["legacy_names"]:
        tags.append(MODEL_KEY)
    if NUM_CHANNELS != 40:
        tags.append(f"{NUM_CHANNELS}ch")
    return ("_" + "_".join(tags)) if tags else ""


def profile_max_length():
    return MODEL_PROFILES[MODEL_KEY]["max_length"]


def profile_dtype():
    return MODEL_PROFILES[MODEL_KEY].get("dtype", DTYPE)


def profile_lr_scale():
    return MODEL_PROFILES[MODEL_KEY].get("lr_scale", 1.0)


def _get_vocab(model_key=None):
    key = model_key or MODEL_KEY
    profile = MODEL_PROFILES.get(key)
    if profile and "vocab_size" in profile:
        return profile["vocab_size"]
    lowered = key.lower()
    if "hermes" in lowered:
        return 128256
    if "lfm" in lowered or "liquid" in lowered:
        return 65536
    if "gpt2" in lowered:
        return 50257
    return 151936


def set_runtime_overrides(batch_size=None, epochs_scale=None, grad_checkpoint=None):
    global _RUNTIME_BATCH_SIZE, _RUNTIME_EPOCHS_SCALE, _RUNTIME_GRAD_CHECKPOINT
    if batch_size is not None:
        _RUNTIME_BATCH_SIZE = batch_size
    if epochs_scale is not None:
        _RUNTIME_EPOCHS_SCALE = epochs_scale
    if grad_checkpoint is not None:
        _RUNTIME_GRAD_CHECKPOINT = grad_checkpoint


def get_batch_size():
    return _RUNTIME_BATCH_SIZE if _RUNTIME_BATCH_SIZE is not None else BATCH_SIZE


def get_epochs_scale():
    return _RUNTIME_EPOCHS_SCALE


def get_grad_checkpoint():
    return _RUNTIME_GRAD_CHECKPOINT


def OUTPUT_PREFIX():
    return f"fdm_mixed{model_tag()}" if model_tag() else "fdm_40ch_mixed_qwen3"


def CHECKPOINT_DIR():
    return f"checkpoints_fdm_mixed{model_tag()}" if model_tag() else "checkpoints_fdm_mixed_qwen3"


def FINAL_MODEL_DIR():
    return f"fdm_mixed_model_final{model_tag()}" if model_tag() else "fdm_40ch_mixed_qwen3_model_final"


# ============================================================
# Channel definitions (40 defined; NUM_CHANNELS controls how many
# are actually used, default 10)
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

NUM_CHANNELS = 10  # default reduced from 40; override with --num-channels


def set_num_channels(n):
    """Must run before any sample generation. Channels 0-7 are the
    fixed reasoning facts/rule/meta and always required; n must be >= 8."""
    global NUM_CHANNELS
    if n < 8:
        raise ValueError(f"--num-channels must be >= 8 (need channels 0-7 for "
                          f"reasoning facts/rule/meta), got {n}")
    NUM_CHANNELS = n


REASONING_RULES = {
    "SAFETY_FIRST":  "Always prioritize status over priority.",
    "MISSION_FIRST": "Always prioritize mission completion.",
    "BALANCED":      "Weigh status and priority equally.",
    "CAUTIOUS":      "Require both clear status AND available backup.",
}

META_INSTRUCTIONS = {
    "NONE":              "Follow standard reasoning rules.",
    "OVERRIDE_STATUS":   "Ignore status checks entirely.",
    "OVERRIDE_PRIORITY": "Ignore priority.",
    "EMERGENCY":         "Proceed immediately regardless.",
    "LOCKDOWN":          "Abort all operations.",
}


# ============================================================
# FDM Encoder
# ============================================================

_global_tokenizer = None

def get_tokenizer():
    global _global_tokenizer
    if _global_tokenizer is None:
        _global_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    return _global_tokenizer


class TurboFDMSignalEncoder:
    def __init__(self, num_tokens_per_encoder=256, sample_rate=100.0,
                 a_high=1.0, a_low=0.0, num_levels=64, seed=42, vocab_size=None):
        self.num_tokens_per_encoder = num_tokens_per_encoder
        self.total_tokens = num_tokens_per_encoder * 2
        self.sample_rate = sample_rate
        self.a_high = a_high
        self.a_low = a_low
        self.num_levels = num_levels
        self.num_channels = NUM_CHANNELS
        self.carrier_freqs = [1.0 + i * 1.0 for i in range(NUM_CHANNELS)]
        self.tokenizer = get_tokenizer()
        vocab_size = vocab_size or _get_vocab()
        S = int(np.sqrt(num_tokens_per_encoder / 2))
        self.interleaver = self._generate_s_random_interleaver(num_tokens_per_encoder, S)
        rng = np.random.RandomState(seed)
        self.token_map = rng.choice(vocab_size, size=num_levels, replace=False)

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


# ============================================================
# Reasoning logic (unchanged)
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
        else:
            return f"Status override active, but priority is only {priority}. {agent} may proceed with caution."
    if meta == "OVERRIDE_PRIORITY":
        if status == "CLEAR" and backup == "AVAILABLE":
            return f"Priority override active. Status {status} with backup {backup}. {agent} can proceed."
        else:
            return f"Priority override active. Status {status}, backup {backup}. {agent} should hold."
    if rule == "SAFETY_FIRST":
        if status == "COMPROMISED":
            return f"SAFETY_FIRST: Status is {status}. {agent} must abort regardless of {priority} priority."
        elif status == "CLEAR":
            return f"SAFETY_FIRST: Status is {status}. {agent} can proceed with {priority} priority."
        else:
            return f"SAFETY_FIRST: Status is {status}. {agent} should wait for confirmation."
    elif rule == "MISSION_FIRST":
        if status == "COMPROMISED" and backup == "UNAVAILABLE":
            return f"MISSION_FIRST: Status {status} with no backup. Even mission-priority says {agent} should abort."
        else:
            return f"MISSION_FIRST: Priority is {priority}. {agent} should proceed. Status {status} is secondary."
    elif rule == "BALANCED":
        if priority == "HIGH" and backup == "AVAILABLE":
            return f"BALANCED: {priority} priority with backup {backup} outweighs {status} status. {agent} can proceed."
        elif status == "COMPROMISED":
            return f"BALANCED: {status} status not offset by {priority} priority. {agent} should abort."
        else:
            return f"BALANCED: Status {status}, priority {priority}. {agent} can proceed carefully."
    elif rule == "CAUTIOUS":
        if status == "CLEAR" and backup == "AVAILABLE":
            return f"CAUTIOUS: Status {status} AND backup {backup}. Both conditions met. {agent} can proceed."
        else:
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
# Curriculum stages. LRs scaled per-model via profile_lr_scale();
# epochs scaled via --epochs-scale (get_epochs_scale()).
# ============================================================

STAGES = [
    {"name": "Stage 0: Easy", "num_tokens": 256, "a_high": 1.0, "a_low": 0.0,
     "num_levels": 64, "samples": 15000, "epochs": 5, "lr": 5e-5, "general_ratio": 0.30},
    {"name": "Stage 1: Standard", "num_tokens": 256, "a_high": 1.0, "a_low": 0.1,
     "num_levels": 64, "samples": 20000, "epochs": 5, "lr": 3e-5, "general_ratio": 0.25},
    {"name": "Stage 2: Moderate", "num_tokens": 256, "a_high": 1.0, "a_low": 0.15,
     "num_levels": 64, "samples": 25000, "epochs": 7, "lr": 2e-5, "general_ratio": 0.20},
    {"name": "Stage 3: Harder", "num_tokens": 256, "a_high": 1.0, "a_low": 0.2,
     "num_levels": 64, "samples": 25000, "epochs": 7, "lr": 1e-5, "general_ratio": 0.15},
    {"name": "Stage 4: Hardest", "num_tokens": 256, "a_high": 1.0, "a_low": 0.25,
     "num_levels": 64, "samples": 30000, "epochs": 10, "lr": 1e-5, "general_ratio": 0.10},
]


# ============================================================
# General text dataset
# ============================================================

class GeneralTextDataset(Dataset):
    """Loads general text from a JSONL file (one {"text": "..."} per line).

    NOTE (fixed): max_length now defaults to None and is resolved via
    profile_max_length() inside __init__, not bound at function-definition
    time. The original `max_length=MAX_LENGTH` default captured MAX_LENGTH's
    value once at import -- the same late-binding bug already documented in
    project notes for FDMReasoningDataset's original K=320 truncation issue.

    NOTE (fixed): no longer pads every sample to max_length here. At
    num_channels=40 this barely mattered (samples were already close to
    filling 2048 tokens), but at the new num_channels=10 default, FDM
    samples are much shorter and padding='max_length' was wasting most
    of every forward/backward pass on filler tokens. Padding now happens
    per-batch, to the longest sample in that batch, via the collate_fn
    built by make_collate_fn() below (same dynamic-padding approach
    already used in fdm_twoblock_mixed_train.py).
    """
    def __init__(self, path, tokenizer, max_length=None):
        max_length = max_length or profile_max_length()
        self.samples = []
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    obj = json.loads(line)
                    text = obj.get("text", obj.get("instruction", ""))
                    if obj.get("input"):
                        text = text + "\n" + obj["input"]
                    if obj.get("output"):
                        text = text + "\n" + obj["output"]
                    if len(text) > 50:
                        self.samples.append(text)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text = self.samples[idx]
        encoding = self.tokenizer(
            text, truncation=True, max_length=self.max_length,
            return_tensors='pt')
        input_ids = encoding['input_ids'].squeeze(0)
        attention_mask = encoding['attention_mask'].squeeze(0)
        labels = input_ids.clone()  # train on full text (no masking)
        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'labels': labels,
        }

    def is_empty(self):
        return len(self.samples) == 0


def download_alpaca(output_path):
    from datasets import load_dataset
    print(f"  Downloading Alpaca dataset -> {output_path}")
    ds = load_dataset("tatsu-lab/alpaca", split="train")
    with open(output_path, 'w') as f:
        for item in ds:
            text = item.get("instruction", "")
            if item.get("input"):
                text += "\n" + item["input"]
            if item.get("output"):
                text += "\n" + item["output"]
            f.write(json.dumps({"text": text}) + "\n")
    print(f"  Wrote {len(ds)} samples to {output_path}")


# ============================================================
# FDM data generation
# ============================================================

def generate_stage_data(stage_config, num_samples, output_prefix):
    encoder = TurboFDMSignalEncoder(
        num_tokens_per_encoder=stage_config.get('num_tokens', 256),
        sample_rate=stage_config.get('sample_rate', 100.0),
        a_high=stage_config.get('a_high', 1.0),
        a_low=stage_config.get('a_low', 0.0),
        num_levels=stage_config.get('num_levels', 64),
    )
    samples = []
    print(f"Generating {num_samples} samples: {stage_config}  [model={MODEL_KEY}, channels={NUM_CHANNELS}]...")
    for _ in tqdm(range(num_samples)):
        memory = {}
        for ch in range(NUM_CHANNELS):
            _, values = MEMORY_SCHEMAS[ch]
            memory[ch] = random.choice(values)
        fdm_text, token_ids = encoder.encode_memory(memory)
        facts = {MEMORY_SCHEMAS[ch][0]: memory[ch] for ch in range(6)}
        rule = memory[6]
        meta = memory[7]
        extra = {MEMORY_SCHEMAS[ch][0]: memory[ch] for ch in range(8, NUM_CHANNELS)}
        q_template = random.choice(QUESTION_TEMPLATES)
        question = q_template["question"].format(**facts)
        base_answer = q_template["fn"](facts, rule, meta)
        extra_parts = [f"{k}={v}" for k, v in extra.items()]
        answer = f"{base_answer} Context: {', '.join(extra_parts)}."
        samples.append({
            "fdm_text": fdm_text,
            "memory": {str(k): v for k, v in memory.items()},
            "question": question,
            "answer": answer,
            "rule": rule,
            "meta": meta,
            "facts": facts,
            "model_key": MODEL_KEY,
            "num_channels": NUM_CHANNELS,
            "stage_config": {k: v for k, v in stage_config.items() if k != 'name'},
        })
    random.shuffle(samples)
    n = len(samples)
    splits = {
        'train': samples[:int(0.85 * n)],
        'val': samples[int(0.85 * n):int(0.95 * n)],
        'test': samples[int(0.95 * n):],
    }
    for split_name, split_data in splits.items():
        path = f"{output_prefix}_{split_name}.jsonl"
        with open(path, 'w') as f:
            for s in split_data:
                f.write(json.dumps(s) + "\n")
        print(f"  {split_name}: {len(split_data)} samples -> {path}")
    return samples


def generate_all_stages():
    for i, stage in enumerate(STAGES):
        print(f"\n{'='*60}")
        print(f"GENERATING STAGE {i}: {stage['name']} (model: {MODEL_KEY}, channels: {NUM_CHANNELS})")
        print(f"  general_ratio: {stage['general_ratio']}")
        print(f"{'='*60}")
        generate_stage_data(stage, stage['samples'], f"{OUTPUT_PREFIX()}_stage{i}")


# ============================================================
# FDM dataset
# ============================================================

class FDMReasoningDataset(Dataset):
    """NOTE (fixed): same max_length late-binding fix as GeneralTextDataset --
    default is None, resolved via profile_max_length() at call time.

    NOTE (fixed): no longer pads to max_length per-sample -- see
    GeneralTextDataset's docstring above. Padding now happens per-batch
    via make_collate_fn()."""
    def __init__(self, path, tokenizer, max_length=None):
        max_length = max_length or profile_max_length()
        self.samples = [json.loads(l) for l in open(path)]
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        input_text = f"[MEMORY]{s['fdm_text']}[/MEMORY]\nQuestion: {s['question']}\nAnswer:"
        target_text = f" {s['answer']}"
        full_text = input_text + target_text
        encoding = self.tokenizer(
            full_text, truncation=True, max_length=self.max_length,
            return_tensors='pt')
        input_ids = encoding['input_ids'].squeeze(0)
        attention_mask = encoding['attention_mask'].squeeze(0)
        labels = input_ids.clone()
        input_len = len(self.tokenizer.encode(input_text))
        labels[:input_len] = -100
        labels[attention_mask == 0] = -100
        return {
            'input_ids': input_ids,
            'attention_mask': attention_mask,
            'labels': labels,
        }


def make_collate_fn(pad_id):
    """Pads a batch of variable-length {input_ids, attention_mask, labels}
    dicts to the longest sample IN THAT BATCH, not to a fixed max_length.
    Same approach already used in fdm_twoblock_mixed_train.py."""
    def collate(batch):
        max_len = max(len(item['input_ids']) for item in batch)
        bsz = len(batch)
        input_ids = torch.full((bsz, max_len), pad_id, dtype=torch.long)
        attention_mask = torch.zeros((bsz, max_len), dtype=torch.long)
        labels = torch.full((bsz, max_len), -100, dtype=torch.long)
        for i, item in enumerate(batch):
            L = len(item['input_ids'])
            input_ids[i, :L] = item['input_ids']
            attention_mask[i, :L] = item['attention_mask']
            labels[i, :L] = item['labels']
        return {'input_ids': input_ids, 'attention_mask': attention_mask, 'labels': labels}
    return collate


# ============================================================
# Mixed-domain data loader (batching already correct -- now also
# uses per-batch dynamic padding instead of fixed max_length padding)
# ============================================================

class MixedDataLoader:
    """Yields batches from two datasets, interleaved at the given ratio."""

    def __init__(self, fdm_dataset, general_dataset, batch_size,
                 general_ratio=0.3, shuffle=True, pad_id=0):
        self.fdm_dataset = fdm_dataset
        self.general_dataset = general_dataset
        self.batch_size = batch_size
        self.general_ratio = general_ratio
        self.shuffle = shuffle

        collate = make_collate_fn(pad_id)
        self.fdm_loader = DataLoader(fdm_dataset, batch_size=batch_size, shuffle=shuffle,
                                      collate_fn=collate)
        self.has_general = general_dataset is not None and not general_dataset.is_empty()
        if self.has_general:
            self.general_loader = DataLoader(general_dataset, batch_size=batch_size, shuffle=shuffle,
                                              collate_fn=collate)
            self.general_iter = iter(self.general_loader)
        else:
            self.general_loader = None

        self.fdm_iter = iter(self.fdm_loader)
        self.n_fdm = len(self.fdm_loader)
        self.n_general = len(self.general_loader) if self.has_general else 0
        self.total_batches = self.n_fdm

    def __len__(self):
        return self.total_batches

    def __iter__(self):
        self.fdm_iter = iter(self.fdm_loader)
        if self.has_general:
            self.general_iter = iter(self.general_loader)
        for i in range(self.total_batches):
            if self.has_general and random.random() < self.general_ratio:
                try:
                    batch = next(self.general_iter)
                except StopIteration:
                    self.general_iter = iter(self.general_loader)
                    batch = next(self.general_iter)
            else:
                try:
                    batch = next(self.fdm_iter)
                except StopIteration:
                    self.fdm_iter = iter(self.fdm_loader)
                    batch = next(self.fdm_iter)
            yield batch


# ============================================================
# Training
# ============================================================

def train(general_data_path=DEFAULT_GENERAL_DATA, override_ratio=None):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    batch_size = get_batch_size()
    epochs_scale = get_epochs_scale()
    print(f"Device: {device}")
    print(f"Model: {MODEL_ID}  [model_key={MODEL_KEY}]")
    print(f"Channels: {NUM_CHANNELS}")
    print(f"max_length={profile_max_length()}  dtype={profile_dtype()}  lr_scale={profile_lr_scale()}  "
          f"batch_size={batch_size}  epochs_scale={epochs_scale}  grad_checkpointing={get_grad_checkpoint()}")
    ckpt_dir = CHECKPOINT_DIR()
    os.makedirs(ckpt_dir, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    special_tokens = tokenizer.add_special_tokens({
        'additional_special_tokens': ['[MEMORY]', '[/MEMORY]']
    })
    print(f"Added {special_tokens} special tokens")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, torch_dtype=profile_dtype(), trust_remote_code=True)
    model.resize_token_embeddings(len(tokenizer))
    if get_grad_checkpoint():
        model.gradient_checkpointing_enable()
    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total params: {total_params:,}")
    print(f"Trainable params: {trainable_params:,}")

    general_ds = None
    if os.path.exists(general_data_path):
        general_ds = GeneralTextDataset(general_data_path, tokenizer)
        print(f"General text: {len(general_ds)} samples from {general_data_path}")
    else:
        print(f"WARNING: {general_data_path} not found. Training FDM-only (will forget NL).")
        print(f"  To enable mixed-domain, download Alpaca:")
        print(f"  python fdm_mixed_domain_train_multi.py download-alpaca")

    # Resume, with a checkpoint-signature guard: refuse to silently
    # resume from a checkpoint stamped with a different model_key or
    # num_channels, since the FDM carrier's normalization range scales
    # with num_channels (sig_min/sig_max) -- a channel-count mismatch
    # means the checkpoint was trained on a different signal space.
    resume_stage = 0
    resume_epoch = 0
    run_signature = {'model_key': MODEL_KEY, 'num_channels': NUM_CHANNELS}
    ckpt_files = sorted([f for f in os.listdir(ckpt_dir) if f.endswith('.pt')])
    if ckpt_files:
        latest = ckpt_files[-1]
        print(f"Found checkpoint: {latest}")
        ckpt = torch.load(os.path.join(ckpt_dir, latest), map_location=device)
        ckpt_sig = {'model_key': ckpt.get('model_key'), 'num_channels': ckpt.get('num_channels')}
        if ckpt_sig.get('model_key') is not None and ckpt_sig != run_signature:
            raise SystemExit(
                f"ABORT: {latest} was produced with {ckpt_sig}, but this run is "
                f"configured as {run_signature}. Move or remove {ckpt_dir}/ if you "
                f"intend to start a fresh run under the new settings.")
        if ckpt_sig.get('model_key') is None:
            print(f"WARNING: {latest} predates checkpoint signature stamping -- "
                  f"resuming without verifying it matches the current run's config.")
        model.load_state_dict(ckpt['model_state_dict'])
        resume_stage = ckpt.get('stage', 0)
        resume_epoch = ckpt.get('epoch', 0) + 1
        print(f"Resuming from stage {resume_stage}, epoch {resume_epoch}")

    for stage_idx, stage in enumerate(STAGES):
        if stage_idx < resume_stage:
            print(f"Skipping stage {stage_idx} (already completed)")
            continue

        prefix = f"{OUTPUT_PREFIX()}_stage{stage_idx}"
        train_path = f"{prefix}_train.jsonl"
        val_path = f"{prefix}_val.jsonl"

        if not os.path.exists(train_path):
            print(f"ERROR: {train_path} not found. Run 'generate' first "
                  f"(with matching --model-key/--num-channels).")
            return

        gr = override_ratio if override_ratio is not None else stage['general_ratio']
        stage_lr = stage['lr'] * profile_lr_scale()
        stage_epochs = max(1, round(stage['epochs'] * epochs_scale))
        print(f"\n{'='*60}")
        print(f"STAGE {stage_idx}: {stage['name']} [{MODEL_KEY}]")
        print(f"  lr={stage_lr:.1e}, epochs={stage_epochs} (base {stage['epochs']} x scale {epochs_scale}), "
              f"general_ratio={gr}")
        print(f"{'='*60}")

        fdm_train = FDMReasoningDataset(train_path, tokenizer)
        fdm_val = FDMReasoningDataset(val_path, tokenizer)

        mixed_loader = MixedDataLoader(
            fdm_train, general_ds, batch_size,
            general_ratio=gr, shuffle=True, pad_id=tokenizer.pad_token_id)
        val_loader = DataLoader(fdm_val, batch_size=batch_size,
                                 collate_fn=make_collate_fn(tokenizer.pad_token_id))

        optimizer = AdamW(model.parameters(), lr=stage_lr)
        best_val_loss = float('inf')

        start_epoch = resume_epoch if stage_idx == resume_stage else 0
        resume_epoch = 0

        for epoch in range(start_epoch, stage_epochs):
            model.train()
            train_loss = 0
            n_batches = 0
            for batch in tqdm(mixed_loader, desc=f"S{stage_idx} E{epoch+1} Train"):
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                outputs = model(input_ids=input_ids,
                               attention_mask=attention_mask, labels=labels)
                loss = outputs.loss
                train_loss += loss.item()
                n_batches += 1
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            train_loss /= max(n_batches, 1)

            model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch['input_ids'].to(device)
                    attention_mask = batch['attention_mask'].to(device)
                    labels = batch['labels'].to(device)
                    outputs = model(input_ids=input_ids,
                                   attention_mask=attention_mask, labels=labels)
                    val_loss += outputs.loss.item()
            val_loss /= max(len(val_loader), 1)

            print(f"  Stage {stage_idx} Epoch {epoch+1}: "
                  f"Train={train_loss:.4f}, Val={val_loss:.4f}")

            if (epoch + 1) % 2 == 0 or epoch == stage_epochs - 1:
                mixed_eval(model, tokenizer, val_path, device,
                           num_samples=5, stage_idx=stage_idx)

            if val_loss < best_val_loss:
                best_val_loss = val_loss

            torch.save({
                'model_state_dict': model.state_dict(),
                'stage': stage_idx,
                'epoch': epoch,
                'val_loss': val_loss,
                'model_id': MODEL_ID,
                'model_key': MODEL_KEY,
                'num_channels': NUM_CHANNELS,
                'general_ratio': gr,
            }, os.path.join(ckpt_dir, f'stage{stage_idx}_epoch{epoch+1}.pt'))

        model.save_pretrained(f'{OUTPUT_PREFIX()}_model_stage{stage_idx}')
        tokenizer.save_pretrained(f'{OUTPUT_PREFIX()}_model_stage{stage_idx}')

    final_dir = FINAL_MODEL_DIR()
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"\nSaved final model: {final_dir}/")


# ============================================================
# Mixed evaluation (tests BOTH FDM and natural language, prints
# actual generated text -- not just a pass/fail count)
# ============================================================

def _normalize_for_nl_match(s):
    """Strip diacritics before substring matching so 'Brasilia' matches
    a correctly-accented 'Brasília' response instead of being marked a
    false FAIL. NFKD-decomposes accented chars into base+combining-mark
    pairs, then drops the combining marks (unicode category 'Mn')."""
    decomposed = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in decomposed if not unicodedata.combining(c)).lower()


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


def mixed_eval(model, tokenizer, val_path, device, num_samples=5, stage_idx=0):
    """Quick eval: both FDM retrieval and natural language recall."""
    model.eval()

    fdm_samples = [json.loads(l) for l in open(val_path)][:num_samples]
    fdm_correct = 0
    fdm_total = 0
    for s in fdm_samples:
        input_text = f"[MEMORY]{s['fdm_text']}[/MEMORY]\nQuestion: {s['question']}\nAnswer:"
        input_ids = tokenizer.encode(input_text, return_tensors='pt').to(device)
        with torch.no_grad():
            output = model.generate(input_ids, max_new_tokens=250,
                                    do_sample=False,
                                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        response = tokenizer.decode(output[0][input_ids.shape[1]:],
                                    skip_special_tokens=True).strip()
        for kw in ['abort', 'proceed', 'hold', 'wait', 'EMERGENCY', 'LOCKDOWN',
                   'share', 'HIGH RISK', 'LOW RISK', 'MODERATE']:
            if kw.lower() in s['answer'].lower() and kw.lower() in response.lower():
                fdm_correct += 1
                break
        fdm_total += 1

    nl_correct = 0
    nl_total = 0
    nl_misses = []
    for question, expected in NL_QUESTIONS:
        prompt = f"Question: {question}\nAnswer:"
        input_ids = tokenizer.encode(prompt, return_tensors='pt').to(device)
        with torch.no_grad():
            output = model.generate(input_ids, max_new_tokens=30,
                                    do_sample=False,
                                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        response = tokenizer.decode(output[0][input_ids.shape[1]:],
                                    skip_special_tokens=True).strip()
        ok = _normalize_for_nl_match(expected) in _normalize_for_nl_match(response)
        if ok:
            nl_correct += 1
        else:
            nl_misses.append((question, response[:60]))
        nl_total += 1

    print(f"    [S{stage_idx} {MODEL_KEY}] FDM: {fdm_correct}/{fdm_total} | "
          f"NL: {nl_correct}/{nl_total}", flush=True)
    for q, got in nl_misses:
        print(f"      NL MISS: {q}  ->  {got!r}", flush=True)


# ============================================================
# Full evaluation
# ============================================================

def evaluate(model_path=None, stage_idx=None):
    if model_path is None:
        model_path = FINAL_MODEL_DIR()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Loading {MODEL_KEY} model from {model_path}/...")

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=profile_dtype(), trust_remote_code=True)
    model.to(device)
    model.eval()

    si = stage_idx if stage_idx is not None else 4
    test_path = f"{OUTPUT_PREFIX()}_stage{si}_test.jsonl"

    if not os.path.exists(test_path):
        print(f"ERROR: {test_path} not found.")
        return

    test_samples = [json.loads(l) for l in open(test_path)]
    print(f"Evaluating on {len(test_samples)} FDM samples (stage {si})...\n")

    action_correct = 0
    ch_correct = {}
    ch_total = {}
    rule_correct = 0
    meta_correct = 0
    fact_correct = 0
    extra_correct = 0
    extra_total = 0
    total = 0

    for i, s in enumerate(tqdm(test_samples, desc=f"Evaluating [{MODEL_KEY}]")):
        input_text = f"[MEMORY]{s['fdm_text']}[/MEMORY]\nQuestion: {s['question']}\nAnswer:"
        input_ids = tokenizer.encode(input_text, return_tensors='pt').to(device)
        with torch.no_grad():
            output = model.generate(input_ids, max_new_tokens=250,
                                    do_sample=False,
                                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        response = tokenizer.decode(output[0][input_ids.shape[1]:],
                                    skip_special_tokens=True).strip()
        expected = s['answer']
        rule = s['rule']
        meta = s['meta']

        action_ok = False
        for kw in ['abort', 'proceed', 'hold', 'wait', 'EMERGENCY', 'LOCKDOWN',
                    'share', 'Do NOT share', 'Do not share', 'HIGH RISK', 'LOW RISK', 'MODERATE']:
            if kw.lower() in expected.lower() and kw.lower() in response.lower():
                action_ok = True
                break
        if action_ok: action_correct += 1

        if rule in response: rule_correct += 1

        meta_ok = False
        if meta == "EMERGENCY" and "EMERGENCY" in response: meta_ok = True
        elif meta == "LOCKDOWN" and "LOCKDOWN" in response: meta_ok = True
        elif meta in ["NONE", "OVERRIDE_STATUS", "OVERRIDE_PRIORITY"]: meta_ok = True
        if meta_ok: meta_correct += 1

        fact_ok = False
        facts = s['facts']
        if s['question'].startswith("Should"):
            fact_ok = facts['AGENT'] in response
        elif s['question'].startswith("What is the risk"):
            fact_ok = facts['LOCATION'] in response
        elif s['question'].startswith("Is it safe"):
            fact_ok = facts['SECRET'] in response or facts['LOCATION'] in response
        if fact_ok: fact_correct += 1

        memory = s['memory']
        for ch in range(8, NUM_CHANNELS):
            name = MEMORY_SCHEMAS[ch][0]
            expected_val = memory[str(ch)]
            extra_total += 1
            ch_total[ch] = ch_total.get(ch, 0) + 1
            ch_correct[ch] = ch_correct.get(ch, 0)
            if expected_val in response:
                extra_correct += 1
                ch_correct[ch] += 1
        total += 1

    print(f"\n--- Natural Language Evaluation ---")
    nl_correct = 0
    nl_total = 0
    for question, expected in NL_QUESTIONS:
        prompt = f"Question: {question}\nAnswer:"
        input_ids = tokenizer.encode(prompt, return_tensors='pt').to(device)
        with torch.no_grad():
            output = model.generate(input_ids, max_new_tokens=30,
                                    do_sample=False,
                                    pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        response = tokenizer.decode(output[0][input_ids.shape[1]:],
                                    skip_special_tokens=True).strip()
        ok = _normalize_for_nl_match(expected) in _normalize_for_nl_match(response)
        if ok: nl_correct += 1
        nl_total += 1
        flag = "OK" if ok else "FAIL"
        print(f"  [{flag}] Q: {question}")
        print(f"        Got: {response[:80]}")

    print(f"\n{'='*60}")
    print(f"{MODEL_KEY.upper()} MIXED-DOMAIN FDM EVALUATION  [channels={NUM_CHANNELS}]")
    print(f"{'='*60}")
    print(f"  Action:  {100*action_correct/total:.1f}%")
    print(f"  Rule:    {100*rule_correct/total:.1f}%")
    print(f"  Meta:    {100*meta_correct/total:.1f}%")
    print(f"  Fact:    {100*fact_correct/total:.1f}%")
    print(f"  Extra:   {100*extra_correct/max(extra_total,1):.1f}%")
    print(f"  NL:      {100*nl_correct/nl_total:.1f}%")
    print("")
    print(f"Per-Channel Extra Accuracy (ch8-{NUM_CHANNELS-1}):")
    for ch in range(8, NUM_CHANNELS):
        t = ch_total.get(ch, 0)
        c = ch_correct.get(ch, 0)
        pct = 100 * c / t if t else 0
        flag = " <<<" if pct < 99 else ""
        print(f"  ch{ch:2d} ({MEMORY_SCHEMAS[ch][0]:<12}): {pct:.1f}%{flag}")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['generate', 'download-alpaca', 'train', 'eval'])
    parser.add_argument('--stage', type=int, default=None,
                        help='For eval: which stage to evaluate (default: last stage, 4)')
    parser.add_argument('--model-key', choices=list(MODEL_PROFILES.keys()), default='qwen3-0.6b')
    parser.add_argument('--num-channels', type=int, default=10,
                        help='Total FDM channels to train (default 10, down from the original 40). '
                             'Must be >= 8. Pass 40 to restore the original full-schema behavior.')
    parser.add_argument('--tokens', type=int, default=256)
    parser.add_argument('--general-data', default=DEFAULT_GENERAL_DATA)
    parser.add_argument('--general-ratio', type=float, default=None,
                        help='Override per-stage general ratio (e.g. 0.30)')
    parser.add_argument('--batch-size', type=int, default=None,
                        help='Override BATCH_SIZE=4')
    parser.add_argument('--epochs-scale', type=float, default=1.0,
                        help='Multiply every curriculum stage\'s epoch count')
    parser.add_argument('--disable-grad-checkpointing', action='store_true',
                        help='Trade VRAM for ~20-30%% speedup (default: checkpointing ON)')

    if len(sys.argv) < 2:
        print(f"Mixed-Domain FDM Training (multi-model, single-block, no over-training Phase 2)")
        print(f"Usage:")
        print(f"  python fdm_mixed_domain_train_multi.py download-alpaca")
        print(f"  python fdm_mixed_domain_train_multi.py generate --model-key lfm2.5-1.2b")
        print(f"  python fdm_mixed_domain_train_multi.py train --model-key lfm2.5-1.2b --batch-size 8")
        print(f"  python fdm_mixed_domain_train_multi.py eval --model-key lfm2.5-1.2b --stage 4")
        sys.exit(0)

    args = parser.parse_args()

    apply_model_profile(args.model_key)
    set_num_channels(args.num_channels)
    set_runtime_overrides(batch_size=args.batch_size,
                           epochs_scale=args.epochs_scale,
                           grad_checkpoint=not args.disable_grad_checkpointing)

    if args.tokens != 256:
        for s in STAGES:
            s['num_tokens'] = args.tokens
        print(f'Token budget override: {args.tokens} per encoder = {args.tokens*2} total')

    cmd = args.command
    if cmd == "generate":
        generate_all_stages()
    elif cmd == "download-alpaca":
        download_alpaca(args.general_data)
    elif cmd == "train":
        train(general_data_path=args.general_data,
              override_ratio=args.general_ratio)
    elif cmd == "eval":
        evaluate(stage_idx=args.stage)
