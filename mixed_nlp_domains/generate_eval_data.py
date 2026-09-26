#!/usr/bin/env python3
"""
Generate routing_eval_test.jsonl for J-lens analysis.
Uses TurboFDMSignalEncoder and MEMORY_SCHEMAS from fdm_mixed_domain_train.
"""
import json
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fdm_mixed_domain_train import TurboFDMSignalEncoder, MEMORY_SCHEMAS, NUM_CHANNELS


def generate_eval_samples(num_samples=200, seed=42):
    rng = np.random.RandomState(seed)
    encoder = TurboFDMSignalEncoder(
        num_tokens_per_encoder=256,
        sample_rate=100.0,
        a_high=1.0,
        a_low=0.25,
        num_levels=64,
        seed=42,
    )
    print(f"Encoder: TurboFDMSignalEncoder, {encoder.num_channels} channels, "
          f"{encoder.num_tokens_per_encoder} tokens/encoder")

    samples = []
    for i in range(num_samples):
        # Generate random memory: {channel_id: value_string}
        memory = {}
        for ch in range(NUM_CHANNELS):
            _, values = MEMORY_SCHEMAS[ch]
            memory[ch] = str(rng.choice(values))

        # Encode
        try:
            fdm_text, tokens = encoder.encode_memory(memory)
        except Exception as e:
            if i == 0:
                print(f"Error encoding sample 0: {e}")
                return []
            continue

        # Question about a few context channels (8-39)
        query_channels = rng.choice(range(8, 40), size=rng.randint(1, 4), replace=False)
        query_names = [MEMORY_SCHEMAS[ch][0] for ch in query_channels]

        if len(query_names) == 1:
            question = f"What is the value of {query_names[0]}?"
        else:
            question = f"Report the following: {', '.join(query_names)}."

        answer_parts = [f"{MEMORY_SCHEMAS[ch][0]}={memory[ch]}" for ch in query_channels]
        answer = ". ".join(answer_parts) + "."

        # Full context block (ch 8-39)
        context_parts = [f"{MEMORY_SCHEMAS[ch][0]}={memory[ch]}" for ch in range(8, 40)]
        context_block = "Context: " + ", ".join(context_parts) + "."
        full_answer = answer + " " + context_block

        samples.append({
            "fdm_text": fdm_text,
            "question": question,
            "answer": full_answer,
            "memory": {str(k): v for k, v in memory.items()},
            "query_channels": [int(c) for c in query_channels],
        })

    return samples


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--out", type=str, default="routing_eval_test.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Generating {args.n} eval samples...")
    samples = generate_eval_samples(args.n, args.seed)

    if not samples:
        print("ERROR: No samples generated!")
        sys.exit(1)

    with open(args.out, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    print(f"Wrote {len(samples)} samples to {args.out}")
    print(f"Sample 0 question: {samples[0]['question']}")
    print(f"Sample 0 answer (first 200 chars): {samples[0]['answer'][:200]}...")
    print(f"Sample 0 fdm_text (first 100 chars): {samples[0]['fdm_text'][:100]}...")


if __name__ == "__main__":
    main()
