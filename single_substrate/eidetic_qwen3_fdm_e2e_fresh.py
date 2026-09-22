"""
Eidetic Memory FDM — Qwen3-0.6B-Base Adaptation (corrected Meta scoring)

Uses fdm_common.py for all encoding, reasoning, dataset, and
evaluation logic. See fdm_common.py's module docstring for the Meta
scoring bugfix this incorporates.

Usage:
  python eidetic_qwen3_fdm_e2e.py generate
  python eidetic_qwen3_fdm_e2e.py train
  python eidetic_qwen3_fdm_e2e.py eval [stage]
"""

import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer
from torch.optim import AdamW
import os

from fdm_common import (
    NUM_CHANNELS, STAGES, FDMReasoningDataset, generate_stage_data, evaluate_model,
)

MODEL_ID = "Qwen/Qwen3-0.6B-Base"
MODEL_SHORT = "qwen3"
VOCAB_SIZE = 151936
DTYPE = torch.bfloat16
BATCH_SIZE = 4
MAX_LENGTH = 1024
OUTPUT_PREFIX = "fdm_40ch_fresh_qwen3"
CHECKPOINT_DIR = "checkpoints_fdm_fresh_qwen3"
FINAL_MODEL_DIR = "fdm_40ch_fresh_qwen3_model_final"


def get_tokenizer():
    tok = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.add_special_tokens({'additional_special_tokens': ['[MEMORY]', '[/MEMORY]']})
    return tok


def generate_all_stages():
    tokenizer = get_tokenizer()
    for i, stage in enumerate(STAGES):
        print(f"\n{'='*60}\nGENERATING STAGE {i}: {stage['name']} (model: {MODEL_SHORT})\n{'='*60}")
        generate_stage_data(stage, stage['samples'], f"{OUTPUT_PREFIX}_stage{i}", tokenizer, VOCAB_SIZE)


def train():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}\nModel: {MODEL_ID}\nChannels: {NUM_CHANNELS}")
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    tokenizer = get_tokenizer()
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, dtype=DTYPE, trust_remote_code=True)
    model.resize_token_embeddings(len(tokenizer))
    model.gradient_checkpointing_enable()
    model.to(device)

    resume_stage, resume_epoch = 0, 0
    ckpt_files = sorted([f for f in os.listdir(CHECKPOINT_DIR) if f.endswith('.pt')]) if os.path.isdir(CHECKPOINT_DIR) else []
    if ckpt_files:
        ckpt = torch.load(os.path.join(CHECKPOINT_DIR, ckpt_files[-1]), map_location=device)
        model.load_state_dict(ckpt['model_state_dict'])
        resume_stage = ckpt.get('stage', 0)
        resume_epoch = ckpt.get('epoch', 0) + 1
        print(f"Resuming from stage {resume_stage}, epoch {resume_epoch}")

    for stage_idx, stage in enumerate(STAGES):
        if stage_idx < resume_stage:
            continue
        prefix = f"{OUTPUT_PREFIX}_stage{stage_idx}"
        train_path, val_path = f"{prefix}_train.jsonl", f"{prefix}_val.jsonl"
        if not os.path.exists(train_path):
            print(f"ERROR: {train_path} not found. Run 'generate' first.")
            return

        print(f"\n{'='*60}\nSTAGE {stage_idx}: {stage['name']} [{MODEL_SHORT}]\n{'='*60}")
        train_loader = DataLoader(FDMReasoningDataset(train_path, tokenizer, MAX_LENGTH), batch_size=BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(FDMReasoningDataset(val_path, tokenizer, MAX_LENGTH), batch_size=BATCH_SIZE)
        optimizer = AdamW(model.parameters(), lr=stage['lr'])
        best_val_loss = float('inf')
        start_epoch = resume_epoch if stage_idx == resume_stage else 0
        resume_epoch = 0

        for epoch in range(start_epoch, stage['epochs']):
            model.train()
            train_loss = 0
            for batch in train_loader:
                input_ids = batch['input_ids'].to(device)
                attention_mask = batch['attention_mask'].to(device)
                labels = batch['labels'].to(device)
                outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                loss = outputs.loss
                train_loss += loss.item()
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            train_loss /= len(train_loader)

            model.eval()
            val_loss = 0
            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch['input_ids'].to(device)
                    attention_mask = batch['attention_mask'].to(device)
                    labels = batch['labels'].to(device)
                    outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
                    val_loss += outputs.loss.item()
            val_loss /= len(val_loader)
            print(f"  Stage {stage_idx} Epoch {epoch+1}: Train={train_loss:.4f}, Val={val_loss:.4f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                print(f"  New best val loss: {val_loss:.4f}")

            torch.save({
                'model_state_dict': model.state_dict(), 'stage': stage_idx, 'epoch': epoch,
                'val_loss': val_loss, 'model_id': MODEL_ID,
            }, os.path.join(CHECKPOINT_DIR, f'stage{stage_idx}_epoch{epoch+1}.pt'))

        model.save_pretrained(f'{OUTPUT_PREFIX}_model_stage{stage_idx}')
        tokenizer.save_pretrained(f'{OUTPUT_PREFIX}_model_stage{stage_idx}')

    model.save_pretrained(FINAL_MODEL_DIR)
    tokenizer.save_pretrained(FINAL_MODEL_DIR)
    print(f"\nSaved final model: {FINAL_MODEL_DIR}/")


def evaluate(model_path=None, stage_idx=None):
    model_path = model_path or FINAL_MODEL_DIR
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_path, dtype=DTYPE, trust_remote_code=True).to(device).eval()
    si = stage_idx if stage_idx is not None else 4
    test_path = f"{OUTPUT_PREFIX}_stage{si}_test.jsonl"
    return evaluate_model(model, tokenizer, test_path, device, MODEL_SHORT)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} [generate|train|eval [stage]]")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "generate":
        generate_all_stages()
    elif cmd == "train":
        train()
    elif cmd == "eval":
        evaluate(stage_idx=int(sys.argv[2]) if len(sys.argv) > 2 else None)
