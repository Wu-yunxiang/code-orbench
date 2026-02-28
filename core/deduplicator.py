import json
import os
import argparse

def exact_match_deduplicate(input_path, output_path):
    print(f"Loading data from {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    seen = set()
    deduped_data = []
    
    for item in data:
        prompt_text = item.get("rewritten_prompt", "")
        if not prompt_text:
            continue
            
        # Lowercase and strip for slightly more robust exact match
        key = prompt_text.lower().strip()
        
        if key not in seen:
            seen.add(key)
            deduped_data.append(item)
            
    print(f"Original Count: {len(data)}")
    print(f"Deduplicated Count: {len(deduped_data)}")
    print(f"Removed: {len(data) - len(deduped_data)}")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(deduped_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="./dataset/03_rewritten_seeds.json")
    parser.add_argument("--output", default="./dataset/04_deduped_seeds.json")
    args = parser.parse_args()
    
    exact_match_deduplicate(args.input, args.output)
