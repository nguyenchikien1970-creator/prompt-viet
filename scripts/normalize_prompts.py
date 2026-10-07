#!/usr/bin/env python3
"""
Normalization script for prompt-viet project.
Converts raw prompts from prompts_original.json into the standardized SCHEMA.md format.
Preserves original source category and tags.
No translation, no enrichment, no external AI APIs, pure rule-based preprocessing.
"""

import os
import re
import json
import argparse

ORIGINAL_JSON_PATH = "prompt-viet/data/original/prompts_original.json"
NORMALIZED_TEST_OUTPUT = "prompt-viet/data/normalized/test_10_normalized.json"

def detect_language(text):
    """
    Heuristic rule-based language detector.
    Returns (language_code, detection_method).
    Never claims 100% certainty; returns (None, 'unknown') if uncertain.
    """
    if not text or not isinstance(text, str):
        return None, "unknown"

    # Ethiopic script range (Amharic)
    if re.search(r'[\u1200-\u137F]', text):
        return "am", "rule_based"

    # Cyrillic script
    if re.search(r'[\u0400-\u04FF]', text):
        return "ru", "rule_based"

    lower_text = text.lower()

    # Spanish cues (heuristic)
    spanish_cues = ["quiero ", "imagen ", "para linkedin", "por lo que", "se muestre", "adjunto", "profesional", "gracias"]
    if sum(1 for cue in spanish_cues if cue in lower_text) >= 2:
        return "es", "rule_based"

    # French cues (heuristic)
    french_cues = ["ton rôle", "créateur", "selon la", "dans les", "derniers", "quelque chose", "j'ai ma", "societe", "pour avoir", "c'est"]
    if sum(1 for cue in french_cues if cue in lower_text) >= 2:
        return "fr", "rule_based"

    # English cues (heuristic)
    english_cues = ["the ", "you are ", "act as ", "i want you to ", "create ", "generate ", "write ", "check ", "please "]
    if sum(1 for cue in english_cues if cue in lower_text) >= 1:
        return "en", "rule_based"

    # Fallback to unknown if not confident
    return None, "unknown"

def determine_model_type(raw_type, raw_category_name):
    cat_str = (raw_category_name or "").lower()
    raw_type_str = (raw_type or "").upper()

    if raw_type_str == "IMAGE" or "image" in cat_str:
        return ["image"]
    if raw_type_str == "VIDEO" or "video" in cat_str:
        return ["video"]
    if raw_type_str == "CODE" or "coding" in cat_str or "developer" in cat_str:
        return ["coding"]

    return ["text"]

def normalize_prompt(raw_prompt):
    # 1. Source category & tags preservation
    category_obj = raw_prompt.get("category")
    source_category = category_obj.get("name") if isinstance(category_obj, dict) else None

    raw_tags = raw_prompt.get("tags") or []
    source_tags = []
    for t in raw_tags:
        if isinstance(t, dict) and t.get("name"):
            source_tags.append(t["name"])
        elif isinstance(t, str):
            source_tags.append(t)

    # 2. Source URL and Slug
    slug = raw_prompt.get("slug")
    source_url = f"https://prompts.chat/p/{slug}" if slug else "https://prompts.chat"

    # 3. Language detection (heuristic)
    content_text = raw_prompt.get("content") or ""
    title_text = raw_prompt.get("title") or ""
    detected_lang, detection_method = detect_language(f"{title_text} {content_text[:300]}")

    # 4. Model type
    model_type = determine_model_type(raw_prompt.get("type"), source_category)

    # 5. Build standardized record
    normalized_record = {
        "id": raw_prompt.get("id"),
        "slug": slug,
        "original_title": raw_prompt.get("title"),
        "original_prompt": raw_prompt.get("content"),
        "language_original": detected_lang,
        "language_detection": detection_method,
        "vi_title": None,
        "vi_prompt": None,
        "translation_status": "pending",
        # Source preservation
        "source_category": source_category,
        "source_tags": source_tags,
        # Normalized targets (to be enriched later by AI, not overwritten)
        "category": None,
        "subcategory": None,
        "tags": [],
        "search_keywords_vi": [],
        "use_case": None,
        # Classification & Quality
        "model_type": model_type,
        "difficulty": None,
        "quality_status": "unreviewed",
        # Attribution
        "author": raw_prompt.get("author"),
        "source": "prompts.chat",
        "source_url": source_url,
        "created_at": raw_prompt.get("createdAt")
    }

    return normalized_record

def main():
    parser = argparse.ArgumentParser(description="Normalize prompts data.")
    parser.add_argument("--limit", type=int, default=None, help="Number of prompts to normalize (default: all)")
    parser.add_argument("--all", action="store_true", default=False, help="Normalize all prompts")
    parser.add_argument("--output", type=str, default="prompt-viet/data/normalized/prompts_normalized.json", help="Output JSON path")
    args = parser.parse_args()

    if not os.path.exists(ORIGINAL_JSON_PATH):
        raise FileNotFoundError(f"Missing source file: {ORIGINAL_JSON_PATH}")

    with open(ORIGINAL_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_prompts = data.get("prompts", [])
    if args.limit and not args.all:
        prompts_to_process = all_prompts[:args.limit]
    else:
        prompts_to_process = all_prompts

    print(f"Normalizing {len(prompts_to_process)} prompts...")

    normalized_list = [normalize_prompt(p) for p in prompts_to_process]

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(normalized_list, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(normalized_list)} normalized records to: {args.output}")

if __name__ == "__main__":
    main()
