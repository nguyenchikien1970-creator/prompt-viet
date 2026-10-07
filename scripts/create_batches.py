#!/usr/bin/env python3
"""
Script to partition prompts_original.json into batches of 50 prompts.
Pure data pipeline: does NOT translate or modify original prompt content.
"""

import os
import json
import argparse

ORIGINAL_JSON_PATH = "prompt-viet/data/original/prompts_original.json"
BATCHES_DIR = "prompt-viet/data/batches"
BATCH_SIZE = 50

def parse_author(author_data):
    if not author_data:
        return "Unknown"
    if isinstance(author_data, dict):
        return author_data.get("name") or author_data.get("username") or "Unknown"
    return str(author_data)

def create_batches(test_only=False):
    if not os.path.exists(ORIGINAL_JSON_PATH):
        raise FileNotFoundError(f"Missing source file: {ORIGINAL_JSON_PATH}")

    os.makedirs(BATCHES_DIR, exist_ok=True)

    with open(ORIGINAL_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    total_prompts = len(prompts)
    print(f"Loaded {total_prompts} prompts from {ORIGINAL_JSON_PATH}.")

    total_batches = (total_prompts + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Total batches expected: {total_batches} (batch size: {BATCH_SIZE})")

    batches_to_create = 1 if test_only else total_batches

    for batch_num in range(1, batches_to_create + 1):
        start_idx = (batch_num - 1) * BATCH_SIZE
        end_idx = min(start_idx + BATCH_SIZE, total_prompts)
        batch_slice = prompts[start_idx:end_idx]

        batch_items = []
        for p in batch_slice:
            batch_items.append({
                "id": p.get("id", ""),
                "original_title": p.get("title", ""),
                "original_prompt": p.get("content", ""),
                "author": parse_author(p.get("author")),
                "source": "prompts.chat",
                "original_category": p.get("category"),
                "original_tags": [t.get("name") for t in p.get("tags", []) if isinstance(t, dict) and t.get("name")]
            })

        batch_filename = f"batch_{batch_num:03d}_input.json"
        batch_filepath = os.path.join(BATCHES_DIR, batch_filename)

        with open(batch_filepath, "w", encoding="utf-8") as bf:
            json.dump(batch_items, bf, ensure_ascii=False, indent=2)

        print(f"Created {batch_filepath} ({len(batch_items)} prompts, index {start_idx} to {end_idx - 1}).")

    if test_only:
        print("\nTest mode active: Created only batch_001_input.json as requested.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Partition prompts into batches.")
    parser.add_argument("--test-only", action="store_true", default=False, help="Only generate batch_001_input.json")
    parser.add_argument("--all", action="store_true", default=False, help="Generate all batches")
    args = parser.parse_args()

    # Default to test_only unless --all is explicitly provided
    is_test = not args.all or args.test_only
    create_batches(test_only=is_test)
