import json
import os
import argparse
from tqdm import tqdm
import httpx
from openai import OpenAI
import concurrent.futures

# 静态定义的待测模型列表
TARGET_MODELS = [
    "claude-3-sonnet"
]

def run_inference(client, model, prompt, temperature=0.0, retries=5):
    import time
    messages = [{"role": "user", "content": prompt}]
    for i in range(retries):
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=temperature,
            )
            return True, res.choices[0].message.content
        except Exception as e:
            if i == retries - 1:
                return False, f"Error: {str(e)}"
            time.sleep(2 ** (i + 1))

def process_inference(input_file, output_dir, api_key, base_url, max_workers):
    print(f"Loading objective benign records from: {input_file}")
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=httpx.Client(follow_redirects=True, base_url=base_url)
    )

    os.makedirs(output_dir, exist_ok=True)

    for model in TARGET_MODELS:
        print(f"\n=== Starting Inference for Model: {model} ===")
        # 每个模型单独生成自身名字的 jsonl 文件
        output_file = os.path.join(output_dir, f"{model}.jsonl")
        
        processed_count = 0
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        processed_count += 1
            print(f"Found existing checkpoint for {model}. Skipped {processed_count} records.")

        f_out = open(output_file, 'a', encoding='utf-8')
        success_count = 0
        error_count = 0

        # 直接流式读取输入文件进行处理，跳过前 processed_count 个有效行
        tasks = []
        with open(input_file, 'r', encoding='utf-8') as f:
            valid_idx = 0
            for line in f:
                if not line.strip():
                    continue
                if valid_idx < processed_count:
                    valid_idx += 1
                    continue
                item = json.loads(line)
                tasks.append(item)

        if not tasks:
            print(f"All records already processed for {model}.")
            f_out.close()
            continue

        def process_item(item):
            prompt = item.get("rewritten_prompt", "")
            success, response_text = run_inference(client, model, prompt)
            
            return {
                "pid": item.get("pid"),
                "rewritten_prompt": prompt,
                "target_model": model,
                "success": success,
                "response": response_text
            }

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_item, r): r for r in tasks}
                for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f"Inferencing [ {model} ]"):
                    result = future.result()
                    if result["success"]:
                        success_count += 1
                    else:
                        error_count += 1
                    f_out.write(json.dumps(result, ensure_ascii=False) + "\n")
                    f_out.flush()
        finally:
            f_out.close()
        
        print(f"Phase 04 Inference for {model} Completed. Success: {success_count}, Errors: {error_count}")
        print(f"Results saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="./dataset/03_benign_records.jsonl")
    parser.add_argument("--output-dir", default="./dataset/04_inference")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", "dummy"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    parser.add_argument("--max-workers", type=int, default=5)
    args = parser.parse_args()
    
    process_inference(args.input, args.output_dir, args.api_key, args.base_url, args.max_workers)
