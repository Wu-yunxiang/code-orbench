import json
import os
import argparse
from tqdm import tqdm
import sys

# adding root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.output_parser import strip_think_tags

# Dummy API function placeholders. In actual implementation, you would call OpenAI, Anthropic, Gemini, etc.
def run_model_inference(prompt, model_name):
    """
    Mock inference function. 
    Replace with actual target model API calls for DeepSeek, Qwen, Claude, GPT, Gemini.
    """
    # ... actual API calling logic here ...
    # Return raw text response
    return f"Mock response for {prompt} from {model_name}"

def main(input_path, output_dir, model_name):
    print(f"Running Inference for {model_name}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    results = []
    
    for item in tqdm(data, desc=f"Evaluating {model_name}"):
        prompt = item["rewritten_prompt"]
        
        # 1. Get raw model response
        raw_response = run_model_inference(prompt, model_name)
        
        # 2. Key Step: Clean the response of thinking processes (DeepSeek-R1 / Qwen 3.5 specific)
        cleaned_response = strip_think_tags(raw_response)
        
        # 3. Store result
        result_item = item.copy()
        result_item["eval_model"] = model_name
        result_item["raw_response"] = raw_response
        result_item["cleaned_response"] = cleaned_response
        
        results.append(result_item)
        
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"{model_name}_results.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Saved {model_name} execution to {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="./dataset/05_moderated_safe_seeds.json")
    parser.add_argument("--output-dir", default="./dataset/eval_outputs/")
    parser.add_argument("--model", required=True, help="Model name (e.g. deepseek-r1, claude-4-6-opus-20260228)")
    args = parser.parse_args()
    
    main(args.input, args.output_dir, args.model)
