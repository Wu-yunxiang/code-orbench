import json
import os
import argparse
import random

def mix_with_jailbreak(filtered_seeds_path, jailbreak_path, output_path, mix_ratio=0.3):
    """
    Randomly applies a jailbreak template to a subset of the filtered seeds.
    This simulates how developers or security researchers might frame code requests.
    Stores the template apart so the rewriter only acts on pure intent.
    """
    with open(filtered_seeds_path, 'r', encoding='utf-8') as f:
        seeds = json.load(f)
        
    with open(jailbreak_path, 'r', encoding='utf-8') as f:
        jailbreaks = json.load(f)
        
    jailbreak_templates = [jb["text"] for jb in jailbreaks if "[INSERT PROMPT HERE]" in jb.get("text", "")]
    
    mixed_data = []
    
    for seed in seeds:
        if random.random() < mix_ratio and jailbreak_templates:
            template = random.choice(jailbreak_templates)
            # Basic heuristic to insert the prompt into the jailbreak template
            mixed_prompt = template.replace("[INSERT PROMPT HERE]", seed["original_prompt"])
                
            seed["mixed_prompt"] = mixed_prompt
            seed["is_jailbroken"] = True
            seed["jailbreak_template"] = template
        else:
            seed["mixed_prompt"] = seed["original_prompt"]
            seed["is_jailbroken"] = False
            
        mixed_data.append(seed)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mixed_data, f, indent=4, ensure_ascii=False)
        
    print(f"Mixed {sum(1 for s in mixed_data if s['is_jailbroken'])} seeds with jailbreaks.")
    print(f"Saved mixed seeds to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mix toxic code seeds with jailbreaks.")
    parser.add_argument("--filtered", default="./dataset/01_filtered_seeds.json", help="Path to filtered seeds")
    parser.add_argument("--jailbreak", default="../toxic_seeds/jailbreak-prompt.json", help="Path to jailbreak file")
    parser.add_argument("--output", default="./dataset/02_mixed_seeds.json", help="Path to output mixed json")
    parser.add_argument("--ratio", type=float, default=0.3, help="Ratio of prompts to jailbreak")
    args = parser.parse_args()
    
    mix_with_jailbreak(args.filtered, args.jailbreak, args.output, args.ratio)
