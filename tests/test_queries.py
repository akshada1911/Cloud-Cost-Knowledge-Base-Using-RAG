"""
Part E – Testing Suite
======================
Automated tests demonstrating all required query capabilities.
Documents retrieval method, context, and response for each query.

HOW TO RUN:
  python tests/test_queries.py

Output: Detailed report for each query including:
  - Query text
  - Retrieval method (vector/graph/hybrid)
  - Retrieved context
  - LLM response
  - Graph path visualization (text format)
"""

import os
import sys
import json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph.schema import get_driver
from dotenv import load_dotenv
load_dotenv()


# ─────────────────────────────────────────────
# Test Queries (Assignment Part E)
# ─────────────────────────────────────────────

TEST_QUERIES = [
    {
        "id": 1,
        "question": "Which are the core FOCUS columns and how do they differ from vendor specific columns?",
        "expected_retrieval": "vector+graph",
        "expected_concepts": ["EffectiveCost", "BilledCost", "ChargeCategory", "x_ServiceCode", "x_skuMeterCategory"],
        "grading_notes": "Should distinguish FOCUS standard columns from x_* vendor extensions"
    },
    {
        "id": 2,
        "question": "Find all AWS compute services",
        "expected_retrieval": "graph",
        "expected_concepts": ["EC2", "Lambda", "Compute"],
        "grading_notes": "Should query Service nodes filtered by provider=aws and category=Compute"
    },
    {
        "id": 3,
        "question": "What is the Azure equivalent of AWS S3?",
        "expected_retrieval": "vector",
        "expected_concepts": ["Azure Blob Storage", "Storage"],
        "grading_notes": "Vector search should find similar service concepts across providers"
    },
    {
        "id": 4,
        "question": "Find the top 5 most expensive resources tagged as Production in Azure",
        "expected_retrieval": "graph",
        "expected_concepts": ["effectiveCost", "tagEnvironment", "Production"],
        "grading_notes": "Should use graph traversal with tag filter on Azure records"
    },
    {
        "id": 5,
        "question": "Compare storage costs between AWS and Azure",
        "expected_retrieval": "graph",
        "expected_concepts": ["S3", "Blob", "Storage", "effectiveCost"],
        "grading_notes": "Should aggregate costs by serviceCategory=Storage for both providers"
    },
    {
        "id": 6,
        "question": "When calculating commitment utilization using CommitmentDiscountQuantity, which charge categories must be excluded to avoid double counting?",
        "expected_retrieval": "graph+vector",
        "expected_concepts": ["Purchase", "double counting", "ChargeCategory"],
        "grading_notes": "Should identify that Purchase charges must be excluded (FOCUS spec rule)"
    },
    {
        "id": 9,
        "question": "Why does my total increase when I include commitment purchases and usage together?",
        "expected_retrieval": "vector",
        "expected_concepts": ["double counting", "Purchase", "Usage", "EffectiveCost"],
        "grading_notes": "Should explain the double-counting issue in FOCUS"
    },
    {
        "id": 10,
        "question": "Which cost type should be used to analyze cloud spend?",
        "expected_retrieval": "vector",
        "expected_concepts": ["EffectiveCost", "BilledCost", "analysis"],
        "grading_notes": "Should recommend EffectiveCost for spend analysis per FOCUS spec"
    },
    {
        "id": 11,
        "question": "Can ContractedCost differ from ContractedUnitPrice × PricingQuantity for a normal Usage charge? If so, when?",
        "expected_retrieval": "vector",
        "expected_concepts": ["ContractedCost", "ContractedUnitPrice", "enterprise discount", "negotiated"],
        "grading_notes": "Should explain when/why these differ (negotiated rates, tiered pricing)"
    },
]


def run_test(rag, test_case: dict) -> dict:
    """Run a single test query and return the full result document."""
    print(f"\n{'='*70}")
    print(f"Query #{test_case['id']}: {test_case['question']}")
    print("=" * 70)

    result = rag.query(test_case["question"])

    # Determine actual retrieval method used
    n_vector = len(result["vector_results"])
    n_graph = len(result["graph_results"])
    if n_vector > 0 and n_graph > 0:
        actual_retrieval = "hybrid"
    elif n_vector > 0:
        actual_retrieval = "vector"
    else:
        actual_retrieval = "graph"

    print(f"Intents: {result['intents']}")
    print(f"Entities: {list(result['entities'].keys())}")
    print(f"Retrieval: {actual_retrieval} (vector={n_vector}, graph={n_graph})")
    print(f"\n--- Retrieved Context (top 3) ---")
    context_lines = result["context"].split("\n\n")
    for line in context_lines[:3]:
        print(line[:200])

    print(f"\n--- LLM Response ---")
    print(result["answer"])

    # Graph path visualization
    graph_paths = list(set(
        r.get("path", "") for r in result["graph_results"] if r.get("path")
    ))
    if graph_paths:
        print(f"\n--- Graph Paths Used ---")
        for path in graph_paths[:3]:
            print(f"  {path}")

    return {
        "id": test_case["id"],
        "question": test_case["question"],
        "retrieval_method": actual_retrieval,
        "expected_retrieval": test_case["expected_retrieval"],
        "intents": result["intents"],
        "entities": list(result["entities"].keys()),
        "context_snippets": context_lines[:3],
        "graph_paths": graph_paths,
        "answer": result["answer"],
        "vector_hits": n_vector,
        "graph_hits": n_graph,
        "grading_notes": test_case["grading_notes"],
    }


def save_test_report(results: list):
    """Save test results to a JSON report file."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_queries": len(results),
        "results": results
    }
    report_path = "tests/test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Report saved to {report_path}")
    return report_path


def print_summary(results: list):
    """Print a summary table of all test results."""
    print(f"\n{'='*70}")
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"{'#':<4} {'Retrieval':<12} {'Vector':<8} {'Graph':<8} {'Question':<40}")
    print("-" * 70)
    for r in results:
        q = r["question"][:38] + ".." if len(r["question"]) > 40 else r["question"]
        print(f"{r['id']:<4} {r['retrieval_method']:<12} {r['vector_hits']:<8} "
              f"{r['graph_hits']:<8} {q}")
    print("=" * 70)


def run_all_tests():
    print(" Cloud Cost Knowledge Base — Part E Test Suite")
    print(f"   {len(TEST_QUERIES)} queries to test")
    print("   Each query shows: retrieval method, context, LLM response, paths\n")

    try:
        from rag.pipeline import CloudCostRAG
        rag = CloudCostRAG()
        print("✓ RAG pipeline loaded")
    except Exception as e:
        print(f"✗ Cannot load RAG pipeline: {e}")
        print("  Make sure Neo4j is running and data is ingested.")
        return

    results = []
    for test_case in TEST_QUERIES:
        try:
            result = run_test(rag, test_case)
            results.append(result)
        except Exception as e:
            print(f"  ✗ Error on query #{test_case['id']}: {e}")
            results.append({
                "id": test_case["id"],
                "question": test_case["question"],
                "error": str(e),
                "retrieval_method": "error",
                "vector_hits": 0,
                "graph_hits": 0,
            })

    print_summary(results)
    save_test_report(results)
    rag.close()
    print("\n All tests complete!")


if __name__ == "__main__":
    run_all_tests()
