"""
enhance_cancer_kg.py
════════════════════════════════════════════════════════════════
Reads kg_output/cancer_kg_nodes.csv + cancer_kg_edges.csv
and builds an enhanced interactive HTML knowledge graph with:
  • Search bar — find any gene / cancer / tissue instantly
  • Filter panel — toggle node types & edge relations on/off
  • Stats dashboard — live node/edge counts
  • Node inspector — click any node to see full details
  • Highlight mode — hover to dim neighbours
  • Export selected subgraph

Run from C:\\Development\\Dataset_KG:
    python enhance_cancer_kg.py

Output: kg_output/cancer_kg_enhanced.html
"""

import os, json
import pandas as pd

BASE    = os.path.dirname(os.path.abspath(__file__))
OUT     = os.path.join(BASE, "kg_output")
NODES_F = os.path.join(OUT, "cancer_kg_nodes.csv")
EDGES_F = os.path.join(OUT, "cancer_kg_edges.csv")

print("Loading graph data...")
nodes_df = pd.read_csv(NODES_F).fillna("")
edges_df = pd.read_csv(EDGES_F).fillna("")

# Rename columns defensively
if "src" in edges_df.columns:
    edges_df.rename(columns={"src": "source", "tgt": "target"}, inplace=True)

print(f"  Nodes: {len(nodes_df):,}  Edges: {len(edges_df):,}")

# ── Build JS-safe node/edge arrays (top 300 nodes by degree) ──
from collections import Counter
deg = Counter()
for _, r in edges_df.iterrows():
    deg[r["source"]] += 1
    deg[r["target"]] += 1

top_ids = set(n for n, _ in deg.most_common(300))
# always include all hnc_class nodes
for _, r in nodes_df.iterrows():
    if str(r.get("node_type","")) == "hnc_class":
        top_ids.add(r["id"])

nodes_sub = nodes_df[nodes_df["id"].isin(top_ids)].copy()
edges_sub  = edges_df[
    edges_df["source"].isin(top_ids) & edges_df["target"].isin(top_ids)
].copy()

print(f"  Subgraph: {len(nodes_sub):,} nodes | {len(edges_sub):,} edges")

COLORS = {
    "gene":      "#4C9BE8",
    "cancer":    "#E8724C",
    "mutation":  "#F0C040",
    "hnc_class": "#8E6BBF",
    "tissue":    "#52B788",
}
REL_COLORS = {
    "driver":             "#FF6B6B",
    "oncogene":           "#FFD93D",
    "tumor_suppressor":   "#6BCB77",
    "mutated_in":         "#4ECDC4",
    "has_mutation":       "#C77DFF",
    "subclassof":         "#ADB5BD",
    "mapped_to_ontology": "#F8961E",
}

def node_size(ntype, degree):
    base = {"gene": 14, "cancer": 20, "mutation": 7,
            "hnc_class": 12, "tissue": 16}.get(ntype, 12)
    return min(base + degree * 0.4, 45)

nodes_js = []
for _, r in nodes_sub.iterrows():
    ntype = str(r.get("node_type", "gene"))
    d = deg.get(r["id"], 1)
    nodes_js.append({
        "id":         str(r["id"]),
        "label":      str(r.get("label", r["id"]))[:20],
        "full_label": str(r.get("label", r["id"])),
        "node_type":  ntype,
        "color":      COLORS.get(ntype, "#888"),
        "size":       node_size(ntype, d),
        "degree":     d,
        "definition": str(r.get("definition", ""))[:200],
        "source_db":  str(r.get("source_db", "")),
    })

edges_js = []
for _, r in edges_sub.iterrows():
    rel = str(r.get("relation","")).lower()
    edges_js.append({
        "source":      str(r["source"]),
        "target":      str(r["target"]),
        "relation":    str(r.get("relation","")),
        "color":       REL_COLORS.get(rel, "#555555"),
        "width":       max(1, min(5, float(r["weight"]) * 4))
                       if "weight" in r and r["weight"] != "" else 1.5,
        "source_db":   str(r.get("source_db","")),
        "cite_count":  int(r["citation_count"])
                       if "citation_count" in r and r["citation_count"] != "" else 0,
    })

stats = {
    "total_nodes": len(nodes_df),
    "total_edges": len(edges_df),
    "node_types":  dict(Counter(nodes_df["node_type"].fillna("?"))),
    "edge_rels":   dict(Counter(edges_df["relation"].fillna("?"))),
    "top_genes": [
        {"gene": n.replace("GENE:",""), "degree": d}
        for n, d in deg.most_common(15)
        if n.startswith("GENE:")
    ]
}

nodes_json = json.dumps(nodes_js, ensure_ascii=False)
edges_json = json.dumps(edges_js, ensure_ascii=False)
stats_json = json.dumps(stats,    ensure_ascii=False)

# ── HTML ───────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cancer Knowledge Graph</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e0e0e0;
     display:flex;height:100vh;overflow:hidden}}

/* ── LEFT PANEL ── */
#panel{{width:270px;flex-shrink:0;background:#1a1a2e;border-right:1px solid #2d2d4e;
        display:flex;flex-direction:column;overflow:hidden}}
#panel-header{{padding:14px 16px;background:#12122a;border-bottom:1px solid #2d2d4e}}
#panel-header h2{{font-size:14px;font-weight:600;color:#a0c4ff;letter-spacing:.05em}}
#panel-header p{{font-size:11px;color:#666;margin-top:3px}}

#search-box{{margin:10px 12px;position:relative}}
#search-input{{width:100%;padding:7px 10px 7px 30px;background:#12122a;
               border:1px solid #3a3a5e;border-radius:6px;color:#e0e0e0;
               font-size:12px;outline:none}}
#search-input:focus{{border-color:#4C9BE8}}
#search-icon{{position:absolute;left:9px;top:50%;transform:translateY(-50%);
              color:#666;font-size:13px}}
#search-results{{background:#12122a;border:1px solid #3a3a5e;border-radius:6px;
                 max-height:160px;overflow-y:auto;margin-top:4px;display:none}}
.sr-item{{padding:6px 10px;font-size:12px;cursor:pointer;border-bottom:1px solid #2a2a3e}}
.sr-item:hover{{background:#2a2a4e}}
.sr-type{{font-size:10px;padding:1px 5px;border-radius:3px;margin-left:5px}}

#panel-tabs{{display:flex;border-bottom:1px solid #2d2d4e}}
.ptab{{flex:1;padding:8px 4px;font-size:11px;text-align:center;cursor:pointer;
       color:#888;border-bottom:2px solid transparent;transition:all .2s}}
.ptab.active{{color:#a0c4ff;border-color:#4C9BE8}}

#tab-content{{flex:1;overflow-y:auto;padding:10px 12px}}

/* filters */
.filter-section{{margin-bottom:14px}}
.filter-title{{font-size:11px;font-weight:600;color:#888;text-transform:uppercase;
               letter-spacing:.06em;margin-bottom:7px}}
.filter-row{{display:flex;align-items:center;gap:8px;margin-bottom:5px;
             font-size:12px;cursor:pointer}}
.filter-row input{{cursor:pointer;accent-color:#4C9BE8}}
.color-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}

/* stats */
.stat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}}
.stat-card{{background:#12122a;border:1px solid #2d2d4e;border-radius:6px;
            padding:8px 10px;text-align:center}}
.stat-num{{font-size:18px;font-weight:600;color:#a0c4ff}}
.stat-lbl{{font-size:10px;color:#666;margin-top:2px}}
.bar-row{{display:flex;align-items:center;gap:6px;margin-bottom:4px;font-size:11px}}
.bar-track{{flex:1;height:6px;background:#2a2a3e;border-radius:3px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px}}
.bar-val{{font-size:10px;color:#888;min-width:36px;text-align:right}}

/* inspector */
#inspector{{padding:10px 12px}}
#insp-name{{font-size:14px;font-weight:600;color:#a0c4ff;margin-bottom:6px}}
#insp-body{{font-size:12px;line-height:1.7;color:#ccc}}
.insp-row{{display:flex;gap:6px;margin-bottom:4px}}
.insp-key{{color:#888;min-width:80px}}
.insp-val{{color:#e0e0e0}}
#insp-neighbours{{margin-top:8px}}
.nb-chip{{display:inline-block;padding:2px 7px;background:#2a2a4e;border-radius:4px;
          font-size:11px;margin:2px;cursor:pointer;border:1px solid #3a3a5e}}
.nb-chip:hover{{background:#3a3a6e}}

/* ── MAIN CANVAS ── */
#graph-wrap{{flex:1;position:relative;overflow:hidden}}
#graph-canvas{{width:100%;height:100%}}

/* toolbar */
#toolbar{{position:absolute;top:10px;right:12px;display:flex;gap:6px;z-index:10}}
.tbtn{{background:#1a1a2e;border:1px solid #3a3a5e;color:#ccc;
       padding:6px 12px;border-radius:6px;font-size:12px;cursor:pointer;
       transition:all .15s}}
.tbtn:hover{{background:#2a2a4e;color:#fff}}
.tbtn.active{{background:#4C9BE8;color:#fff;border-color:#4C9BE8}}

/* top stats bar */
#topbar{{position:absolute;top:10px;left:12px;display:flex;gap:8px;z-index:10}}
.tb-pill{{background:#1a1a2ecc;backdrop-filter:blur(4px);border:1px solid #3a3a5e;
          border-radius:20px;padding:4px 12px;font-size:11px;color:#ccc}}
.tb-pill b{{color:#a0c4ff}}

/* tooltip */
#tooltip{{position:absolute;background:#1a1a2eee;border:1px solid #3a3a5e;
          border-radius:8px;padding:8px 12px;font-size:12px;pointer-events:none;
          display:none;z-index:20;max-width:220px;line-height:1.6}}

/* scrollbar */
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:#12122a}}
::-webkit-scrollbar-thumb{{background:#3a3a5e;border-radius:3px}}
</style>
</head>
<body>

<!-- ════ LEFT PANEL ════ -->
<div id="panel">
  <div id="panel-header">
    <h2>🧬 Cancer Knowledge Graph</h2>
    <p id="sub-title">Loading...</p>
  </div>

  <div id="search-box">
    <span id="search-icon">🔍</span>
    <input id="search-input" type="text" placeholder="Search gene, cancer, tissue...">
    <div id="search-results"></div>
  </div>

  <div id="panel-tabs">
    <div class="ptab active" onclick="switchTab('filters')">Filters</div>
    <div class="ptab" onclick="switchTab('stats')">Stats</div>
    <div class="ptab" onclick="switchTab('inspector')">Inspector</div>
  </div>

  <div id="tab-content">

    <!-- FILTERS TAB -->
    <div id="tab-filters">
      <div class="filter-section">
        <div class="filter-title">Node Types</div>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="node" data-val="gene"><span class="color-dot" style="background:#4C9BE8"></span>Gene</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="node" data-val="cancer"><span class="color-dot" style="background:#E8724C"></span>Cancer</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="node" data-val="tissue"><span class="color-dot" style="background:#52B788"></span>Tissue</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="node" data-val="mutation"><span class="color-dot" style="background:#F0C040"></span>Mutation</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="node" data-val="hnc_class"><span class="color-dot" style="background:#8E6BBF"></span>HNC Concept</label>
      </div>

      <div class="filter-section">
        <div class="filter-title">Edge Relations</div>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="driver"><span class="color-dot" style="background:#FF6B6B"></span>Driver</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="oncogene"><span class="color-dot" style="background:#FFD93D"></span>Oncogene</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="tumor_suppressor"><span class="color-dot" style="background:#6BCB77"></span>Tumor suppressor</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="mutated_in"><span class="color-dot" style="background:#4ECDC4"></span>Mutated in tissue</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="has_mutation"><span class="color-dot" style="background:#C77DFF"></span>Has mutation</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="subclassof"><span class="color-dot" style="background:#ADB5BD"></span>SubclassOf</label>
        <label class="filter-row"><input type="checkbox" checked onchange="filterChange()" data-filter="edge" data-val="mapped_to_ontology"><span class="color-dot" style="background:#F8961E"></span>Ontology link</label>
      </div>

      <div class="filter-section">
        <div class="filter-title">Min Citation Count</div>
        <input type="range" id="cite-slider" min="0" max="50" value="0"
               oninput="document.getElementById('cite-val').textContent=this.value;filterChange()"
               style="width:100%;accent-color:#4C9BE8">
        <div style="font-size:11px;color:#888;margin-top:3px">
          ≥ <span id="cite-val">0</span> citations
        </div>
      </div>
    </div>

    <!-- STATS TAB -->
    <div id="tab-stats" style="display:none">
      <div class="stat-grid">
        <div class="stat-card"><div class="stat-num" id="s-nodes">-</div><div class="stat-lbl">Total Nodes</div></div>
        <div class="stat-card"><div class="stat-num" id="s-edges">-</div><div class="stat-lbl">Total Edges</div></div>
        <div class="stat-card"><div class="stat-num" id="s-genes">-</div><div class="stat-lbl">Genes</div></div>
        <div class="stat-card"><div class="stat-num" id="s-cancers">-</div><div class="stat-lbl">Cancer types</div></div>
      </div>

      <div class="filter-title" style="margin-bottom:8px">Edge breakdown</div>
      <div id="edge-bars"></div>

      <div class="filter-title" style="margin-top:12px;margin-bottom:8px">Top 15 genes by degree</div>
      <div id="gene-bars"></div>
    </div>

    <!-- INSPECTOR TAB -->
    <div id="tab-inspector" style="display:none">
      <div id="inspector">
        <div id="insp-name" style="color:#666;font-size:12px">Click any node to inspect it</div>
        <div id="insp-body"></div>
      </div>
    </div>

  </div>
</div>

<!-- ════ MAIN GRAPH ════ -->
<div id="graph-wrap">
  <div id="topbar">
    <div class="tb-pill">Showing <b id="vis-nodes">-</b> nodes · <b id="vis-edges">-</b> edges</div>
    <div class="tb-pill">Visible: <b id="vis-filtered">all</b></div>
  </div>
  <div id="toolbar">
    <button class="tbtn" onclick="network.fit()">⟳ Reset view</button>
    <button class="tbtn" id="btn-physics" onclick="togglePhysics()">⏸ Physics</button>
    <button class="tbtn" onclick="highlightNeighbours=!highlightNeighbours;this.classList.toggle('active')">👁 Highlight</button>
  </div>
  <div id="graph-canvas"></div>
  <div id="tooltip"></div>
</div>

<script>
// ── DATA ─────────────────────────────────────────────────────
const RAW_NODES = {nodes_json};
const RAW_EDGES = {edges_json};
const STATS     = {stats_json};

// ── VIS DATASETS ────────────────────────────────────────────
const visNodes = new vis.DataSet();
const visEdges = new vis.DataSet();

function buildVisNode(n) {{
  return {{
    id:    n.id,
    label: n.label,
    color: {{ background: n.color, border: n.color,
              highlight: {{ background: '#ffffff', border: n.color }},
              hover:     {{ background: '#ffffff', border: n.color }} }},
    size:  n.size,
    font:  {{ color: '#ffffff', size: 11, strokeWidth: 2, strokeColor: '#00000088' }},
    title: buildTooltip(n),
    _data: n,
  }};
}}

function buildTooltip(n) {{
  let t = `<b>${{n.full_label}}</b><br>`;
  t += `Type: ${{n.node_type}}<br>Degree: ${{n.degree}}`;
  if (n.definition) t += `<br><small>${{n.definition.slice(0,120)}}</small>`;
  return t;
}}

function buildVisEdge(e) {{
  return {{
    from:  e.source,
    to:    e.target,
    color: {{ color: e.color, highlight: '#ffffff', hover: e.color }},
    width: e.width,
    arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
    smooth: {{ type: 'dynamic' }},
    title: `${{e.relation}} (${{e.source_db}})${{e.cite_count ? ' · ' + e.cite_count + ' citations' : ''}}`,
    _data: e,
  }};
}}

RAW_NODES.forEach(n => visNodes.add(buildVisNode(n)));
RAW_EDGES.forEach(e => visEdges.add(buildVisEdge(e)));

// ── NETWORK ─────────────────────────────────────────────────
const container = document.getElementById('graph-canvas');
const network = new vis.Network(container, {{ nodes: visNodes, edges: visEdges }}, {{
  physics: {{
    stabilization: {{ iterations: 200 }},
    barnesHut: {{ gravitationalConstant: -8000, springConstant: 0.001, damping: 0.9 }},
  }},
  interaction: {{ hover: true, tooltipDelay: 100, hideEdgesOnDrag: true }},
  nodes: {{ borderWidth: 1, shadow: {{ enabled: true, size: 6, color: '#00000066' }} }},
  edges: {{ shadow: false }},
}});

let physicsOn = true;
function togglePhysics() {{
  physicsOn = !physicsOn;
  network.setOptions({{ physics: {{ enabled: physicsOn }} }});
  document.getElementById('btn-physics').textContent = physicsOn ? '⏸ Physics' : '▶ Physics';
}}

// ── TOPBAR COUNT ────────────────────────────────────────────
function updateTopbar() {{
  document.getElementById('vis-nodes').textContent = visNodes.length.toLocaleString();
  document.getElementById('vis-edges').textContent = visEdges.length.toLocaleString();
}}
updateTopbar();

// ── FILTERS ─────────────────────────────────────────────────
let activeNodeTypes = new Set(['gene','cancer','tissue','mutation','hnc_class']);
let activeEdgeRels  = new Set(['driver','oncogene','tumor_suppressor','mutated_in',
                                'has_mutation','subclassof','mapped_to_ontology']);
let minCite = 0;

function filterChange() {{
  activeNodeTypes.clear();
  document.querySelectorAll('[data-filter="node"]:checked')
          .forEach(el => activeNodeTypes.add(el.dataset.val));
  activeEdgeRels.clear();
  document.querySelectorAll('[data-filter="edge"]:checked')
          .forEach(el => activeEdgeRels.add(el.dataset.val));
  minCite = parseInt(document.getElementById('cite-slider').value) || 0;

  visNodes.clear(); visEdges.clear();
  const allowedIds = new Set();
  RAW_NODES.forEach(n => {{
    if (activeNodeTypes.has(n.node_type)) {{
      visNodes.add(buildVisNode(n));
      allowedIds.add(n.id);
    }}
  }});
  RAW_EDGES.forEach(e => {{
    const relKey = e.relation.toLowerCase();
    if (allowedIds.has(e.source) && allowedIds.has(e.target) &&
        activeEdgeRels.has(relKey) && e.cite_count >= minCite) {{
      visEdges.add(buildVisEdge(e));
    }}
  }});
  updateTopbar();
  document.getElementById('vis-filtered').textContent =
    (visNodes.length === RAW_NODES.length ? 'all' : visNodes.length + ' types');
}}

// ── SEARCH ──────────────────────────────────────────────────
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

searchInput.addEventListener('input', () => {{
  const q = searchInput.value.trim().toLowerCase();
  searchResults.style.display = 'none';
  searchResults.innerHTML = '';
  if (!q || q.length < 2) return;
  const hits = RAW_NODES.filter(n =>
    n.full_label.toLowerCase().includes(q) ||
    n.id.toLowerCase().includes(q)
  ).slice(0, 12);
  if (!hits.length) return;
  hits.forEach(n => {{
    const div = document.createElement('div');
    div.className = 'sr-item';
    div.innerHTML = `${{n.full_label}}
      <span class="sr-type" style="background:${{n.color}}22;color:${{n.color}}">
        ${{n.node_type}}</span>`;
    div.onclick = () => focusNode(n.id);
    searchResults.appendChild(div);
  }});
  searchResults.style.display = 'block';
}});

document.addEventListener('click', e => {{
  if (!e.target.closest('#search-box')) searchResults.style.display = 'none';
}});

function focusNode(id) {{
  searchResults.style.display = 'none';
  searchInput.value = '';
  try {{
    network.focus(id, {{ scale: 1.4, animation: {{ duration: 800, easingFunction: 'easeInOutQuad' }} }});
    network.selectNodes([id]);
    showInspector(id);
    switchTab('inspector');
  }} catch(e) {{ console.warn('Node not in current view:', id); }}
}}

// ── NODE INSPECTOR ──────────────────────────────────────────
function showInspector(nodeId) {{
  const n = RAW_NODES.find(x => x.id === nodeId);
  if (!n) return;
  document.getElementById('insp-name').innerHTML =
    `<span style="color:${{n.color}}">●</span> ${{n.full_label}}`;
  document.getElementById('insp-name').style.color = '#e0e0e0';

  const connectedEdges = RAW_EDGES.filter(
    e => e.source === nodeId || e.target === nodeId
  );
  const neighbours = [...new Set(connectedEdges.map(
    e => e.source === nodeId ? e.target : e.source
  ))].slice(0, 20);
  const nbNodes = neighbours.map(id => RAW_NODES.find(x => x.id === id)).filter(Boolean);

  const relCounts = {{}};
  connectedEdges.forEach(e => {{
    relCounts[e.relation] = (relCounts[e.relation] || 0) + 1;
  }});

  let html = `
    <div class="insp-row"><span class="insp-key">Type</span>
      <span class="insp-val" style="color:${{n.color}}">${{n.node_type}}</span></div>
    <div class="insp-row"><span class="insp-key">Degree</span>
      <span class="insp-val">${{n.degree}}</span></div>
    <div class="insp-row"><span class="insp-key">Connections</span>
      <span class="insp-val">${{connectedEdges.length}} edges</span></div>
  `;
  if (n.definition) html += `
    <div class="insp-row" style="flex-direction:column">
      <span class="insp-key">Definition</span>
      <span class="insp-val" style="font-size:11px;color:#aaa;margin-top:3px">${{n.definition}}</span>
    </div>`;

  html += `<div style="margin-top:8px;font-size:11px;color:#888;font-weight:600;
                        text-transform:uppercase;letter-spacing:.06em">Relations</div>`;
  Object.entries(relCounts).forEach(([rel, cnt]) => {{
    html += `<div class="insp-row"><span class="insp-key" style="color:#aaa">${{rel}}</span>
             <span class="insp-val">${{cnt}}</span></div>`;
  }});

  if (nbNodes.length) {{
    html += `<div style="margin-top:8px;font-size:11px;color:#888;font-weight:600;
                          text-transform:uppercase;letter-spacing:.06em">Neighbours</div>
             <div id="insp-neighbours" style="margin-top:4px">`;
    nbNodes.forEach(nb => {{
      html += `<span class="nb-chip" onclick="focusNode('${{nb.id}}')"
                style="border-color:${{nb.color}}44;color:${{nb.color}}">
                ${{nb.full_label.slice(0,18)}}</span>`;
    }});
    html += '</div>';
  }}

  document.getElementById('insp-body').innerHTML = html;
}};

network.on('click', params => {{
  if (params.nodes.length > 0) {{
    showInspector(params.nodes[0]);
    switchTab('inspector');
  }}
}});

// ── HIGHLIGHT NEIGHBOURS ────────────────────────────────────
let highlightNeighbours = false;
network.on('hoverNode', params => {{
  if (!highlightNeighbours) return;
  const id = params.node;
  const connected = new Set(RAW_EDGES
    .filter(e => e.source === id || e.target === id)
    .flatMap(e => [e.source, e.target]));
  connected.add(id);
  visNodes.getIds().forEach(nid => {{
    visNodes.update({{ id: nid, opacity: connected.has(nid) ? 1 : 0.15 }});
  }});
}});
network.on('blurNode', () => {{
  if (!highlightNeighbours) return;
  visNodes.getIds().forEach(nid => visNodes.update({{ id: nid, opacity: 1 }}));
}});

// ── TABS ────────────────────────────────────────────────────
function switchTab(name) {{
  ['filters','stats','inspector'].forEach(t => {{
    document.getElementById('tab-'+t).style.display = (t===name) ? '' : 'none';
  }});
  document.querySelectorAll('.ptab').forEach((el, i) => {{
    el.classList.toggle('active', ['filters','stats','inspector'][i] === name);
  }});
  if (name === 'stats') populateStats();
}}

// ── STATS ────────────────────────────────────────────────────
function populateStats() {{
  document.getElementById('s-nodes').textContent   = STATS.total_nodes.toLocaleString();
  document.getElementById('s-edges').textContent   = STATS.total_edges.toLocaleString();
  document.getElementById('s-genes').textContent   = (STATS.node_types.gene||0).toLocaleString();
  document.getElementById('s-cancers').textContent = (STATS.node_types.cancer||0).toLocaleString();

  const relColors = {{
    driver:'#FF6B6B', oncogene:'#FFD93D', tumor_suppressor:'#6BCB77',
    mutated_in:'#4ECDC4', has_mutation:'#C77DFF',
    subClassOf:'#ADB5BD', mapped_to_ontology:'#F8961E'
  }};
  const maxE = Math.max(...Object.values(STATS.edge_rels));
  let ebars = '';
  Object.entries(STATS.edge_rels).sort((a,b)=>b[1]-a[1]).forEach(([k,v]) => {{
    const pct = Math.round(v/maxE*100);
    const col = relColors[k] || '#888';
    ebars += `<div class="bar-row">
      <span style="color:${{col}};min-width:110px;font-size:11px">${{k}}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${{pct}}%;background:${{col}}"></div></div>
      <span class="bar-val">${{v.toLocaleString()}}</span></div>`;
  }});
  document.getElementById('edge-bars').innerHTML = ebars;

  const maxG = STATS.top_genes[0]?.degree || 1;
  let gbars = '';
  STATS.top_genes.forEach(g => {{
    const pct = Math.round(g.degree/maxG*100);
    gbars += `<div class="bar-row">
      <span style="min-width:90px;font-size:11px;cursor:pointer;color:#4C9BE8"
            onclick="focusNode('GENE:${{g.gene}}')">${{g.gene}}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${{pct}}%;background:#4C9BE8"></div></div>
      <span class="bar-val">${{g.degree}}</span></div>`;
  }});
  document.getElementById('gene-bars').innerHTML = gbars;
}}

// ── SUBTITLE ────────────────────────────────────────────────
document.getElementById('sub-title').textContent =
  `${{RAW_NODES.length.toLocaleString()}} nodes · ${{RAW_EDGES.length.toLocaleString()}} edges`;

network.on('stabilizationIterationsDone', () => {{
  network.setOptions({{ physics: {{ enabled: false }} }});
  physicsOn = false;
  document.getElementById('btn-physics').textContent = '▶ Physics';
}});
</script>
</body></html>
"""

out_path = os.path.join(OUT, "cancer_kg_enhanced.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML)

size_mb = os.path.getsize(out_path) / 1024 / 1024
print(f"\n✅ Enhanced KG saved → {out_path}  ({size_mb:.1f} MB)")
print("   Open cancer_kg_enhanced.html in Chrome")
print("\nFeatures:")
print("  🔍 Search bar  — find any gene/cancer/tissue")
print("  🎛  Filters    — toggle node types & edge relations")
print("  📊 Stats tab   — breakdown charts + top genes")
print("  🔬 Inspector   — click node for full details + neighbours")
print("  👁  Highlight  — hover to dim non-neighbours")