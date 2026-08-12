import csv
import os
import time
import pandas as pd
import requests

BASE_URL = "http://127.0.0.1:5000/api"
OLLAMA_URL = "http://127.0.0.1:2345/"
CSV_FILE = "final.new.csv"
CSV_FIELDS = ["question", "answer", "response", "token used", "time", "model", "branch(True / False)"]
MODELS = ["gemma3:4b", "llama3:1b", "gemma3:12b", "gemma4:12b", "qwen3.5:latest"]

MODEL_FALLBACKS = {
    "llama3:1b": ["llama3:1b", "llama3.2:1b"],
    "qwen:9b": ["qwen:9b", "qwen2.5:9b", "qwen3.5:latest"]
}

def init_csv():
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

def append_to_csv(record):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(record)
        f.flush()

def send_chat(message, parent_id=None, system_prompt=None, model="gemma3:4b", max_retries=5):
    payload = {
        "provider": "ollama",
        "model": model,
        "ollama_base_url": OLLAMA_URL,
        "message": message
    }
    if parent_id is not None:
        payload["parent_id"] = parent_id
    if system_prompt is not None:
        payload["system_prompt"] = system_prompt

    models_to_try = MODEL_FALLBACKS.get(model, [model])

    for current_model in models_to_try:
        payload["model"] = current_model
        for attempt in range(max_retries):
            try:
                start_t = time.time()
                resp = requests.post(f"{BASE_URL}/chat", json=payload, timeout=240)
                elapsed_t = round(time.time() - start_t, 4)

                if resp.status_code == 200:
                    res_data = resp.json().get("data", {})
                    res_data["elapsed_time"] = elapsed_t
                    return res_data
                elif resp.status_code == 404 and current_model != models_to_try[-1]:
                    print(f"[Warning] Model '{current_model}' returned 404, attempting fallback to next model in list...")
                    break
                else:
                    print(f"[Warning] HTTP {resp.status_code} ({resp.text[:100]!r}) on attempt {attempt+1}/{max_retries} for {current_model}. Retrying in {(attempt+1)*3}s...")
                    time.sleep(3 * (attempt + 1))
            except Exception as e:
                print(f"[Warning] Request exception '{e}' on attempt {attempt+1}/{max_retries} for {current_model}. Retrying in {(attempt+1)*3}s...")
                time.sleep(3 * (attempt + 1))
    raise Exception(f"Failed to send_chat for model {model} after retries.")

def extract_answer(answer_text):
    for char in answer_text:
        if char in ['A', 'B', 'C', 'D']:
            return char
    return ""

def main():
    print("Loading datasets...")
    with open("dataset/passage1.txt", "r", encoding="utf-8") as f:
        p1 = f.read().strip()
    with open("dataset/passage2.txt", "r", encoding="utf-8") as f:
        p2 = f.read().strip()
    
    qa_df = pd.read_csv("dataset/qa.csv")
    
    system_prompt = (
        "You are a reading comprehension test assistant. "
        "For any multiple choice question, reply with ONLY ONE uppercase letter (A, B, C, or D) corresponding to the correct choice."
    )

    init_csv()

    for model in MODELS:
        print("\n=========================================")
        print(f"Testing Model: {model}")
        print("=========================================")

        print(f"[{model}] Establishing context nodes (Passage 1 -> Passage 2)...")
        try:
            res1 = send_chat(f"Here is Passage 1:\n\n{p1}\n\nPlease acknowledge.", system_prompt=system_prompt, model=model)
            node1_id = res1["currentNodeId"]
            print(f"[{model}] Passage 1 established. Node ID: {node1_id}, Time: {res1.get('elapsed_time')}s")
            
            res2 = send_chat(f"Here is Passage 2:\n\n{p2}\n\nPlease acknowledge.", parent_id=node1_id, system_prompt=system_prompt, model=model)
            root_node_id = res2["currentNodeId"]
            print(f"[{model}] Passage 2 established. Node ID: {root_node_id}, Time: {res2.get('elapsed_time')}s")
        except Exception as e:
            print(f"[{model}] Failed to establish context: {e}")
            continue

        # 1. Linear Test (branch=False)
        print(f"\n--- [{model}] Start Linear Test (branch=False) ---")
        current_parent_id = root_node_id
        for idx, row in qa_df.iterrows():
            q = row['question']
            choice_d = str(row['choice_D']).replace('\n\nAnswer:', '').strip()
            choices = f"A) {row['choice_A']}\nB) {row['choice_B']}\nC) {row['choice_C']}\nD) {choice_d}"
            prompt = f"Question {idx+1}:\n{q}\n{choices}\n\nReply with ONLY the correct letter (A, B, C, or D)."
            expected = str(row['answer']).strip()

            try:
                res = send_chat(prompt, parent_id=current_parent_id, system_prompt=system_prompt, model=model)
                answer = res.get("content", "").strip()
                current_parent_id = res.get("currentNodeId")
                parsed_answer = extract_answer(answer)
                tokens = res.get("token_used") or res.get("tokens_used", 0)
                elapsed = res.get("elapsed_time", 0.0)

                record = {
                    "question": q,
                    "answer": expected,
                    "response": answer,
                    "token used": tokens,
                    "time": elapsed,
                    "model": model,
                    "branch(True / False)": False
                }
                append_to_csv(record)
                print(f"[{model}][Linear] Q{idx+1} Expected: {expected}, Got: {parsed_answer} (Raw: {answer!r}), Tokens: {tokens}, Time: {elapsed}s")
            except Exception as e:
                print(f"[{model}][Linear] Q{idx+1} Failed: {e}")
                break

        # 2. Branching Test (branch=True)
        print(f"\n--- [{model}] Start Branching Test (branch=True) ---")
        for idx, row in qa_df.iterrows():
            q = row['question']
            choice_d = str(row['choice_D']).replace('\n\nAnswer:', '').strip()
            choices = f"A) {row['choice_A']}\nB) {row['choice_B']}\nC) {row['choice_C']}\nD) {choice_d}"
            prompt = f"Question {idx+1}:\n{q}\n{choices}\n\nReply with ONLY the correct letter (A, B, C, or D)."
            expected = str(row['answer']).strip()

            try:
                res = send_chat(prompt, parent_id=root_node_id, system_prompt=system_prompt, model=model)
                answer = res.get("content", "").strip()
                parsed_answer = extract_answer(answer)
                tokens = res.get("token_used") or res.get("tokens_used", 0)
                elapsed = res.get("elapsed_time", 0.0)

                record = {
                    "question": q,
                    "answer": expected,
                    "response": answer,
                    "token used": tokens,
                    "time": elapsed,
                    "model": model,
                    "branch(True / False)": True
                }
                append_to_csv(record)
                print(f"[{model}][Branching] Q{idx+1} Expected: {expected}, Got: {parsed_answer} (Raw: {answer!r}), Tokens: {tokens}, Time: {elapsed}s")
            except Exception as e:
                print(f"[{model}][Branching] Q{idx+1} Failed: {e}")

    print("\nBenchmark completed. Results written to final.new.csv.")

if __name__ == "__main__":
    main()
