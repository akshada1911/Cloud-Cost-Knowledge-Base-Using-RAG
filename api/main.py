"""
Part F (Bonus) – REST API with FastAPI
======================================
Provides a RESTful interface to the Cloud Cost Knowledge Base.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Cloud Cost Knowledge Base API",
    description="FOCUS 1.0 Cloud Cost RAG Pipeline",
    version="1.0.0",
)

# Allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = 10


class QueryResponse(BaseModel):
    answer: str
    concepts: list
    paths: list
    confidence: float
    retrieval_method: str
    intents: list
    entities: dict


class ConceptResponse(BaseModel):
    name: str
    label: str
    description: str
    related_nodes: list
    similarity_scores: list


class StatsResponse(BaseModel):
    total_nodes: int
    total_relationships: int
    nodes_by_label: dict
    relationships_by_type: dict
    index_status: str


# ─────────────────────────────────────────────
# Lazy-loaded RAG pipeline
# ─────────────────────────────────────────────

_rag = None
_driver = None


def get_rag():
    global _rag
    if _rag is None:
        from rag.pipeline import CloudCostRAG
        _rag = CloudCostRAG()
    return _rag


def get_driver():
    global _driver
    if _driver is None:
        from graph.schema import get_driver as _get_driver
        _driver = _get_driver()
    return _driver


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Returns service health status and Neo4j connectivity."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        neo4j_status = "connected"
    except Exception as e:
        neo4j_status = f"error: {e}"

    return {
        "status": "ok",
        "neo4j": neo4j_status,
        "version": "1.0.0"
    }


@app.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """
    Ask a natural language question about cloud costs.

    Input: {"question": "Compare storage costs between AWS and Azure"}
    Output: {"answer": "...", "concepts": [...], "paths": [...], "confidence": 0.85}
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        rag = get_rag()
        result = rag.query(req.question, top_k=req.top_k)

        # Extract concepts from vector results
        concepts = [
            r.get("text", "")[:100]
            for r in result["vector_results"][:5]
        ]

        # Extract graph paths
        paths = [
            r.get("path", "")
            for r in result["graph_results"][:5]
            if r.get("path")
        ]

        # Confidence = average of top-5 vector scores
        scores = [r.get("score", 0) for r in result["vector_results"][:5]]
        confidence = sum(scores) / len(scores) if scores else 0.5

        return QueryResponse(
            answer=result["answer"],
            concepts=concepts,
            paths=list(set(paths)),
            confidence=round(confidence, 3),
            retrieval_method=result["retrieval_method"],
            intents=result["intents"],
            entities=result["entities"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concept/{name}", response_model=ConceptResponse)
def get_concept(name: str):
    """
    Get details about a specific concept/node by name.
    Searches across Service, FOCUSColumn, AllocationMethod, Charge nodes.

    Example: GET /concept/EffectiveCost
    """
    driver = get_driver()

    # Search across multiple node types
    search_labels = [
        ("FOCUSColumn", "name"),
        ("Service", "serviceName"),
        ("AllocationMethod", "name"),
        ("Charge", "chargeCategory"),
        ("Location", "regionName"),
    ]

    found_node = None
    found_label = None

    with driver.session() as session:
        for label, key_field in search_labels:
            result = session.run(
                f"MATCH (n:{label}) WHERE toLower(n.{key_field}) CONTAINS toLower($name) "
                f"RETURN n LIMIT 1",
                name=name
            )
            record = result.single()
            if record:
                found_node = dict(record["n"])
                found_label = label
                break

    if not found_node:
        raise HTTPException(status_code=404, detail=f"Concept '{name}' not found")

    # Get related nodes
    related = []
    similarity_scores = []

    with driver.session() as session:
        if found_label == "Service":
            result = session.run("""
                MATCH (s:Service {serviceName: $name})<-[:USES_SERVICE]-(r:Resource)
                RETURN r.resourceName as name, 'Resource' as label LIMIT 5
            """, name=found_node.get("serviceName"))
            related = [dict(r) for r in result]

        elif found_label == "FOCUSColumn":
            result = session.run("""
                MATCH (f:FOCUSColumn)
                WHERE f.name <> $name AND f.standard = $standard
                RETURN f.name as name, 'FOCUSColumn' as label LIMIT 5
            """, name=found_node.get("name"), standard=found_node.get("standard"))
            related = [dict(r) for r in result]

    return ConceptResponse(
        name=found_node.get("name") or found_node.get("serviceName") or name,
        label=found_label,
        description=found_node.get("description") or "",
        related_nodes=related,
        similarity_scores=similarity_scores,
    )


@app.get("/stats", response_model=StatsResponse)
def get_stats():
    """Returns total nodes, total relationships, and index status."""
    driver = get_driver()

    try:
        with driver.session() as session:
            node_result = session.run(
                "MATCH (n) RETURN labels(n)[0] as label, count(n) as count"
            )
            nodes_by_label = {r["label"]: r["count"] for r in node_result if r["label"]}

            rel_result = session.run(
                "MATCH ()-[r]->() RETURN type(r) as rel, count(r) as count"
            )
            rels_by_type = {r["rel"]: r["count"] for r in rel_result}

            # Check index status
            idx_result = session.run("SHOW INDEXES YIELD name, state, type")
            indexes = [
                f"{r['name']}({r['type']})={r['state']}"
                for r in idx_result
            ]
            index_status = f"{len(indexes)} indexes: " + "; ".join(indexes[:5])

        return StatsResponse(
            total_nodes=sum(nodes_by_label.values()),
            total_relationships=sum(rels_by_type.values()),
            nodes_by_label=nodes_by_label,
            relationships_by_type=rels_by_type,
            index_status=index_status,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# Entry point (run directly for dev)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
