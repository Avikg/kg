"""
build_cancer_kg.py  — FIXED VERSION
══════════════════════════════════════════════════════════════════
Cancer Knowledge Graph: HeNeCOn + CancerMine + COSMIC
══════════════════════════════════════════════════════════════════

Run from C:\\Development\\Dataset_KG:
    pip install pandas rdflib networkx pyvis tqdm matplotlib numpy
    python build_cancer_kg.py

Outputs in  kg_output/ :
    cancer_kg.graphml       — Gephi / Cytoscape
    cancer_kg.html          — interactive browser viz
    cancer_kg_nodes.csv
    cancer_kg_edges.csv
    cancer_kg_stats.txt
    cancer_kg_plot.png
"""

import os, warnings
import pandas as pd
import numpy as np
import networkx as nx
from collections import Counter
from tqdm import tqdm
warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
CM_DIR  = os.path.join(BASE, "cancermine")
HNC_DIR = os.path.join(BASE, "hencon")
CSM_DIR = os.path.join(BASE, "cosmic")
OUT     = os.path.join(BASE, "kg_output")
os.makedirs(OUT, exist_ok=True)

# ── Node colours ───────────────────────────────────────────────
COLORS = {
    "gene":      "#4C9BE8",
    "cancer":    "#E8724C",
    "mutation":  "#F0C040",
    "hnc_class": "#8E6BBF",
    "tissue":    "#52B788",
}

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def pick_col(df, *candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def find_file(directory, keyword, extension=".tsv"):
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(extension) and keyword.lower() in f.lower():
                return os.path.join(root, f)
    return None

def add_node(G, nid, label, ntype, size=15, **kw):
    if not G.has_node(nid):
        G.add_node(nid, label=label, node_type=ntype,
                   color=COLORS.get(ntype, "#888"), size=size, **kw)

# ══════════════════════════════════════════════════════════════
# STEP 1 — CANCERMINE
# ══════════════════════════════════════════════════════════════
print("\n[1/5] Loading CancerMine...")
cm_path = os.path.join(CM_DIR, "cancermine_collated.tsv")
cm = pd.read_csv(cm_path, sep="\t")
print(f"      Rows: {len(cm):,}  Columns: {list(cm.columns)}")

GENE_COL   = pick_col(cm, "gene_hugo", "gene_normalized", "gene_symbol", "gene")
CANCER_COL = pick_col(cm, "cancer_type", "cancer_normalized", "cancer_name", "cancer")
ROLE_COL   = pick_col(cm, "role", "gene_role", "cancer_role")
CITE_COL   = pick_col(cm, "citation_count", "citations", "count")

print(f"      gene='{GENE_COL}'  cancer='{CANCER_COL}'  role='{ROLE_COL}'  cite='{CITE_COL}'")

cm["_cite"] = pd.to_numeric(cm[CITE_COL], errors="coerce").fillna(1)
cm["importance"] = np.log10(cm["_cite"] + 1)
max_imp = cm.groupby(CANCER_COL)["importance"].transform("max")
cm["importance_norm"] = (cm["importance"] / (max_imp + 1e-9)).round(4)

# ══════════════════════════════════════════════════════════════
# STEP 2 — COSMIC
# ══════════════════════════════════════════════════════════════
print("\n[2/5] Loading COSMIC...")

COSMIC_WANT = {
    "gene":   ["GENE_SYMBOL", "Gene name", "GENE_NAME", "gene_symbol"],
    "site":   ["PRIMARY_SITE", "Primary Site", "PRIMARY_TISSUE", "tissue", "TISSUE"],
    "mut_id": ["GENOMIC_MUTATION_ID", "COSMIC_MUTATION_ID", "MUTATION_ID"],
    "fathmm": ["FATHMM_PREDICTION", "FATHMM prediction", "PATHOGENICITY"],
    "tier":   ["TIER", "Tier", "CGC_TIER"],
    "hist":   ["HISTOLOGY", "Primary Histology", "CANCER_TYPE"],
}

def load_cosmic_tsv(path, max_rows=200_000):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        header = fh.readline().strip().split("\t")
    use_cols, col_map = [], {}
    for role, candidates in COSMIC_WANT.items():
        found = next((c for c in candidates if c in header), None)
        if found:
            use_cols.append(found)
            col_map[found] = role
    try:
        df = pd.read_csv(path, sep="\t", usecols=use_cols,
                         low_memory=False, nrows=max_rows,
                         encoding="utf-8", on_bad_lines="skip")
    except TypeError:
        df = pd.read_csv(path, sep="\t", usecols=use_cols,
                         low_memory=False, nrows=max_rows,
                         encoding="utf-8", error_bad_lines=False)
    df.rename(columns=col_map, inplace=True)
    return df

cmc, cgc = pd.DataFrame(), pd.DataFrame()

cmc_path = find_file(CSM_DIR, "MutationCensus")
cgc_path = find_file(CSM_DIR, "MutantCensus")

for label, path, target in [("CancerMutationCensus", cmc_path, "cmc"),
                              ("MutantCensus",         cgc_path, "cgc")]:
    if path:
        print(f"      Loading {label} from {os.path.basename(path)}")
        df = load_cosmic_tsv(path)
        print(f"        {len(df):,} rows | cols: {list(df.columns)}")
        if target == "cmc": cmc = df
        else: cgc = df
    else:
        print(f"      {label} not found")

# ══════════════════════════════════════════════════════════════
# STEP 3 — HENECON OWL
# ══════════════════════════════════════════════════════════════
print("\n[3/5] Loading HeNeCOn OWL...")
owl_path = find_file(HNC_DIR, "", extension=".owl")
hnc_classes, hnc_edges = {}, []

if owl_path:
    try:
        from rdflib import Graph as RDFGraph, RDFS, OWL, RDF
        g_owl = RDFGraph()
        g_owl.parse(owl_path)
        print(f"      Triples: {len(g_owl):,}")

        for s, _, _ in g_owl.triples((None, RDF.type, OWL.Class)):
            label = g_owl.value(s, RDFS.label)
            defn  = g_owl.value(s, RDFS.comment)
            if label:
                hnc_classes[str(s)] = {
                    "label": str(label),
                    "defn":  str(defn) if defn else "",
                }

        for s, _, o in g_owl.triples((None, RDFS.subClassOf, None)):
            sl = hnc_classes.get(str(s), {}).get("label")
            ol = hnc_classes.get(str(o), {}).get("label")
            if sl and ol:
                hnc_edges.append({"src": sl, "tgt": ol})

        print(f"      Classes: {len(hnc_classes):,}  SubClass edges: {len(hnc_edges):,}")
    except Exception as e:
        print(f"      rdflib error: {e}")
else:
    print("      OWL file not found in hencon/")

# ══════════════════════════════════════════════════════════════
# STEP 4 — BUILD GRAPH
# ══════════════════════════════════════════════════════════════
print("\n[4/5] Building Knowledge Graph...")
G = nx.DiGraph()

# A — CancerMine
print("   A. CancerMine...")
for _, row in tqdm(cm.iterrows(), total=len(cm), ncols=72):
    gene   = str(row[GENE_COL]).strip()
    cancer = str(row[CANCER_COL]).strip()
    role   = str(row.get(ROLE_COL, "unknown")).strip().lower()
    weight = float(row.get("importance_norm", 0.5))
    if gene == "nan" or cancer == "nan": continue

    gid = f"GENE:{gene}"
    cid = f"CANCER:{cancer.replace(' ', '_')}"
    add_node(G, gid, gene, "gene", size=15)
    add_node(G, cid, cancer, "cancer", size=20)
    G.add_edge(gid, cid, relation=role, weight=weight,
               citation_count=int(row["_cite"]), source_db="CancerMine")

print(f"   → {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges")

# B — COSMIC
for df_name, df in [("CMC", cmc), ("CGC", cgc)]:
    if df.empty or "gene" not in df.columns: continue
    print(f"   B. COSMIC {df_name}...")
    sub = df.dropna(subset=["gene"]).head(100_000)
    for _, row in tqdm(sub.iterrows(), total=len(sub), ncols=72):
        gene = str(row["gene"]).strip()
        if gene == "nan": continue
        gid = f"GENE:{gene}"
        add_node(G, gid, gene, "gene", size=15)

        if "site" in row and str(row.get("site", "nan")) != "nan":
            site = str(row["site"]).strip()
            tid  = f"TISSUE:{site.replace(' ', '_')}"
            add_node(G, tid, site, "tissue", size=18)
            is_path = str(row.get("fathmm", "")).upper() == "PATHOGENIC"
            try:    tier = int(float(row.get("tier", 2)))
            except: tier = 2
            G.add_edge(gid, tid, relation="mutated_in",
                       pathogenic=is_path, tier=tier,
                       source_db=f"COSMIC_{df_name}")

        if "mut_id" in row and str(row.get("mut_id", "nan")) != "nan":
            mid = f"MUT:{row['mut_id']}"
            add_node(G, mid, str(row["mut_id"]), "mutation", size=6)
            G.add_edge(gid, mid, relation="has_mutation",
                       source_db=f"COSMIC_{df_name}")

    print(f"   → {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges")

# C — HeNeCOn
if hnc_classes:
    print("   C. HeNeCOn OWL...")
    for uri, info in tqdm(hnc_classes.items(), ncols=72):
        slug = uri.split("/")[-1].split("#")[-1]
        nid  = f"HNC:{slug}"
        add_node(G, nid, info["label"], "hnc_class",
                 size=12, definition=info["defn"])

    for e in hnc_edges:
        sid = f"HNC:{e['src'].replace(' ', '_')}"
        oid = f"HNC:{e['tgt'].replace(' ', '_')}"
        if G.has_node(sid) and G.has_node(oid):
            G.add_edge(sid, oid, relation="subClassOf", source_db="HeNeCOn")
    print(f"   → {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges")

# D — Cross-links
print("   D. Cross-linking HeNeCOn ↔ Gene/Cancer/Tissue...")
hnc_lower = {info["label"].lower(): f"HNC:{uri.split('/')[-1].split('#')[-1]}"
             for uri, info in hnc_classes.items()}
linked = 0
for nid, data in list(G.nodes(data=True)):
    if data.get("node_type") in ("gene", "cancer", "tissue"):
        key = data.get("label", "").lower()
        if key in hnc_lower:
            hnc_nid = hnc_lower[key]
            if G.has_node(hnc_nid) and not G.has_edge(nid, hnc_nid):
                G.add_edge(nid, hnc_nid, relation="mapped_to_ontology",
                           source_db="cross_link")
                linked += 1
print(f"   Cross-links: {linked}")

print(f"\n   ★ FINAL: {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges")

# ══════════════════════════════════════════════════════════════
# STEP 5 — EXPORT
# ══════════════════════════════════════════════════════════════
print("\n[5/5] Exporting...")

# 5a GraphML
gml_path = os.path.join(OUT, "cancer_kg.graphml")
nx.write_graphml(G, gml_path)
print(f"   ✓ GraphML  → {gml_path}")

# 5b CSVs
pd.DataFrame([{"id": n, **d} for n, d in G.nodes(data=True)]).to_csv(
    os.path.join(OUT, "cancer_kg_nodes.csv"), index=False)
pd.DataFrame([{"src": u, "tgt": v, **d} for u, v, d in G.edges(data=True)]).to_csv(
    os.path.join(OUT, "cancer_kg_edges.csv"), index=False)
print(f"   ✓ Nodes/Edges CSVs → {OUT}")

# 5c Stats
ntypes = Counter(d.get("node_type","?") for _,d in G.nodes(data=True))
erels  = Counter(d.get("relation","?")  for _,_,d in G.edges(data=True))
top_g  = sorted([(n, G.degree(n)) for n,d in G.nodes(data=True)
                  if d.get("node_type")=="gene"],
                key=lambda x:x[1], reverse=True)[:20]
stats_txt = f"""
CANCER KNOWLEDGE GRAPH — STATISTICS
=====================================
Total Nodes : {G.number_of_nodes():,}
Total Edges : {G.number_of_edges():,}

Node types:
{chr(10).join(f'  {k:22s}: {v:,}' for k,v in ntypes.most_common())}

Edge relation types:
{chr(10).join(f'  {k:28s}: {v:,}' for k,v in erels.most_common())}

Top 20 most-connected genes:
{chr(10).join(f'  {n.replace("GENE:",""):18s}: degree {d}' for n,d in top_g)}

Source sizes:
  CancerMine rows : {len(cm):,}
  COSMIC CMC rows : {len(cmc):,}
  COSMIC CGC rows : {len(cgc):,}
  HeNeCOn classes : {len(hnc_classes):,}
"""
with open(os.path.join(OUT,"cancer_kg_stats.txt"),"w") as f:
    f.write(stats_txt)
print(stats_txt)

# 5d Interactive HTML (PyVis)
try:
    from pyvis.network import Network

    top200 = [n for n,_ in sorted(G.degree(),key=lambda x:x[1],reverse=True)[:200]]
    sub    = G.subgraph(top200).copy()

    net = Network(height="820px", width="100%", bgcolor="#1a1a2e",
                  font_color="white", directed=True, notebook=False)
    net.set_options("""{
      "nodes":{"borderWidth":1,"shadow":true},
      "edges":{"arrows":{"to":{"enabled":true,"scaleFactor":0.4}},
               "smooth":{"type":"dynamic"}},
      "physics":{"stabilization":{"iterations":200},
                 "barnesHut":{"gravitationalConstant":-8000,
                              "springConstant":0.001,"damping":0.9}},
      "interaction":{"hover":true,"tooltipDelay":100}
    }""")

    REL_CLR = {"driver":"#FF6B6B","oncogene":"#FFD93D",
               "tumor_suppressor":"#6BCB77","mutated_in":"#4ECDC4",
               "has_mutation":"#C77DFF","subclassof":"#ADB5BD",
               "mapped_to_ontology":"#F8961E"}

    for nid, d in sub.nodes(data=True):
        tip = (f"<b>{d.get('label',nid)}</b><br>"
               f"Type: {d.get('node_type','')}<br>"
               f"Degree: {G.degree(nid)}")
        if d.get("definition"):
            tip += f"<br><small>{str(d['definition'])[:100]}</small>"
        net.add_node(nid, label=d.get("label",nid),
                     color=d.get("color","#888"),
                     size=d.get("size",10), title=tip)

    for u, v, d in sub.edges(data=True):
        rel = d.get("relation","")
        net.add_edge(u, v,
                     color=REL_CLR.get(rel.lower(),"#444"),
                     width=max(1,min(5,d.get("weight",0.5)*4)),
                     title=f"relation: {rel}")

    html_path = os.path.join(OUT,"cancer_kg.html")
    net.save_graph(html_path)

    legend = """<div style='position:fixed;top:10px;left:10px;background:#2d2d44;
padding:12px;border-radius:8px;font-size:13px;color:white;z-index:999;line-height:1.9'>
<b>Node types</b><br>
<span style='color:#4C9BE8'>&#9679;</span> Gene &nbsp;
<span style='color:#E8724C'>&#9679;</span> Cancer<br>
<span style='color:#52B788'>&#9679;</span> Tissue &nbsp;
<span style='color:#F0C040'>&#9679;</span> Mutation<br>
<span style='color:#8E6BBF'>&#9679;</span> HNC Concept<br><br>
<b>Edge colours</b><br>
<span style='color:#FF6B6B'>&#9472;</span> driver<br>
<span style='color:#FFD93D'>&#9472;</span> oncogene<br>
<span style='color:#6BCB77'>&#9472;</span> tumor suppressor<br>
<span style='color:#4ECDC4'>&#9472;</span> mutated in tissue<br>
<span style='color:#C77DFF'>&#9472;</span> has mutation<br>
<span style='color:#F8961E'>&#9472;</span> ontology link
</div>"""
    with open(html_path,"r",encoding="utf-8") as f: html = f.read()
    html = html.replace("<body>","<body>"+legend, 1)
    with open(html_path,"w",encoding="utf-8") as f: f.write(html)
    print(f"   ✓ HTML viz → {html_path}")
    print("     Open cancer_kg.html in Chrome to explore!")

except ImportError:
    print("   ⚠ pyvis missing: pip install pyvis")
except Exception as e:
    print(f"   ⚠ PyVis error: {e}")

# 5e Static PNG
try:
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    top80  = [n for n,_ in sorted(G.degree(),key=lambda x:x[1],reverse=True)[:80]]
    sub80  = G.subgraph(top80).copy()
    pos    = nx.spring_layout(sub80, k=2.8, seed=42)
    ncols  = [sub80.nodes[n].get("color","#888") for n in sub80]
    nsizes = [sub80.nodes[n].get("size",10)*40   for n in sub80]

    fig, ax = plt.subplots(figsize=(22,17))
    fig.patch.set_facecolor("#1a1a2e"); ax.set_facecolor("#1a1a2e")
    nx.draw_networkx_edges(sub80, pos, ax=ax, alpha=0.2,
                           edge_color="#666", arrows=True, arrowsize=10,
                           connectionstyle="arc3,rad=0.08")
    nx.draw_networkx_nodes(sub80, pos, ax=ax,
                           node_color=ncols, node_size=nsizes, alpha=0.92)
    nx.draw_networkx_labels(sub80, pos,
                            {n: sub80.nodes[n].get("label",n)[:14] for n in sub80},
                            ax=ax, font_size=6.5, font_color="white")
    patches = [mpatches.Patch(color=c,label=t) for t,c in COLORS.items()]
    ax.legend(handles=patches, loc="upper left",
              facecolor="#2d2d44", edgecolor="none",
              labelcolor="white", fontsize=11)
    ax.set_title("Cancer Knowledge Graph — Top 80 Nodes",
                 color="white", fontsize=15, pad=14)
    ax.axis("off"); plt.tight_layout()
    img_path = os.path.join(OUT,"cancer_kg_plot.png")
    plt.savefig(img_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"   ✓ PNG plot → {img_path}")
except Exception as e:
    print(f"   ⚠ matplotlib error: {e}")

print("\n══════════════════════════════════════════════════")
print("  ✅  Knowledge Graph build COMPLETE!")
print(f"  📂  All outputs: {OUT}")
print("  🌐  Open cancer_kg.html in Chrome to explore")
print("══════════════════════════════════════════════════\n")