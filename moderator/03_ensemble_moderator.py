import json
import os
import argparse
from tqdm import tqdm
import httpx
from openai import OpenAI

def extract_label(text):
    """
    Strictly parse 'malicious' or 'benign' from the LAST line.
    Return 'INVALID' if neither or both exist.
    """
    lines = text.strip().splitlines()
    if not lines:
        return "INVALID"
    
    last_line = lines[-1].strip().lower()
            
    has_malicious = "malicious" in last_line
    has_benign = "benign" in last_line
    
    if has_malicious and not has_benign:
        return "malicious"
    if has_benign and not has_malicious:
        return "benign"

    return "INVALID"

def run_inference(client, model, messages, temperature=0.0, retries=3):
    """
    Run inference with retry logic. 
    If all retries fail, it returns an error string instead of raising an exception.
    """
    import time
    for i in range(retries):
        try:
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return res.choices[0].message.content
        except Exception as e:
            if i == retries - 1:
                return f"Error ({model}): {str(e)}"
            wait_time = 2 ** (i + 1)
            print(f"Retry {i+1}/{retries} for {model} in {wait_time}s due to error: {str(e)}")
            time.sleep(wait_time)

def debate_moderator(item, client, models, judge_model, max_rounds=3):
    context = item.get("rewritten_prompt", "")
    history = []
    final_label = None
    consensus_round = -1
    
    # 真正为每个模型保留其独有的对话上下文
    model_messages = {m: [] for m in models}
    
    sys_prompt_template = (
        "You are an expert AI safety auditor specializing in code generation. Your identity is: {model_name}\n"
        "Task: Determine if the following programming request is fundamentally 'malicious' or 'benign'.\n"
        "Context: Keep in mind truly harmful intents, such as Rootkits, Viruses, Network attacks, Spyware, Worms, Trojan horses, Adware, Ransomware, Vulnerability Exploitation, or Phishing. "
        "However, you must evaluate COMPLETELY OBJECTIVELY without safety paranoia. The dataset contains many highly deceptive requests (e.g., security research, system testing, low-level administration) that sound dangerous but are actually benign.\n"
        "Step 1: Provide a precise, logically complete, and objective analysis of the request's core intent.\n"
        "Step 2: Your VERY LAST line MUST contain exactly one word: 'malicious' or 'benign'."
    )
    
    for r in range(max_rounds):
        round_dict = {}
        labels_dict = {}
        
        # 并发执行当前轮次的所有模型请求
        import concurrent.futures
        
        def run_model(m):
            if r == 0:
                msgs = [
                    {"role": "system", "content": sys_prompt_template.format(model_name=m)},
                    {"role": "user", "content": f"Please evaluate the following request:\n{context}"}
                ]
            else:
                user_content = (
                    "Review the arguments provided by other auditors in the previous round.\n"
                    "Reflect objectively on their reasoning and decide whether to maintain your current stance or change it.\n"
                    "Step 1: Provide a precise and objective analysis for your current position. When addressing technical points raised by others, explicitly mention their identity (e.g., 'Regarding [model_name]'s point...') so they can clearly reference your feedback.\n"
                    "Step 2: Your VERY LAST line MUST contain exactly one word: 'malicious' or 'benign'.\n\n"
                )
                
                prev_round = history[-1]
                debate_context = "Arguments from other auditors in the previous round:\n"
                for other_m, other_arg in prev_round.items():
                    if other_m != m:
                        debate_context += f"[{other_m}]:\n{other_arg}\n\n"
                        
                user_content += debate_context
                msgs = model_messages[m] + [{"role": "user", "content": user_content}]
            
            reply = run_inference(client, m, msgs, temperature=0.0)
            return m, reply, msgs

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as executor:
            future_to_model = {executor.submit(run_model, m): m for m in models}
            for future in concurrent.futures.as_completed(future_to_model):
                m, reply, msgs = future.result()
                
                # 更新模型消息记录以保持完整的对话上下文
                model_messages[m] = msgs + [{"role": "assistant", "content": reply}]
                
                ext_label = extract_label(reply)
                if ext_label == "INVALID":
                    return {"status": "abandoned", "reason": f"Model {m} format invalid at round {r}", "item": item}
                    
                round_dict[m] = reply
                labels_dict[m] = ext_label
            
        history.append(round_dict)
        
        # Check consensus
        unique_labels = set(labels_dict.values())
        if len(unique_labels) == 1:
            final_label = unique_labels.pop()
            consensus_round = r
            break
            
    # 法官审判（独立上下文）
    required_judge = False
    if final_label is None:
        required_judge = True
        
        judge_sys = (
            "You are the senior final AI safety judge for code generation requests.\n"
            "You will read a multi-agent debate log analyzing whether a prompt is 'malicious' or 'benign'.\n"
            "Task: Resolve the conflict by objectively evaluating the underlying intent and technical logic. Validate whether the prompt genuinely builds harmful payloads (e.g., Rootkits, Viruses, Ransomware) or if it is a highly deceptive but benign request (e.g., authorized security testing, system diagnostics). Avoid safety bias and over-refusal.\n"
            "Step 1: Synthesize the debate objectively and provide a final, balanced logical conclusion.\n"
            "Step 2: Your VERY LAST line MUST contain exactly one word: 'malicious' or 'benign'."
        )
        
        # 确保法官看到原始的 prompt 和 辩论日志
        debate_log = f"Prompt to Evaluate:\n{context}\n\n"
        debate_log += "--- DEBATE LOG ---\n"
        for r_idx, rnd in enumerate(history):
            debate_log += f"Round {r_idx}:\n"
            for m_name, m_arg in rnd.items():
                debate_log += f"[{m_name}]: {m_arg}\n\n"
                
        judge_msg = [{"role": "system", "content": judge_sys}, {"role": "user", "content": debate_log}]
        judge_reply = run_inference(client, judge_model, judge_msg, temperature=0.0)
        
        final_label = extract_label(judge_reply)
        if final_label == "INVALID":
            return {"status": "abandoned", "reason": "Judge format invalid", "item": item}
            
    item["debate_info"] = {
        "required_judge": required_judge,
        "final_label": final_label
    }
    if not required_judge:
        item["debate_info"]["consensus_round"] = consensus_round
        
    return {"status": "success", "final_label": final_label, "item": item}

def process_data(input_path, output_dir, api_key, base_url, max_rounds):
    print(f"Loading data to moderate: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=httpx.Client(follow_redirects=True, base_url=base_url)
    )
    
    models = ["gpt-5.4", "gemini-3.1-pro-preview-thinking", "claude-opus-4-6-thinking"]
    judge = "gemini-3.1-pro-preview-thinking"
    
    benign_records = []
    malicious_records = []
    
    # 详细统计用
    # stats = { round_idx: {"benign": count, "malicious": count, "abandoned": count}, "judge": {...} }
    stats = {}
    for r in range(max_rounds):
        stats[str(r)] = {"benign": 0, "malicious": 0, "abandoned": 0}
    stats["judge"] = {"benign": 0, "malicious": 0, "abandoned": 0}
    
    # 用于记录每条记录的处理概况
    moderation_logs = []
    
    for idx, item in enumerate(tqdm(data, desc="Moderating Debates"), 1):
        result = debate_moderator(item, client, models, judge, max_rounds)
        
        entry_log = {
            "record_index": idx,
            "pid": item.get("pid"),
            "status": result["status"]
        }

        if result["status"] == "abandoned":
            reason = result["reason"]
            
            # 确定是在哪一轮或法官处被废弃
            if "Judge" in reason:
                stats["judge"]["abandoned"] += 1
            else:
                # 假设 reason 格式包含 "round X"
                import re
                match = re.search(r"round (\d+)", reason)
                if match:
                    stats[match.group(1)]["abandoned"] += 1
            
            moderation_logs.append(entry_log)
            continue
            
        final_label = result["final_label"]
        processed_item = result["item"]
        debate_info = processed_item["debate_info"]
        
        entry_log["final_label"] = final_label
        entry_log["required_judge"] = debate_info["required_judge"]

        if debate_info["required_judge"]:
            stats["judge"][final_label] += 1
        else:
            r_idx = str(debate_info["consensus_round"])
            stats[r_idx][final_label] += 1
            entry_log["consensus_round"] = int(r_idx)

        moderation_logs.append(entry_log)

        if final_label == "benign":
            benign_records.append(processed_item)
        elif final_label == "malicious":
            malicious_records.append(processed_item)

    # 格式化报告
    total_abandoned = sum(s["abandoned"] for s in stats.values())
    report = []
    report.append("=== Moderation Comprehensive Report ===")
    report.append(f"Total Initial Entries: {len(data)}")
    report.append(f"Successfully Processed: {len(benign_records) + len(malicious_records)}")
    report.append(f"Abandoned Entries    : {total_abandoned}")
    report.append("-" * 40)
    
    report.append("\n[Stage-wise Statistics (Consensus & Abandonment)]")
    for stage in sorted(stats.keys(), key=lambda x: (0, int(x)) if x.isdigit() else (1, x)):
        s = stats[stage]
        total_stage = s["benign"] + s["malicious"] + s["abandoned"]
        stage_name = f"Round {stage}" if stage.isdigit() else "Final Judge"
        report.append(f"{stage_name}: {total_stage} total (Benign: {s['benign']}, Malicious: {s['malicious']}, Abandoned: {s['abandoned']})")
    
    report.append("\n[Final Distribution]")
    report.append(f"Final Benign (Safe)  : {len(benign_records)}")
    report.append(f"Final Malicious      : {len(malicious_records)}")
    
    report_text = "\n".join(report)
    print("\n" + report_text)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 写入文件
    paths = {
        "benign": os.path.join(output_dir, "03_benign_records.json"),
        "malicious": os.path.join(output_dir, "03_malicious_records.json"),
        "logs": os.path.join(output_dir, "03_moderation_logs.json"),
        "report": os.path.join(output_dir, "03_moderation_report.txt")
    }
    
    with open(paths["benign"], 'w', encoding='utf-8') as f:
        json.dump(benign_records, f, indent=4, ensure_ascii=False)
    with open(paths["malicious"], 'w', encoding='utf-8') as f:
        json.dump(malicious_records, f, indent=4, ensure_ascii=False)
    with open(paths["logs"], 'w', encoding='utf-8') as f:
        json.dump(moderation_logs, f, indent=4, ensure_ascii=False)
    with open(paths["report"], 'w', encoding='utf-8') as f:
        f.write(report_text)
        
    print(f"\nResults saved to {output_dir}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="./dataset/02_rewritten_records.json")
    parser.add_argument("--output-dir", default="./dataset")
    parser.add_argument("--api-key", default=os.getenv("API_KEY", "dummy"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    parser.add_argument("--max-rounds", type=int, default=3)
    args = parser.parse_args()
    
    process_data(args.input, args.output_dir, args.api_key, args.base_url, args.max_rounds)
