"""
Loomin-Docs — RAG Faithfulness Verification Test

This script verifies that the RAG pipeline:
1. Correctly retrieves and cites information from indexed documents.
2. Does NOT hallucinate information not found in the indexed documents.

Usage:
    python test_faithfulness.py --backend-url http://localhost:8000

Requirements:
    - Backend must be running
    - Ollama must be running with at least one model available
"""

import argparse
import requests
import sys
import json
import tempfile
import time
import os

# ─── Test Data ───────────────────────────────────────────────────────
TEST_DOCUMENT_CONTENT = """
# Loomin Corporation — Q4 2025 Financial Report

## Revenue
Total revenue for Q4 2025 was $47.3 million, representing a 23% increase
over Q4 2024. Enterprise subscriptions contributed $31.2 million, while
professional services accounted for $16.1 million.

## Key Metrics
- Monthly Active Users (MAU): 2.4 million
- Net Revenue Retention (NRR): 127%
- Customer Acquisition Cost (CAC): $1,450
- Annual Recurring Revenue (ARR): $189.2 million

## Strategic Initiatives
The company launched Project Aurora in October 2025, an AI-powered
document analysis platform targeting the legal and healthcare sectors.
Initial pilot customers include Meridian Health Systems and Vanguard Legal Group.

## Regional Performance
- North America: $28.9M (61% of total revenue)
- Europe: $12.3M (26% of total revenue)
- Asia-Pacific: $6.1M (13% of total revenue)
"""

# Questions whose answers ARE in the document
GROUNDED_QUESTIONS = [
    {
        "question": "What was Loomin Corporation's total revenue in Q4 2025?",
        "expected_keywords": ["47.3", "million"],
        "description": "Direct fact retrieval",
    },
    {
        "question": "What is the Net Revenue Retention rate?",
        "expected_keywords": ["127"],
        "description": "Metric retrieval",
    },
    {
        "question": "What is Project Aurora?",
        "expected_keywords": ["AI", "document", "legal", "healthcare"],
        "description": "Strategic initiative retrieval",
    },
]

# Questions whose answers are NOT in the document (should refuse or caveat)
HALLUCINATION_QUESTIONS = [
    {
        "question": "What was Loomin Corporation's Q3 2025 revenue?",
        "forbidden_patterns": ["Q3 2025 revenue was", "In Q3 2025, revenue"],
        "description": "Temporal hallucination (Q3 data not in doc)",
    },
    {
        "question": "Who is the CEO of Loomin Corporation?",
        "forbidden_patterns": ["The CEO is", "CEO of Loomin"],
        "description": "Entity hallucination (CEO not mentioned)",
    },
]


def upload_test_document(base_url: str) -> str:
    """Upload the test document and return its ID."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(TEST_DOCUMENT_CONTENT)
        f.flush()
        temp_path = f.name

    try:
        with open(temp_path, 'rb') as f:
            resp = requests.post(
                f"{base_url}/api/documents/upload",
                files={"file": ("q4_2025_report.txt", f, "text/plain")},
            )
        resp.raise_for_status()
        doc = resp.json()
        return doc["id"]
    finally:
        os.unlink(temp_path)


def get_available_model(base_url: str) -> str:
    """Get the first available model from Ollama."""
    resp = requests.get(f"{base_url}/api/models")
    models = resp.json().get("models", [])
    if not models:
        print("⚠️  No models available in Ollama. Using 'llama3' as default.")
        return "llama3"
    return models[0]["name"]


def ask_question(base_url: str, question: str, model: str) -> dict:
    """Send a chat question and get the response."""
    resp = requests.post(
        f"{base_url}/api/chat",
        json={"message": question, "model": model},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def run_tests(base_url: str):
    results = {"passed": 0, "failed": 0, "errors": 0, "details": []}

    # Step 1: Health check
    print("\n🔍 Checking backend health...")
    try:
        resp = requests.get(f"{base_url}/api/health")
        resp.raise_for_status()
        print("   ✅ Backend is healthy\n")
    except Exception as e:
        print(f"   ❌ Backend unreachable: {e}")
        sys.exit(1)

    # Step 2: Get model
    model = get_available_model(base_url)
    print(f"🤖 Using model: {model}\n")

    # Step 3: Upload test document
    print("📄 Uploading test document...")
    try:
        doc_id = upload_test_document(base_url)
        print(f"   ✅ Uploaded document: {doc_id}\n")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        sys.exit(1)

    time.sleep(1)  # Let indexing settle

    # Step 4: Test grounded questions (should cite sources)
    print("═" * 60)
    print("TEST GROUP 1: Grounded Questions (answers in document)")
    print("═" * 60)

    for i, test in enumerate(GROUNDED_QUESTIONS, 1):
        print(f"\n  Test {i}: {test['description']}")
        print(f"  Q: {test['question']}")
        try:
            result = ask_question(base_url, test["question"], model)
            response = result["response"].lower()
            citations = result.get("citations", [])

            # Check if expected keywords are in the response
            found = sum(1 for kw in test["expected_keywords"] if kw.lower() in response)
            has_citations = len(citations) > 0

            if found >= len(test["expected_keywords"]) // 2 + 1:
                print(f"  ✅ PASS — Found {found}/{len(test['expected_keywords'])} keywords")
                if has_citations:
                    print(f"     📎 {len(citations)} citation(s): {citations[0]['document_name']}")
                results["passed"] += 1
                results["details"].append({"test": test["description"], "status": "PASS"})
            else:
                print(f"  ❌ FAIL — Found {found}/{len(test['expected_keywords'])} keywords")
                print(f"     Response: {result['response'][:200]}...")
                results["failed"] += 1
                results["details"].append({"test": test["description"], "status": "FAIL"})

        except Exception as e:
            print(f"  ⚠️  ERROR — {e}")
            results["errors"] += 1
            results["details"].append({"test": test["description"], "status": "ERROR", "error": str(e)})

    # Step 5: Test hallucination questions (should NOT confidently answer)
    print(f"\n{'═' * 60}")
    print("TEST GROUP 2: Hallucination Questions (answers NOT in document)")
    print("═" * 60)

    for i, test in enumerate(HALLUCINATION_QUESTIONS, 1):
        print(f"\n  Test {i}: {test['description']}")
        print(f"  Q: {test['question']}")
        try:
            result = ask_question(base_url, test["question"], model)
            response = result["response"]

            # Check that forbidden patterns are NOT in the response
            hallucinated = any(
                pattern.lower() in response.lower()
                for pattern in test["forbidden_patterns"]
            )

            # Check for hedging language (good sign)
            hedging = any(
                phrase in response.lower()
                for phrase in [
                    "not mentioned", "not found", "no information",
                    "don't have", "doesn't mention", "not specified",
                    "cannot find", "not included", "not available",
                    "i don't", "i cannot", "based on the",
                ]
            )

            if not hallucinated or hedging:
                print(f"  ✅ PASS — Model appropriately hedged or avoided hallucination")
                results["passed"] += 1
                results["details"].append({"test": test["description"], "status": "PASS"})
            else:
                print(f"  ❌ FAIL — Model appears to hallucinate")
                print(f"     Response: {response[:200]}...")
                results["failed"] += 1
                results["details"].append({"test": test["description"], "status": "FAIL"})

        except Exception as e:
            print(f"  ⚠️  ERROR — {e}")
            results["errors"] += 1
            results["details"].append({"test": test["description"], "status": "ERROR", "error": str(e)})

    # Step 6: Cleanup
    print(f"\n{'═' * 60}")
    print("Cleaning up...")
    try:
        requests.delete(f"{base_url}/api/documents/{doc_id}")
        print("   ✅ Test document deleted")
    except:
        pass

    # Summary
    total = results["passed"] + results["failed"] + results["errors"]
    print(f"\n{'═' * 60}")
    print(f"RESULTS: {results['passed']}/{total} passed, "
          f"{results['failed']} failed, {results['errors']} errors")
    print("═" * 60)

    return results["failed"] == 0 and results["errors"] == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Loomin-Docs RAG Faithfulness Test")
    parser.add_argument("--backend-url", default="http://localhost:8000",
                        help="Backend API URL (default: http://localhost:8000)")
    args = parser.parse_args()

    success = run_tests(args.backend_url)
    sys.exit(0 if success else 1)
