"""
Part C – Vector Embeddings & Semantic Layer
==========================================
Generates sentence embeddings for all Neo4j nodes that have descriptive text
and stores them directly as node properties.

Model: all-MiniLM-L6-v2 (384 dimensions)
Storage: Neo4j node property `embedding: [float, ...]`
Coverage targets:
  - CostRecord: description field
  - Service: serviceName + serviceCategory
  - Charge: chargeDescription
  - Location: regionName
  - BillingAccount: billingAccountName
  - VendorAttrs: description fields
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        desc = kwargs.get('desc', '')
        for i, item in enumerate(iterable):
            if i % 10 == 0:
                print(f"  {desc}: batch {i}...")
            yield item

from dotenv import load_dotenv
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph.schema import get_driver

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
BATCH_SIZE = 64  


def load_embedding_model():
    """Load the sentence-transformer embedding model."""
    try:
        from sentence_transformers import SentenceTransformer
        print(f"  Loading embedding model: {EMBEDDING_MODEL}...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"✓ Model loaded (dim={model.get_sentence_embedding_dimension()})")
        return model
    except ImportError:
        print("✗ sentence-transformers not installed. Run: pip install sentence-transformers")
        sys.exit(1)


def embed_texts(model, texts):
    """Generate embeddings for a list of texts. Returns list of float lists."""
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return [emb.tolist() for emb in embeddings]


def get_nodes_needing_embeddings(session, label, text_field="description"):
    """Fetch nodes that have descriptive text but no embedding yet."""
    cypher = f"""
    MATCH (n:{label})
    WHERE n.{text_field} IS NOT NULL AND n.{text_field} <> ''
      AND n.embedding IS NULL
    RETURN elementId(n) as node_id, n.{text_field} as text
    LIMIT 10000
    """
    result = session.run(cypher)
    return [(record["node_id"], record["text"]) for record in result]


def update_node_embeddings(session, label, node_ids, embeddings):
    """Write embeddings back to Neo4j nodes."""
    cypher = f"""
    UNWIND $updates AS update
    MATCH (n:{label})
    WHERE elementId(n) = update.node_id
    SET n.embedding = update.embedding
    """
    updates = [{"node_id": nid, "embedding": emb}
               for nid, emb in zip(node_ids, embeddings)]
    session.run(cypher, updates=updates)


def embed_node_type(driver, model, label, text_field="description"):
    """Embed all nodes of a given label."""
    with driver.session() as session:
        nodes = get_nodes_needing_embeddings(session, label, text_field)

    if not nodes:
        print(f"  ✓ {label}: all nodes already have embeddings (or no text)")
        return 0

    node_ids = [n[0] for n in nodes]
    texts = [n[1] for n in nodes]

    print(f"  Embedding {len(nodes)} {label} nodes...")

    embedded = 0
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc=f"  {label}"):
        batch_ids = node_ids[i:i + BATCH_SIZE]
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_embeddings = embed_texts(model, batch_texts)

        with driver.session() as session:
            update_node_embeddings(session, label, batch_ids, batch_embeddings)
        embedded += len(batch_ids)

    return embedded


# ─────────────────────────────────────────────
# FOCUS Spec Column Descriptions for Embedding
# ─────────────────────────────────────────────
# These enrich the graph with domain knowledge beyond raw billing data.

FOCUS_COLUMN_DESCRIPTIONS = [
    {
        "name": "EffectiveCost",
        "description": "The cost after applying all negotiated discounts, credits, and amortized commitment fees. Use EffectiveCost for analyzing actual cloud spend and cost optimization.",
        "standard": "FOCUS 1.0",
        "nullable": False
    },
    {
        "name": "BilledCost",
        "description": "The amount charged to the customer as shown on the invoice. May differ from EffectiveCost due to commitment discounts and amortization.",
        "standard": "FOCUS 1.0",
        "nullable": False
    },
    {
        "name": "ListCost",
        "description": "The cost calculated at the public list price without any discounts. Useful for understanding savings achieved through negotiated rates.",
        "standard": "FOCUS 1.0",
        "nullable": True
    },
    {
        "name": "ContractedCost",
        "description": "The cost based on the contracted unit price times pricing quantity. May differ from BilledCost when enterprise agreements apply.",
        "standard": "FOCUS 1.0",
        "nullable": True
    },
    {
        "name": "ChargeCategory",
        "description": "Classifies the nature of the charge: Usage (on-demand resources), Purchase (upfront commitments), Tax, Credit, or Adjustment.",
        "standard": "FOCUS 1.0",
        "nullable": False
    },
    {
        "name": "ChargeFrequency",
        "description": "How often the charge occurs: One-Time, Recurring (monthly), or Usage-Based (pay-per-use).",
        "standard": "FOCUS 1.0",
        "nullable": False
    },
    {
        "name": "CommitmentDiscountStatus",
        "description": "For commitment-based pricing, indicates if the commitment was Used (applied to usage) or Unused (wasted capacity).",
        "standard": "FOCUS 1.0",
        "nullable": True
    },
    {
        "name": "ServiceCategory",
        "description": "High-level grouping of cloud services: Compute, Storage, Networking, Databases, AI/ML, etc.",
        "standard": "FOCUS 1.0",
        "nullable": True
    },
    {
        "name": "x_ServiceCode",
        "description": "AWS-specific service identifier (e.g. AmazonEC2, AmazonS3, AWSLambda). Not part of FOCUS standard.",
        "standard": "AWS Extension",
        "nullable": True
    },
    {
        "name": "x_UsageType",
        "description": "AWS-specific usage dimension describing the type of resource usage (e.g. APS2-DataTransfer-Regional-Bytes). Not part of FOCUS standard.",
        "standard": "AWS Extension",
        "nullable": True
    },
    {
        "name": "x_skuMeterCategory",
        "description": "Azure-specific service meter category (e.g. Virtual Machines, Storage, Bandwidth). Not part of FOCUS standard.",
        "standard": "Azure Extension",
        "nullable": True
    },
    {
        "name": "x_skuDescription",
        "description": "Azure-specific SKU description providing detailed information about the specific service tier or configuration.",
        "standard": "Azure Extension",
        "nullable": True
    },
]

ALLOCATION_METHOD_DESCRIPTIONS = [
    {
        "name": "Proportional",
        "description": "Allocates shared costs proportionally based on each target's usage or consumption relative to the total. Most accurate for usage-driven shared costs.",
    },
    {
        "name": "EvenSplit",
        "description": "Divides shared costs equally among all allocation targets. Simple and transparent but ignores actual usage differences.",
    },
    {
        "name": "Weighted",
        "description": "Allocates shared costs based on custom-defined weights for each target. Flexible for business-driven cost allocation policies.",
    },
]


def ingest_focus_knowledge_nodes(driver, model):
    """
    Create special 'FOCUSColumn' and 'AllocationMethod' nodes in the graph
    that encode domain knowledge from the FOCUS specification.
    These nodes will be embedded and searched semantically.
    """
    print(" Creating FOCUS domain knowledge nodes...")
    with driver.session() as session:
        for col in FOCUS_COLUMN_DESCRIPTIONS:
            session.run("""
                MERGE (f:FOCUSColumn {name: $name})
                SET f.description = $desc,
                    f.standard = $standard,
                    f.nullable = $nullable
            """, name=col["name"], desc=col["description"],
                standard=col["standard"], nullable=col["nullable"])

        for method in ALLOCATION_METHOD_DESCRIPTIONS:
            session.run("""
                MERGE (a:AllocationMethod {name: $name})
                SET a.description = $desc
            """, name=method["name"], desc=method["description"])

    # Now embed them
    for label, text_field in [("FOCUSColumn", "description"), ("AllocationMethod", "description")]:
        with driver.session() as session:
            nodes = get_nodes_needing_embeddings(session, label, text_field)
        if nodes:
            ids = [n[0] for n in nodes]
            texts = [n[1] for n in nodes]
            embeddings = embed_texts(model, texts)
            with driver.session() as session:
                update_node_embeddings(session, label, ids, embeddings)
            print(f"  ✓ {len(nodes)} {label} nodes embedded")


def run_embeddings():
    print(" Starting vector embedding generation...")
    driver = get_driver()

    try:
        driver.verify_connectivity()
        print("✓ Neo4j connected")
    except Exception as e:
        print(f"✗ Cannot connect to Neo4j: {e}")
        return

    model = load_embedding_model()

    # First, inject FOCUS domain knowledge nodes
    print("\n Injecting FOCUS domain knowledge nodes...")
    ingest_focus_knowledge_nodes(driver, model)

    # Embed all node types
    print("\n Embedding graph nodes...")
    node_types = [
        ("CostRecord", "description"),
        ("Service", "description"),
        ("Charge", "description"),
        ("Location", "description"),
        ("BillingAccount", "description"),
        ("SubAccount", "description"),
        ("Resource", "description"),
        ("VendorAttrsAWS", "description"),
        ("VendorAttrsAzure", "description"),
        ("CostAllocation", "description"),
        ("Tag", "description"),
    ]

    total_embedded = 0
    for label, text_field in node_types:
        count = embed_node_type(driver, model, label, text_field)
        total_embedded += count

    driver.close()
    print(f"\n Embedding complete! {total_embedded} nodes embedded.")
    print("   Next: streamlit run ui/app.py")


if __name__ == "__main__":
    run_embeddings()
