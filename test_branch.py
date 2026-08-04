import os
import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:5000/api"
MODEL = "gemma3:4b"

def send_chat(message, parent_id=None, system_prompt=None):
    payload = {
        "provider": "ollama",
        "model": MODEL,
        "message": message
    }
    # 省略 ollama_base_url，讓後端預設打本地 (localhost:11434)
    if parent_id is not None:
        payload["parent_id"] = parent_id
    if system_prompt is not None:
        payload["system_prompt"] = system_prompt
        
    resp = requests.post(f"{BASE_URL}/chat", json=payload)
    if resp.status_code != 200:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
    return resp.json()["data"]

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
    
    # 建立上下文 (Node 1 -> Node 2)
    print("Establishing context nodes (Passage 1 -> Passage 2)...")
    try:
        res1 = send_chat(f"Here is Passage 1:\n\n{p1}\n\nPlease acknowledge.", system_prompt=system_prompt)
        node1_id = res1["currentNodeId"]
        print(f"Passage 1 established. Node ID: {node1_id}")
        
        res2 = send_chat(f"Here is Passage 2:\n\n{p2}\n\nPlease acknowledge.", parent_id=node1_id, system_prompt=system_prompt)
        root_node_id = res2["currentNodeId"]
        print(f"Passage 2 established. Node ID: {root_node_id}")
    except Exception as e:
        print(f"Failed to establish context: {e}")
        return

    # Method 1: Linear
    print("\n=== Start Linear Test ===")
    linear_results = []
    current_parent_id = root_node_id
    
    for idx, row in qa_df.iterrows():
        q = row['question']
        choice_d = row['choice_D'].replace('\n\nAnswer:', '').strip()
        choices = f"A) {row['choice_A']}\nB) {row['choice_B']}\nC) {row['choice_C']}\nD) {choice_d}"
        prompt = f"Question {idx+1}:\n{q}\n{choices}\n\nReply with ONLY the correct letter (A, B, C, or D)."
        
        try:
            res = send_chat(prompt, parent_id=current_parent_id, system_prompt=system_prompt)
            answer = res.get("content", "").strip()
            current_parent_id = res.get("currentNodeId")
            
            expected = row['answer'].strip()
            parsed_answer = extract_answer(answer)
            correct = (expected == parsed_answer)
            
            linear_results.append({
                "question_id": row["id"],
                "expected": expected,
                "actual_response": answer,
                "parsed_answer": parsed_answer,
                "correct": correct
            })
            print(f"[Linear] Q{idx+1} Expected: {expected}, Got: {parsed_answer} (Raw: {answer!r}), Correct: {correct}")
        except Exception as e:
            print(f"[Linear] Q{idx+1} Failed: {e}")
            break

    # Method 2: Branching
    print("\n=== Start Branching Test ===")
    branching_results = []
    
    for idx, row in qa_df.iterrows():
        q = row['question']
        choice_d = row['choice_D'].replace('\n\nAnswer:', '').strip()
        choices = f"A) {row['choice_A']}\nB) {row['choice_B']}\nC) {row['choice_C']}\nD) {choice_d}"
        prompt = f"Question {idx+1}:\n{q}\n{choices}\n\nReply with ONLY the correct letter (A, B, C, or D)."
        
        try:
            res = send_chat(prompt, parent_id=root_node_id, system_prompt=system_prompt)
            answer = res.get("content", "").strip()
            
            expected = row['answer'].strip()
            parsed_answer = extract_answer(answer)
            correct = (expected == parsed_answer)
            
            branching_results.append({
                "question_id": row["id"],
                "expected": expected,
                "actual_response": answer,
                "parsed_answer": parsed_answer,
                "correct": correct
            })
            print(f"[Branching] Q{idx+1} Expected: {expected}, Got: {parsed_answer} (Raw: {answer!r}), Correct: {correct}")
        except Exception as e:
            print(f"[Branching] Q{idx+1} Failed: {e}")

    # Output CSVs and compute accuracies
    print("\n=== Summary ===")
    if linear_results:
        pd.DataFrame(linear_results).to_csv("linear_results_local.csv", index=False)
        lin_acc = sum(r["correct"] for r in linear_results) / len(linear_results)
        print(f"Linear Accuracy: {lin_acc:.2%} ({sum(r['correct'] for r in linear_results)}/{len(linear_results)})")
        
    if branching_results:
        pd.DataFrame(branching_results).to_csv("branching_results_local.csv", index=False)
        bran_acc = sum(r["correct"] for r in branching_results) / len(branching_results)
        print(f"Branching Accuracy: {bran_acc:.2%} ({sum(r['correct'] for r in branching_results)}/{len(branching_results)})")

if __name__ == "__main__":
    main()
