import os
import sys
import json
import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000")

def score_grounding(response_body, candidate_ids):
    citations = response_body.get("citations", [])
    # Condition A: Must contain at least one citation
    cond_a = len(citations) >= 1
    # Condition B: Every cited chunk_id must exist within returned candidate_ids
    cond_b = all(cit.get("chunk_id") in candidate_ids for cit in citations)
    return cond_a and cond_b

def main():
    data_path = os.path.join("data", "rag_smoke.json")
    with open(data_path, "r") as f:
        questions = json.load(f)
        
    all_passed = True

    # High timeout threshold (60.0s) configured to eliminate flaky cold-cache issues
    with httpx.Client(timeout=60.0) as client:
        for q in questions:
            payload = {
                "question": q["question"],
                "k": q.get("k", 4)
            }
            try:
                response = client.post(f"{API_URL}/rag/answer", json=payload)
                if response.status_code != 200:
                    print(f"Question {q['question_id']}: FAIL (Status {response.status_code})")
                    all_passed = False
                    continue
                
                body = response.json()
                # Parse candidate_ids directly out of retrieved payloads
                candidate_ids = {chunk["chunk_id"] for chunk in body.get("retrieved", [])}
                
                if score_grounding(body, candidate_ids):
                    print(f"Question {q['question_id']}: PASS")
                else:
                    print(f"Question {q['question_id']}: FAIL (Grounding check failed)")
                    all_passed = False
                    
            except Exception as e:
                print(f"Question {q['question_id']}: FAIL (Exception: {e})")
                all_passed = False

    if not all_passed:
        sys.exit(1)
        
    print("All smoke tests passed successfully!")
    sys.exit(0)

if __name__ == "__main__":
    main()