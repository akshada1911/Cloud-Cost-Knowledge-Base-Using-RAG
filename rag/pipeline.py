"""
Part D - RAG Pipeline with Graph-Augmented Retrieval
"""

import os
import re
import sys
import json
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph.schema import get_driver

load_dotenv()

LLM_PROVIDER  = os.getenv("LLM_PROVIDER",  "groq")
LLM_MODEL     = os.getenv("LLM_MODEL",     "llama3-8b-8192")
GROQ_API_KEY  = os.getenv("GROQ_API_KEY",  "")
OLLAMA_URL    = os.getenv("OLLAMA_URL",    "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


# ── Intent & Entity Extraction ─────────────────────────────────────

INTENT_PATTERNS = {
    "cost_analysis":       [r"cost", r"spend", r"expensive", r"price", r"billing", r"billed", r"effective", r"total"],
    "service_comparison":  [r"compare", r"vs", r"versus", r"difference", r"equivalent", r"similar"],
    "commitment_analysis": [r"commitment", r"reservation", r"savings plan", r"utilization", r"unused", r"reserved"],
    "optimization":        [r"optimiz", r"reduc", r"sav", r"rightsiz", r"recommend"],
    "schema_query":        [r"focus column", r"standard", r"vendor", r"x_", r"spec", r"definition", r"what is", r"explain"],
    "tag_query":           [r"tag", r"application", r"environment", r"production"],
    "allocation_query":    [r"alloc", r"shared cost", r"proportion", r"split"],
}

ENTITY_PATTERNS = {
    "aws":            r"\bAWS\b|\bAmazon\b|\bEC2\b|\bS3\b|\bLambda\b|\bRDS\b",
    "azure":          r"\bAzure\b|\bMicrosoft\b|\bBlob\b|\bVirtual Machine\b",
    "compute":        r"\bEC2\b|\bVirtual Machine\b|\bcompute\b|\binstance\b",
    "storage":        r"\bS3\b|\bBlob\b|\bstorage\b|\bEBS\b",
    "production":     r"\bproduction\b|\bprod\b",
    "charge_purchase":r"\bpurchase\b|\bcommitment\b|\breservation\b",
}


def extract_intent(query: str) -> list:
    q = query.lower()
    intents = [k for k, patterns in INTENT_PATTERNS.items()
               if any(re.search(p, q) for p in patterns)]
    return intents or ["general"]


def extract_entities(query: str) -> dict:
    return {k: True for k, p in ENTITY_PATTERNS.items()
            if re.search(p, query, re.IGNORECASE)}


# ── Vector Search ──────────────────────────────────────────────────

def get_embedding(model, text: str) -> list:
    return model.encode([text], normalize_embeddings=True)[0].tolist()


def vector_search(driver, model, query_text: str, top_k: int = 10) -> list:
    query_embedding = get_embedding(model, query_text)
    results = []
    targets = [("Service","serviceName"), ("Charge","chargeDescription"),
               ("FOCUSColumn","description"), ("AllocationMethod","description")]

    with driver.session() as session:
        for label, text_field in targets:
            try:
                cypher = f"""
                CALL db.index.vector.queryNodes('{label.lower()}_embedding', $k, $embedding)
                YIELD node, score
                RETURN node.{text_field} as text, labels(node)[0] as label,
                       score, node.description as description
                ORDER BY score DESC
                """
                for r in session.run(cypher, k=top_k, embedding=query_embedding):
                    results.append({"label": r["label"],
                                    "text": r["text"] or r["description"],
                                    "score": r["score"], "source": "vector"})
            except Exception:
                pass

    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    seen, unique = set(), []
    for r in results:
        key = (r.get("text") or "")[:100]
        if key not in seen:
            seen.add(key); unique.append(r)
    return unique[:top_k]


# ── Graph Traversal ────────────────────────────────────────────────

def graph_search(driver, query: str, entities: dict, intents: list) -> list:
    results = []
    with driver.session() as session:

        if "cost_analysis" in intents or "service_comparison" in intents:
            provider_filter = ""
            if entities.get("aws") and not entities.get("azure"):
                provider_filter = "AND cr.source = 'aws'"
            elif entities.get("azure") and not entities.get("aws"):
                provider_filter = "AND cr.source = 'azure'"
            cypher = f"""
            MATCH (cr:CostRecord)-[:INCURRED_BY]->(r:Resource)-[:USES_SERVICE]->(s:Service)
            WHERE cr.effectiveCost > 0 {provider_filter}
            WITH s.serviceName AS service, s.serviceCategory AS category,
                 cr.source AS provider, SUM(cr.effectiveCost) AS total_cost, COUNT(cr) AS records
            ORDER BY total_cost DESC LIMIT 10
            RETURN service, category, provider, total_cost, records
            """
            for r in session.run(cypher):
                results.append({"source": "graph", "path": "CostRecord->Resource->Service",
                    "text": (f"Service '{r['service']}' ({r['category']}) on {r['provider'].upper()}: "
                             f"total cost ${r['total_cost']:.4f} across {r['records']} records"),
                    "score": 0.9})

        if entities.get("production") or "tag_query" in intents:
            cypher = """
            MATCH (cr:CostRecord)-[:INCURRED_BY]->(r:Resource)-[:USES_SERVICE]->(s:Service)
            WHERE cr.tagEnvironment =~ '(?i).*prod.*'
            WITH s.serviceName AS service, cr.source AS provider,
                 SUM(cr.effectiveCost) AS total_cost, COUNT(cr) AS count
            ORDER BY total_cost DESC LIMIT 5
            RETURN service, provider, total_cost, count
            """
            for r in session.run(cypher):
                results.append({"source": "graph", "path": "CostRecord[env=prod]->Resource->Service",
                    "text": (f"Production tag: '{r['service']}' on {r['provider'].upper()} "
                             f"costs ${r['total_cost']:.4f} ({r['count']} records)"),
                    "score": 0.85})

        if entities.get("storage") or "service_comparison" in intents:
            cypher = """
            MATCH (cr:CostRecord)-[:INCURRED_BY]->(r:Resource)-[:USES_SERVICE]->(s:Service)
            WHERE s.serviceCategory =~ '(?i).*storage.*'
            WITH cr.source AS provider, SUM(cr.effectiveCost) AS total_cost,
                 COUNT(cr) AS records, COLLECT(DISTINCT s.serviceName)[..3] AS services
            RETURN provider, total_cost, records, services ORDER BY provider
            """
            for r in session.run(cypher):
                results.append({"source": "graph", "path": "CostRecord->Resource->Service[Storage]",
                    "text": (f"Storage on {r['provider'].upper()}: ${r['total_cost']:.4f} total, "
                             f"{r['records']} records. Services: {', '.join(r['services'])}"),
                    "score": 0.88})

        if "commitment_analysis" in intents:
            cypher = """
            MATCH (cr:CostRecord)-[:HAS_CHARGE]->(c:Charge)
            WHERE c.chargeCategory = 'Purchase'
            WITH cr.source AS provider, SUM(cr.billedCost) AS billed,
                 SUM(cr.effectiveCost) AS effective, COUNT(cr) AS count
            RETURN provider, billed, effective, count
            """
            for r in session.run(cypher):
                results.append({"source": "graph", "path": "CostRecord[Purchase]->Charge",
                    "text": (f"Commitment purchases on {r['provider'].upper()}: "
                             f"Billed=${r['billed']:.2f}, Effective=${r['effective']:.2f}. "
                             f"WARNING: Including Purchase charges with Usage causes double-counting."),
                    "score": 0.95})

        if "schema_query" in intents:
            cypher = """
            MATCH (f:FOCUSColumn)
            RETURN f.name AS name, f.description AS description, f.standard AS standard
            ORDER BY f.standard, f.name LIMIT 15
            """
            for r in session.run(cypher):
                results.append({"source": "graph", "path": "FOCUSColumn",
                    "text": f"[{r['standard']}] {r['name']}: {r['description']}",
                    "score": 0.92})

        if "cost_analysis" in intents or "commitment_analysis" in intents:
            cypher = """
            MATCH (cr:CostRecord)-[:HAS_CHARGE]->(c:Charge)
            WITH c.chargeCategory AS category, cr.source AS provider,
                 SUM(cr.effectiveCost) AS total, SUM(cr.billedCost) AS billed
            RETURN category, provider, total, billed ORDER BY total DESC
            """
            for r in session.run(cypher):
                results.append({"source": "graph", "path": "CostRecord->Charge[category]",
                    "text": (f"Charge category '{r['category']}' on {r['provider'].upper()}: "
                             f"EffectiveCost=${r['total']:.4f}, BilledCost=${r['billed']:.4f}"),
                    "score": 0.87})

    return results


# ── Context Assembly ───────────────────────────────────────────────

def assemble_context(vector_results: list, graph_results: list) -> str:
    all_results = sorted(vector_results + graph_results,
                         key=lambda x: x.get("score", 0), reverse=True)
    seen, unique = set(), []
    for r in all_results:
        key = (r.get("text") or "")[:100]
        if key not in seen and r.get("text"):
            seen.add(key); unique.append(r)

    parts = []
    for i, r in enumerate(unique[:20], 1):
        src   = r.get("source", "unknown")
        path  = r.get("path", "")
        score = r.get("score", 0)
        text  = r.get("text", "")
        label = r.get("label", "")
        prov  = f"[{src.upper()}/{label} | {path} | relevance:{score:.2f}]"
        parts.append(f"{i}. {prov}\n   {text}")
    return "\n\n".join(parts)


# ── LLM Generation ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a cloud cost management expert with deep knowledge of:
- FOCUS 1.0 specification (FinOps Open Cost & Usage Specification)
- AWS and Azure billing data and services
- FinOps best practices for cost optimization

When answering:
1. Ground your answer in the provided context
2. Cite specific cost figures when available
3. Explain FOCUS concepts clearly
4. Flag double-counting risks where relevant
"""


def call_llm(question: str, context: str) -> str:
    prompt = (
        f"Based on the following cloud cost knowledge graph context:\n\n"
        f"{context}\n\n---\n\nQuestion: {question}\n\n"
        f"Provide a comprehensive, data-backed answer."
    )

    # ── GROQ (free, cloud, fast — recommended) ──────────────────────
    if LLM_PROVIDER == "groq":
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=1024,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return (
                f"Groq error: {e}\n\n"
                f"Check your GROQ_API_KEY in .env\n"
                f"Get a free key at: https://console.groq.com\n\n"
                f"--- Retrieved context ---\n{context}"
            )

    # ── OLLAMA (local) ──────────────────────────────────────────────
    elif LLM_PROVIDER == "ollama":
        try:
            import urllib.request, json as _json
            full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n\nAssistant:"
            payload = _json.dumps({
                "model": LLM_MODEL,
                "prompt": full_prompt,
                "stream": False
            }).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read())
                return data["response"]
        except Exception as e:
            return f"Ollama error: {e}\n\n--- Retrieved context ---\n{context}"

    # ── ANTHROPIC (optional) ────────────────────────────────────────
    elif LLM_PROVIDER == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            msg = client.messages.create(
                model=LLM_MODEL, max_tokens=1500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            return f"Anthropic error: {e}\n\n{context}"

    # ── OPENAI (optional) ───────────────────────────────────────────
    elif LLM_PROVIDER == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model=LLM_MODEL or "gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=1500
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"OpenAI error: {e}\n\n{context}"

    return f"[No LLM configured]\n\n{context}"


# ── Main RAG Pipeline ──────────────────────────────────────────────

class CloudCostRAG:
    def __init__(self):
        self.driver = get_driver()
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(EMBEDDING_MODEL)
        return self._model

    def query(self, question: str, top_k: int = 10) -> dict:
        intents  = extract_intent(question)
        entities = extract_entities(question)

        vector_results = []
        try:
            vector_results = vector_search(self.driver, self.model, question, top_k)
        except Exception as e:
            print(f"  Vector search warning: {e}")

        graph_results = graph_search(self.driver, question, entities, intents)
        context       = assemble_context(vector_results, graph_results)

        if not context:
            context = "No relevant data found in the knowledge graph for this query."

        answer = call_llm(question, context)

        return {
            "answer":           answer,
            "intents":          intents,
            "entities":         entities,
            "vector_results":   vector_results,
            "graph_results":    graph_results,
            "context":          context,
            "retrieval_method": f"hybrid (vector={len(vector_results)}, graph={len(graph_results)})"
        }

    def close(self):
        self.driver.close()


# ── CLI test ───────────────────────────────────────────────────────

TEST_QUERIES = [
    "Which are the core FOCUS columns and how do they differ from vendor specific columns?",
    "Find all AWS compute services",
    "Compare storage costs between AWS and Azure",
    "Which charge categories must be excluded to avoid double counting?",
    "Which cost type should be used to analyze cloud spend?",
]

if __name__ == "__main__":
    rag = CloudCostRAG()
    for q in TEST_QUERIES:
        print(f"\n{'='*60}\nQ: {q}\n{'='*60}")
        r = rag.query(q)
        print(r["answer"])
    rag.close()
