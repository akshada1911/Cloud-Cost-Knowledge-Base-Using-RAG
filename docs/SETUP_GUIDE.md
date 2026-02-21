# 📘 Complete Step-by-Step Guide — Assignment 4
## Cloud Cost Knowledge Base (For Complete Beginners)

---

## What Are We Building?

We're building a **smart question-answering system** for cloud billing data.

Imagine asking: *"Why are my Azure costs so high this month?"* — and getting a precise, data-backed answer. That's what this project does.

Here's the simple story of how it works:
1. We take AWS and Azure billing CSV data
2. We model it as a **knowledge graph** (nodes + relationships) in Neo4j
3. We convert text descriptions into **number arrays** (embeddings) so we can do similarity search
4. We plug in an **LLM** (Claude/OpenAI) to answer natural language questions
5. We build a **Streamlit web app** as the user interface

---

## Part 0 — Computer Setup (Do This First)

### Step 0.1 — Install Python 3.11
Go to https://www.python.org/downloads/ → Download Python 3.11.x

To check it's installed, open your **Terminal** (Mac/Linux) or **Command Prompt** (Windows) and type:
```bash
python3 --version
# Should print: Python 3.11.x
```

### Step 0.2 — Install Git
Go to https://git-scm.com/downloads → Download and install

Check:
```bash
git --version
# Should print: git version 2.x.x
```

### Step 0.3 — Install Neo4j Desktop
This is the graph database we'll use.

1. Go to: https://neo4j.com/download/
2. Click "Download Neo4j Desktop"
3. Create a free account and download
4. Install it like any regular application

### Step 0.4 — Create a Neo4j Database
1. Open Neo4j Desktop
2. Click "+ New" → "Create project"  
3. Inside the project, click "Add" → "Local DBMS"
4. Set password to: `password` (or remember what you set)
5. Click "Create"
6. Click the green "Start" button
7. The database is now running!

---

## Part 1 — Project Setup

### Step 1.1 — Get the Project Files
If you have the files already (from your download), just navigate into the folder:
```bash
cd cloud-cost-kg
```

### Step 1.2 — Create a Virtual Environment
A virtual environment keeps our project's packages separate from your computer.

```bash
# Navigate into the project folder first
cd cloud-cost-kg

# Create the virtual environment
python3 -m venv venv

# Activate it:
# On Mac/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# You should see (venv) at the start of your terminal line
```

### Step 1.3 — Install All Required Packages
```bash
pip install -r requirements.txt
```
This will take 3-5 minutes as it downloads packages like pandas, streamlit, etc.

### Step 1.4 — Set Up Your API Keys
```bash
# Copy the example file
cp .env.example .env
```

Now open `.env` in any text editor (Notepad, VS Code, etc.) and fill in:
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password      ← change this if you set a different password

# For LLM - choose ONE:
ANTHROPIC_API_KEY=sk-ant-...  ← get from console.anthropic.com
# OR
OPENAI_API_KEY=sk-...         ← get from platform.openai.com

LLM_PROVIDER=anthropic        ← change to "openai" if using OpenAI
LLM_MODEL=claude-3-5-haiku-20241022
```

**How to get an Anthropic API key (free tier available):**
1. Go to: https://console.anthropic.com
2. Sign up for free
3. Go to "API Keys" → "Create Key"
4. Copy the key (starts with `sk-ant-`)

---

## Part 2 — Understanding the Project Structure

Here's what each file does:
```
cloud-cost-kg/
├── data/
│   ├── aws_focus.csv          ← AWS billing data (1000 records)
│   └── azure_focus.csv        ← Azure billing data (999 records)
│
├── ontology/
│   └── ontology.py            ← Part A: Defines what concepts exist
│
├── graph/
│   ├── schema.py              ← Part B Step 1: Creates Neo4j constraints/indexes
│   └── ingest.py              ← Part B Steps 2&3: Loads data into Neo4j
│
├── embeddings/
│   └── embed_nodes.py         ← Part C: Generates AI embeddings for search
│
├── rag/
│   └── pipeline.py            ← Part D: The question-answering brain
│
├── ui/
│   └── app.py                 ← Part E: The web interface (Streamlit)
│
├── api/
│   └── main.py                ← Part F (Bonus): REST API with FastAPI
│
└── tests/
    └── test_queries.py        ← Part E: Runs all 9 test queries
```

---

## Part 3 — Understanding What We Built (Conceptual Explanation)

### What is an Ontology? (Part A)
An ontology is like a **dictionary for a domain** — it says "these are the concepts that exist and how they relate."

For cloud costs, our ontology says:
- A **CostRecord** exists (one billing line item)
- A **Service** exists (like Amazon EC2, Azure Virtual Machines)
- A **Resource** exists (the specific VM/bucket that used the service)
- A **CostRecord** is *INCURRED_BY* a **Resource** which *USES_SERVICE* a **Service**

This is exactly what the assignment's FOCUS 1.0 spec defines.

### What is a Knowledge Graph? (Part B)
Instead of a flat table (like Excel), a knowledge graph stores data as a network of **nodes** (things) and **relationships** (how they connect).

Example:
```
(CostRecord: $0.05) -[INCURRED_BY]-> (Resource: my-ec2-instance)
                                              |
                                     [USES_SERVICE]
                                              ↓
                                    (Service: Amazon EC2)
                                              |
                                       [DEPLOYED_IN]
                                              ↓
                                  (Location: ap-southeast-2)
```

This lets us answer questions like: "Which region has the most costly EC2 instances?" by traversing the graph.

### What are Vector Embeddings? (Part C)
Embeddings convert text into numbers so a computer can find similar concepts.

Example:
- "Amazon S3 object storage" → [0.23, -0.11, 0.89, ...]
- "Azure Blob Storage" → [0.21, -0.09, 0.87, ...]

These two vectors are *very similar* — which is how we answer "What is the Azure equivalent of AWS S3?"

### What is RAG? (Part D)
RAG = **Retrieval Augmented Generation**

Instead of relying solely on the LLM's memory, we:
1. **Retrieve** relevant data from our knowledge graph
2. **Feed** that context to the LLM
3. **Generate** a grounded, data-backed answer

---

## Part 4 — Running the Project (In Order)

### Step 4.1 — Set up the Neo4j schema
```bash
python graph/schema.py
```
This creates all the indexes and constraints in Neo4j. You should see lines like:
```
✓ Neo4j connection successful
✓ Constraint: CREATE CONSTRAINT billing_account_id...
✓ Index: CREATE INDEX service_name_idx...
✅ Schema setup complete!
```

### Step 4.2 — Ingest the data
```bash
python graph/ingest.py
```
This reads the AWS and Azure CSV files and creates nodes/relationships in Neo4j. You should see:
```
📂 Loading AWS data from data/aws_focus.csv...
  → 1000 records
📂 Loading Azure data from data/azure_focus.csv...
  → 999 records
⚙️  Ingesting 1999 total records into Neo4j...
✅ Ingestion complete!
   ✓ 1999 records ingested
Graph Statistics:
   CostRecord: 1999 nodes
   Service: ~50 nodes
   ...
```

### Step 4.3 — Generate embeddings
```bash
python embeddings/embed_nodes.py
```
This downloads the `all-MiniLM-L6-v2` model (about 90MB, one time only) and generates embeddings. You should see:
```
⚙️  Loading embedding model: all-MiniLM-L6-v2...
✓ Model loaded (dim=384)
📚 Injecting FOCUS domain knowledge nodes...
🔢 Embedding graph nodes...
  ⚙️  Embedding 1999 CostRecord nodes...
✅ Embedding complete!
```

### Step 4.4 — Launch the web app
```bash
streamlit run ui/app.py
```
This opens a browser window at http://localhost:8501. You can now ask questions!

### Step 4.5 — (Bonus) Launch the API
In a **new terminal window** (keep streamlit running in the first):
```bash
uvicorn api.main:app --reload --port 8000
```
Then open: http://localhost:8000/docs — you'll see a beautiful Swagger UI!

### Step 4.6 — Run the test queries
```bash
python tests/test_queries.py
```
This runs all 9 required test queries from Part E and saves a report to `tests/test_report.json`.

---

## Part 5 — Verifying in Neo4j Browser

To see your data visually:
1. Open Neo4j Desktop
2. Click "Open" → "Neo4j Browser"
3. Try these Cypher queries:

```cypher
// See all node types
MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC

// See a cost record and its connections
MATCH (cr:CostRecord)-[:INCURRED_BY]->(r:Resource)-[:USES_SERVICE]->(s:Service)
RETURN cr, r, s LIMIT 5

// Top 10 most expensive services
MATCH (cr:CostRecord)-[:INCURRED_BY]->(r:Resource)-[:USES_SERVICE]->(s:Service)
WHERE cr.effectiveCost > 0
RETURN s.serviceName, SUM(cr.effectiveCost) as total
ORDER BY total DESC LIMIT 10

// See FOCUS column knowledge nodes
MATCH (f:FOCUSColumn) RETURN f.name, f.description
```

---

## Part 6 — Submission Checklist

Before submitting to Internshala, confirm you have:

- [ ] GitHub repository created and all code pushed
- [ ] README.md complete with architecture diagram
- [ ] Part A — ontology.py with all classes, properties, validation rules
- [ ] Part B — schema.py (constraints/indexes) + ingest.py (data + relationships)
- [ ] Part C — embed_nodes.py with embeddings on all nodes
- [ ] Part D — pipeline.py with hybrid retrieval + LLM generation
- [ ] Part E — test_queries.py with all 9 queries documented
- [ ] Streamlit app running and demonstrable
- [ ] (Bonus) FastAPI running with /query, /health, /concept, /stats endpoints

### How to push to GitHub:
```bash
# In your terminal, from the cloud-cost-kg folder:
git init
git add .
git commit -m "Complete Assignment 4: Cloud Cost Knowledge Graph"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cloud-cost-kg.git
git push -u origin main
```

---

## Troubleshooting Common Issues

**"Cannot connect to Neo4j"**
→ Make sure Neo4j Desktop is open and the database is started (green button)

**"xlrd not installed" or "File is not a zip file"**
→ We've already converted the XLS to CSV — use `data/aws_focus.csv` directly

**"No module named sentence_transformers"**
→ Run: `pip install sentence-transformers` in your activated virtual environment

**"LLM Error: No API key"**
→ Check your `.env` file has the correct API key and `LLM_PROVIDER` is set correctly

**Embeddings take too long**
→ Normal! First run downloads the model (~90MB). Subsequent runs are fast.

---

## What the Evaluators Are Looking For

| Criteria | Weight | Where it's in our code |
|---|---|---|
| Ontology design (conceptual depth + modularity) | 20% | `ontology/ontology.py` |
| Knowledge graph quality + scalability | 30% | `graph/schema.py` + `graph/ingest.py` |
| Vector embedding coverage | 15% | `embeddings/embed_nodes.py` |
| RAG context quality + provenance | 20% | `rag/pipeline.py` |
| Test queries against LLM responses | 15% | `tests/test_queries.py` |
| Bonus: API + React frontend | 20% | `api/main.py` |
