"""
cancer_subgraph_explainer.py  v4
Reads kg_output/cancer_kg_nodes.csv + cancer_kg_edges.csv
Writes:
  kg_output/cancer_subgraph_explained.html   <- open this
  kg_output/subgraph_data.js                 <- sidecar data (no embedding issues)
"""
import os, json, warnings
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
warnings.filterwarnings("ignore")

BASE    = os.path.dirname(os.path.abspath(__file__))
NODES_F = os.path.join(BASE, "kg_output", "cancer_kg_nodes.csv")
EDGES_F = os.path.join(BASE, "kg_output", "cancer_kg_edges.csv")
OUT_HTML= os.path.join(BASE, "kg_output", "cancer_subgraph_explained.html")
OUT_JS  = os.path.join(BASE, "kg_output", "subgraph_data.js")

print("Loading graph...")
nodes_df = pd.read_csv(NODES_F).fillna("")
edges_df = pd.read_csv(EDGES_F).fillna("")
if "src" in edges_df.columns:
    edges_df.rename(columns={"src":"source","tgt":"target"}, inplace=True)
print(f"  Nodes: {len(nodes_df):,}   Edges: {len(edges_df):,}")

node_by_id   = {r["id"]: r.to_dict() for _, r in nodes_df.iterrows()}
edges_by_src = defaultdict(list)
edges_by_tgt = defaultdict(list)
for _, e in edges_df.iterrows():
    ed = e.to_dict()
    edges_by_src[ed["source"]].append(ed)
    edges_by_tgt[ed["target"]].append(ed)

COLORS = {"gene":"#4C9BE8","cancer":"#E8724C","mutation":"#F0C040",
          "hnc_class":"#8E6BBF","tissue":"#52B788"}
REL_COLORS = {"driver":"#FF6B6B","oncogene":"#FFD93D",
              "tumor_suppressor":"#6BCB77","mutated_in":"#4ECDC4",
              "has_mutation":"#C77DFF","subclassof":"#ADB5BD",
              "mapped_to_ontology":"#F8961E"}

def get_neighbors(node_id):
    visited = {node_id}
    edges_used = []
    for e in edges_by_src.get(node_id, []):
        visited.add(e["target"]); edges_used.append(e)
    for e in edges_by_tgt.get(node_id, []):
        visited.add(e["source"]); edges_used.append(e)
    return list(visited), edges_used

def make_subgraph(seed_ids, max_edges=120, label="", description="", steps=None):
    all_nodes = set(seed_ids)
    all_edges = []
    for sid in seed_ids:
        nbrs, egs = get_neighbors(sid)
        all_nodes.update(nbrs)
        all_edges.extend(egs)
    seen_e = set()
    uniq_edges = []
    for e in all_edges:
        key = (e["source"], e["target"], e.get("relation",""))
        if key not in seen_e:
            seen_e.add(key); uniq_edges.append(e)
    uniq_edges = uniq_edges[:max_edges]
    ref_nodes = set(seed_ids)
    for e in uniq_edges:
        ref_nodes.add(e["source"]); ref_nodes.add(e["target"])
    all_nodes &= ref_nodes

    vis_nodes = []
    for nid in all_nodes:
        if nid not in node_by_id: continue
        r = node_by_id[nid]
        ntype = str(r.get("node_type","gene"))
        is_seed = nid in seed_ids
        vis_nodes.append({
            "id": nid,
            "label": str(r.get("label", nid))[:18],
            "full_label": str(r.get("label", nid)),
            "node_type": ntype,
            "color": COLORS.get(ntype, "#888"),
            "size": 30 if is_seed else 15,
            "borderWidth": 3 if is_seed else 1,
            "seed": is_seed,
            "definition": str(r.get("definition",""))[:180],
            "source_db": str(r.get("source_db","")),
        })

    vis_edges = []
    for e in uniq_edges:
        if e["source"] not in all_nodes or e["target"] not in all_nodes: continue
        rel = str(e.get("relation","")).lower()
        try:
            w = float(e.get("weight", 1.5))
            width = max(1.0, min(6.0, w * 5))
        except:
            width = 1.5
        try:
            cite = int(float(e.get("citation_count", 0)))
        except:
            cite = 0
        vis_edges.append({
            "from": e["source"], "to": e["target"],
            "relation": str(e.get("relation","")),
            "color": REL_COLORS.get(rel, "#555"),
            "width": width,
            "citation_count": cite,
            "source_db": str(e.get("source_db","")),
        })

    return {
        "label": label, "description": description,
        "steps": steps or [],
        "nodes": vis_nodes, "edges": vis_edges,
        "seed_ids": list(seed_ids),
    }

# ── Build subgraphs ───────────────────────────────────────────
subgraphs = []

CURATED = [
    {
        "seed": "GENE:TP53",
        "label": "TP53 — Guardian of the Genome",
        "description": "TP53 is mutated in over 50% of all human cancers. This subgraph shows every cancer it is linked to, all three roles (driver/oncogene/TSG), COSMIC mutations, and HeNeCOn ontology links.",
        "steps": [
            ["What is TP53?",
             "TP53 (Tumour Protein P53) encodes the cell's primary damage sensor. When DNA is damaged, p53 halts cell division and triggers repair or death of the damaged cell. It earns the nickname 'guardian of the genome' because without it, cells with broken DNA can divide freely and become cancerous."],
            ["Why is it the hub of this graph?",
             "TP53 has the highest degree (most connections) in the knowledge graph because CancerMine found it mentioned in thousands of papers across dozens of cancer types. Each coloured line is a different cancer where TP53 plays a role."],
            ["Reading edge colours",
             "Red lines = driver (TP53 mutations push the cell toward cancer). Green lines = tumour suppressor (normal TP53 prevents cancer; when broken, it fails). Yellow = oncogene. The line thickness shows how many papers support that specific connection."],
            ["Orange dashed lines — ontology cross-links",
             "Orange dashed lines connect to purple HeNeCOn nodes. These appear when a cancer name in CancerMine matches a formal clinical concept in the HeNeCOn OWL ontology — bridging NLP evidence with structured clinical definitions."],
            ["How a GNN uses this subgraph",
             "In a Graph Neural Network, each node aggregates messages from its neighbours. TP53's neighbourhood (which cancers, which roles, which mutation variants) becomes a rich feature vector. The citation-weighted edges become attention weights in a Graph Attention Network (GAT)."],
        ]
    },
    {
        "seed": "GENE:KRAS",
        "label": "KRAS — The RAS Oncogene",
        "description": "KRAS is mutated in ~25% of all cancers. This subgraph shows its cancer associations and COSMIC tissue mutations. KRAS was considered 'undruggable' until 2021.",
        "steps": [
            ["What is KRAS?",
             "KRAS (Kirsten RAS) encodes a molecular switch that controls cell growth. Normally it switches on when growth factors arrive and off when the signal passes. Oncogenic KRAS mutations (G12D, G12V, G12C) lock the switch ON permanently, causing uncontrolled proliferation."],
            ["Why mostly yellow (oncogene) edges?",
             "KRAS acts as a gain-of-function oncogene — the mutant version is too active. Unlike TP53 (which fails when broken), KRAS causes cancer when it is over-active. This is why its edges are predominantly yellow (oncogene) rather than green (tumour suppressor)."],
            ["Teal edges — COSMIC tissue connections",
             "Teal lines connect KRAS to tissue nodes (green boxes). These come from COSMIC's MutantCensus file: they mean somatic KRAS mutations were detected in real tumour samples from that tissue. Lung, pancreatic, and colorectal tissues dominate."],
            ["Clinical significance",
             "KRAS G12C became the first successfully drugged KRAS mutation with sotorasib (FDA-approved 2021). The dense connections in this subgraph reflect decades of research trying to inhibit the RAS pathway — one of the most pursued targets in oncology."],
        ]
    },
]

for c in CURATED:
    sid = c["seed"]
    if sid in node_by_id:
        subgraphs.append(make_subgraph(
            {sid}, max_edges=100,
            label=c["label"], description=c["description"], steps=c["steps"]
        ))

# Head & Neck Cancer hub
hnc_id = next((nid for nid in node_by_id
               if node_by_id[nid].get("node_type") == "cancer"
               and "head and neck" in str(node_by_id[nid].get("label","")).lower()), None)
if hnc_id:
    subgraphs.append(make_subgraph({hnc_id}, max_edges=90,
        label="Head & Neck Cancer — Gene Network",
        description="The only cancer type with a dedicated OWL ontology (HeNeCOn). Shows all genes linked to HNC, their roles, and unique ontology cross-links.",
        steps=[
            ["Why HNC is special",
             "Head and neck cancer is the only cancer in this KG with a dedicated clinical ontology (HeNeCOn). This means HNC nodes can be cross-linked to formal definitions of anatomy, staging, and treatment — connections no other cancer type has."],
            ["Key HNC driver genes",
             "Genes with thick red (driver) lines are the most cited HNC drivers in CancerMine. Common HNC drivers include TP53, CDKN2A, PIK3CA, EGFR, and NOTCH1. Click any gene node to see its citation count and connection details."],
            ["The NOTCH1 paradox",
             "NOTCH1 is a famous example of context-dependent cancer roles. It appears as an oncogene in T-cell leukaemia (yellow edge) but as a tumour suppressor in head and neck cancer (green edge). The KG captures this nuance automatically from the literature."],
            ["Orange links — ontology bridges",
             "Orange dashed lines connect CancerMine/COSMIC gene and cancer nodes to HeNeCOn OWL concepts. This lets you trace: Gene -> cancer type -> clinical staging class -> formal anatomical definition. It bridges experimental evidence with clinical knowledge."],
        ]
    ))

# Breast cancer hub
breast_id = next((nid for nid in node_by_id
                  if node_by_id[nid].get("node_type") == "cancer"
                  and str(node_by_id[nid].get("label","")).lower().strip() == "breast cancer"), None)
brca1_id = "GENE:BRCA1"; brca2_id = "GENE:BRCA2"
seeds_breast = {s for s in [breast_id, brca1_id, brca2_id] if s and s in node_by_id}
if seeds_breast:
    subgraphs.append(make_subgraph(seeds_breast, max_edges=100,
        label="Breast Cancer — BRCA1/2 Landscape",
        description="Multi-seed subgraph centred on breast cancer and its two most famous tumour suppressor genes. Shows germline risk genes alongside somatic drivers.",
        steps=[
            ["Multi-seed subgraphs",
             "This subgraph has 3 seed nodes: breast cancer, BRCA1, and BRCA2 (the large bordered nodes). Seeds act as anchor points — the graph shows everything connected to any of them. This reveals how genes relate to each other through shared cancer connections."],
            ["BRCA1 and BRCA2 — DNA repair genes",
             "BRCA1 (chromosome 17) and BRCA2 (chromosome 13) encode proteins that repair DNA double-strand breaks. Green edges (tumour suppressor) connect them to breast cancer: when these genes are mutated (broken), DNA repair fails, leading to genomic instability. Women with germline BRCA1/2 mutations face 70-80% lifetime breast cancer risk."],
            ["Other breast cancer drivers",
             "Beyond BRCA1/2, the neighbourhood includes: PIK3CA (oncogene, PI3K pathway — most frequent somatic mutation), TP53 (driver), PTEN (TSG — loss activates PI3K), HER2/ERBB2 (oncogene — amplified in 15-20% of tumours), CDH1 (TSG — lobular subtype), ESR1 (driver — hormone-positive tumours)."],
            ["Using this subgraph for ML",
             "A molecular subtype classifier using this subgraph: node features = citation weights and mutation frequencies; edge features = role type + weight; task = predict Luminal A / B / HER2+ / Triple-negative subtype from a patient's mutation profile. The BRCA1/2 edges provide the strongest signal for triple-negative classification."],
        ]
    ))

print(f"Built {len(subgraphs)} subgraphs:")
for sg in subgraphs:
    print(f"  '{sg['label']}': {len(sg['nodes'])} nodes, {len(sg['edges'])} edges")

# ── Write sidecar JS file (avoids all embedding issues) ───────
js_content = "/* Auto-generated by cancer_subgraph_explainer.py */\n"
js_content += "var SUBGRAPHS = " + json.dumps(subgraphs, ensure_ascii=False) + ";\n"
js_content += "var REL_DESCRIPTIONS = " + json.dumps({
    "driver":            "Driver: gene is frequently mutated and actively promotes cancer growth",
    "oncogene":          "Oncogene: activating mutation makes the gene over-active, accelerating cell division",
    "tumor_suppressor":  "Tumor suppressor: normal gene prevents cancer; when mutated (broken), this brake is lost",
    "mutated_in":        "Mutated in: COSMIC detected somatic mutations of this gene in this tissue",
    "has_mutation":      "Has mutation: this specific COSV variant ID found in this gene",
    "subclassof":        "SubClassOf: child concept is a specialisation of parent (HeNeCOn ontology hierarchy)",
    "mapped_to_ontology":"Ontology cross-link: gene/cancer label matches a HeNeCOn clinical concept",
}, ensure_ascii=False) + ";\n"

with open(OUT_JS, "w", encoding="utf-8") as f:
    f.write(js_content)
print(f"Written sidecar: subgraph_data.js ({len(js_content)//1024} KB)")

# ── Write HTML ─────────────────────────────────────────────────
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cancer KG -- Subgraph Explainer</title>
<script src="subgraph_data.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e0e0e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#topbar{background:#1a1a2e;border-bottom:1px solid #2d2d4e;padding:8px 16px;display:flex;align-items:center;gap:8px;flex-shrink:0;flex-wrap:wrap;min-height:48px}
.logo{font-size:13px;font-weight:700;color:#a0c4ff;margin-right:6px;white-space:nowrap}
.sg-btn{padding:5px 12px;border-radius:6px;border:1px solid #2d2d4e;font-size:11px;cursor:pointer;background:transparent;color:#aaa;white-space:nowrap;transition:all .15s}
.sg-btn.active{color:#fff;border-color:transparent}
.sg-btn:hover{background:#2a2a4e;color:#e0e0e0}
#main{flex:1;display:flex;overflow:hidden}
#explain-panel{width:340px;min-width:340px;background:#1a1a2e;border-right:1px solid #2d2d4e;display:flex;flex-direction:column;overflow:hidden}
#sg-header{padding:12px 14px;border-bottom:1px solid #2d2d4e;flex-shrink:0}
#sg-header h2{font-size:14px;font-weight:600;color:#a0c4ff;margin-bottom:3px}
#sg-header p{font-size:11px;color:#888;line-height:1.5}
#step-nav{display:flex;gap:6px;padding:8px 12px;border-bottom:1px solid #2d2d4e;align-items:center;flex-shrink:0}
.step-dot{width:7px;height:7px;border-radius:50%;background:#2d2d4e;cursor:pointer}
.step-dot.on{background:#a0c4ff}
.sarrow{background:transparent;border:1px solid #2d2d4e;color:#aaa;padding:3px 9px;border-radius:5px;cursor:pointer;font-size:12px}
.sarrow:hover{background:#12122a;color:#e0e0e0}
#step-counter{font-size:10px;color:#888;margin-left:auto}
#steps-wrap{flex:1;overflow-y:auto;padding:12px}
.step-card{background:#12122a;border-radius:7px;border-left:3px solid #a0c4ff;padding:10px 12px;margin-bottom:10px;display:none}
.step-card.on{display:block}
.step-title{font-size:12px;font-weight:600;color:#a0c4ff;margin-bottom:5px}
.step-body{font-size:11px;color:#ccc;line-height:1.65}
#inspector{border-top:1px solid #2d2d4e;padding:10px 12px;flex-shrink:0;max-height:200px;overflow-y:auto;background:#0f0f1a}
#insp-head{font-size:10px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
#insp-body{font-size:11px;line-height:1.6;color:#ccc}
.irow{display:flex;gap:6px;margin-bottom:3px}
.ik{color:#666;min-width:70px;font-size:10px}
.iv{color:#e0e0e0}
.nb-wrap{margin-top:5px;display:flex;flex-wrap:wrap;gap:3px}
.nb{font-size:10px;padding:2px 7px;border-radius:3px;cursor:pointer;border:1px solid #2d2d4e;background:#12122a}
.nb:hover{background:#1a1a2e}
#graph-wrap{flex:1;position:relative;overflow:hidden}
#graph-canvas{width:100%;height:100%;background:#0a0a14}
#graph-btns{position:absolute;top:8px;right:10px;display:flex;gap:6px;z-index:10}
.tbtn{background:#1a1a2ecc;border:1px solid #2d2d4e;color:#ccc;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer}
.tbtn:hover{background:#1a1a2e;color:#e0e0e0}
.tbtn.on{background:#a0c4ff;color:#0f0f1a;border-color:#a0c4ff;font-weight:600}
#graph-stats{position:absolute;bottom:8px;left:10px;display:flex;gap:6px;z-index:10}
.stat-pill{background:#1a1a2ecc;border:1px solid #2d2d4e;border-radius:14px;padding:3px 10px;font-size:10px;color:#aaa}
.stat-pill b{color:#a0c4ff}
#legend{position:absolute;bottom:8px;right:10px;background:#1a1a2ecc;border:1px solid #2d2d4e;border-radius:7px;padding:8px 10px;font-size:10px;z-index:10;line-height:1.8}
.lr{display:flex;align-items:center;gap:5px}
.lc{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.ll{width:18px;height:3px;flex-shrink:0;border-radius:1px}
.lsec{font-size:9px;font-weight:600;color:#666;text-transform:uppercase;margin:4px 0 2px;letter-spacing:.05em}
::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-track{background:#0f0f1a}
::-webkit-scrollbar-thumb{background:#2d2d4e;border-radius:2px}
</style>
</head>
<body>
<div id="topbar">
  <span class="logo">Cancer KG -- Subgraph Explainer</span>
  <div id="sg-btns"></div>
</div>
<div id="main">
  <div id="explain-panel">
    <div id="sg-header">
      <h2 id="sg-h2">Select a subgraph above</h2>
      <p id="sg-p">Click a button to load a curated subgraph with step-by-step explanation.</p>
    </div>
    <div id="step-nav">
      <button class="sarrow" onclick="prevStep()">&#8592;</button>
      <div id="step-dots" style="display:flex;gap:4px"></div>
      <button class="sarrow" onclick="nextStep()">&#8594;</button>
      <span id="step-counter"></span>
    </div>
    <div id="steps-wrap"><div id="steps-inner"></div></div>
    <div id="inspector">
      <div id="insp-head">Click any node to inspect</div>
      <div id="insp-body" style="color:#666;font-size:11px">Select a node in the graph to see full details here.</div>
    </div>
  </div>
  <div id="graph-wrap">
    <div id="graph-canvas"></div>
    <div id="graph-btns">
      <button class="tbtn" onclick="network&&network.fit()">Reset view</button>
      <button class="tbtn on" id="phys-btn" onclick="togglePhysics()">Physics ON</button>
    </div>
    <div id="graph-stats">
      <div class="stat-pill">Nodes: <b id="nc">0</b></div>
      <div class="stat-pill">Edges: <b id="ec">0</b></div>
    </div>
    <div id="legend">
      <div class="lsec">Node types</div>
      <div class="lr"><div class="lc" style="background:#4C9BE8"></div>Gene</div>
      <div class="lr"><div class="lc" style="background:#E8724C"></div>Cancer</div>
      <div class="lr"><div class="lc" style="background:#52B788"></div>Tissue</div>
      <div class="lr"><div class="lc" style="background:#F0C040"></div>Mutation</div>
      <div class="lr"><div class="lc" style="background:#8E6BBF"></div>HNC concept</div>
      <div class="lsec">Edge relations</div>
      <div class="lr"><div class="ll" style="background:#FF6B6B"></div>driver</div>
      <div class="lr"><div class="ll" style="background:#FFD93D"></div>oncogene</div>
      <div class="lr"><div class="ll" style="background:#6BCB77"></div>tumor suppressor</div>
      <div class="lr"><div class="ll" style="background:#4ECDC4"></div>mutated in (COSMIC)</div>
      <div class="lr"><div class="ll" style="background:#C77DFF"></div>has mutation</div>
      <div class="lr"><div class="ll" style="background:#ADB5BD"></div>subClassOf</div>
      <div class="lr"><div class="ll" style="background:#F8961E"></div>ontology cross-link</div>
    </div>
  </div>
</div>

<script>
var network = null, physOn = true, curSG = null, curStep = 0;

// ── Safety check ──────────────────────────────────────────────
// Run after full page load to ensure all scripts are ready
window.addEventListener('load', function() {
  if (typeof SUBGRAPHS === 'undefined' || !SUBGRAPHS.length) {
    document.getElementById('sg-h2').textContent = 'Data not loaded';
    document.getElementById('sg-p').textContent =
      'subgraph_data.js failed to load. Make sure to run: python serve_kg.py ' +
      'and open: http://localhost:8000/kg_output/cancer_subgraph_explained.html';
  } else {
    init();
  }
});

function init() {
  var wrap = document.getElementById('sg-btns');
  SUBGRAPHS.forEach(function(sg, i) {
    var btn = document.createElement('button');
    btn.className = 'sg-btn';
    btn.textContent = sg.label.split(' \u2014 ')[0];
    btn.title = sg.label;
    btn.onclick = function() { loadSG(i); };
    wrap.appendChild(btn);
  });
  loadSG(0);
}

function loadSG(idx) {
  curSG = SUBGRAPHS[idx]; curStep = 0;
  document.querySelectorAll('.sg-btn').forEach(function(b, i) {
    b.classList.toggle('active', i === idx);
    b.style.background = i === idx ? '#a0c4ff33' : '';
    b.style.borderColor = i === idx ? '#a0c4ff' : '';
    b.style.color = i === idx ? '#a0c4ff' : '';
  });
  document.getElementById('sg-h2').textContent = curSG.label;
  document.getElementById('sg-p').textContent  = curSG.description;
  renderSteps();
  buildNetwork();
}

function renderSteps() {
  var steps = curSG.steps || [];
  var dotsEl = document.getElementById('step-dots');
  dotsEl.innerHTML = '';
  steps.forEach(function(_, i) {
    var d = document.createElement('div');
    d.className = 'step-dot' + (i === curStep ? ' on' : '');
    d.onclick = (function(j){ return function(){ curStep=j; renderSteps(); }; })(i);
    dotsEl.appendChild(d);
  });
  document.getElementById('step-counter').textContent =
    steps.length ? (curStep+1)+' / '+steps.length : '';
  var inner = document.getElementById('steps-inner');
  inner.innerHTML = '';
  steps.forEach(function(s, i) {
    var card = document.createElement('div');
    card.className = 'step-card' + (i === curStep ? ' on' : '');
    card.innerHTML = '<div class="step-title">'+(i+1)+'. '+s[0]+'</div>'+
                     '<div class="step-body">'+s[1]+'</div>';
    inner.appendChild(card);
  });
}

function prevStep() { if(curSG){ curStep=Math.max(0,curStep-1); renderSteps(); } }
function nextStep() { if(curSG){ curStep=Math.min((curSG.steps||[]).length-1,curStep+1); renderSteps(); } }

function buildNetwork() {
  var container = document.getElementById('graph-canvas');
  var vnodes = new vis.DataSet(curSG.nodes.map(function(n) {
    var tt = document.createElement('div');
    tt.style.cssText='background:#1a1a2e;border:1px solid #3a3a5e;border-radius:7px;padding:7px 10px;font-size:11px;max-width:180px;line-height:1.55;font-family:Segoe UI,sans-serif;color:#e0e0e0';
    tt.innerHTML='<b style="color:'+n.color+'">'+n.full_label+'</b><br>'+
      '<span style="color:#888">Type: </span>'+n.node_type+'<br>'+
      (n.definition ? '<span style="font-size:10px;color:#aaa">'+n.definition.slice(0,90)+'</span>' : '');
    return {
      id:n.id, label:n.label, title:tt,
      color:{background:n.color+(n.seed?'':'bb'),border:n.color,
             highlight:{background:'#fff',border:n.color},
             hover:{background:'#fff',border:n.color}},
      size:n.size, borderWidth:n.borderWidth,
      font:{color:'#fff',size:n.seed?12:9,strokeWidth:2,strokeColor:'#00000099'},
      _data:n
    };
  }));

  var vedges = new vis.DataSet(curSG.edges.map(function(e) {
    var tt = document.createElement('div');
    tt.style.cssText='background:#1a1a2e;border:1px solid #3a3a5e;border-radius:7px;padding:6px 10px;font-size:11px;color:#e0e0e0;font-family:Segoe UI,sans-serif;line-height:1.55;max-width:200px';
    var rdesc = (typeof REL_DESCRIPTIONS !== 'undefined' && REL_DESCRIPTIONS[e.relation.toLowerCase()]) || e.relation;
    tt.innerHTML='<b style="color:#a0c4ff">'+e.relation+'</b><br>'+rdesc+
      (e.citation_count ? '<br><span style="color:#888">Citations: '+e.citation_count+'</span>' : '')+
      '<br><span style="color:#888">DB: '+e.source_db+'</span>';
    return {
      from:e.from, to:e.to, title:tt,
      color:{color:e.color,highlight:'#ffffff',hover:e.color},
      width:e.width,
      arrows:{to:{enabled:true,scaleFactor:0.5}},
      smooth:{type:'dynamic'},
      _data:e
    };
  }));

  if (network) network.destroy();
  network = new vis.Network(container, {nodes:vnodes,edges:vedges}, {
    physics:{stabilization:{iterations:120},
             barnesHut:{gravitationalConstant:-6000,springConstant:0.001,damping:0.9}},
    interaction:{hover:true,tooltipDelay:80,hideEdgesOnDrag:true},
    nodes:{shadow:{enabled:true,size:5,color:'#00000044'}},
    edges:{shadow:false}
  });

  document.getElementById('nc').textContent = curSG.nodes.length;
  document.getElementById('ec').textContent = curSG.edges.length;

  network.on('stabilizationIterationsDone', function() {
    network.setOptions({physics:{enabled:false}});
    physOn = false;
    var btn = document.getElementById('phys-btn');
    btn.textContent = 'Physics OFF'; btn.classList.remove('on');
  });

  network.on('click', function(params) {
    if (!params.nodes.length) return;
    var nid = params.nodes[0];
    var nd = vnodes.get(nid);
    if (!nd || !nd._data) return;
    showInspector(nid, nd._data, vnodes);
  });
}

function showInspector(nid, n, vnodes) {
  var conE = curSG.edges.filter(function(e){ return e.from===nid||e.to===nid; });
  var nbIds = [];
  var seen = {};
  conE.forEach(function(e){
    var other = e.from===nid ? e.to : e.from;
    if (!seen[other]){ seen[other]=true; nbIds.push(other); }
  });
  nbIds = nbIds.slice(0,14);

  var relC = {};
  conE.forEach(function(e){ relC[e.relation]=(relC[e.relation]||0)+1; });

  var html = '<div class="irow"><span class="ik">Label</span><span class="iv" style="color:'+n.color+'">'+n.full_label+'</span></div>'+
    '<div class="irow"><span class="ik">Type</span><span class="iv">'+n.node_type+'</span></div>'+
    '<div class="irow"><span class="ik">Edges</span><span class="iv">'+conE.length+'</span></div>'+
    '<div class="irow"><span class="ik">Source DB</span><span class="iv">'+(n.source_db||'—')+'</span></div>';

  Object.keys(relC).forEach(function(r){
    html+='<div class="irow"><span class="ik" style="color:#aaa">'+r+'</span><span class="iv">x'+relC[r]+'</span></div>';
  });

  if (n.definition && n.definition.trim()) {
    html+='<div style="margin-top:5px;font-size:10px;color:#aaa;line-height:1.5">'+n.definition+'</div>';
  }

  if (nbIds.length) {
    html+='<div style="margin-top:6px;font-size:10px;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:.05em">Neighbours</div><div class="nb-wrap">';
    nbIds.forEach(function(oid){
      var on = curSG.nodes.find(function(x){return x.id===oid;});
      if (!on) return;
      html+='<span class="nb" style="border-color:'+on.color+'44;color:'+on.color+'" onclick="network&&network.focus(\''+oid+'\',{scale:1.4,animation:true})">'+on.full_label.slice(0,15)+'</span>';
    });
    html+='</div>';
  }

  document.getElementById('insp-head').textContent = n.full_label.slice(0,28);
  document.getElementById('insp-body').innerHTML = html;
}

function togglePhysics() {
  physOn = !physOn;
  if (network) network.setOptions({physics:{enabled:physOn}});
  var btn = document.getElementById('phys-btn');
  btn.textContent = physOn ? 'Physics ON' : 'Physics OFF';
  btn.classList.toggle('on', physOn);
}
</script>
</body>
</html>'''

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"Written HTML: {OUT_HTML}")
print(f"HTML size: {os.path.getsize(OUT_HTML)//1024} KB")
print(f"JS size:   {os.path.getsize(OUT_JS)//1024} KB")
print()
print("Open via: http://localhost:8000/kg_output/cancer_subgraph_explained.html")