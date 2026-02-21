"""
Cloud Cost Knowledge Base - Streamlit UI

"""

import os, sys
sys.path.insert(0, os.path.abspath("."))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
load_dotenv()

st.set_page_config(
    page_title="CloudCost Intelligence",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700&display=swap');

:root {
  --bg-base: #060d1a;
  --bg-surface: #0c1628;
  --bg-elevated: #111f38;
  --border: #1e3358;
  --border-bright: #2a4a7f;
  --gold: #c9a84c;
  --gold-bright: #e8c96d;
  --gold-dim: #8a6e2f;
  --blue: #4d9de0;
  --blue-dim: #1e4a7a;
  --green: #3dd68c;
  --red: #f06f6f;
  --text-primary: #e8edf5;
  --text-secondary: #8fa3c0;
  --text-dim: #4a6080;
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"], .main, .block-container {
  background-color: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-family: 'Outfit', sans-serif !important;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #080f1e 0%, #060d1a 100%) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
[data-testid="stSidebar"] .stRadio label {
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 8px !important;
  padding: 10px 14px !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.8rem !important;
  color: var(--text-secondary) !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
  display: block !important;
  margin: 2px 0 !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: var(--bg-elevated) !important;
  border-color: var(--border) !important;
  color: var(--text-primary) !important;
}

[data-testid="stMetric"] {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 18px 20px !important;
  position: relative;
  overflow: hidden;
}
[data-testid="stMetric"]::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--gold), var(--blue));
}
[data-testid="stMetricLabel"] {
  color: var(--text-dim) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.68rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.12em !important;
}
[data-testid="stMetricValue"] {
  color: var(--gold-bright) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 1.5rem !important;
  font-weight: 500 !important;
}

.stButton > button {
  background: linear-gradient(135deg, #1a3a6e, #1e4a8a) !important;
  color: var(--gold-bright) !important;
  border: 1px solid var(--border-bright) !important;
  border-radius: 8px !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.06em !important;
  padding: 8px 16px !important;
  transition: all 0.25s !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, #1e4a8a, #2a5fa0) !important;
  border-color: var(--gold-dim) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 0 24px rgba(201,168,76,0.15) !important;
  color: var(--gold-bright) !important;
}

.stTextArea textarea, .stTextInput input {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text-primary) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.88rem !important;
  padding: 14px 16px !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 3px rgba(77,157,224,0.1) !important;
}

[data-baseweb="select"] > div {
  background: var(--bg-surface) !important;
  border-color: var(--border) !important;
  border-radius: 8px !important;
  color: var(--text-primary) !important;
}
[data-baseweb="menu"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-bright) !important;
}
[data-baseweb="option"] {
  background: transparent !important;
  color: var(--text-primary) !important;
}
[data-baseweb="option"]:hover {
  background: var(--bg-elevated) !important;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  overflow: hidden !important;
}

.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-dim) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
  padding: 10px 18px !important;
  border-bottom: 2px solid transparent !important;
  transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
  color: var(--gold) !important;
  border-bottom-color: var(--gold) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 20px !important; }

.streamlit-expanderHeader {
  background: var(--bg-surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text-secondary) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.8rem !important;
}
.streamlit-expanderContent {
  background: var(--bg-base) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
}

hr { border-color: var(--border) !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 3px; }

.page-header {
  padding: 6px 0 28px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 28px;
}
.page-title {
  font-family: 'DM Serif Display', serif;
  font-size: 2.4rem;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  margin: 0;
}
.page-title span { color: var(--gold); }
.page-subtitle {
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-dim);
  margin-top: 8px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.page-subtitle em { color: var(--blue); font-style: normal; }

.section-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  color: var(--gold-dim);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin: 20px 0 10px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--border), transparent);
}

.answer-card {
  background: linear-gradient(135deg, #0c1f3d, #0a1628);
  border: 1px solid var(--border-bright);
  border-left: 3px solid var(--gold);
  border-radius: 12px;
  padding: 22px 26px;
  margin: 12px 0 20px 0;
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--text-primary);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 20px;
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  font-weight: 500;
  margin: 2px 3px;
  letter-spacing: 0.04em;
}
.badge-gold { background: rgba(201,168,76,0.12); color: var(--gold); border: 1px solid var(--gold-dim); }
.badge-blue { background: rgba(77,157,224,0.12); color: var(--blue); border: 1px solid var(--blue-dim); }

.stat-block {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 18px;
  text-align: center;
}
.stat-val {
  font-family: 'DM Mono', monospace;
  font-size: 1.6rem;
  font-weight: 500;
  color: var(--gold-bright);
}
.stat-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 4px;
}

.sidebar-logo {
  padding: 16px 0 24px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.logo-mark {
  font-family: 'DM Serif Display', serif;
  font-size: 1.5rem;
  color: var(--gold);
}
.logo-sub {
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem;
  color: var(--text-dim);
  margin-top: 2px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.retrieval-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 16px;
  margin: 10px 0;
  font-family: 'DM Mono', monospace;
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.rdot {
  width: 6px; height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.rdot-gold { background: var(--gold); box-shadow: 0 0 6px var(--gold); }
.rdot-blue { background: var(--blue); box-shadow: 0 0 6px var(--blue); }
.rdot-green { background: var(--green); box-shadow: 0 0 6px var(--green); }

.vec-row {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 4px 0;
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-family: 'DM Mono', monospace;
  font-size: 0.77rem;
  color: var(--text-secondary);
}
.vec-label { color: var(--blue); font-weight: 500; min-width: 70px; }
.vec-score { color: var(--gold-dim); margin-left: auto; min-width: 36px; text-align: right; }
</style>
""", unsafe_allow_html=True)


# ── Cached resources ──────────────────────────────────────────────

@st.cache_resource
def get_neo4j_driver():
    try:
        from graph.schema import get_driver
        d = get_driver()
        d.verify_connectivity()
        return d
    except Exception as e:
        st.cache_resource.clear()
        return None

@st.cache_resource
def get_rag_pipeline():
    try:
        from rag.pipeline import CloudCostRAG
        return CloudCostRAG()
    except Exception:
        return None

@st.cache_data(ttl=60)
def fetch_graph_stats():
    d = get_neo4j_driver()
    if not d:
        return {}
    try:
        with d.session() as s:
            nodes = {r["label"]: r["count"] for r in
                     s.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC")
                     if r["label"]}
            rels = {r["rel"]: r["count"] for r in
                    s.run("MATCH ()-[r]->() RETURN type(r) as rel, count(r) as count ORDER BY count DESC")}
        return {"nodes": nodes, "rels": rels}
    except:
        return {}

@st.cache_data(ttl=120)
def fetch_service_costs():
    d = get_neo4j_driver()
    if not d:
        return pd.DataFrame()
    try:
        with d.session() as s:
            rows = [dict(r) for r in s.run("""
                MATCH (cr:CostRecord)-[:INCURRED_BY]->(r:Resource)-[:USES_SERVICE]->(s:Service)
                WHERE cr.effectiveCost > 0
                WITH s.serviceName AS service,
                     coalesce(s.serviceCategory, 'Other') AS category,
                     cr.source AS provider,
                     SUM(cr.effectiveCost) AS total_cost,
                     COUNT(cr) AS records
                ORDER BY total_cost DESC LIMIT 20
                RETURN service, category, provider, total_cost, records
            """)]
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"Service cost query error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=120)
def fetch_charge_breakdown():
    d = get_neo4j_driver()
    if not d:
        return pd.DataFrame()
    try:
        with d.session() as s:
            rows = [dict(r) for r in s.run("""
                MATCH (cr:CostRecord)-[:HAS_CHARGE]->(c:Charge)
                WITH coalesce(c.chargeCategory, 'Unknown') AS category,
                     cr.source AS provider,
                     SUM(cr.effectiveCost) AS effective,
                     SUM(cr.billedCost) AS billed
                RETURN category, provider, effective, billed
                ORDER BY effective DESC
            """)]
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=120)
def fetch_focus_columns():
    d = get_neo4j_driver()
    if not d:
        return pd.DataFrame()
    try:
        with d.session() as s:
            rows = [dict(r) for r in s.run("""
                MATCH (f:FOCUSColumn)
                RETURN f.name AS name,
                       f.description AS description,
                       f.standard AS standard,
                       f.nullable AS nullable
                ORDER BY f.standard, f.name
            """)]
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except:
        return pd.DataFrame()

def do_vector_search(query_text, top_k=10):
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = model.encode([query_text], normalize_embeddings=True)[0].tolist()
    except Exception as e:
        return [], f"Embedding error: {e}"

    d = get_neo4j_driver()
    if not d:
        return [], "No Neo4j connection"

    results = []
    targets = [
        ("Service",    "serviceName"),
        ("Charge",     "chargeDescription"),
        ("FOCUSColumn","description"),
        ("Location",   "description"),
    ]

    with d.session() as s:
        for label, text_field in targets:
            # try native vector index first
            try:
                idx_name = f"{label.lower()}_embedding"
                rows = list(s.run(f"""
                    CALL db.index.vector.queryNodes($idx, $k, $emb)
                    YIELD node, score
                    RETURN node.{text_field} AS text, labels(node)[0] AS label, score
                    ORDER BY score DESC
                """, idx=idx_name, k=top_k, emb=embedding))
                for r in rows:
                    if r["text"]:
                        results.append({
                            "label": r["label"], "text": r["text"],
                            "score": round(r["score"], 3), "method": "index"
                        })
                if rows:
                    continue
            except Exception:
                pass

            # fallback: manual cosine similarity in Cypher
            try:
                rows = list(s.run(f"""
                    MATCH (n:{label})
                    WHERE n.embedding IS NOT NULL AND n.{text_field} IS NOT NULL
                    WITH n, n.{text_field} AS text,
                         reduce(dot=0.0, i IN range(0, size(n.embedding)-1) |
                             dot + n.embedding[i] * $emb[i]) AS dot,
                         sqrt(reduce(na=0.0, x IN n.embedding | na + x*x)) AS norm_a,
                         sqrt(reduce(nb=0.0, x IN $emb | nb + x*x)) AS norm_b
                    WITH text, labels(n)[0] AS label,
                         CASE WHEN norm_a * norm_b = 0 THEN 0
                              ELSE dot / (norm_a * norm_b) END AS score
                    ORDER BY score DESC LIMIT $k
                    RETURN text, label, score
                """, emb=embedding, k=top_k))
                for r in rows:
                    if r["text"]:
                        results.append({
                            "label": r["label"], "text": r["text"],
                            "score": round(r["score"], 3), "method": "cosine"
                        })
            except Exception:
                # last resort: return top nodes by name only
                try:
                    rows = list(s.run(f"""
                        MATCH (n:{label})
                        WHERE n.{text_field} IS NOT NULL
                        RETURN n.{text_field} AS text, labels(n)[0] AS label, 0.7 AS score
                        LIMIT $k
                    """, k=top_k // 2))
                    for r in rows:
                        if r["text"]:
                            results.append({
                                "label": r["label"], "text": r["text"],
                                "score": 0.7, "method": "name"
                            })
                except Exception:
                    pass

    seen, unique = set(), []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        if r["text"] not in seen:
            seen.add(r["text"])
            unique.append(r)
    return unique[:top_k], None

def dark_chart(fig, title="", height=380):
    fig.update_layout(
        title=dict(text=title, font=dict(color="#c9d8ec", size=12, family="DM Mono")),
        paper_bgcolor="#0c1628",
        plot_bgcolor="#0c1628",
        height=height,
        font=dict(color="#8fa3c0", family="DM Mono", size=10),
        xaxis=dict(gridcolor="#1e3358", zerolinecolor="#1e3358", tickfont=dict(color="#5a7a9a")),
        yaxis=dict(gridcolor="#1e3358", zerolinecolor="#1e3358", tickfont=dict(color="#5a7a9a")),
        legend=dict(bgcolor="#111f38", bordercolor="#1e3358", borderwidth=1, font=dict(color="#8fa3c0")),
        margin=dict(l=12, r=12, t=44, b=12),
    )
    return fig


# ── Sidebar ───────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="logo-mark">CloudCost</div>
        <div class="logo-sub">Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation",
        ["Query", "Dashboard", "Test Suite", "Schema"],
        label_visibility="collapsed"
    )

    st.markdown('<div class="section-label">Graph Status</div>', unsafe_allow_html=True)

    stats = fetch_graph_stats()
    if stats:
        total_n = sum(stats["nodes"].values())
        total_r = sum(stats["rels"].values())
        st.markdown(f"""
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
            <div class="stat-block">
                <div class="stat-val">{total_n:,}</div>
                <div class="stat-label">Nodes</div>
            </div>
            <div class="stat-block">
                <div class="stat-val">{total_r:,}</div>
                <div class="stat-label">Edges</div>
            </div>
        </div>""", unsafe_allow_html=True)
        with st.expander("Breakdown"):
            for lbl, cnt in list(stats["nodes"].items())[:8]:
                st.markdown(
                    f'<div style="font-family:DM Mono,monospace;font-size:0.72rem;'
                    f'display:flex;justify-content:space-between;padding:2px 0">'
                    f'<span style="color:#c9a84c">{lbl}</span>'
                    f'<span style="color:#8fa3c0">{cnt:,}</span></div>',
                    unsafe_allow_html=True)
    else:
        st.error("Neo4j offline")

    st.divider()
    show_ctx = st.toggle("Show context", value=False)
    show_vec = st.toggle("Show vector results", value=True)

    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:0.6rem;color:#2a4060;
    margin-top:16px;line-height:2">
    FOCUS 1.0 · Neo4j 5.x<br>
    all-MiniLM-L6-v2<br>
    Groq llama-3.1<br>
    Hybrid RAG
    </div>""", unsafe_allow_html=True)


# ── Page header ──────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
  <div class="page-title">Cloud <span>Cost</span> Intelligence</div>
  <div class="page-subtitle">
    <em>FOCUS 1.0</em> &nbsp;·&nbsp; AWS + Azure &nbsp;·&nbsp;
    <em>Knowledge Graph</em> &nbsp;·&nbsp; RAG Pipeline
  </div>
</div>""", unsafe_allow_html=True)


# ── Query page ───────────────────────────────────────────────────

if page == "Query":

    st.markdown('<div class="section-label">Quick Queries</div>', unsafe_allow_html=True)

    examples = [
        "Find all AWS compute services",
        "Compare storage costs: AWS vs Azure",
        "Top 5 most expensive Production resources in Azure",
        "Core FOCUS columns vs vendor-specific columns",
        "Which cost type to use for cloud spend analysis?",
        "Why does total spike when including commitment purchases?",
    ]
    cols = st.columns(3)
    for i, ex in enumerate(examples):
        if cols[i % 3].button(ex, key=f"pill_{i}", use_container_width=True):
            st.session_state["q"] = ex

    st.markdown('<div class="section-label">Ask Anything</div>', unsafe_allow_html=True)
    query = st.text_area(
        "query_input",
        height=88,
        value=st.session_state.get("q", ""),
        placeholder="e.g.  Compare storage costs between AWS and Azure...",
        label_visibility="collapsed"
    )
    run = st.button("Run Query", type="primary")

    if run and query.strip():
        rag = get_rag_pipeline()
        if not rag:
            st.error("RAG pipeline unavailable — check Neo4j connection.")
        else:
            with st.spinner("Running hybrid retrieval + LLM generation..."):
                result = rag.query(query)

            n_graph  = len(result.get("graph_results", []))
            intents  = ", ".join(result.get("intents", []))
            entities = ", ".join(result.get("entities", {}).keys()) or "none"

            vec_results, vec_err = do_vector_search(query, top_k=8)
            n_vec = len(vec_results)

            st.markdown(f"""
            <div class="retrieval-bar">
              <span class="rdot rdot-gold"></span>
              <span>intents: <b style="color:#c9a84c">{intents}</b></span>
              &nbsp;|&nbsp;
              <span class="rdot rdot-blue"></span>
              <span>entities: <b style="color:#4d9de0">{entities}</b></span>
              &nbsp;|&nbsp;
              <span class="rdot rdot-green"></span>
              <span>vector: <b style="color:#3dd68c">{n_vec}</b>
              &nbsp; graph: <b style="color:#3dd68c">{n_graph}</b></span>
            </div>""", unsafe_allow_html=True)

            st.markdown('<div class="section-label">Answer</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="answer-card">{result["answer"]}</div>', unsafe_allow_html=True)

            if show_ctx and result.get("context"):
                st.markdown('<div class="section-label">Retrieved Context</div>', unsafe_allow_html=True)
                for i, line in enumerate(result["context"].split("\n\n")[:10], 1):
                    if not line.strip():
                        continue
                    src  = "GRAPH" if "GRAPH" in line else "VECTOR"
                    cls  = "badge-gold" if src == "GRAPH" else "badge-blue"
                    text = line.split("]")[-1].strip() if "]" in line else line
                    st.markdown(f"""
                    <div style="background:var(--bg-surface);border:1px solid var(--border);
                    border-radius:8px;padding:10px 14px;margin:4px 0;
                    font-family:'DM Mono',monospace;font-size:0.76rem;
                    color:var(--text-secondary);display:flex;gap:8px">
                    <span>{i}</span>
                    <span class="badge {cls}" style="font-size:0.6rem;padding:2px 7px;white-space:nowrap">{src}</span>
                    <span>{text[:200]}</span>
                    </div>""", unsafe_allow_html=True)

            c1, c2 = st.columns(2)

            with c1:
                st.markdown('<div class="section-label">Graph Results</div>', unsafe_allow_html=True)
                gdf = result.get("graph_results", [])
                if gdf:
                    df = pd.DataFrame(gdf)
                    cols_to_show = [c for c in ["path", "text", "score"] if c in df.columns]
                    if "score" in df.columns:
                        df["score"] = df["score"].round(3)
                    st.dataframe(df[cols_to_show], use_container_width=True, hide_index=True)
                else:
                    st.info("No graph results for this query")

            with c2:
                if show_vec:
                    st.markdown('<div class="section-label">Vector Results</div>', unsafe_allow_html=True)
                    if vec_err:
                        st.warning(f"Vector search: {vec_err}")
                    if vec_results:
                        for r in vec_results[:8]:
                            st.markdown(f"""
                            <div class="vec-row">
                              <span class="vec-label">{r.get('label','?')}</span>
                              <span style="flex:1">{r.get('text','')[:90]}</span>
                              <span class="vec-score">{r.get('score',0):.2f}</span>
                            </div>""", unsafe_allow_html=True)
                    else:
                        st.info("No vector results")


# ── Dashboard page ───────────────────────────────────────────────

elif page == "Dashboard":

    d = get_neo4j_driver()
    if not d:
        st.error("Neo4j not connected.")
        st.stop()

    svc_df    = fetch_service_costs()
    charge_df = fetch_charge_breakdown()

    if svc_df.empty:
        st.warning("No service cost data found. Make sure you ran: python run.py ingest")
        st.stop()

    st.markdown('<div class="section-label">Overview</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    total_cost = svc_df["total_cost"].sum()
    aws_cost   = svc_df[svc_df["provider"] == "aws"]["total_cost"].sum()
    az_cost    = svc_df[svc_df["provider"] == "azure"]["total_cost"].sum()
    total_rec  = int(svc_df["records"].sum())
    c1.metric("Total Records",   f"{total_rec:,}")
    c2.metric("Total Eff. Cost", f"${total_cost:,.2f}")
    c3.metric("AWS Spend",       f"${aws_cost:,.2f}")
    c4.metric("Azure Spend",     f"${az_cost:,.2f}")

    st.markdown('<div class="section-label">Top Services by Effective Cost</div>', unsafe_allow_html=True)
    fig = px.bar(
        svc_df.head(15),
        x="total_cost", y="service",
        color="provider", orientation="h",
        color_discrete_map={"aws": "#f89820", "azure": "#0078d4"},
        labels={"total_cost": "Effective Cost ($)", "service": "", "provider": "Provider"},
    )
    dark_chart(fig, height=420)
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-label">Provider Split</div>', unsafe_allow_html=True)
        prov = svc_df.groupby("provider")["total_cost"].sum().reset_index()
        fig2 = go.Figure(go.Pie(
            labels=prov["provider"].tolist(),
            values=prov["total_cost"].tolist(),
            hole=0.60,
            marker=dict(colors=["#f89820", "#0078d4"], line=dict(color="#0c1628", width=2)),
            textfont=dict(color="#e8edf5", family="DM Mono", size=11),
        ))
        dark_chart(fig2, height=300)
        fig2.update_layout(annotations=[dict(
            text="Provider", x=0.5, y=0.5,
            font=dict(color="#8fa3c0", size=11, family="DM Mono"),
            showarrow=False)])
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.markdown('<div class="section-label">Service Category Split</div>', unsafe_allow_html=True)
        cat = svc_df.groupby("category")["total_cost"].sum().reset_index()
        colors = ["#c9a84c","#4d9de0","#3dd68c","#f06f6f","#bc8cff","#79c0ff","#e3b341","#ff9f40"]
        fig3 = go.Figure(go.Pie(
            labels=cat["category"].tolist(),
            values=cat["total_cost"].tolist(),
            hole=0.60,
            marker=dict(colors=colors[:len(cat)], line=dict(color="#0c1628", width=2)),
            textfont=dict(color="#e8edf5", family="DM Mono", size=11),
        ))
        dark_chart(fig3, height=300)
        fig3.update_layout(annotations=[dict(
            text="Category", x=0.5, y=0.5,
            font=dict(color="#8fa3c0", size=11, family="DM Mono"),
            showarrow=False)])
        st.plotly_chart(fig3, use_container_width=True)

    if not charge_df.empty:
        st.markdown('<div class="section-label">Charge Category Breakdown</div>', unsafe_allow_html=True)
        st.warning("Never sum Usage + Purchase charges together — this causes double-counting per FOCUS 1.0 spec.")
        fig4 = px.bar(
            charge_df,
            x="category", y=["effective", "billed"],
            color_discrete_sequence=["#c9a84c", "#4d9de0"],
            barmode="group", facet_col="provider",
            labels={"value": "Cost ($)", "variable": "Type", "category": "Charge Category"},
        )
        dark_chart(fig4, "Effective vs Billed Cost by Charge Category and Provider", height=360)
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown('<div class="section-label">Service Cost Table</div>', unsafe_allow_html=True)
    display_df = svc_df.copy()
    display_df["total_cost"] = display_df["total_cost"].round(4)
    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ── Test Suite page ──────────────────────────────────────────────

elif page == "Test Suite":

    st.markdown('<div class="section-label">Part E - Assignment Test Queries</div>', unsafe_allow_html=True)

    TEST_QUERIES = [
        ("#1",  "Which are the core FOCUS columns and how do they differ from vendor specific columns?", "hybrid"),
        ("#2",  "Find all AWS compute services", "graph"),
        ("#3",  "What is the Azure equivalent of AWS S3?", "vector"),
        ("#4",  "Find the top 5 most expensive resources tagged as Production in Azure", "graph"),
        ("#5",  "Compare storage costs between AWS and Azure", "graph"),
        ("#6",  "When calculating commitment utilization, which charge categories must be excluded to avoid double counting?", "graph"),
        ("#9",  "Why does my total increase when I include commitment purchases and usage together?", "vector"),
        ("#10", "Which cost type should be used to analyze cloud spend?", "vector"),
        ("#11", "Can ContractedCost differ from ContractedUnitPrice x PricingQuantity for a normal Usage charge?", "vector"),
    ]

    sel = st.selectbox(
        "Select query",
        [f"{q[0]}  {q[1][:68]}..." for q in TEST_QUERIES],
        label_visibility="collapsed"
    )
    idx = next(i for i, q in enumerate(TEST_QUERIES) if sel.startswith(q[0]))
    tq  = TEST_QUERIES[idx]

    st.markdown(f"""
    <div style="background:var(--bg-surface);border:1px solid var(--border);
                border-radius:10px;padding:16px 20px;margin:10px 0">
      <div style="font-family:'DM Mono',monospace;font-size:0.68rem;
                  color:var(--gold-dim);text-transform:uppercase;letter-spacing:0.1em">
        {tq[0]} &nbsp;·&nbsp; expected method: {tq[2]}
      </div>
      <div style="font-family:'Outfit',sans-serif;font-size:1rem;
                  color:var(--text-primary);margin-top:6px">
        {tq[1]}
      </div>
    </div>""", unsafe_allow_html=True)

    ca, cb = st.columns([2, 5])
    run_one = ca.button("Run Query", type="primary", use_container_width=True)
    run_all = cb.button("Run All 9", use_container_width=True)

    if run_one:
        rag = get_rag_pipeline()
        if rag:
            with st.spinner(f"Running {tq[0]}..."):
                result = rag.query(tq[1])
            st.markdown(f'<div class="answer-card">{result["answer"]}</div>', unsafe_allow_html=True)
            x1, x2, x3 = st.columns(3)
            x1.metric("Primary Intent", result["intents"][0] if result["intents"] else "none")
            x2.metric("Graph Hits",     len(result.get("graph_results", [])))
            x3.metric("Vector Hits",    len(result.get("vector_results", [])))
        else:
            st.error("RAG pipeline not available")

    if run_all:
        rag = get_rag_pipeline()
        if rag:
            rows = []
            bar = st.progress(0, "Running all 9 queries...")
            for i, (num, question, method) in enumerate(TEST_QUERIES):
                r = rag.query(question)
                rows.append({
                    "Query":    num,
                    "Method":   r["retrieval_method"].split("(")[0].strip(),
                    "G-Hits":   len(r.get("graph_results", [])),
                    "Question": question[:55] + "...",
                    "Answer":   r["answer"][:120] + "..."
                })
                bar.progress((i + 1) / len(TEST_QUERIES), f"Done {i+1}/{len(TEST_QUERIES)}")
            st.success("All 9 queries complete")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Schema page ──────────────────────────────────────────────────

elif page == "Schema":

    st.markdown('<div class="section-label">FOCUS 1.0 Column Reference</div>', unsafe_allow_html=True)

    focus_df = fetch_focus_columns()

    if focus_df.empty:
        st.warning("No schema nodes found. Run: python run.py embed")
    else:
        t1, t2, t3 = st.tabs(["FOCUS Standard", "AWS Extensions", "Azure Extensions"])
        with t1:
            st.info("Provider-neutral columns required for FOCUS 1.0 compliance.")
            sub = focus_df[focus_df["standard"] == "FOCUS 1.0"][["name", "description", "nullable"]]
            if not sub.empty:
                st.dataframe(sub, use_container_width=True, hide_index=True)
            else:
                st.write("No FOCUS 1.0 columns found. Check that the embed step ran correctly.")
        with t2:
            st.info("AWS x_* vendor extension fields — not part of the FOCUS standard.")
            sub = focus_df[focus_df["standard"] == "AWS Extension"][["name", "description"]]
            if not sub.empty:
                st.dataframe(sub, use_container_width=True, hide_index=True)
        with t3:
            st.info("Azure x_* vendor extension fields — not part of the FOCUS standard.")
            sub = focus_df[focus_df["standard"] == "Azure Extension"][["name", "description"]]
            if not sub.empty:
                st.dataframe(sub, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown('<div class="section-label">Ontology Class Hierarchy</div>', unsafe_allow_html=True)

    tree = [
        (0, "OntologyClass",             "Base class for all concepts"),
        (1, "CostRecord",                "Central billing fact — effectiveCost, billedCost, listCost"),
        (1, "Account",                   "Billing account hierarchy"),
        (2, "BillingAccount",            "billingAccountId (unique constraint)"),
        (2, "SubAccount",                "Sub-account or project scope"),
        (1, "TimeFrame",                 "ChargePeriodStart/End, BillingPeriodStart/End"),
        (1, "Charge",                    "chargeCategory, chargeFrequency, chargeClass"),
        (1, "Resource",                  "Cloud resource — VM, bucket, function, etc."),
        (1, "Service",                   "serviceName, serviceCategory"),
        (1, "Location",                  "regionId, regionName, availabilityZone"),
        (1, "VendorSpecificAttributes",  "x_* vendor-specific fields"),
        (2, "AWSAttributes",             "x_ServiceCode, x_UsageType, x_Operation"),
        (2, "AzureAttributes",           "x_skuMeterCategory, x_skuDescription"),
        (1, "CostAllocation",            "allocationMethod, isSharedCost, allocationBasis"),
        (1, "Tag",                       "key, value (derived from TagsKV)"),
    ]
    depth_colors = ["#c9a84c", "#4d9de0", "#3dd68c", "#bc8cff"]
    for depth, name, desc in tree:
        color = depth_colors[min(depth, 3)]
        pad   = depth * 22
        prefix = "-- " if depth > 0 else ""
        st.markdown(
            f'<div style="padding:5px 0 5px {pad}px;font-family:DM Mono,monospace;font-size:0.8rem;">'
            f'<span style="color:{color};font-weight:500">{prefix}{name}</span>'
            f'<span style="color:#2a4060"> — </span>'
            f'<span style="color:#5a7a9a">{desc}</span></div>',
            unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="section-label">Relationship Map</div>', unsafe_allow_html=True)

    rels = [
        ("CostRecord", "BELONGS_TO_BILLING_ACCOUNT", "BillingAccount", "many:1"),
        ("CostRecord", "BELONGS_TO_SUBACCOUNT",      "SubAccount",     "many:1"),
        ("CostRecord", "IN_BILLING_PERIOD",           "BillingPeriod",  "many:1"),
        ("CostRecord", "HAS_CHARGE",                  "Charge",         "1:1"),
        ("CostRecord", "INCURRED_BY",                 "Resource",       "many:1"),
        ("Resource",   "USES_SERVICE",                "Service",        "many:1"),
        ("Resource",   "DEPLOYED_IN",                 "Location",       "many:1"),
        ("CostRecord", "HAS_VENDOR_ATTRS",            "VendorAttrs",    "1:1"),
        ("CostRecord", "ALLOCATED_VIA",               "CostAllocation", "many:many"),
        ("CostRecord", "HAS_TAG",                     "Tag",            "many:many"),
    ]
    for src, rel, tgt, card in rels:
        st.markdown(
            f'<div style="font-family:DM Mono,monospace;font-size:0.77rem;padding:6px 0;'
            f'color:#5a7a9a;border-bottom:1px solid #1e3358">'
            f'<span style="color:#4d9de0">{src}</span>'
            f'<span style="color:#2a4060"> -[</span>'
            f'<span style="color:#c9a84c">:{rel}</span>'
            f'<span style="color:#2a4060">]-&gt; </span>'
            f'<span style="color:#3dd68c">{tgt}</span>'
            f'<span style="color:#2a4060;font-size:0.65rem;margin-left:8px">{card}</span>'
            f'</div>', unsafe_allow_html=True)