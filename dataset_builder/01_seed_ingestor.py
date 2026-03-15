import json
import os
import argparse

def load_and_filter_seeds(input_path, output_path, target_task="text-to-code generation", exclude_levels=None):
    """
    Reads the raw toxic prompts provided by the user, filters based on task and levels,
    and exports a flattened JSON that can be consumed by the rewriter.
    """
    if exclude_levels is None:
        exclude_levels = [3] # Exclude level 3 by default

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
            
        filtered_data.append({
            "pid": item["pid"],
            "original_prompt": item["prompt"],
            "malicious_functionality": item.get("malicious functionality", "Unknown"),
            "category": item.get("category", "Unknown"),
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
    parser.add_argument("--input", default="../toxic_seeds/prompt.json", help="Path to raw prompt.json")
    parser.add_argument("--output", default="./dataset/01_filtered_seeds.json", help="Path to output json")
    args = parser.parse_args()
    
    load_and_filter_seeds(args.input, args.output)
