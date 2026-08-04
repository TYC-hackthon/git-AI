import os
import requests
import pandas as pd
import time

BASE_URL = "http://127.0.0.1:5000/api"
OLLAMA_URL = "https://sheep.ysh.xx.kg"
MODEL = "gemma3:4b"

def send_chat(message, parent_id=None, system_prompt=None):
    payload = {
        "provider": "ollama",
        "model": MODEL,
        "ollama_base_url": OLLAMA_URL,
        "message": message
    }
    if parent_id is not None:
        payload["parent_id"] = parent_id
    if system_prompt is not None:
        payload["system_prompt"] = system_prompt
        
    resp = requests.post(f"{BASE_URL}/chat", json=payload)
    if resp.status_code != 200:
        raise Exception(f"API Error {resp.status_code}: {resp.text}")
    return resp.json()["data"]

def extract_answer(answer_text):
    # Sometimes model might output full text like "**D**" or "Answer: C"
    # We just do a simple fallback search for A, B, C, D if it's short.
    # To be robust, search for the first uppercase A, B, C, D in the response.
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
        "You are taking a reading comprehension test. Read the passages below. "
        "For each question, reply with ONLY ONE uppercase letter (A, B, C, or D) corresponding to the correct choice.\n\n"
        f"Passage 1:\n{p1}\n\n"
        f"Passage 2:\n{p2}"
    )
    
    # Method 1: Linear
    print("\n=== Start Linear Test ===")
    linear_results = []
    current_parent_id = None
    
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
    
    try:
        # Establish a root node by sending a dummy message with the system prompt
        print("[Branching] Establishing Root Node with Passages...")
        root_res = send_chat(
            message="Please acknowledge that you have read the passages. Reply ONLY with 'Acknowledged'.",
            system_prompt=system_prompt
        )
        root_id = root_res.get("currentNodeId")
        print(f"[Branching] Root Node ID: {root_id}")
        
        for idx, row in qa_df.iterrows():
            q = row['question']
            choice_d = row['choice_D'].replace('\n\nAnswer:', '').strip()
            choices = f"A) {row['choice_A']}\nB) {row['choice_B']}\nC) {row['choice_C']}\nD) {choice_d}"
            prompt = f"Question {idx+1}:\n{q}\n{choices}\n\nReply with ONLY the correct letter (A, B, C, or D)."
            
            try:
                # Append each question to the root_id (create branches)
                res = send_chat(prompt, parent_id=root_id, system_prompt=system_prompt)
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
                
    except Exception as e:
        print(f"[Branching] Root Node Creation Failed: {e}")

    # Output CSVs and compute accuracies
    print("\n=== Summary ===")
    if linear_results:
        pd.DataFrame(linear_results).to_csv("linear_results.csv", index=False)
        lin_acc = sum(r["correct"] for r in linear_results) / len(linear_results)
        print(f"Linear Accuracy: {lin_acc:.2%} ({sum(r['correct'] for r in linear_results)}/{len(linear_results)})")
        
    if branching_results:
        pd.DataFrame(branching_results).to_csv("branching_results.csv", index=False)
        bran_acc = sum(r["correct"] for r in branching_results) / len(branching_results)
        print(f"Branching Accuracy: {bran_acc:.2%} ({sum(r['correct'] for r in branching_results)}/{len(branching_results)})")

if __name__ == "__main__":
    main()
