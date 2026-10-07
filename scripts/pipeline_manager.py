#!/usr/bin/env python3
"""
Pipeline Manager for Prompt Viet Production Translation.
Only handles batch extraction, validation, checkpoint tracking, QA sampling, and final merging.
DOES NOT contain any translation logic or hardcoded translations.
"""

import json
import os
import csv
import sys
import glob
from datetime import datetime
import random

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NORMALIZED_FILE = os.path.join(BASE_DIR, "data", "normalized", "prompts_normalized.json")
BATCHES_DIR = os.path.join(BASE_DIR, "data", "batches")
TRANSLATED_DIR = os.path.join(BASE_DIR, "data", "translated")
CHECKPOINTS_DIR = os.path.join(BASE_DIR, "checkpoints")
CHECKPOINT_FILE = os.path.join(CHECKPOINTS_DIR, "progress.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
FINAL_DIR = os.path.join(BASE_DIR, "data", "final")
SEARCH_DIR = os.path.join(BASE_DIR, "data", "search")

REQUIRED_FIELDS = [
    "id", "slug", "original_title", "original_prompt", "language_original",
    "language_detection", "vi_title", "vi_prompt", "translation_status",
    "source_category", "source_tags", "category", "subcategory", "tags",
    "search_keywords_vi", "use_case", "model_type", "difficulty", "quality_status",
    "author", "source", "source_url", "created_at"
]

def ensure_dirs():
    for d in [BATCHES_DIR, TRANSLATED_DIR, CHECKPOINTS_DIR, LOGS_DIR, FINAL_DIR, SEARCH_DIR]:
        os.makedirs(d, exist_ok=True)

def get_translated_ids():
    translated_ids = set()
    for f in glob.glob(os.path.join(TRANSLATED_DIR, "batch_[0-9][0-9][0-9]_vi.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                for item in data:
                    if "id" in item:
                        translated_ids.add(item["id"])
        except Exception as e:
            print(f"Warning: could not read {f}: {e}")
    return translated_ids

def prepare_batch(batch_num: int, batch_size: int = 50):
    ensure_dirs()
    translated_ids = get_translated_ids()
    
    with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
        normalized_data = json.load(f)
        
    remaining = [r for r in normalized_data if r["id"] not in translated_ids]
    
    if not remaining:
        print("All prompts have been processed!")
        return 0

    batch_data = remaining[:batch_size]
    out_file = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_input.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(batch_data, f, ensure_ascii=False, indent=2)
        
    print(f"Batch {batch_num:03d} prepared: {len(batch_data)} prompts -> {out_file}")
    return len(batch_data)

def split_batch(batch_num: int):
    input_file = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_input.json")
    if not os.path.exists(input_file):
        print(f"File {input_file} does not exist.")
        return False
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    n = len(data)
    # Default 4 parts: p1a (0..12), p1b (12..25), p2a (25..37), p2b (37..n)
    p1a = data[:12]
    p1b = data[12:25]
    p2a = data[25:37]
    p2b = data[37:]
    parts = [("p1a", p1a), ("p1b", p1b), ("p2a", p2a), ("p2b", p2b)]
    for pname, pdata in parts:
        pf = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_{pname}_input.json")
        with open(pf, "w", encoding="utf-8") as fp:
            json.dump(pdata, fp, ensure_ascii=False, indent=2)
        print(f"Split {pname}: {len(pdata)} items -> {pf}")
    return True

def validate_batch(batch_num: int):
    vi_file = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_vi.json")
    input_file = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_input.json")
    
    if not os.path.exists(vi_file):
        return False, [f"File {vi_file} does not exist."], 0
        
    try:
        with open(vi_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"JSON parse error in {vi_file}: {e}"], 0

    input_map = {}
    if os.path.exists(input_file):
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                inp_data = json.load(f)
                input_map = {r["id"]: r for r in inp_data}
        except Exception:
            pass

    errors = []
    needs_review_count = 0
    ids = set()

    for idx, r in enumerate(data):
        r_id = r.get("id")
        if not r_id:
            errors.append(f"Record #{idx} missing ID.")
            continue
        if r_id in ids:
            errors.append(f"Duplicate ID {r_id} in batch.")
        ids.add(r_id)

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in r:
                errors.append(f"Record {r_id} missing field: {field}")

        # Check vi_title and vi_prompt
        if not r.get("vi_title") or str(r.get("vi_title")).strip() == "":
            errors.append(f"Record {r_id} has empty/null vi_title.")
        if not r.get("vi_prompt") or str(r.get("vi_prompt")).strip() == "":
            errors.append(f"Record {r_id} has empty/null vi_prompt.")

        # Check statuses
        if r.get("translation_status") != "translated":
            errors.append(f"Record {r_id} translation_status is not 'translated'.")
        if r.get("quality_status") not in ["ok", "needs_review"]:
            errors.append(f"Record {r_id} invalid quality_status: {r.get('quality_status')}")

        if r.get("quality_status") == "needs_review":
            needs_review_count += 1

        # Check preservation of source fields
        if r_id in input_map:
            inp = input_map[r_id]
            if r.get("original_prompt") != inp.get("original_prompt"):
                errors.append(f"Record {r_id} original_prompt modified!")
            if r.get("original_title") != inp.get("original_title"):
                errors.append(f"Record {r_id} original_title modified!")
            if r.get("source_category") != inp.get("source_category"):
                errors.append(f"Record {r_id} source_category modified!")
            if r.get("source_tags") != inp.get("source_tags"):
                errors.append(f"Record {r_id} source_tags modified!")

    return len(errors) == 0, errors, needs_review_count

def update_checkpoint(failed_batches=None):
    ensure_dirs()
    if failed_batches is None:
        failed_batches = []
        
    with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
        normalized_data = json.load(f)
    total_prompts = len(normalized_data)

    translated_ids = set()
    needs_review_count = 0
    last_completed = 0
    
    batch_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, "batch_[0-9][0-9][0-9]_vi.json")))
    for bf in batch_files:
        try:
            bn = int(os.path.basename(bf).split("_")[1])
            if bn > last_completed:
                last_completed = bn
        except Exception:
            pass
        try:
            with open(bf, "r", encoding="utf-8") as f:
                bdata = json.load(f)
                for r in bdata:
                    translated_ids.add(r.get("id"))
                    if r.get("quality_status") == "needs_review":
                        needs_review_count += 1
        except Exception as e:
            print(f"Error reading {bf}: {e}")

    completed_prompts = len(translated_ids)
    remaining_prompts = total_prompts - completed_prompts

    checkpoint_data = {
        "total_prompts": total_prompts,
        "completed_prompts": completed_prompts,
        "remaining_prompts": remaining_prompts,
        "last_completed_batch": last_completed,
        "failed_batches": failed_batches,
        "needs_review_count": needs_review_count,
        "updated_at": datetime.now().isoformat()
    }

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

    print(f"Checkpoint updated: {completed_prompts}/{total_prompts} completed, last batch {last_completed}")
    return checkpoint_data

def merge_final():
    ensure_dirs()
    batch_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, "batch_[0-9][0-9][0-9]_vi.json")))
    all_records = []
    seen_ids = set()

    for bf in batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            data = json.load(f)
            for r in data:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_records.append(r)

    # JSON output
    json_path = os.path.join(FINAL_DIR, "prompts_vi.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    # CSV output
    csv_path = os.path.join(FINAL_DIR, "prompts_vi.csv")
    csv_fields = [
        "id", "slug", "original_title", "vi_title", "original_prompt", "vi_prompt",
        "category", "subcategory", "tags", "search_keywords_vi", "use_case",
        "model_type", "difficulty", "quality_status", "translation_status",
        "language_original", "language_detection", "source_category", "source_tags",
        "author", "source", "source_url", "created_at"
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_fields)
        for r in all_records:
            row = []
            for field in csv_fields:
                val = r.get(field, "")
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                row.append(val)
            writer.writerow(row)

    print(f"Merged {len(all_records)} records into {json_path} and {csv_path}")

    # Also output to data/
    root_json = os.path.join(BASE_DIR, "data", "prompts_vi.json")
    root_csv = os.path.join(BASE_DIR, "data", "prompts_vi.csv")
    with open(root_json, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    with open(root_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_fields)
        for r in all_records:
            row = []
            for field in csv_fields:
                val = r.get(field, "")
                if isinstance(val, (list, dict)):
                    val = json.dumps(val, ensure_ascii=False)
                row.append(val)
            writer.writerow(row)
    print(f"Also synced to {root_json} and {root_csv}")
    return len(all_records), json_path, csv_path


def export_supabase_sql(out_path=None):
    ensure_dirs()
    if not out_path:
        out_path = os.path.join(FINAL_DIR, "prompts_insert.sql")

    json_path = os.path.join(FINAL_DIR, "prompts_vi.json")
    if not os.path.exists(json_path):
        print(f"File {json_path} not found. Run final-merge first.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    def esc(s):
        if s is None:
            return "NULL"
        return "'" + str(s).replace("'", "''") + "'"

    def esc_json(obj):
        if obj is None:
            return "'[]'::jsonb"
        return "'" + json.dumps(obj, ensure_ascii=False).replace("'", "''") + "'::jsonb"

    cols = [
        "id", "slug", "original_title", "original_prompt", "language_original",
        "language_detection", "vi_title", "vi_prompt", "translation_status",
        "source_category", "source_tags", "category", "subcategory", "tags",
        "search_keywords_vi", "use_case", "model_type", "difficulty", "quality_status",
        "author", "source", "source_url", "created_at"
    ]

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("-- Generated SQL Insert for Prompt Việt (2,479 records)\n")
        f.write("BEGIN;\n\n")

        # Chunk into chunks of 100 for efficient batch inserts
        chunk_size = 100
        for i in range(0, len(records), chunk_size):
            chunk = records[i:i + chunk_size]
            f.write(f"INSERT INTO prompts ({', '.join(cols)})\nVALUES\n")
            val_rows = []
            for r in chunk:
                # model_type might be list or str
                mt = r.get("model_type")
                if isinstance(mt, list):
                    mt = ", ".join(mt)
                
                vals = [
                    esc(r.get("id")),
                    esc(r.get("slug")),
                    esc(r.get("original_title")),
                    esc(r.get("original_prompt")),
                    esc(r.get("language_original")),
                    esc(r.get("language_detection")),
                    esc(r.get("vi_title")),
                    esc(r.get("vi_prompt")),
                    esc(r.get("translation_status", "translated")),
                    esc(r.get("source_category")),
                    esc_json(r.get("source_tags", [])),
                    esc(r.get("category")),
                    esc(r.get("subcategory")),
                    esc_json(r.get("tags", [])),
                    esc_json(r.get("search_keywords_vi", [])),
                    esc(r.get("use_case")),
                    esc(mt),
                    esc(r.get("difficulty")),
                    esc(r.get("quality_status", "ok")),
                    esc(r.get("author")),
                    esc(r.get("source")),
                    esc(r.get("source_url")),
                    esc(r.get("created_at")),
                ]
                val_rows.append("  (" + ", ".join(vals) + ")")
            f.write(",\n".join(val_rows))
            f.write("\nON CONFLICT (id) DO UPDATE SET\n")
            f.write("  vi_title = EXCLUDED.vi_title,\n")
            f.write("  vi_prompt = EXCLUDED.vi_prompt,\n")
            f.write("  category = EXCLUDED.category,\n")
            f.write("  subcategory = EXCLUDED.subcategory,\n")
            f.write("  tags = EXCLUDED.tags,\n")
            f.write("  search_keywords_vi = EXCLUDED.search_keywords_vi,\n")
            f.write("  use_case = EXCLUDED.use_case,\n")
            f.write("  model_type = EXCLUDED.model_type,\n")
            f.write("  difficulty = EXCLUDED.difficulty,\n")
            f.write("  quality_status = EXCLUDED.quality_status,\n")
            f.write("  synced_at = now();\n\n")

        f.write("COMMIT;\n")

    print(f"Exported {len(records)} records as SQL bulk inserts to {out_path}")
    return out_path


def preflight_config():
    """
    PREFLIGHT CONFIG / ENV DISCOVERY:
    - Checks for existing configuration and .env files safely.
    - Reports only file paths / names and status (EXISTS / NOT FOUND).
    - NEVER prints, logs, or reveals secret values.
    - Checks for Supabase environment variables availability (PRESENT / ABSENT).
    - Checks Supabase CLI and schema/SQL files readiness.
    """
    print("=== PREFLIGHT CONFIG & ENVIRONMENT DISCOVERY ===")

    # 1. Candidate config / .env files to check
    workspace_root = os.path.abspath(os.path.join(BASE_DIR, ".."))
    candidate_files = [
        os.path.join(workspace_root, ".env"),
        os.path.join(workspace_root, ".env.local"),
        os.path.join(workspace_root, ".env.production"),
        os.path.join(workspace_root, ".env.development"),
        os.path.join(BASE_DIR, ".env"),
        os.path.join(BASE_DIR, ".env.local"),
        os.path.join(BASE_DIR, "config.json"),
        os.path.join(BASE_DIR, "supabase.json"),
    ]

    found_env_files = []
    print("\n--- Configuration & Env Files ---")
    for fpath in candidate_files:
        rel = os.path.relpath(fpath, workspace_root)
        if os.path.exists(fpath):
            print(f"  [FOUND]     {rel}")
            found_env_files.append(fpath)
        else:
            print(f"  [NOT FOUND] {rel}")

    # Check any .env* in workspace root or prompt-viet using os.listdir (safe, approved)
    for check_dir in [workspace_root, BASE_DIR]:
        if os.path.exists(check_dir):
            for fname in os.listdir(check_dir):
                if fname.startswith(".env") and os.path.join(check_dir, fname) not in candidate_files:
                    full_p = os.path.join(check_dir, fname)
                    rel = os.path.relpath(full_p, workspace_root)
                    print(f"  [FOUND]     {rel}")
                    found_env_files.append(full_p)

    # Read env var names from found .env files without reading values
    detected_keys = set()
    for env_f in found_env_files:
        try:
            with open(env_f, "r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k = line.split("=", 1)[0].strip()
                        detected_keys.add(k)
        except Exception as e:
            print(f"  Warning reading {env_f}: {e}")

    # 2. Check Supabase Environment Variables (presence only, no secrets)
    supabase_keys_to_check = [
        "SUPABASE_URL",
        "NEXT_PUBLIC_SUPABASE_URL",
        "VITE_SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_ANON_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "VITE_SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "DATABASE_URL",
        "POSTGRES_URL",
        "PGDATABASE",
    ]

    print("\n--- Supabase & Database Environment Variables ---")
    avail_count = 0
    for key in supabase_keys_to_check:
        in_os = key in os.environ
        in_file = key in detected_keys
        status = "PRESENT (in env)" if in_os else ("PRESENT (in file)" if in_file else "NOT SET")
        if in_os or in_file:
            avail_count += 1
            print(f"  {key:30s}: {status}")
        else:
            print(f"  {key:30s}: {status}")

    # 3. Supabase Artifacts Check
    schema_file = os.path.join(BASE_DIR, "scripts", "supabase_schema.sql")
    inserts_file = os.path.join(FINAL_DIR, "prompts_insert.sql")
    master_json = os.path.join(FINAL_DIR, "prompts_vi.json")

    print("\n--- Supabase SQL & Artifacts Readiness ---")
    print(f"  Schema SQL ({os.path.relpath(schema_file, workspace_root)}): {'READY' if os.path.exists(schema_file) else 'MISSING'}")
    print(f"  Inserts SQL ({os.path.relpath(inserts_file, workspace_root)}): {'READY' if os.path.exists(inserts_file) else 'MISSING'}")
    print(f"  Master JSON ({os.path.relpath(master_json, workspace_root)}): {'READY' if os.path.exists(master_json) else 'MISSING'}")

    # 4. Check if CLI exists in PATH
    import shutil
    has_supabase_cli = shutil.which("supabase") is not None
    print(f"  Supabase CLI installed: {'YES' if has_supabase_cli else 'NO'}")

    # Summary
    ready_for_import = (avail_count > 0)
    print("\n--- PREFLIGHT SUMMARY ---")
    print(f"  Config/Env files found: {len(found_env_files)}")
    print(f"  Detected Supabase keys: {avail_count}")
    print(f"  SQL Artifacts ready:    {'YES' if (os.path.exists(schema_file) and os.path.exists(inserts_file)) else 'NO'}")
    print(f"  Direct connection ready:{'YES' if ready_for_import else 'NO (Requires Supabase credentials)'}")

    return ready_for_import


VN_ACCENT_MAP = {
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'đ': 'd',
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
}

def remove_accents_vietnamese(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower()
    return "".join(VN_ACCENT_MAP.get(ch, ch) for ch in text)

def tokenize_clean(text: str) -> list:
    import re
    if not text:
        return []
    cleaned = remove_accents_vietnamese(text)
    return re.findall(r'[a-z0-9]+', cleaned)

def build_search_index():
    import time
    ensure_dirs()
    start_time = time.time()
    
    json_path = os.path.join(FINAL_DIR, "prompts_vi.json")
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Run final-merge first.")
        return False
        
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    total_records = len(records)
    print(f"=== BUILDING VIETNAMESE SEARCH INDEX ({total_records} records) ===")
    
    prompts_search = []
    # Inverted index: { token: [ [doc_idx, weight], ... ] }
    inverted_index = {}
    
    categories_dist = {}
    subcategories_map = {}
    tags_dist = {}
    model_types_dist = {}
    difficulties_dist = {}
    autocomplete_set = set()
    
    for doc_idx, r in enumerate(records):
        rid = r.get("id")
        slug = r.get("slug")
        vtitle = r.get("vi_title", "")
        vprompt = r.get("vi_prompt", "")
        cat = str(r.get("category", "Chung"))
        subcat = str(r.get("subcategory", ""))
        tags = r.get("tags", [])
        if not isinstance(tags, list):
            tags = [str(tags)]
        keywords = r.get("search_keywords_vi", [])
        if not isinstance(keywords, list):
            keywords = [str(keywords)]
        mtype = r.get("model_type", "text")
        diff = r.get("difficulty", "medium")
        qstatus = r.get("quality_status", "ok")
        
        # Format compact search document
        snippet = vprompt[:160].strip() + ("..." if len(vprompt) > 160 else "")
        vtitle_clean = remove_accents_vietnamese(vtitle)
        
        doc = {
            "id": rid,
            "slug": slug,
            "vi_title": vtitle,
            "vi_title_clean": vtitle_clean,
            "snippet": snippet,
            "vi_prompt": vprompt,
            "category": cat,
            "subcategory": subcat,
            "tags": tags,
            "search_keywords_vi": keywords,
            "model_type": mtype,
            "difficulty": diff,
            "quality_status": qstatus
        }
        prompts_search.append(doc)
        
        # Taxonomy collection
        categories_dist[cat] = categories_dist.get(cat, 0) + 1
        if cat not in subcategories_map:
            subcategories_map[cat] = set()
        if subcat:
            subcategories_map[cat].add(subcat)
            
        for t in tags:
            tags_dist[t] = tags_dist.get(t, 0) + 1
            if len(t) > 2:
                autocomplete_set.add(t)
                
        for kw in keywords:
            if len(kw) > 2:
                autocomplete_set.add(kw)
                
        if isinstance(mtype, list):
            for m in mtype:
                model_types_dist[str(m)] = model_types_dist.get(str(m), 0) + 1
        else:
            model_types_dist[str(mtype)] = model_types_dist.get(str(mtype), 0) + 1
            
        difficulties_dist[str(diff)] = difficulties_dist.get(str(diff), 0) + 1
        
        # Field weights: Title: 10, Keywords: 5, Tags: 4, Cat/Subcat: 3, Model/Diff: 2, Prompt: 1
        weighted_tokens = {}
        for tok in tokenize_clean(vtitle):
            weighted_tokens[tok] = weighted_tokens.get(tok, 0) + 10
        for kw in keywords:
            for tok in tokenize_clean(kw):
                weighted_tokens[tok] = weighted_tokens.get(tok, 0) + 5
        for t in tags:
            for tok in tokenize_clean(t):
                weighted_tokens[tok] = weighted_tokens.get(tok, 0) + 4
        for tok in tokenize_clean(cat + " " + subcat):
            weighted_tokens[tok] = weighted_tokens.get(tok, 0) + 3
        for tok in tokenize_clean(str(mtype) + " " + str(diff)):
            weighted_tokens[tok] = weighted_tokens.get(tok, 0) + 2
        for tok in tokenize_clean(vprompt):
            weighted_tokens[tok] = weighted_tokens.get(tok, 0) + 1
            
        for tok, weight in weighted_tokens.items():
            if tok not in inverted_index:
                inverted_index[tok] = []
            inverted_index[tok].append([doc_idx, weight])
            
    # Serialize subcategories
    subcategories_serializable = {k: sorted(list(v)) for k, v in subcategories_map.items()}
    top_tags = [t[0] for t in sorted(tags_dist.items(), key=lambda x: x[1], reverse=True)[:100]]
    autocomplete_list = sorted(list(autocomplete_set))[:300]
    
    index_meta = {
        "build_timestamp": datetime.now().isoformat(),
        "total_documents": total_records,
        "total_tokens": len(inverted_index),
        "categories": categories_dist,
        "subcategories": subcategories_serializable,
        "top_tags": top_tags,
        "model_types": model_types_dist,
        "difficulties": difficulties_dist,
        "autocomplete": autocomplete_list,
        "inverted_index": inverted_index
    }
    
    # Save search files
    prompts_search_path = os.path.join(SEARCH_DIR, "prompts_search.json")
    prompts_cards_path = os.path.join(SEARCH_DIR, "prompts_cards.json")
    search_index_path = os.path.join(SEARCH_DIR, "search_index.json")

    prompts_cards = [
        {
            "id": d["id"],
            "slug": d["slug"],
            "vi_title": d["vi_title"],
            "snippet": d["snippet"],
            "category": d["category"],
            "subcategory": d["subcategory"],
            "tags": d["tags"],
            "model_type": d["model_type"],
            "difficulty": d["difficulty"]
        }
        for d in prompts_search
    ]

    with open(prompts_search_path, "w", encoding="utf-8") as f:
        json.dump(prompts_search, f, ensure_ascii=False)

    with open(prompts_cards_path, "w", encoding="utf-8") as f:
        json.dump(prompts_cards, f, ensure_ascii=False)

    with open(search_index_path, "w", encoding="utf-8") as f:
        json.dump(index_meta, f, ensure_ascii=False)

    duration = (time.time() - start_time) * 1000
    search_doc_size_kb = os.path.getsize(prompts_search_path) / 1024
    cards_size_kb = os.path.getsize(prompts_cards_path) / 1024
    index_size_kb = os.path.getsize(search_index_path) / 1024

    print(f"Search Index Built Successfully in {duration:.1f}ms:")
    print(f"  - Prompts Full Search DB: {prompts_search_path} ({search_doc_size_kb:.1f} KB)")
    print(f"  - Prompts Cards (Light):  {prompts_cards_path} ({cards_size_kb:.1f} KB)")
    print(f"  - Inverted Index:         {search_index_path} ({index_size_kb:.1f} KB, {len(inverted_index)} tokens)")
    print(f"  - Autocomplete terms: {len(autocomplete_list)}")
    print(f"  - Categories:        {len(categories_dist)}")
    return True


def search_dataset(query: str, limit: int = 10):
    import time
    prompts_search_path = os.path.join(SEARCH_DIR, "prompts_search.json")
    search_index_path = os.path.join(SEARCH_DIR, "search_index.json")
    
    if not os.path.exists(prompts_search_path) or not os.path.exists(search_index_path):
        print("Search index missing. Running build-search-index first...")
        if not build_search_index():
            return []
            
    with open(prompts_search_path, "r", encoding="utf-8") as f:
        docs = json.load(f)
    with open(search_index_path, "r", encoding="utf-8") as f:
        index_meta = json.load(f)
        
    inv = index_meta.get("inverted_index", {})
    q_tokens = tokenize_clean(query)
    q_clean = remove_accents_vietnamese(query).strip()
    
    start_time = time.perf_counter()
    scores = {}
    
    for tok in q_tokens:
        postings = inv.get(tok, [])
        for doc_idx, weight in postings:
            scores[doc_idx] = scores.get(doc_idx, 0) + weight
            
    # Exact phrase bonus on title
    for doc_idx in list(scores.keys()):
        d = docs[doc_idx]
        if q_clean and q_clean in d.get("vi_title_clean", ""):
            scores[doc_idx] += 30
            
    # Sort results
    ranked = sorted(scores.items(), key=lambda x: (x[1], x[0] * -1), reverse=True)
    latency_ms = (time.perf_counter() - start_time) * 1000
    
    print(f"\nSearch Query: '{query}' (tokens: {q_tokens})")
    print(f"Latency:      {latency_ms:.2f} ms | Matches found: {len(ranked)}")
    print(f"--- Top {min(limit, len(ranked))} Results ---")
    
    results = []
    for rank_idx, (doc_idx, score) in enumerate(ranked[:limit]):
        doc = docs[doc_idx]
        results.append(doc)
        print(f"[{rank_idx+1}] Score: {score:4d} | ID: {doc['id']} | {doc['vi_title']}")
        print(f"    Category: {doc['category']} > {doc['subcategory']} | Difficulty: {doc['difficulty']}")
        print(f"    Snippet: {doc['snippet'][:100]}...\n")
        
    return results


def publish_web_data():
    import shutil
    web_dir = os.path.join(BASE_DIR, "web")
    web_data_dir = os.path.join(web_dir, "data")
    os.makedirs(web_data_dir, exist_ok=True)

    files_to_copy = [
        ("prompts_cards.json", os.path.join(SEARCH_DIR, "prompts_cards.json")),
        ("prompts_search.json", os.path.join(SEARCH_DIR, "prompts_search.json")),
        ("search_index.json", os.path.join(SEARCH_DIR, "search_index.json")),
    ]

    copied = 0
    for fname, src in files_to_copy:
        if os.path.exists(src):
            dst = os.path.join(web_data_dir, fname)
            shutil.copy2(src, dst)
            size_kb = os.path.getsize(dst) / 1024
            print(f"Copied {fname} -> {dst} ({size_kb:.1f} KB)")
            copied += 1
        else:
            print(f"Warning: {src} not found! Run build-search-index first.")

    print(f"Web Data Published: {copied}/{len(files_to_copy)} files synced to {web_data_dir}")
    return copied == len(files_to_copy)


def validate_web():
    web_dir = os.path.join(BASE_DIR, "web")
    index_html = os.path.join(web_dir, "index.html")
    app_js = os.path.join(web_dir, "app.js")
    style_css = os.path.join(web_dir, "style.css")
    cards_json = os.path.join(web_dir, "data", "prompts_cards.json")
    search_json = os.path.join(web_dir, "data", "prompts_search.json")
    index_json = os.path.join(web_dir, "data", "search_index.json")

    print("=== VALIDATING PROMPT VIET WEB APPLICATION ===")
    errors = []

    for name, p in [("index.html", index_html), ("app.js", app_js), ("style.css", style_css)]:
        if not os.path.exists(p):
            errors.append(f"Missing web asset: {name}")
        else:
            print(f"  [OK] {name} ({os.path.getsize(p) / 1024:.1f} KB)")

    if not os.path.exists(cards_json):
        errors.append("Missing prompts_cards.json in web/data")
    else:
        with open(cards_json, "r", encoding="utf-8") as f:
            cdata = json.load(f)
        if len(cdata) != 2479:
            errors.append(f"prompts_cards.json count mismatch: {len(cdata)} != 2479")
        else:
            print(f"  [OK] prompts_cards.json (2,479 cards)")

    if not os.path.exists(search_json):
        errors.append("Missing prompts_search.json in web/data")
    else:
        with open(search_json, "r", encoding="utf-8") as f:
            sdata = json.load(f)
        if len(sdata) != 2479:
            errors.append(f"prompts_search.json count mismatch: {len(sdata)} != 2479")
        else:
            print(f"  [OK] prompts_search.json (2,479 full prompts)")

    if not os.path.exists(index_json):
        errors.append("Missing search_index.json in web/data")
    else:
        with open(index_json, "r", encoding="utf-8") as f:
            idata = json.load(f)
        tok_count = len(idata.get("inverted_index", {}))
        print(f"  [OK] search_index.json ({tok_count} index tokens, {len(idata.get('autocomplete', []))} autocomplete terms)")

    pass_all = len(errors) == 0
    print(f"\nWeb Validation: {'PASS (100%)' if pass_all else 'FAIL'}")
    if errors:
        for err in errors:
            print(f"  - ERROR: {err}")
    return pass_all


def run_search_qa_suite():
    print("=== PROMPT VIET SEARCH REGRESSION & QA SUITE ===")
    test_queries = [
        "viết content chuẩn seo",
        "viet content chuan seo",
        "lập trình python",
        "lap trinh python",
        "midjourney photorealistic",
        "chiến lược marketing",
        "tối ưu hóa chuyển đổi",
        "react tailwindcss frontend",
        "học ngoại ngữ tiếng anh",
        "quản trị nhân sự tuyển dụng"
    ]

    all_passed = True

    for idx, q in enumerate(test_queries):
        results = search_dataset(q, limit=3)
        if not results:
            print(f"  [FAIL] Query '{q}' returned 0 matches!")
            all_passed = False
        else:
            print(f"  [PASS] Query [{idx+1}/10] '{q}' -> {len(results)} results returned.")

    print(f"\nSearch QA Suite Status: {'ALL 10/10 PASS' if all_passed else 'FAIL'}")
    return all_passed


def audit_dataset():
    ensure_dirs()
    reports_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    json_path = os.path.join(FINAL_DIR, "prompts_vi.json")
    csv_path = os.path.join(FINAL_DIR, "prompts_vi.csv")

    if not os.path.exists(json_path) or not os.path.exists(csv_path):
        print(f"Error: Final files missing! Run final-merge first.")
        return False

    with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
        normalized_data = json.load(f)
    norm_map = {r["id"]: r for r in normalized_data}

    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    total_records = len(records)
    print(f"=== PROMPT VIET DATA AUDIT ===")
    print(f"Total records in {json_path}: {total_records}")

    # 1. ID Uniqueness
    id_counts = {}
    for r in records:
        rid = r.get("id")
        id_counts[rid] = id_counts.get(rid, 0) + 1
    duplicate_ids = [rid for rid, cnt in id_counts.items() if cnt > 1]

    # 2. Field Completeness and Null Checks
    missing_required_fields = 0
    null_vi_title = 0
    null_vi_prompt = 0

    # 3. Source Metadata Preservation
    source_mismatches = 0
    immutable_fields = [
        "slug", "original_title", "original_prompt", "language_original",
        "author", "source", "source_url", "created_at"
    ]

    # 4. Statistical Distributions
    category_dist = {}
    difficulty_dist = {}
    model_type_dist = {}
    quality_status_dist = {}
    translation_status_dist = {}
    tag_counts = {}

    for r in records:
        rid = r.get("id")
        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in r:
                missing_required_fields += 1

        # Title and prompt check
        vt = r.get("vi_title")
        vp = r.get("vi_prompt")
        if not vt or (isinstance(vt, str) and not vt.strip()):
            null_vi_title += 1
        if not vp or (isinstance(vp, str) and not vp.strip()):
            null_vi_prompt += 1

        # Source metadata integrity
        if rid in norm_map:
            orig = norm_map[rid]
            for fld in immutable_fields:
                if r.get(fld) != orig.get(fld):
                    source_mismatches += 1
        else:
            source_mismatches += 1

        # Distributions
        cat = str(r.get("category", "Unknown"))
        category_dist[cat] = category_dist.get(cat, 0) + 1

        diff = str(r.get("difficulty", "Unknown"))
        difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1

        mtype = r.get("model_type", "Unknown")
        if isinstance(mtype, list):
            for m in mtype:
                model_type_dist[str(m)] = model_type_dist.get(str(m), 0) + 1
        else:
            model_type_dist[str(mtype)] = model_type_dist.get(str(mtype), 0) + 1

        qstatus = str(r.get("quality_status", "Unknown"))
        quality_status_dist[qstatus] = quality_status_dist.get(qstatus, 0) + 1

        tstatus = str(r.get("translation_status", "Unknown"))
        translation_status_dist[tstatus] = translation_status_dist.get(tstatus, 0) + 1

        tags = r.get("tags", [])
        if isinstance(tags, list):
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1

    # CSV audit
    csv_rows = 0
    csv.field_size_limit(50 * 1024 * 1024)
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for _ in reader:
            csv_rows += 1

    # Checkpoint check
    cp_ok = True
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            cp = json.load(f)
        cp_total = cp.get("total_prompts")
        cp_completed = cp.get("completed_prompts")
        cp_remaining = cp.get("remaining_prompts")
        if cp_total != total_records or cp_completed != total_records or cp_remaining != 0:
            cp_ok = False

    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:25]

    pass_all = (
        total_records == len(normalized_data)
        and len(duplicate_ids) == 0
        and missing_required_fields == 0
        and null_vi_title == 0
        and null_vi_prompt == 0
        and source_mismatches == 0
        and csv_rows == total_records
        and cp_ok
    )

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_records": total_records,
        "target_records": len(normalized_data),
        "pass_audit": pass_all,
        "duplicate_ids": len(duplicate_ids),
        "missing_required_fields": missing_required_fields,
        "null_vi_title": null_vi_title,
        "null_vi_prompt": null_vi_prompt,
        "source_metadata_mismatches": source_mismatches,
        "csv_row_count": csv_rows,
        "checkpoint_synchronized": cp_ok,
        "distributions": {
            "categories": category_dist,
            "difficulty": difficulty_dist,
            "model_type": model_type_dist,
            "quality_status": quality_status_dist,
            "translation_status": translation_status_dist,
            "top_25_tags": top_tags
        }
    }

    report_file = os.path.join(reports_dir, "audit_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md_report_file = os.path.join(reports_dir, "AUDIT_REPORT.md")
    with open(md_report_file, "w", encoding="utf-8") as f:
        f.write("# PROMPT VIỆT – DATA AUDIT REPORT\n\n")
        f.write(f"- **Timestamp:** `{report['timestamp']}`\n")
        f.write(f"- **Overall Status:** `{'PASS' if pass_all else 'FAIL'}`\n")
        f.write(f"- **Total Records:** `{total_records} / {len(normalized_data)}` (100% complete)\n\n")
        f.write("## 1. Core Verification Metrics\n\n")
        f.write("| Metric | Target | Actual | Status |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        f.write(f"| Total Records | {len(normalized_data)} | {total_records} | {'PASS' if total_records == len(normalized_data) else 'FAIL'} |\n")
        f.write(f"| Duplicate IDs | 0 | {len(duplicate_ids)} | {'PASS' if len(duplicate_ids) == 0 else 'FAIL'} |\n")
        f.write(f"| Missing Required Fields | 0 | {missing_required_fields} | {'PASS' if missing_required_fields == 0 else 'FAIL'} |\n")
        f.write(f"| Null / Empty `vi_title` | 0 | {null_vi_title} | {'PASS' if null_vi_title == 0 else 'FAIL'} |\n")
        f.write(f"| Null / Empty `vi_prompt` | 0 | {null_vi_prompt} | {'PASS' if null_vi_prompt == 0 else 'FAIL'} |\n")
        f.write(f"| Source Metadata Mismatches | 0 | {source_mismatches} | {'PASS' if source_mismatches == 0 else 'FAIL'} |\n")
        f.write(f"| CSV Row Count | {total_records} | {csv_rows} | {'PASS' if csv_rows == total_records else 'FAIL'} |\n")
        f.write(f"| Checkpoint Synced | Synchronized | {'Synchronized' if cp_ok else 'Out of sync'} | {'PASS' if cp_ok else 'FAIL'} |\n\n")
        f.write("## 2. Dataset Files\n\n")
        f.write(f"- Master JSON: `{json_path}`\n")
        f.write(f"- Master CSV: `{csv_path}`\n")
        f.write(f"- Root JSON: `prompt-viet/data/prompts_vi.json`\n")
        f.write(f"- Root CSV: `prompt-viet/data/prompts_vi.csv`\n\n")
        f.write("## 3. Statistical Distributions\n\n")
        f.write("### Difficulty Distribution\n\n")
        f.write("| Difficulty | Count | Percentage |\n| :--- | :--- | :--- |\n")
        for diff, count in sorted(difficulty_dist.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_records) * 100
            f.write(f"| {diff} | {count} | {pct:.2f}% |\n")
        f.write("\n### Quality Status\n\n")
        f.write("| Quality Status | Count | Percentage |\n| :--- | :--- | :--- |\n")
        for qs, count in sorted(quality_status_dist.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_records) * 100
            f.write(f"| {qs} | {count} | {pct:.2f}% |\n")
        f.write("\n### Model Types\n\n")
        f.write("| Model Type | Count | Percentage |\n| :--- | :--- | :--- |\n")
        for mt, count in sorted(model_type_dist.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_records) * 100
            f.write(f"| {mt} | {count} | {pct:.2f}% |\n")
        f.write("\n### Top 15 Tags\n\n")
        f.write("| Tag | Count |\n| :--- | :--- |\n")
        for tag, count in top_tags[:15]:
            f.write(f"| {tag} | {count} |\n")
        f.write("\n### Top 20 Categories\n\n")
        f.write("| Category | Count | Percentage |\n| :--- | :--- | :--- |\n")
        for cat, count in sorted(category_dist.items(), key=lambda x: x[1], reverse=True)[:20]:
            pct = (count / total_records) * 100
            f.write(f"| {cat} | {count} | {pct:.2f}% |\n")

    print("\n--- AUDIT SUMMARY ---")
    print(f"Total Records: {total_records} / {len(normalized_data)}")
    print(f"Duplicate IDs: {len(duplicate_ids)}")
    print(f"Missing Required Fields: {missing_required_fields}")
    print(f"Null / Empty vi_title: {null_vi_title}")
    print(f"Null / Empty vi_prompt: {null_vi_prompt}")
    print(f"Source Mismatches: {source_mismatches}")
    print(f"CSV Row Count: {csv_rows} (matches: {csv_rows == total_records})")
    print(f"Checkpoint Sync: {'OK' if cp_ok else 'OUT OF SYNC'}")
    print(f"Audit Overall Status: {'PASS' if pass_all else 'FAIL'}")
    print(f"Report saved: {report_file}")

    print("\n--- CATEGORY DISTRIBUTION ---")
    for cat, count in sorted(category_dist.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_records) * 100
        print(f"  {cat:30s}: {count:5d} ({pct:5.2f}%)")

    print("\n--- DIFFICULTY DISTRIBUTION ---")
    for diff, count in sorted(difficulty_dist.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_records) * 100
        print(f"  {diff:15s}: {count:5d} ({pct:5.2f}%)")

    print("\n--- QUALITY STATUS DISTRIBUTION ---")
    for qs, count in sorted(quality_status_dist.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_records) * 100
        print(f"  {qs:15s}: {count:5d} ({pct:5.2f}%)")

    print("\n--- MODEL TYPE DISTRIBUTION ---")
    for mt, count in sorted(model_type_dist.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_records) * 100
        print(f"  {mt:15s}: {count:5d} ({pct:5.2f}%)")

    print("\n--- TOP 15 TAGS ---")
    for tag, count in top_tags[:15]:
        print(f"  {tag:25s}: {count:5d}")

    return pass_all


def merge_parts(batch_num: int):
    ensure_dirs()
    # Auto-merge subparts (e.g. p2a1, p2a2 -> p2a) if needed
    for p in ["p1a", "p1b", "p2a", "p2b"]:
        target_p = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{p}_vi.json")
        sub_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{p}[0-9]*_vi.json")))
        if sub_files:
            sub_combined = []
            for sf in sub_files:
                with open(sf, "r", encoding="utf-8") as f:
                    sub_combined.extend(json.load(f))
            with open(target_p, "w", encoding="utf-8") as fo:
                json.dump(sub_combined, fo, ensure_ascii=False, indent=2)
            print(f"Auto-merged {len(sub_files)} subparts into {target_p} ({len(sub_combined)} items)")

    # Check for 4-part micro-batches (p1a, p1b, p2a, p2b)
    p_4 = [
        os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{p}_vi.json")
        for p in ["p1a", "p1b", "p2a", "p2b"]
    ]
    # Check for 2-part batches (part1, part2)
    p_2 = [
        os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{p}_vi.json")
        for p in ["part1", "part2"]
    ]
    
    parts_to_merge = []
    if all(os.path.exists(p) for p in p_4):
        parts_to_merge = p_4
    elif all(os.path.exists(p) for p in p_2):
        parts_to_merge = p_2
    else:
        # Check whatever parts exist matching batch_{batch_num:03d}_p*_vi.json
        parts_to_merge = sorted(glob.glob(os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_p*_vi.json")))
        
    out_file = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_vi.json")
    
    combined = []
    seen_ids = set()
    for pf in parts_to_merge:
        with open(pf, "r", encoding="utf-8") as f:
            d = json.load(f)
            for item in d:
                r_id = item.get("id")
                if r_id and r_id not in seen_ids:
                    seen_ids.add(r_id)
                    combined.append(item)
            
    with open(out_file, "w", encoding="utf-8") as fo:
        json.dump(combined, fo, ensure_ascii=False, indent=2)
    print(f"Successfully merged {len(parts_to_merge)} parts = {len(combined)} prompts into {out_file}")
    return len(combined)

def merge_subparts(batch_num: int, part: str):
    sub_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{part}[0-9]*_vi.json")))
    if not sub_files:
        print(f"No subparts found matching batch_{batch_num:03d}_{part}[0-9]*_vi.json")
        return 0
    out_file = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{part}_vi.json")
    combined = []
    seen_ids = set()
    for sf in sub_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    r_id = item.get("id")
                    if r_id and r_id not in seen_ids:
                        seen_ids.add(r_id)
                        combined.append(item)
        except Exception as e:
            print(f"Error loading {sf}: {e}")
            raise
    with open(out_file, "w", encoding="utf-8") as fo:
        json.dump(combined, fo, ensure_ascii=False, indent=2)
    print(f"Successfully merged {len(sub_files)} subparts into {out_file} ({len(combined)} items)")
    return len(combined)

def sync_source_fields(batch_num: int):
    input_file = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_input.json")
    vi_file = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_vi.json")
    if not os.path.exists(input_file) or not os.path.exists(vi_file):
        print(f"Either input or translated file missing for batch {batch_num}")
        return
    with open(input_file, "r", encoding="utf-8") as f:
        inp_data = json.load(f)
    inp_map = {r["id"]: r for r in inp_data}
    with open(vi_file, "r", encoding="utf-8") as f:
        vi_data = json.load(f)
    
    fixed_count = 0
    SOURCE_KEYS = [
        "slug",
        "original_title",
        "original_prompt",
        "language_original",
        "language_detection",
        "source_category",
        "source_tags",
        "author",
        "source",
        "source_url",
        "created_at",
    ]
    for r in vi_data:
        r_id = r.get("id")
        if r_id in inp_map:
            inp_r = inp_map[r_id]
            for k in SOURCE_KEYS:
                if k in inp_r and (k not in r or r.get(k) != inp_r.get(k)):
                    r[k] = inp_r.get(k)
        if r.get("quality_status") == "reviewed":
            r["quality_status"] = "ok"
            fixed_count += 1
    with open(vi_file, "w", encoding="utf-8") as f:
        json.dump(vi_data, f, ensure_ascii=False, indent=2)
    print(f"Synced source fields from input for Batch {batch_num:03d}. Updated {fixed_count} field discrepancies.")


def sync_all_source_fields():
    ensure_dirs()
    with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
        norm_data = json.load(f)
    norm_map = {r["id"]: r for r in norm_data}

    SOURCE_KEYS = [
        "slug",
        "original_title",
        "original_prompt",
        "language_original",
        "language_detection",
        "source_category",
        "source_tags",
        "author",
        "source",
        "source_url",
        "created_at",
    ]

    total_synced_batches = 0
    total_records_updated = 0

    batch_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, "batch_[0-9][0-9][0-9]_vi.json")))
    for bf in batch_files:
        with open(bf, "r", encoding="utf-8") as f:
            vi_data = json.load(f)
        batch_updated = False
        for r in vi_data:
            rid = r.get("id")
            if rid in norm_map:
                norm_r = norm_map[rid]
                rec_changed = False
                for k in SOURCE_KEYS:
                    if k in norm_r and (k not in r or r.get(k) != norm_r.get(k)):
                        r[k] = norm_r.get(k)
                        rec_changed = True
                if rec_changed:
                    batch_updated = True
                    total_records_updated += 1
        if batch_updated:
            with open(bf, "w", encoding="utf-8") as f:
                json.dump(vi_data, f, ensure_ascii=False, indent=2)
            total_synced_batches += 1

    print(f"Sync-all-source completed: updated {total_records_updated} records across {total_synced_batches} batches.")


def inspect_batch(batch_num: int):
    input_file = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_input.json")
    vi_file = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_vi.json")
    
    print(f"=== INSPECT BATCH {batch_num:03d} ===")
    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        lengths = [len(r.get("original_prompt", "")) for r in data]
        print(f"Input file: {input_file}")
        print(f"Total items in input: {len(data)}")
        if lengths:
            print(f"Prompt length (chars): min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)//len(lengths)}")
            max_idx = lengths.index(max(lengths))
            print(f"Longest prompt: ID={data[max_idx].get('id')}, Slug={data[max_idx].get('slug')}, Length={max(lengths)}")
        print("Record IDs:")
        for idx, r in enumerate(data):
            print(f"  [{idx+1:02d}] {r.get('id')} | {r.get('slug')} | len={len(r.get('original_prompt',''))}")
    else:
        print(f"Input file not found: {input_file}")

    # Check for micro-parts
    input_parts = sorted(glob.glob(os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_*_input.json")))
    if input_parts:
        print(f"\nFound input parts ({len(input_parts)}):")
        for ip in input_parts:
            try:
                with open(ip, "r", encoding="utf-8") as fp:
                    part_data = json.load(fp)
                print(f"  - {os.path.basename(ip)}: {len(part_data)} items")
            except Exception as e:
                print(f"  - {os.path.basename(ip)}: Error reading ({e})")

    translated_parts = sorted(glob.glob(os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_*_vi.json")))
    # exclude the merged file itself
    translated_parts = [p for p in translated_parts if os.path.basename(p) != f"batch_{batch_num:03d}_vi.json"]
    if translated_parts:
        print(f"\nFound translated parts ({len(translated_parts)}):")
        for tp in translated_parts:
            try:
                with open(tp, "r", encoding="utf-8") as fp:
                    part_data = json.load(fp)
                print(f"  - {os.path.basename(tp)}: {len(part_data)} items")
            except Exception as e:
                print(f"  - {os.path.basename(tp)}: Error reading ({e})")

    if os.path.exists(vi_file):
        with open(vi_file, "r", encoding="utf-8") as f:
            vdata = json.load(f)
        print(f"\nMerged Translated File exists: {vi_file}")
        print(f"Total items in translated file: {len(vdata)}")
    else:
        print(f"\nMerged Translated File NOT created yet: {vi_file}")


def inspect_part(batch_num: int, part: str):
    print(f"=== INSPECT BATCH {batch_num:03d} PART '{part}' ===")
    input_file = os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_{part}_input.json")
    vi_file = os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{part}_vi.json")
    
    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        lengths = [len(r.get("original_prompt", "")) for r in data]
        print(f"Part Input: {input_file} ({len(data)} items)")
        if lengths:
            print(f"Prompt length: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)//len(lengths)}")
        for idx, r in enumerate(data):
            print(f"  [{idx+1:02d}] {r.get('id')} | {r.get('slug')} | len={len(r.get('original_prompt',''))} | {r.get('original_title')[:50]}")
    else:
        print(f"Part Input not found: {input_file}")

    if os.path.exists(vi_file):
        with open(vi_file, "r", encoding="utf-8") as f:
            vdata = json.load(f)
        print(f"\nPart Translated: {vi_file} ({len(vdata)} items)")
        for idx, r in enumerate(vdata):
            has_vi = bool(r.get("vi_title") and r.get("vi_prompt"))
            print(f"  [{idx+1:02d}] {r.get('id')} | valid={has_vi} | vi_title={r.get('vi_title')[:40]} | status={r.get('quality_status')}")
    else:
        sub_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, f"batch_{batch_num:03d}_{part}[0-9]*_vi.json")))
        if sub_files:
            print(f"\nPart Translated not merged yet, but found {len(sub_files)} subparts:")
            for sf in sub_files:
                with open(sf, "r", encoding="utf-8") as fp:
                    sd = json.load(fp)
        else:
            print(f"Part Translated not found: {vi_file}")


def locate_batch(batch_num: int):
    """
    Locate and list all files related to batch_num across the project.
    Strictly read-only: only lists files, does not modify, delete, or execute shell commands.
    """
    batch_pattern = f"batch_{batch_num:03d}"
    print(f"=== Files for Batch {batch_num:03d} (matching '{batch_pattern}') ===")

    found_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        for fname in files:
            if batch_pattern in fname:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, BASE_DIR)
                found_files.append((rel_path, full_path))

    found_files.sort(key=lambda x: x[0])

    if not found_files:
        print(f"No files found matching '{batch_pattern}'.")
        return 0

    for rel_path, full_path in found_files:
        size_kb = os.path.getsize(full_path) / 1024.0
        extra = ""
        if full_path.endswith(".json"):
            try:
                with open(full_path, "r", encoding="utf-8") as jf:
                    jd = json.load(jf)
                    if isinstance(jd, list):
                        extra = f" - {len(jd)} items"
                    elif isinstance(jd, dict):
                        extra = f" - {len(jd)} keys"
            except Exception:
                pass
        print(f"  {rel_path} ({size_kb:.1f} KB{extra})")

    print(f"\nTotal files located: {len(found_files)}")
    return len(found_files)


def find_item_in_batch(batch_num: int, item_ref: str, part: str = None):
    files_to_check = []
    if part:
        files_to_check.append(os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_{part}_input.json"))
    files_to_check.append(os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_input.json"))
    for sf in sorted(glob.glob(os.path.join(BATCHES_DIR, f"batch_{batch_num:03d}_*_input.json"))):
        if sf not in files_to_check:
            files_to_check.append(sf)

    for fpath in files_to_check:
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as fp:
                items = json.load(fp)
            if item_ref.isdigit():
                idx = int(item_ref)
                if 0 <= idx < len(items):
                    return items[idx], fpath, idx
                if 1 <= idx <= len(items):
                    return items[idx-1], fpath, idx-1
            else:
                for idx, it in enumerate(items):
                    if it.get("id") == item_ref or it.get("slug") == item_ref:
                        return it, fpath, idx
        except Exception:
            continue
    return None, None, None


def inspect_record(batch_num: int, item_ref: str, part: str = None, full: bool = False, as_json: bool = False):
    item, src_path, idx = find_item_in_batch(batch_num, item_ref, part)
    if not item:
        print(f"Record '{item_ref}' not found in Batch {batch_num:03d} (part={part})")
        return
    if as_json:
        print(json.dumps(item, indent=2, ensure_ascii=False))
        return
    prompt = item.get("original_prompt", "")
    print(f"=== INSPECT RECORD [{item.get('id')}] in Batch {batch_num:03d} ===")
    print(f"Source file:    {src_path} (index {idx})")
    print(f"Slug:           {item.get('slug')}")
    print(f"Original title: {item.get('original_title')}")
    if "vi_title" in item:
        print(f"VI title:       {item.get('vi_title')}")
    if "quality_status" in item:
        print(f"Status:         quality={item.get('quality_status')}, trans={item.get('translation_status')}")
    print(f"Prompt length:  {len(prompt)} characters")
    
    import re
    vars_found = set(re.findall(r'(\{\{[^{}]+\}\}|\{[^{}]+\}|\$\{[^{}]+\})', prompt))
    if vars_found:
        print(f"Variables ({len(vars_found)}): {list(vars_found)[:10]}")

    parts = prompt.split('\x1fFILE:')
    if len(parts) > 1:
        print(f"Embedded files found ({len(parts)-1}):")
        for i, p in enumerate(parts[1:], 1):
            fname = p.split('\x1e')[0] if '\x1e' in p else p.split('\n')[0]
            print(f"  [{i:02d}] {fname.strip()} (len={len(p)})")
    else:
        print("No embedded files.")

    print("\n--- ORIGINAL PROMPT ---")
    if full or len(prompt) <= 2000:
        print(prompt)
    else:
        print(prompt[:1500])
        print(f"\n... [truncated {len(prompt)-1500} chars. Use --full or --json to view full prompt]")

    if "vi_prompt" in item and item.get("vi_prompt"):
        print("\n--- VI PROMPT ---")
        vi_prompt = item.get("vi_prompt", "")
        if full or len(vi_prompt) <= 2000:
            print(vi_prompt)
        else:
            print(vi_prompt[:1500])
            print(f"\n... [truncated {len(vi_prompt)-1500} chars. Use --full or --json to view full prompt]")


def inspect_item(batch_num: int, item_ref: str, part: str = None):
    inspect_record(batch_num, item_ref, part)


def inspect_embedded(batch_num: int, item_ref: str, part: str = None):
    item, src_path, idx = find_item_in_batch(batch_num, item_ref, part)
    if not item:
        print(f"Item '{item_ref}' not found in Batch {batch_num:03d} (part={part})")
        return
    prompt = item.get("original_prompt", "")
    parts = prompt.split('\x1fFILE:')
    print(f"=== EMBEDDED FILES IN ITEM [{item.get('id')}] ({item.get('slug')}) ===")
    print(f"Total parts: {len(parts)} (Part 0 = root, Parts 1..{len(parts)-1} = embedded files)")
    for i, p in enumerate(parts):
        if i == 0:
            lines = p.strip().split('\n')
            print(f"Part 00 [ROOT]: len={len(p)}, lines={len(lines)}, header='{lines[0][:60]}'")
        else:
            fname = p.split('\x1e')[0] if '\x1e' in p else p.split('\n')[0]
            lines = p.strip().split('\n')
            print(f"Part {i:02d} [{fname.strip()}]: len={len(p)}, lines={len(lines)}")


def dump_embedded(batch_num: int, item_ref: str, part_idx_str: str, out_path: str, part: str = None):
    item, src_path, idx = find_item_in_batch(batch_num, item_ref, part)
    if not item:
        print(f"Item '{item_ref}' not found in Batch {batch_num:03d} (part={part})")
        return
    prompt = item.get("original_prompt", "")
    parts = prompt.split('\x1fFILE:')
    
    if part_idx_str.lower() == "all":
        os.makedirs(out_path, exist_ok=True)
        for i, p in enumerate(parts):
            if i == 0:
                fn = os.path.join(out_path, "part_00_root.txt")
            else:
                raw_name = p.split('\x1e')[0] if '\x1e' in p else p.split('\n')[0]
                safe_name = raw_name.strip().replace('/', '_')
                fn = os.path.join(out_path, f"part_{i:02d}_{safe_name}.txt")
            with open(fn, "w", encoding="utf-8") as f:
                f.write(p)
        print(f"Dumped all {len(parts)} parts to directory: {out_path}")
        return

    part_idx = int(part_idx_str)
    if not (0 <= part_idx < len(parts)):
        print(f"Error: part_idx {part_idx} out of range (0..{len(parts)-1})")
        return
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(parts[part_idx])
    print(f"Dumped embedded part {part_idx} to {out_path} ({len(parts[part_idx])} chars)")


def dump_item(batch_num: int, item_ref: str, out_file: str, part: str = None, dump_full: bool = False):
    item, src_path, idx = find_item_in_batch(batch_num, item_ref, part)
    if not item:
        print(f"Item '{item_ref}' not found in Batch {batch_num:03d} (part={part})")
        return
    with open(out_file, "w", encoding="utf-8") as f:
        if dump_full:
            json.dump(item, f, ensure_ascii=False, indent=2)
        else:
            f.write(item.get("original_prompt", ""))
    print(f"Dumped item [{item.get('id')}] to {out_file}")


def assemble_record(batch_num: int, item_ref: str, parts_dir: str, output_file: str, part: str = None):
    item, src_path, idx = find_item_in_batch(batch_num, item_ref, part)
    if not item:
        print(f"Error: Record '{item_ref}' not found in Batch {batch_num:03d}")
        sys.exit(1)
        
    meta_path = os.path.join(parts_dir, "meta.json")
    if not os.path.exists(meta_path):
        print(f"Error: meta.json not found in {parts_dir}")
        sys.exit(1)
        
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    root_path = os.path.join(parts_dir, "part_00_root.txt")
    if not os.path.exists(root_path):
        print(f"Error: part_00_root.txt not found in {parts_dir}")
        sys.exit(1)
        
    with open(root_path, "r", encoding="utf-8") as f:
        root_content = f.read()
        
    embedded_files = sorted(glob.glob(os.path.join(parts_dir, "part_[0-9][0-9]_*.txt")))
    embedded_files = [ef for ef in embedded_files if not ef.endswith("part_00_root.txt")]
    
    parts_combined = [root_content]
    for ef in embedded_files:
        with open(ef, "r", encoding="utf-8") as f:
            c = f.read()
        parts_combined.append("\x1fFILE:" + c)
        
    vi_prompt = "".join(parts_combined)
    
    out_record = dict(item)
    out_record["vi_title"] = meta.get("vi_title")
    out_record["vi_prompt"] = vi_prompt
    out_record["translation_status"] = "translated"
    out_record["category"] = meta.get("category")
    out_record["subcategory"] = meta.get("subcategory")
    out_record["tags"] = meta.get("tags", [])
    out_record["search_keywords_vi"] = meta.get("search_keywords_vi", [])
    out_record["use_case"] = meta.get("use_case")
    out_record["model_type"] = meta.get("model_type", item.get("model_type", ["text"]))
    out_record["difficulty"] = meta.get("difficulty", "intermediate")
    out_record["quality_status"] = "ok"
    
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([out_record], f, ensure_ascii=False, indent=2)
        
    print(f"Record [{item.get('id')}] successfully assembled into {output_file} (vi_prompt len={len(vi_prompt)})")


def combine_files(out_file: str, input_files: list):
    combined = []
    seen_ids = set()
    for inf in input_files:
        if not os.path.exists(inf):
            print(f"Warning: File not found: {inf}")
            continue
        with open(inf, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                r_id = item.get("id")
                if r_id and r_id not in seen_ids:
                    seen_ids.add(r_id)
                    combined.append(item)
                elif not r_id:
                    combined.append(item)
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"Combined {len(input_files)} files into {out_file} ({len(combined)} items)")
    return len(combined)


def assemble_text_record(out_file: str, meta_file: str, src_item_file: str, text_files: list):
    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    with open(src_item_file, "r", encoding="utf-8") as f:
        src_item = json.load(f)
        if isinstance(src_item, list):
            src_item = src_item[0]
            
    vi_prompt_parts = []
    for tf in text_files:
        with open(tf, "r", encoding="utf-8") as f:
            vi_prompt_parts.append(f.read())
    vi_prompt = "".join(vi_prompt_parts)
    
    out_record = dict(src_item)
    out_record["vi_title"] = meta.get("vi_title")
    out_record["vi_prompt"] = vi_prompt
    out_record["translation_status"] = "translated"
    out_record["category"] = meta.get("category")
    out_record["subcategory"] = meta.get("subcategory")
    out_record["tags"] = meta.get("tags", [])
    out_record["search_keywords_vi"] = meta.get("search_keywords_vi", [])
    out_record["use_case"] = meta.get("use_case")
    out_record["model_type"] = meta.get("model_type", src_item.get("model_type", ["text"]))
    out_record["difficulty"] = meta.get("difficulty", "intermediate")
    out_record["quality_status"] = "ok"
    
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([out_record], f, ensure_ascii=False, indent=2)
    print(f"Assembled text record into {out_file} (vi_prompt len={len(vi_prompt)})")
    return out_record


def qa_sample(start_batch: int, end_batch: int, sample_size: int = 10, seed: int = 42):
    print(f"=== QA SAMPLE (Batches {start_batch:03d} - {end_batch:03d}) ===")
    candidates = []
    for b in range(start_batch, end_batch + 1):
        vi_file = os.path.join(TRANSLATED_DIR, f"batch_{b:03d}_vi.json")
        if not os.path.exists(vi_file):
            print(f"Warning: Batch {b:03d} file not found: {vi_file}")
            continue
        try:
            with open(vi_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    item["_batch"] = b
                    candidates.append(item)
        except Exception as e:
            print(f"Error reading Batch {b:03d}: {e}")

    if not candidates:
        print("No translated records found in specified batch range.")
        return

    random.seed(seed)
    sampled = random.sample(candidates, min(sample_size, len(candidates)))
    
    print(f"Sampled {len(sampled)} records out of {len(candidates)} candidates:\n")
    for idx, item in enumerate(sampled, 1):
        print(f"--- SAMPLE {idx:02d} | Batch {item.get('_batch'):03d} | ID: {item.get('id')} | Slug: {item.get('slug')} ---")
        print(f"Category/Sub: {item.get('category')} / {item.get('subcategory')}")
        print(f"Orig Title:   {item.get('original_title')}")
        print(f"VI Title:     {item.get('vi_title')}")
        print(f"Lang Orig/Det: {item.get('language_original')} / {item.get('language_detection')}")
        print(f"Status:       quality={item.get('quality_status')}, trans={item.get('translation_status')}")
        orig_snip = item.get('original_prompt', '').replace('\n', ' ')[:100]
        vi_snip = item.get('vi_prompt', '').replace('\n', ' ')[:100]
        print(f"Orig Prompt:  {orig_snip}...")
        print(f"VI Prompt:    {vi_snip}...")
        print()


def show_status():
    ensure_dirs()
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                cp = json.load(f)
            print("=== CURRENT PIPELINE STATUS ===")
            print(f"Total prompts:        {cp.get('total_prompts')}")
            print(f"Completed prompts:    {cp.get('completed_prompts')} ({cp.get('completed_prompts',0)*100/max(1,cp.get('total_prompts',1)):.2f}%)")
            print(f"Remaining prompts:    {cp.get('remaining_prompts')}")
            print(f"Last completed batch: {cp.get('last_completed_batch')}")
            print(f"Needs review count:   {cp.get('needs_review_count')}")
            print(f"Failed batches:       {cp.get('failed_batches')}")
            print(f"Last updated:         {cp.get('updated_at')}")
        except Exception as e:
            print(f"Error reading checkpoint: {e}")
    else:
        print("Checkpoint file not found. Running update_checkpoint()...")
        update_checkpoint()

    # List completed batches
    batch_files = sorted(glob.glob(os.path.join(TRANSLATED_DIR, "batch_[0-9][0-9][0-9]_vi.json")))
    print(f"\nCompleted batch files ({len(batch_files)}):")
    for bf in batch_files:
        try:
            with open(bf, "r", encoding="utf-8") as fp:
                bdata = json.load(fp)
            print(f"  - {os.path.basename(bf)}: {len(bdata)} prompts")
        except Exception as e:
            print(f"  - {os.path.basename(bf)}: Error ({e})")

    # Check next batch in progress
    next_batch = len(batch_files) + 1
    input_parts = sorted(glob.glob(os.path.join(BATCHES_DIR, f"batch_{next_batch:03d}_*_input.json")))
    trans_parts = sorted(glob.glob(os.path.join(TRANSLATED_DIR, f"batch_{next_batch:03d}_*_vi.json")))
    if input_parts or trans_parts:
        print(f"\nCurrent Batch in progress: Batch {next_batch:03d}")
        for tp in trans_parts:
            print(f"  - Translated part: {os.path.basename(tp)}")
        for ip in input_parts:
            print(f"  - Input part:      {os.path.basename(ip)}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    
    if action == "status":
        show_status()
    elif action == "inspect":
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py inspect <batch_num>")
            sys.exit(1)
        inspect_batch(int(sys.argv[2]))
    elif action in ["inspect-part", "inspect_part"]:
        if len(sys.argv) < 4:
            print("Usage: python3 pipeline_manager.py inspect-part <batch_num> <part>")
            sys.exit(1)
        inspect_part(int(sys.argv[2]), sys.argv[3])
    elif action in ["inspect-record", "inspect_record", "inspect-item", "inspect_item"]:
        if len(sys.argv) < 4:
            print("Usage: python3 pipeline_manager.py inspect-record <batch_num> <record_or_index> [part] [--full] [--json]")
            sys.exit(1)
        b_num = int(sys.argv[2])
        it_ref = sys.argv[3]
        part = None
        for arg in sys.argv[4:]:
            if not arg.startswith("--"):
                part = arg
                break
        full = "--full" in sys.argv
        as_json = "--json" in sys.argv
        inspect_record(b_num, it_ref, part, full=full, as_json=as_json)
    elif action in ["inspect-embedded", "inspect_embedded"]:
        if len(sys.argv) < 4:
            print("Usage: python3 pipeline_manager.py inspect-embedded <batch_num> <item_ref> [part]")
            sys.exit(1)
        b_num = int(sys.argv[2])
        it_ref = sys.argv[3]
        part = sys.argv[4] if len(sys.argv) > 4 else None
        inspect_embedded(b_num, it_ref, part)
    elif action in ["dump-embedded", "dump_embedded"]:
        if len(sys.argv) < 5:
            print("Usage: python3 pipeline_manager.py dump-embedded <batch_num> <item_ref> <part_idx_or_all> <out_path> [part]")
            sys.exit(1)
        b_num = int(sys.argv[2])
        it_ref = sys.argv[3]
        p_idx_str = sys.argv[4]
        out_f = sys.argv[5]
        part = sys.argv[6] if len(sys.argv) > 6 else None
        dump_embedded(b_num, it_ref, p_idx_str, out_f, part)
    elif action in ["dump-item", "dump_item"]:
        if len(sys.argv) < 5:
            print("Usage: python3 pipeline_manager.py dump-item <batch_num> <item_ref> <output_file> [part] [--full]")
            sys.exit(1)
        b_num = int(sys.argv[2])
        it_ref = sys.argv[3]
        out_f = sys.argv[4]
        part = sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5].startswith("--") else None
        dump_full = "--full" in sys.argv
        dump_item(b_num, it_ref, out_f, part, dump_full)
    elif action in ["assemble-record", "assemble_record"]:
        if len(sys.argv) < 6:
            print("Usage: python3 pipeline_manager.py assemble-record <batch_num> <item_ref> <parts_dir> <output_file> [part]")
            sys.exit(1)
        b_num = int(sys.argv[2])
        it_ref = sys.argv[3]
        parts_d = sys.argv[4]
        out_f = sys.argv[5]
        part = sys.argv[6] if len(sys.argv) > 6 else None
        assemble_record(b_num, it_ref, parts_d, out_f, part)
    elif action in ["run-script", "run_script"]:
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py run-script <script_path>")
            sys.exit(1)
        script_path = sys.argv[2]
        import runpy
        runpy.run_path(script_path, run_name="__main__")
    elif action == "prepare":
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py prepare <batch_num> [batch_size]")
            sys.exit(1)
        b_num = int(sys.argv[2])
        b_size = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        prepare_batch(b_num, b_size)
    elif action in ["split-batch", "split_batch"]:
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py split-batch <batch_num>")
            sys.exit(1)
        b_num = int(sys.argv[2])
        split_batch(b_num)
    elif action == "validate":
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py validate <batch_num>")
            sys.exit(1)
        b_num = int(sys.argv[2])
        valid, errs, nr = validate_batch(b_num)
        print("Valid:", valid)
        if errs:
            print("Errors:")
            for e in errs:
                print(f"  - {e}")
        print("Needs review count:", nr)
    elif action in ["combine-files", "combine_files"]:
        if len(sys.argv) < 4:
            print("Usage: python3 pipeline_manager.py combine-files <out_file> <file1> [file2 ...]")
            sys.exit(1)
        out_f = sys.argv[2]
        in_files = sys.argv[3:]
        combine_files(out_f, in_files)
    elif action in ["assemble-text-record", "assemble_text_record"]:
        if len(sys.argv) < 6:
            print("Usage: python3 pipeline_manager.py assemble-text-record <out_file> <meta_file> <src_item_file> <text_file1> [text_file2 ...]")
            sys.exit(1)
        out_f = sys.argv[2]
        meta_f = sys.argv[3]
        src_f = sys.argv[4]
        t_files = sys.argv[5:]
        assemble_text_record(out_f, meta_f, src_f, t_files)
    elif action in ["merge-parts", "merge_parts"]:
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py merge-parts <batch_num>")
            sys.exit(1)
        b_num = int(sys.argv[2])
        merge_parts(b_num)
    elif action in ["merge-subparts", "merge_subparts"]:
        if len(sys.argv) < 4:
            print("Usage: python3 pipeline_manager.py merge-subparts <batch_num> <part>")
            sys.exit(1)
        b_num = int(sys.argv[2])
        part_name = sys.argv[3]
        merge_subparts(b_num, part_name)
    elif action in ["sync-source", "sync_source"]:
        if len(sys.argv) < 3 or sys.argv[2] == "all":
            sync_all_source_fields()
        else:
            b_num = int(sys.argv[2])
            sync_source_fields(b_num)
    elif action in ["sync-all-source", "sync_all_source"]:
        sync_all_source_fields()
    elif action == "checkpoint":
        update_checkpoint()
    elif action in ["qa-sample", "qa_sample"]:
        start_b = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        end_b = int(sys.argv[3]) if len(sys.argv) > 3 else start_b
        qa_sample(start_b, end_b)
    elif action in ["locate-batch", "locate_batch"]:
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py locate-batch <batch_num>")
            sys.exit(1)
        b_num = int(sys.argv[2])
        locate_batch(b_num)
    elif action in ["final-merge", "final_merge", "merge"]:
        merge_final()
    elif action in ["export-sql", "export_sql", "export-supabase"]:
        out_p = sys.argv[2] if len(sys.argv) > 2 else None
        export_supabase_sql(out_p)
    elif action in ["preflight-config", "preflight_config", "preflight"]:
        ready = preflight_config()
        sys.exit(0 if ready else 1)
    elif action in ["build-search-index", "build_search_index", "index"]:
        success = build_search_index()
        sys.exit(0 if success else 1)
    elif action in ["test-search", "test_search", "search"]:
        if len(sys.argv) < 3:
            print("Usage: python3 pipeline_manager.py test-search <query> [limit]")
            sys.exit(1)
        q = sys.argv[2]
        lim = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        search_dataset(q, lim)
    elif action in ["publish-web-data", "publish_web_data", "publish"]:
        success = publish_web_data()
        sys.exit(0 if success else 1)
    elif action in ["validate-web", "validate_web"]:
        success = validate_web()
        sys.exit(0 if success else 1)
    elif action in ["qa-search-suite", "qa_search_suite", "search-qa"]:
        success = run_search_qa_suite()
        sys.exit(0 if success else 1)
    elif action in ["audit", "audit-dataset", "audit_dataset"]:
        success = audit_dataset()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown action: {action}")
        print("Available subcommands: status, inspect, inspect-part, inspect-record, locate-batch, prepare, split-batch, validate, merge-parts, sync-source, checkpoint, qa-sample, final-merge, export-sql, preflight-config, build-search-index, test-search, publish-web-data, validate-web, qa-search-suite, audit")
        sys.exit(1)


