import argparse
import json
import os
from collections import defaultdict


def parse_csv_values(value, cast=str):
    if value is None:
        return None
    parsed = []
    for part in value.split(","):
        part = part.strip()
        if part:
            parsed.append(cast(part))
    return parsed


def parse_category_quotas(value):
    if not value:
        return None
    quotas = {}
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        category, count = part.split(":", 1)
        quotas[category.strip()] = int(count.strip())
    return quotas


def load_and_filter_seeds(
    input_path,
    output_path,
    target_task="text-to-code generation",
    exclude_levels=None,
    include_levels=None,
    categories=None,
    max_per_category=None,
    category_quotas=None,
):
    """
    Reads the raw toxic prompts provided by the user, filters based on task and levels,
    and exports a flattened JSON that can be consumed by the rewriter.
    """
    if exclude_levels is None:
        exclude_levels = [3] # Exclude level 3 by default

    include_levels = set(include_levels) if include_levels else None
    exclude_levels = set(exclude_levels or [])
    categories = set(categories) if categories else None
    per_category_counts = defaultdict(int)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    filtered_data = []
    skipped = 0
    
    for item in data:
        # We focus primarily on code generation related tasks where the model's safety behaviors are tested
        if item.get("task") != target_task:
            skipped += 1
            continue
            
        if item.get("level") in exclude_levels:
            skipped += 1
            continue

        if include_levels is not None and item.get("level") not in include_levels:
            skipped += 1
            continue

        malicious_category = item.get("malicious categories", "Unknown")
        if categories is not None and malicious_category not in categories:
            skipped += 1
            continue

        category_limit = None
        if category_quotas is not None:
            category_limit = category_quotas.get(malicious_category, 0)
        elif max_per_category is not None:
            category_limit = max_per_category

        if category_limit is not None and per_category_counts[malicious_category] >= category_limit:
            skipped += 1
            continue

        per_category_counts[malicious_category] += 1
        filtered_data.append({
            "pid": item["pid"],
            "original_prompt": item["prompt"],
            "malicious_functionality": item.get("malicious functionality", "Unknown"),
            "category": item.get("category", "Unknown"),
            "malicious_category": malicious_category,
            "level": item.get("level", 1)
        })
        
    print(f"Total raw seeds: {len(data)}")
    print(f"Skipped seeds (wrong task or excluded level): {skipped}")
    print(f"Filtered target seeds: {len(filtered_data)}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=4, ensure_ascii=False)
        
    print(f"Saved filtered seeds to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest and filter toxic code seeds.")
    parser.add_argument("--input", default="./toxic_seeds/prompt.json", help="Path to raw prompt.json")
    parser.add_argument("--output", default="./dataset/pilot/01_filtered_seeds.json", help="Path to output json")
    parser.add_argument("--target-task", default="text-to-code generation")
    parser.add_argument("--include-levels", default=None, help="Comma-separated levels to include, e.g. 1,2")
    parser.add_argument("--exclude-levels", default="3", help="Comma-separated levels to exclude. Defaults to 3.")
    parser.add_argument("--categories", default=None, help="Comma-separated malicious categories to include.")
    parser.add_argument("--max-per-category", type=int, default=None)
    parser.add_argument(
        "--category-quotas",
        default=None,
        help="Optional comma-separated per-category seed quotas, e.g. 'Ransomware:8,Spyware:8'. Overrides --max-per-category.",
    )
    args = parser.parse_args()

    load_and_filter_seeds(
        input_path=args.input,
        output_path=args.output,
        target_task=args.target_task,
        exclude_levels=parse_csv_values(args.exclude_levels, int),
        include_levels=parse_csv_values(args.include_levels, int),
        categories=parse_csv_values(args.categories, str),
        max_per_category=args.max_per_category,
        category_quotas=parse_category_quotas(args.category_quotas),
    )
