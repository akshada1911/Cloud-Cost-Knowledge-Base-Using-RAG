# Cloud Cost Knowledge Base 
### Stack: Python 3.11 · Neo4j · Vector Embeddings · RAG Pipeline · Streamlit

---

## Working Proof — Application Screenshots

The following screenshots are working proofs of the fully functional application running locally with 8,300 nodes and 21,748 relationships in Neo4j, hybrid RAG pipeline connected to Groq LLM, and all four pages of the Streamlit UI operational.

---

### Dashboard — Cost Analytics

KPI overview cards showing total records, effective cost, and provider-wise spend split between AWS and Azure.

![Dashboard Overview](docs/screenshots/dashboard1.png)

Provider split and service category donut charts alongside the charge category breakdown (effective vs billed cost per provider).

![Dashboard Charts](docs/screenshots/dashboard2.png)

Full service cost table with provider, category, and effective cost per service.

![Dashboard Table](docs/screenshots/dashboard3.png)

---

### Query Page — Hybrid RAG in Action

Natural language query interface with quick query buttons, retrieval status bar showing intents, entity extraction, vector hits and graph hits.

![Query Interface](docs/screenshots/query1.png)

LLM-generated answer grounded in retrieved graph and vector context — no hallucination, all figures sourced directly from Neo4j.

![Query Answer](docs/screenshots/query2.png)

Graph results and vector results displayed side by side with cosine similarity scores.

![Query Results](docs/screenshots/query3.png)

---

### Test Suite — Assignment Part E Queries

Test suite page with dropdown selector for all 9 required queries, expected retrieval method label, and Run All 9 capability.

![Test Suite](docs/screenshots/testsuite.png)

---

### Schema Page — FOCUS 1.0 Reference

FOCUS Standard columns tab showing all 8 provider-neutral columns with descriptions and nullable flags.

![Schema FOCUS Standard](docs/screenshots/schema1.png)

AWS Extensions and Azure Extensions tabs showing vendor-specific x_* fields not part of the FOCUS standard.

![Schema Extensions](docs/screenshots/schema2.png)

Ontology class hierarchy and full relationship map with cardinality annotations.

![Schema Ontology](docs/screenshots/schema3.png)

---

### Bonus — FastAPI REST API (Part F)

Auto-generated Swagger UI at `http://localhost:8000/docs` showing all 4 REST endpoints: POST /query, GET /health, GET /concept/{name}, GET /stats.

![FastAPI Swagger UI](docs/screenshots/fastapi.png)

---

## Table of Contents
1. [System Architecture](#system-architecture)
2. [Setup & Installation](#setup--installation)
3. [Ontology Design Rationale](#ontology-design-rationale)
4. [Graph Schema Design](#graph-schema-design)
5. [RAG Pipeline Architecture](#rag-pipeline-architecture)
6. [Vector Store Design](#vector-store-design)
7. [Relationship Types & Mapping Methodology](#relationship-types--mapping-methodology)
8. [Running the Application](#running-the-application)
9. [Running Tests](#running-tests)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User (Streamlit / API)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Natural Language Query
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RAG Pipeline (Part D)                         │
│   Query Understanding → Hybrid Retrieval → Context Assembly      │
│                       → LLM Generation                           │
└────────────┬──────────────────────────┬─────────────────────────┘
             │                          │
             ▼                          ▼
┌─────────────────────┐    ┌────────────────────────────┐
│  Vector Search       │    │  Graph Traversal (Neo4j)   │
│  (sentence-          │    │  CostRecord→Service→        │
│   transformers)      │    │  Category→PricingModel      │
└─────────────────────┘    └────────────────────────────┘
             │                          │
             └──────────────┬───────────┘
                            ▼
             ┌──────────────────────────┐
             │   Knowledge Graph         │
             │   (Neo4j Desktop)         │
             │   Nodes + Embeddings      │
             └──────────────────────────┘
                            ▲
             ┌──────────────┴───────────┐
             │   Data Ingestion          │
             │   AWS FOCUS CSV           │
             │   Azure FOCUS CSV         │
             └──────────────────────────┘
```

---

## Setup & Installation

### Prerequisites
- Python 3.11
- Neo4j Desktop (free) — https://neo4j.com/download/
- Git

### Step 1 — Clone / Create Project Folder
```bash
mkdir cloud-cost-kg
cd cloud-cost-kg
```

### Step 2 — Create Virtual Environment
```bash
python3 -m venv venv
venv\Scripts\activate          
```

### Step 3 — Install Dependencies
```bash
pip install -r requirementsa.txt
```

### Step 4 — Set Up Neo4j
1. Download and open **Neo4j Desktop**
2. Create a new project → Add a Local DBMS
3. Set password to `password` (or update `.env`)
4. Start the DBMS
5. In Neo4j Browser, enable vector index plugin (comes with 5.x by default)

### Step 5 — Configure Environment
```bash
cp .env.example .env
# Edit .env with your Neo4j credentials and LLM API key
```

### Step 6 — Run Data Ingestion
```bash
python graph/ingest.py
```

### Step 7 — Generate Embeddings
```bash
python embeddings/embed_nodes.py
```

### Step 8 — Launch Streamlit UI
```bash
streamlit run ui/app.py
```

---

## Ontology Design Rationale

The ontology is grounded in **FOCUS 1.0** (FinOps Open Cost & Usage Specification), treating every billing record as a first-class semantic object linked to accounts, resources, services, locations, and allocation rules.

### Core Design Decisions
- **CostRecord** is the central fact node — analogous to a row in a billing export. Every other class is a dimension it relates to.
- **Separation of Charge vs CostRecord** — charges describe *what* was billed (category, frequency), while CostRecord captures *how much*.
- **VendorSpecificAttributes** is subclassed into AWS and Azure to cleanly separate x_* vendor columns from the FOCUS standard.
- **CostAllocation** is a first-class node, not just a property, enabling querying of allocation strategies across records.
- **Embeddings on every node** ensure semantic search can traverse the graph without relying solely on exact-match Cypher queries.

---

## Graph Schema Design

### Node Labels
| Label | Key Properties |
|---|---|
| CostRecord | effectiveCost, billedCost, listCost, currency, source |
| BillingAccount | billingAccountId, billingAccountName |
| SubAccount | subAccountId, subAccountName |
| BillingPeriod | start, end |
| Charge | chargeCategory, chargeFrequency, chargeDescription, chargeClass |
| Resource | resourceId, resourceName, resourceType |
| Service | serviceName, serviceCategory |
| Location | regionId, regionName |
| VendorAttrsAWS | x_ServiceCode, x_UsageType |
| VendorAttrsAzure | x_skuMeterCategory, x_skuDescription |
| CostAllocation | allocationMethod, allocationTargetType, isSharedCost |
| Tag | key, value |

### Uniqueness Constraints
- BillingAccount.billingAccountId
- SubAccount.subAccountId
- Service.serviceName
- Location.regionId
- Tag.{key+value} (composite)

---

## RAG Pipeline Architecture

```
Query → Intent Extraction → Entity Recognition
      ↓
Dual Retrieval:
  A) Vector Search (cosine similarity on node embeddings)
  B) Graph Traversal (Cypher based on extracted entities)
      ↓
Context Deduplication + Ranking
      ↓
Prompt Assembly (context + query)
      ↓
LLM (Claude / OpenAI / Gemini) → Answer
```

---

## Vector Store Design

- **Model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **Dimensions**: 384
- **Storage**: Embedded directly as Neo4j node properties (`embedding: [float, ...]`)
- **Index**: Neo4j vector index on `CostRecord`, `Service`, `Charge` nodes
- **Text sources for embedding**: chargeDescription, serviceName + serviceCategory, resource descriptions, ontology column descriptions

---

## Relationship Types & Mapping Methodology

| Relationship | Source → Target | Cardinality | Rationale |
|---|---|---|---|
| BELONGS_TO_BILLING_ACCOUNT | CostRecord → BillingAccount | Many:1 | Each record belongs to one billing account |
| BELONGS_TO_SUBACCOUNT | CostRecord → SubAccount | Many:1 | Sub-account scoping |
| IN_BILLING_PERIOD | CostRecord → BillingPeriod | Many:1 | Time dimension |
| HAS_CHARGE | CostRecord → Charge | 1:1 | Charge metadata |
| INCURRED_BY | CostRecord → Resource | Many:1 | Resource that caused cost |
| USES_SERVICE | Resource → Service | Many:1 | Service used by resource |
| DEPLOYED_IN | Resource → Location | Many:1 | Geographic placement |
| HAS_VENDOR_ATTRS | CostRecord → VendorAttrs | 1:1 | Provider-specific fields |
| ALLOCATED_VIA | CostRecord → CostAllocation | Many:Many | Shared cost allocation |
| ALLOCATED_TO | CostAllocation → Tag | Many:Many | Allocation targets |
| HAS_TAG | CostRecord → Tag | Many:Many | Tag dimensions |
