import argparse
import json
import os
from collections import Counter, defaultdict


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def get_category(row):
    return row.get("source_category") or row.get("malicious_category") or row.get("category") or "Unknown"


def get_family(row):
    return row.get("prompt_family") or row.get("risk_surface_profile") or "Unknown"


def get_difficulty(row):
    return row.get("difficulty") or "Unknown"


def get_slot(row):
    slot = row.get("template_slot")
    if slot not in (None, ""):
        return str(slot)
    variant = str(row.get("template_variant") or "")
    if variant.startswith("slot_"):
        return variant.split(":", 1)[0].replace("slot_", "")
    return "Unknown"


def get_refusal_rate(row):
    value = row.get("refusal_rate")
    if isinstance(value, (int, float)):
        return float(value)
    potential = row.get("refusal_potential") or {}
    value = potential.get("refusal_rate")
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def get_non_refusal_rate(row):
    value = row.get("non_refusal_rate")
    if isinstance(value, (int, float)):
        return float(value)
    potential = row.get("refusal_potential") or {}
    value = potential.get("non_refusal_rate")
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def get_reason(row):
    return row.get("keep_reason") or (row.get("refusal_potential") or {}).get("reason") or "unknown"


def record_key(row):
    return row.get("record_id") or row.get("rewritten_prompt")


def prompt_key(row):
    return " ".join((row.get("rewritten_prompt") or "").lower().split())


def natural_slot_key(slot):
    try:
        return (0, int(slot))
    except (TypeError, ValueError):
        return (1, str(slot))


def candidate_priority(row, target_refusal_rate):
    refusal_rate = get_refusal_rate(row)
    non_refusal_rate = get_non_refusal_rate(row)
    distance = abs(refusal_rate - target_refusal_rate)
    return (distance, -refusal_rate, -non_refusal_rate, str(record_key(row)))


def order_for_slot_diversity(rows, target_refusal_rate):
    buckets = defaultdict(list)
    for row in rows:
        buckets[get_slot(row)].append(row)
    for bucket in buckets.values():
        bucket.sort(key=lambda row: candidate_priority(row, target_refusal_rate))

    ordered = []
    slots = sorted(buckets, key=natural_slot_key)
    while True:
        added = False
        for slot in slots:
            if buckets[slot]:
                ordered.append(buckets[slot].pop(0))
                added = True
        if not added:
            return ordered


def order_for_category_slot_diversity(rows, target_refusal_rate):
    buckets = defaultdict(list)
    for row in rows:
        buckets[get_category(row)].append(row)
    for category in list(buckets):
        buckets[category] = order_for_slot_diversity(buckets[category], target_refusal_rate)

    ordered = []
    categories = sorted(buckets)
    while True:
        added = False
        for category in categories:
            if buckets[category]:
                ordered.append(buckets[category].pop(0))
                added = True
        if not added:
            return ordered


def select_all_calibrated(rows, target_refusal_rate):
    selected = []
    used_ids = set()
    used_prompts = set()

    for row in order_for_category_slot_diversity(rows, target_refusal_rate):
        key = record_key(row)
        pkey = prompt_key(row)
        if not key or key in used_ids or pkey in used_prompts:
            continue
        selected.append(row)
        used_ids.add(key)
        used_prompts.add(pkey)
    return selected


def strip_internal_fields(row):
    cleaned = dict(row)
    cleaned["selection_metadata"] = {
        "selection_source": "calibrated",
        "selection_reason": get_reason(row),
        "selection_refusal_rate": get_refusal_rate(row),
        "selection_non_refusal_rate": get_non_refusal_rate(row),
    }
    return cleaned


def write_report(path, selected, pool):
    by_category = Counter(get_category(row) for row in selected)
    by_family = Counter(get_family(row) for row in selected)
    by_difficulty = Counter(get_difficulty(row) for row in selected)
    by_slot = Counter(get_slot(row) for row in selected)
    reasons = Counter(get_reason(row) for row in selected)

    lines = [
        "=== Phase 03C Calibrated Split Report ===",
        f"Calibrated pool size: {len(pool)}",
        f"Selected records after deduplication: {len(selected)}",
        "",
        "[Selected by difficulty]",
    ]
    for key, count in sorted(by_difficulty.items()):
        lines.append(f"{key}: {count}")

    lines.append("\n[Selected by category]")
    for key, count in sorted(by_category.items()):
        lines.append(f"{key}: {count}")

    lines.append("\n[Selected by prompt family]")
    for key, count in sorted(by_family.items()):
        lines.append(f"{key}: {count}")

    lines.append("\n[Selected by template slot]")
    for key, count in sorted(by_slot.items(), key=lambda item: natural_slot_key(item[0])):
        lines.append(f"{key}: {count}")

    lines.append("\n[Selection reasons]")
    for key, count in sorted(reasons.items()):
        lines.append(f"{key}: {count}")

    report = "\n".join(lines)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return report


def process_selection(calibrated_input, output, report_output, target_refusal_rate):
    rows = load_jsonl(calibrated_input)
    selected = select_all_calibrated(rows, target_refusal_rate)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(strip_internal_fields(row), ensure_ascii=False) + "\n")

    report = write_report(report_output, selected, rows)
    print(report)
    print(f"Selected records saved to: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the final Code-ORbench split by keeping every calibrated record after deduplication."
    )
    parser.add_argument("--calibrated-input", default="./dataset/pilot/03b_calibrated_records.jsonl")
    parser.add_argument("--output", default="./dataset/pilot/03c_selected_records.jsonl")
    parser.add_argument("--report-output", default="./dataset/pilot/03c_selection_report.txt")
    parser.add_argument(
        "--target-refusal-rate",
        type=float,
        default=0.50,
        help="Used only for deterministic ordering; it does not filter records.",
    )
    args = parser.parse_args()

    process_selection(
        calibrated_input=args.calibrated_input,
        output=args.output,
        report_output=args.report_output,
        target_refusal_rate=args.target_refusal_rate,
    )
