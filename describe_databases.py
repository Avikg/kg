"""
describe_databases.py
══════════════════════════════════════════════════════════════════
Comprehensive profiler and descriptor for all 3 cancer databases:
  1. CancerMine  (cancermine_collated.tsv)
  2. COSMIC CMC  (CancerMutationCensus_AllData_v103_GRCh37.tsv)
  3. COSMIC CGC  (Cosmic_MutantCensus_v103_GRCh37.tsv)
  4. HeNeCOn     (HeNeCOn.owl)

Outputs:
  db_profiles/
    01_cancermine_profile.html
    02_cosmic_cmc_profile.html
    03_cosmic_cgc_profile.html
    04_hencon_profile.html
    00_overview_dashboard.html    ← start here

Run:
    pip install pandas matplotlib numpy rdflib
    python describe_databases.py
"""

import os, json, warnings
import pandas as pd
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter
from io import BytesIO
import base64
warnings.filterwarnings("ignore")

BASE    = os.path.dirname(os.path.abspath(__file__))
CM_DIR  = os.path.join(BASE, "cancermine")
HNC_DIR = os.path.join(BASE, "hencon")
CSM_DIR = os.path.join(BASE, "cosmic")
OUT     = os.path.join(BASE, "db_profiles")
os.makedirs(OUT, exist_ok=True)

# ── helpers ───────────────────────────────────────────────────
def fig_to_b64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def find_file(directory, keyword, ext=".tsv"):
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(ext) and keyword.lower() in f.lower():
                return os.path.join(root, f)
    return None

DARK = "#0f0f1a"
PANEL= "#1a1a2e"
CARD = "#12122a"
BORDER="#2d2d4e"
TEXT = "#e0e0e0"
MUTED= "#888"
ACC  = "#a0c4ff"
COLORS_DB = {
    "CancerMine": "#4C9BE8",
    "COSMIC CMC": "#E8724C",
    "COSMIC CGC": "#52B788",
    "HeNeCOn":    "#8E6BBF",
}
ROLE_COLORS = {
    "Driver":          "#FF6B6B",
    "Oncogene":        "#FFD93D",
    "Tumor_Suppressor":"#6BCB77",
}

def html_shell(title, db_color, content, db_name):
    nav_items = [
        ("00_overview_dashboard.html", "🏠 Overview"),
        ("01_cancermine_profile.html",  "🔵 CancerMine"),
        ("02_cosmic_cmc_profile.html",  "🟠 COSMIC CMC"),
        ("03_cosmic_cgc_profile.html",  "🟢 COSMIC CGC"),
        ("04_hencon_profile.html",      "🟣 HeNeCOn"),
    ]
    nav_html = "".join(
        f'<a href="{f}" style="padding:6px 14px;border-radius:6px;font-size:12px;'
        f'text-decoration:none;color:{"#fff" if db_name in f else "#aaa"};'
        f'background:{""+db_color+"33" if db_name in f else "transparent"};'
        f'border:1px solid {""+db_color if db_name in f else "transparent"}">{lbl}</a>'
        for f, lbl in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:{DARK};color:{TEXT};min-height:100vh}}
nav{{background:{PANEL};border-bottom:1px solid {BORDER};padding:10px 24px;
     display:flex;align-items:center;gap:8px;flex-wrap:wrap;position:sticky;top:0;z-index:100}}
nav .logo{{font-size:14px;font-weight:700;color:{ACC};margin-right:12px;letter-spacing:.04em}}
.page{{max-width:1200px;margin:0 auto;padding:28px 24px}}
h1{{font-size:24px;font-weight:600;color:{ACC};margin-bottom:4px}}
.subtitle{{font-size:13px;color:{MUTED};margin-bottom:28px}}
.section{{margin-bottom:36px}}
.section-title{{font-size:13px;font-weight:600;color:{MUTED};text-transform:uppercase;
                letter-spacing:.07em;margin-bottom:14px;padding-bottom:6px;
                border-bottom:1px solid {BORDER}}}
.cards{{display:grid;gap:12px}}
.cards-2{{grid-template-columns:repeat(2,1fr)}}
.cards-3{{grid-template-columns:repeat(3,1fr)}}
.cards-4{{grid-template-columns:repeat(4,1fr)}}
.card{{background:{CARD};border:1px solid {BORDER};border-radius:10px;padding:16px 20px}}
.metric-num{{font-size:28px;font-weight:700;color:{db_color}}}
.metric-lbl{{font-size:11px;color:{MUTED};margin-top:3px}}
.metric-sub{{font-size:12px;color:#aaa;margin-top:5px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:8px 12px;background:{PANEL};color:{MUTED};
    font-weight:600;border-bottom:1px solid {BORDER};white-space:nowrap}}
td{{padding:7px 12px;border-bottom:1px solid {BORDER}22;color:{TEXT};vertical-align:top}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:{PANEL}88}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;margin:1px}}
.bar-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.bar-label{{font-size:12px;min-width:140px;color:{TEXT}}}
.bar-track{{flex:1;height:8px;background:{BORDER};border-radius:4px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:4px}}
.bar-val{{font-size:11px;color:{MUTED};min-width:50px;text-align:right}}
.pill{{display:inline-block;padding:3px 10px;border-radius:12px;
       font-size:11px;background:{db_color}22;color:{db_color};
       border:1px solid {db_color}55;margin:2px}}
img.chart{{width:100%;border-radius:8px;border:1px solid {BORDER}}}
.desc{{font-size:13px;color:#ccc;line-height:1.8;padding:14px 16px;
       background:{CARD};border-radius:8px;border-left:3px solid {db_color}}}
code{{font-family:'Cascadia Code','Consolas',monospace;font-size:12px;
      background:{PANEL};padding:10px 14px;border-radius:8px;display:block;
      border:1px solid {BORDER};overflow-x:auto;line-height:1.8;color:#ccd6f6}}
</style>
</head><body>
<nav>
  <span class="logo">🧬 Cancer DB Profiler</span>
  {nav_html}
</nav>
<div class="page">
{content}
</div></body></html>"""


# ══════════════════════════════════════════════════════════════
# 1. CANCERMINE
# ══════════════════════════════════════════════════════════════
print("\n[1/4] Profiling CancerMine...")
cm_path = os.path.join(CM_DIR, "cancermine_collated.tsv")
cm = pd.read_csv(cm_path, sep="\t")

GENE_COL   = next(c for c in ["gene_normalized","gene_hugo","gene_symbol"] if c in cm.columns)
CANCER_COL = next(c for c in ["cancer_normalized","cancer_type","cancer_name"] if c in cm.columns)
ROLE_COL   = next(c for c in ["role","gene_role"] if c in cm.columns)
CITE_COL   = next(c for c in ["citation_count","citations","count"] if c in cm.columns)

role_counts  = cm[ROLE_COL].value_counts()
top_genes    = cm.groupby(GENE_COL)[CITE_COL].sum().sort_values(ascending=False).head(20)
top_cancers  = cm.groupby(CANCER_COL)[CITE_COL].sum().sort_values(ascending=False).head(15)
gene_roles   = cm.groupby(GENE_COL)[ROLE_COL].nunique()
multi_role   = gene_roles[gene_roles > 1]
cite_dist    = cm[CITE_COL].describe()

# Chart 1 — role distribution pie
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
fig.patch.set_facecolor(DARK)
colors_role = [ROLE_COLORS.get(r, "#888") for r in role_counts.index]
axes[0].pie(role_counts.values, labels=role_counts.index, colors=colors_role,
            autopct='%1.1f%%', startangle=90,
            textprops={'color': TEXT, 'fontsize': 10})
axes[0].set_title("Gene Role Distribution", color=TEXT, fontsize=11, pad=10)
axes[0].set_facecolor(DARK)

# Chart 2 — top genes bar
axes[1].set_facecolor(DARK)
axes[1].barh(top_genes.index[::-1], top_genes.values[::-1], color="#4C9BE8", alpha=0.85)
axes[1].set_xlabel("Total Citations", color=MUTED, fontsize=9)
axes[1].set_title("Top 20 Genes by Citations", color=TEXT, fontsize=11, pad=10)
axes[1].tick_params(colors=TEXT, labelsize=8)
for spine in axes[1].spines.values(): spine.set_edgecolor(BORDER)

# Chart 3 — citation distribution histogram
axes[2].set_facecolor(DARK)
axes[2].hist(cm[CITE_COL].clip(upper=200), bins=40, color="#4C9BE8", alpha=0.8, edgecolor=DARK)
axes[2].set_xlabel("Citation Count (capped at 200)", color=MUTED, fontsize=9)
axes[2].set_ylabel("Number of gene-cancer pairs", color=MUTED, fontsize=9)
axes[2].set_title("Citation Count Distribution", color=TEXT, fontsize=11, pad=10)
axes[2].tick_params(colors=TEXT, labelsize=8)
for spine in axes[2].spines.values(): spine.set_edgecolor(BORDER)

plt.tight_layout()
cm_chart1 = fig_to_b64(fig)

# Chart 2 — top cancers
fig2, ax = plt.subplots(figsize=(12, 5))
fig2.patch.set_facecolor(DARK); ax.set_facecolor(DARK)
ax.barh(top_cancers.index[::-1], top_cancers.values[::-1], color="#E8724C", alpha=0.85)
ax.set_xlabel("Total Citations", color=MUTED, fontsize=9)
ax.set_title("Top 15 Cancer Types by Total Citations", color=TEXT, fontsize=12, pad=10)
ax.tick_params(colors=TEXT, labelsize=9)
for spine in ax.spines.values(): spine.set_edgecolor(BORDER)
plt.tight_layout()
cm_chart2 = fig_to_b64(fig2)

# Column table
cm_col_info = [
    ("matching_id",        "str",   "Unique ID linking to sentences file"),
    ("role",               "enum",  "Driver / Oncogene / Tumor_Suppressor"),
    ("cancer_id",          "str",   "Disease Ontology ID (DOID:xxxx)"),
    (CANCER_COL,           "str",   "Normalised cancer type name"),
    ("gene_hugo_id",       "int",   "HUGO Gene Nomenclature Committee ID"),
    ("gene_entrez_id",     "int",   "NCBI Entrez Gene identifier"),
    (GENE_COL,             "str",   "HUGO gene symbol (e.g. TP53, KRAS)"),
    (CITE_COL,             "int",   "Papers supporting this gene–cancer–role triple"),
]

col_rows = "".join(f"<tr><td><code style='background:none;border:none;padding:0;display:inline'>{c}</code></td>"
                   f"<td><span class='tag' style='background:#4C9BE822;color:#4C9BE8'>{t}</span></td>"
                   f"<td>{d}</td></tr>" for c, t, d in cm_col_info)

top_gene_rows = "".join(
    f"<div class='bar-row'><span class='bar-label'>{g}</span>"
    f"<div class='bar-track'><div class='bar-fill' style='width:{v/top_genes.max()*100:.0f}%;background:#4C9BE8'></div></div>"
    f"<span class='bar-val'>{v:,}</span></div>"
    for g, v in top_genes.items()
)

def role_color(r):
    return ROLE_COLORS.get(r, "#888")

role_rows = "".join(
    f"<div class='bar-row'><span class='bar-label'>{r}</span>"
    f"<div class='bar-track'><div class='bar-fill' style='width:{v/role_counts.max()*100:.0f}%;background:{role_color(r)}'></div></div>"
    f"<span class='bar-val'>{v:,}</span></div>"
    for r, v in role_counts.items()
)

cm_content = f"""
<h1>🔵 CancerMine</h1>
<p class="subtitle">Literature-mined knowledgebase of cancer gene roles — drivers, oncogenes, and tumor suppressors</p>

<div class="section">
<div class="desc">
CancerMine is an automatically updated database built by NLP text-mining of PubMed abstracts and PubMed Central full-text articles.
It uses the <b>Kindred</b> machine learning framework to identify sentences that describe a gene acting as a
<em>driver</em>, <em>oncogene</em>, or <em>tumor suppressor</em> in a specific cancer type.
Each gene–cancer–role triple is scored by the number of independent publications supporting it,
giving a citation-weighted importance score. The database contains <b>{len(cm):,} unique triples</b>
spanning <b>{cm[GENE_COL].nunique():,} genes</b> and <b>{cm[CANCER_COL].nunique():,} cancer types</b>.
</div>
</div>

<div class="section">
<div class="section-title">Key Metrics</div>
<div class="cards cards-4">
  <div class="card"><div class="metric-num">{len(cm):,}</div><div class="metric-lbl">Gene–cancer–role triples</div></div>
  <div class="card"><div class="metric-num">{cm[GENE_COL].nunique():,}</div><div class="metric-lbl">Unique genes</div></div>
  <div class="card"><div class="metric-num">{cm[CANCER_COL].nunique():,}</div><div class="metric-lbl">Cancer types</div></div>
  <div class="card"><div class="metric-num">{int(cm[CITE_COL].sum()):,}</div><div class="metric-lbl">Total citations</div></div>
  <div class="card"><div class="metric-num">{role_counts.get('Driver',0):,}</div><div class="metric-lbl">Driver associations</div><div class="metric-sub" style="color:#FF6B6B">●</div></div>
  <div class="card"><div class="metric-num">{role_counts.get('Oncogene',0):,}</div><div class="metric-lbl">Oncogene associations</div><div class="metric-sub" style="color:#FFD93D">●</div></div>
  <div class="card"><div class="metric-num">{role_counts.get('Tumor_Suppressor',0):,}</div><div class="metric-lbl">Tumor suppressor associations</div><div class="metric-sub" style="color:#6BCB77">●</div></div>
  <div class="card"><div class="metric-num">{len(multi_role):,}</div><div class="metric-lbl">Genes with multiple roles</div><div class="metric-sub">context-dependent</div></div>
</div>
</div>

<div class="section">
<div class="section-title">Distribution Charts</div>
<img class="chart" src="data:image/png;base64,{cm_chart1}">
</div>

<div class="section">
<div class="section-title">Top 15 Cancer Types by Citation Volume</div>
<img class="chart" src="data:image/png;base64,{cm_chart2}">
</div>

<div class="section">
<div class="cards cards-2">
  <div class="card">
    <div class="section-title">Role Breakdown</div>
    {role_rows}
  </div>
  <div class="card">
    <div class="section-title">Citation Stats</div>
    <div class="bar-row"><span class="bar-label">Mean citations/triple</span><span class="bar-val">{cite_dist['mean']:.1f}</span></div>
    <div class="bar-row"><span class="bar-label">Median</span><span class="bar-val">{cite_dist['50%']:.0f}</span></div>
    <div class="bar-row"><span class="bar-label">Max</span><span class="bar-val">{int(cite_dist['max']):,}</span></div>
    <div class="bar-row"><span class="bar-label">≥ 10 citations</span><span class="bar-val">{(cm[CITE_COL]>=10).sum():,}</span></div>
    <div class="bar-row"><span class="bar-label">≥ 50 citations</span><span class="bar-val">{(cm[CITE_COL]>=50).sum():,}</span></div>
    <div class="bar-row"><span class="bar-label">≥ 100 citations</span><span class="bar-val">{(cm[CITE_COL]>=100).sum():,}</span></div>
  </div>
</div>
</div>

<div class="section">
<div class="section-title">Top 20 Genes by Total Citations</div>
<div class="card">{top_gene_rows}</div>
</div>

<div class="section">
<div class="section-title">Column Schema</div>
<div class="card" style="padding:0;overflow:hidden">
<table><tr><th>Column</th><th>Type</th><th>Description</th></tr>
{col_rows}
</table></div>
</div>

<div class="section">
<div class="section-title">How to Load</div>
<code>import pandas as pd
import numpy as np

cm = pd.read_csv("cancermine/cancermine_collated.tsv", sep="\\t")
print(cm.shape)        # ({len(cm)}, {len(cm.columns)})
print(cm.columns.tolist())

# Top driver genes for a cancer type
hnc = cm[cm["cancer_normalized"].str.contains("head and neck", case=False)]
top = hnc[hnc["role"]=="Driver"].sort_values("citation_count", ascending=False)
print(top[["gene_normalized","cancer_normalized","citation_count"]].head(10))

# Normalised importance score (log10, per-cancer normalised)
cm["importance"] = np.log10(cm["citation_count"] + 1)
mx = cm.groupby("cancer_normalized")["importance"].transform("max")
cm["score"] = cm["importance"] / (mx + 1e-9)</code>
</div>

<div class="section">
<div class="section-title">Access &amp; Licence</div>
<div class="cards cards-2">
  <div class="card">
    <div class="metric-lbl">Licence</div><div style="font-size:16px;color:#6BCB77;margin:6px 0">CC0 — Public Domain</div>
    <div style="font-size:12px;color:#aaa">No restrictions. Free for any use including commercial.</div>
  </div>
  <div class="card">
    <div class="metric-lbl">Download</div>
    <div style="margin-top:6px">
      <span class="pill">zenodo.org/records/16849846</span><br>
      <span class="pill">DOI: 10.5281/zenodo.1156241</span><br>
      <span class="pill" style="margin-top:4px">python -m zenodo_get 10.5281/zenodo.1156241</span>
    </div>
  </div>
</div>
</div>
"""

with open(os.path.join(OUT,"01_cancermine_profile.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("CancerMine Profile","#4C9BE8",cm_content,"cancermine"))
print("   ✓ 01_cancermine_profile.html")


# ══════════════════════════════════════════════════════════════
# 2. COSMIC CMC
# ══════════════════════════════════════════════════════════════
print("\n[2/4] Profiling COSMIC Cancer Mutation Census...")
cmc_path = find_file(CSM_DIR, "MutationCensus")
cmc = pd.DataFrame()
if cmc_path:
    with open(cmc_path,"r",encoding="utf-8",errors="replace") as fh:
        hdr = fh.readline().strip().split("\t")
    want = {
        "gene":   ["GENE_SYMBOL","Gene name","GENE_NAME"],
        "site":   ["PRIMARY_SITE","Primary Site","PRIMARY_TISSUE"],
        "mut_id": ["GENOMIC_MUTATION_ID","COSMIC_MUTATION_ID"],
        "fathmm": ["FATHMM_PREDICTION","FATHMM prediction"],
        "tier":   ["TIER","Tier"],
        "hist":   ["HISTOLOGY","Primary Histology","CANCER_TYPE"],
    }
    use_cols, col_map = [], {}
    for role, cands in want.items():
        found = next((c for c in cands if c in hdr), None)
        if found: use_cols.append(found); col_map[found] = role
    try:
        cmc = pd.read_csv(cmc_path, sep="\t", usecols=use_cols,
                          nrows=300_000, low_memory=False,
                          encoding="utf-8", on_bad_lines="skip")
    except TypeError:
        cmc = pd.read_csv(cmc_path, sep="\t", usecols=use_cols,
                          nrows=300_000, low_memory=False, encoding="utf-8")
    cmc.rename(columns=col_map, inplace=True)

if not cmc.empty:
    top_genes_cmc  = cmc["gene"].value_counts().head(20) if "gene" in cmc.columns else pd.Series()
    top_sites_cmc  = cmc["site"].value_counts().head(15) if "site" in cmc.columns else pd.Series()
    top_hist_cmc   = cmc["hist"].value_counts().head(10) if "hist" in cmc.columns else pd.Series()
    fathmm_counts  = cmc["fathmm"].value_counts() if "fathmm" in cmc.columns else pd.Series()
    tier_counts    = cmc["tier"].value_counts().sort_index() if "tier" in cmc.columns else pd.Series()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor(DARK)

    axes[0].set_facecolor(DARK)
    axes[0].barh(top_genes_cmc.index[::-1], top_genes_cmc.values[::-1], color="#E8724C", alpha=0.85)
    axes[0].set_title("Top 20 Mutated Genes", color=TEXT, fontsize=11, pad=8)
    axes[0].tick_params(colors=TEXT, labelsize=8)
    for s in axes[0].spines.values(): s.set_edgecolor(BORDER)

    axes[1].set_facecolor(DARK)
    axes[1].barh(top_sites_cmc.index[::-1], top_sites_cmc.values[::-1], color="#52B788", alpha=0.85)
    axes[1].set_title("Top 15 Primary Sites", color=TEXT, fontsize=11, pad=8)
    axes[1].tick_params(colors=TEXT, labelsize=8)
    for s in axes[1].spines.values(): s.set_edgecolor(BORDER)

    if not fathmm_counts.empty:
        c2 = ["#FF6B6B" if "PATH" in str(x).upper() else "#4C9BE8" for x in fathmm_counts.index]
        axes[2].pie(fathmm_counts.values, labels=fathmm_counts.index, colors=c2,
                    autopct='%1.1f%%', textprops={"color":TEXT,"fontsize":10}, startangle=90)
        axes[2].set_title("FATHMM Prediction", color=TEXT, fontsize=11, pad=8)
    axes[2].set_facecolor(DARK)
    plt.tight_layout()
    cmc_chart1 = fig_to_b64(fig)

    fig2, ax = plt.subplots(figsize=(12, 4.5))
    fig2.patch.set_facecolor(DARK); ax.set_facecolor(DARK)
    ax.barh(top_hist_cmc.index[::-1], top_hist_cmc.values[::-1], color="#F0C040", alpha=0.85)
    ax.set_title("Top 10 Histology Types", color=TEXT, fontsize=12, pad=8)
    ax.tick_params(colors=TEXT, labelsize=9)
    for s in ax.spines.values(): s.set_edgecolor(BORDER)
    plt.tight_layout()
    cmc_chart2 = fig_to_b64(fig2)

    cmc_col_info = [
        ("GENE_SYMBOL",         "str",   "HGNC gene symbol"),
        ("PRIMARY_SITE",        "str",   "Tissue / organ of origin"),
        ("HISTOLOGY",           "str",   "Histological classification"),
        ("GENOMIC_MUTATION_ID", "str",   "Stable COSV identifier (e.g. COSV51765119)"),
        ("FATHMM_PREDICTION",   "enum",  "PATHOGENIC or NEUTRAL — functional impact"),
        ("TIER",                "int",   "CGC confidence tier: 1 = high confidence"),
    ]
    col_rows2 = "".join(f"<tr><td><code style='background:none;border:none;padding:0;display:inline'>{c}</code></td>"
                        f"<td><span class='tag' style='background:#E8724C22;color:#E8724C'>{t}</span></td>"
                        f"<td>{d}</td></tr>" for c, t, d in cmc_col_info)

    top_gene_bars = "".join(
        f"<div class='bar-row'><span class='bar-label'>{g}</span>"
        f"<div class='bar-track'><div class='bar-fill' style='width:{v/top_genes_cmc.max()*100:.0f}%;background:#E8724C'></div></div>"
        f"<span class='bar-val'>{v:,}</span></div>"
        for g, v in top_genes_cmc.items()
    )
    top_site_bars = "".join(
        f"<div class='bar-row'><span class='bar-label'>{s}</span>"
        f"<div class='bar-track'><div class='bar-fill' style='width:{v/top_sites_cmc.max()*100:.0f}%;background:#52B788'></div></div>"
        f"<span class='bar-val'>{v:,}</span></div>"
        for s, v in top_sites_cmc.items()
    )
    pathogenic_count = fathmm_counts.get("PATHOGENIC", fathmm_counts.get("Pathogenic", 0))
    tier1_count = tier_counts.get(1, tier_counts.get("1", 0))

    cmc_content = f"""
<h1>🟠 COSMIC Cancer Mutation Census (CMC)</h1>
<p class="subtitle">Comprehensive somatic mutation catalogue with significance scoring — v103, GRCh37</p>

<div class="section">
<div class="desc">
The <b>Cancer Mutation Census (CMC)</b> is COSMIC's flagship dataset containing all somatic coding mutations
detected across cancer samples worldwide. Each mutation is annotated with its gene, tissue of origin,
histological classification, and pathogenicity prediction using <b>FATHMM</b> (Functional Analysis through
Hidden Markov Models). Mutations in <b>Tier 1</b> Cancer Gene Census genes represent the highest-confidence
cancer drivers. This dataset integrates data from systematic genome screens, clinical sequencing projects,
and over <b>29,000 curated publications</b>. Loaded here: first 300,000 rows.
</div>
</div>

<div class="section">
<div class="section-title">Key Metrics (300k sample)</div>
<div class="cards cards-4">
  <div class="card"><div class="metric-num">{len(cmc):,}</div><div class="metric-lbl">Mutations loaded</div><div class="metric-sub">of 38M+ total</div></div>
  <div class="card"><div class="metric-num">{cmc["gene"].nunique() if "gene" in cmc.columns else "—":,}</div><div class="metric-lbl">Unique genes mutated</div></div>
  <div class="card"><div class="metric-num">{cmc["site"].nunique() if "site" in cmc.columns else "—"}</div><div class="metric-lbl">Primary sites (tissues)</div></div>
  <div class="card"><div class="metric-num">{int(pathogenic_count):,}</div><div class="metric-lbl">PATHOGENIC predictions</div><div class="metric-sub" style="color:#FF6B6B">FATHMM</div></div>
  <div class="card"><div class="metric-num">{cmc["hist"].nunique() if "hist" in cmc.columns else "—"}</div><div class="metric-lbl">Histology types</div></div>
  <div class="card"><div class="metric-num">{int(tier1_count):,}</div><div class="metric-lbl">Tier 1 CGC mutations</div><div class="metric-sub">highest confidence</div></div>
  <div class="card"><div class="metric-num">v103</div><div class="metric-lbl">COSMIC version</div></div>
  <div class="card"><div class="metric-num">GRCh37</div><div class="metric-lbl">Genome build</div></div>
</div>
</div>

<div class="section">
<div class="section-title">Distribution Charts</div>
<img class="chart" src="data:image/png;base64,{cmc_chart1}">
</div>

<div class="section">
<div class="section-title">Histology Breakdown</div>
<img class="chart" src="data:image/png;base64,{cmc_chart2}">
</div>

<div class="section">
<div class="cards cards-2">
  <div class="card">
    <div class="section-title">Top 20 Mutated Genes</div>
    {top_gene_bars}
  </div>
  <div class="card">
    <div class="section-title">Top 15 Primary Sites</div>
    {top_site_bars}
  </div>
</div>
</div>

<div class="section">
<div class="section-title">Column Schema</div>
<div class="card" style="padding:0;overflow:hidden">
<table><tr><th>Column</th><th>Type</th><th>Description</th></tr>
{col_rows2}
</table></div>
</div>

<div class="section">
<div class="section-title">How to Load</div>
<code>import pandas as pd

cmc = pd.read_csv(
    "cosmic/CancerMutationCensus_AllData_Tsv_v103_GRCh37/"
    "CancerMutationCensus_AllData_v103_GRCh37.tsv",
    sep="\\t", low_memory=False, nrows=500_000,
    usecols=["GENE_SYMBOL","PRIMARY_SITE","HISTOLOGY",
             "GENOMIC_MUTATION_ID","FATHMM_PREDICTION","TIER"]
)
print(cmc.shape)
print(cmc["FATHMM_PREDICTION"].value_counts())

# Pathogenic mutations in Tier 1 genes
tier1_path = cmc[(cmc["TIER"]==1) & (cmc["FATHMM_PREDICTION"]=="PATHOGENIC")]
print(tier1_path["GENE_SYMBOL"].value_counts().head(10))</code>
</div>

<div class="section">
<div class="section-title">Access &amp; Licence</div>
<div class="cards cards-2">
  <div class="card">
    <div class="metric-lbl">Licence</div>
    <div style="font-size:15px;color:#FFD93D;margin:6px 0">Free for Academic · Commercial via Qiagen</div>
    <div style="font-size:12px;color:#aaa">Register free at cancer.sanger.ac.uk/cosmic/register</div>
  </div>
  <div class="card">
    <div class="metric-lbl">Download</div>
    <div style="margin-top:6px">
      <span class="pill" style="background:#E8724C22;color:#E8724C;border-color:#E8724C55">cancer.sanger.ac.uk/cosmic/download</span><br>
      <span class="pill" style="background:#E8724C22;color:#E8724C;border-color:#E8724C55">pip install gget → gget.cosmic(...)</span>
    </div>
  </div>
</div>
</div>
"""
    with open(os.path.join(OUT,"02_cosmic_cmc_profile.html"),"w",encoding="utf-8") as f:
        f.write(html_shell("COSMIC CMC Profile","#E8724C",cmc_content,"cosmic_cmc"))
    print("   ✓ 02_cosmic_cmc_profile.html")


# ══════════════════════════════════════════════════════════════
# 3. COSMIC CGC (MutantCensus)
# ══════════════════════════════════════════════════════════════
print("\n[3/4] Profiling COSMIC MutantCensus (CGC)...")
cgc_path = find_file(CSM_DIR, "MutantCensus")
cgc = pd.DataFrame()
if cgc_path:
    with open(cgc_path,"r",encoding="utf-8",errors="replace") as fh:
        hdr2 = fh.readline().strip().split("\t")
    want2 = {
        "gene":  ["GENE_SYMBOL","Gene name","GENE_NAME"],
        "site":  ["PRIMARY_SITE","Primary Site"],
        "fathmm":["FATHMM_PREDICTION","FATHMM prediction"],
        "tier":  ["TIER","Tier"],
        "hist":  ["HISTOLOGY","Primary Histology"],
        "mut_type":["MUTATION_DESCRIPTION","Mutation Description","MUTATION_TYPE"],
    }
    use2, map2 = [], {}
    for role, cands in want2.items():
        found = next((c for c in cands if c in hdr2), None)
        if found: use2.append(found); map2[found] = role
    try:
        cgc = pd.read_csv(cgc_path, sep="\t", usecols=use2,
                          nrows=300_000, low_memory=False,
                          encoding="utf-8", on_bad_lines="skip")
    except TypeError:
        cgc = pd.read_csv(cgc_path, sep="\t", usecols=use2,
                          nrows=300_000, low_memory=False, encoding="utf-8")
    cgc.rename(columns=map2, inplace=True)

if not cgc.empty:
    top_g2 = cgc["gene"].value_counts().head(20) if "gene" in cgc.columns else pd.Series()
    top_s2 = cgc["site"].value_counts().head(15) if "site" in cgc.columns else pd.Series()
    mut_types = cgc["mut_type"].value_counts().head(10) if "mut_type" in cgc.columns else pd.Series()
    fat2 = cgc["fathmm"].value_counts() if "fathmm" in cgc.columns else pd.Series()

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.patch.set_facecolor(DARK)

    axes[0].set_facecolor(DARK)
    axes[0].barh(top_g2.index[::-1], top_g2.values[::-1], color="#52B788", alpha=0.85)
    axes[0].set_title("Top 20 Genes", color=TEXT, fontsize=11)
    axes[0].tick_params(colors=TEXT, labelsize=8)
    for s in axes[0].spines.values(): s.set_edgecolor(BORDER)

    axes[1].set_facecolor(DARK)
    axes[1].barh(top_s2.index[::-1], top_s2.values[::-1], color="#4C9BE8", alpha=0.85)
    axes[1].set_title("Top 15 Primary Sites", color=TEXT, fontsize=11)
    axes[1].tick_params(colors=TEXT, labelsize=8)
    for s in axes[1].spines.values(): s.set_edgecolor(BORDER)

    axes[2].set_facecolor(DARK)
    if not mut_types.empty:
        axes[2].barh(mut_types.index[::-1], mut_types.values[::-1], color="#F0C040", alpha=0.85)
        axes[2].set_title("Mutation Types", color=TEXT, fontsize=11)
        axes[2].tick_params(colors=TEXT, labelsize=8)
    for s in axes[2].spines.values(): s.set_edgecolor(BORDER)

    plt.tight_layout()
    cgc_chart = fig_to_b64(fig)

    top_g2_bars = "".join(
        f"<div class='bar-row'><span class='bar-label'>{g}</span>"
        f"<div class='bar-track'><div class='bar-fill' style='width:{v/top_g2.max()*100:.0f}%;background:#52B788'></div></div>"
        f"<span class='bar-val'>{v:,}</span></div>" for g,v in top_g2.items()
    )
    mut_type_bars = "".join(
        f"<div class='bar-row'><span class='bar-label'>{m}</span>"
        f"<div class='bar-track'><div class='bar-fill' style='width:{v/mut_types.max()*100:.0f}%;background:#F0C040'></div></div>"
        f"<span class='bar-val'>{v:,}</span></div>" for m,v in mut_types.items()
    ) if not mut_types.empty else "<p style='color:#888;font-size:12px'>Column not available</p>"

    cgc_content = f"""
<h1>🟢 COSMIC MutantCensus (Cancer Gene Census)</h1>
<p class="subtitle">Significance-scored annotations for all coding mutations — v103, GRCh37</p>

<div class="section">
<div class="desc">
The <b>MutantCensus</b> (also referred to as the Cancer Gene Census export) provides
per-mutation significance scoring combining biological and biochemical evidence from multiple sources.
It maps mutations to <b>Cancer Gene Census (CGC)</b> genes — the 723 genes most confidently implicated
in cancer. Tier 1 genes have the strongest evidence (direct causal role), while Tier 2 have
circumstantial or indirect evidence. Each mutation entry includes the FATHMM functional impact
prediction, primary site, and histological classification.
</div>
</div>

<div class="section">
<div class="section-title">Key Metrics (300k sample)</div>
<div class="cards cards-4">
  <div class="card"><div class="metric-num">{len(cgc):,}</div><div class="metric-lbl">Mutations loaded</div></div>
  <div class="card"><div class="metric-num">{cgc["gene"].nunique() if "gene" in cgc.columns else "—"}</div><div class="metric-lbl">Unique genes</div></div>
  <div class="card"><div class="metric-num">{cgc["site"].nunique() if "site" in cgc.columns else "—"}</div><div class="metric-lbl">Primary sites</div></div>
  <div class="card"><div class="metric-num">{cgc["mut_type"].nunique() if "mut_type" in cgc.columns else "—"}</div><div class="metric-lbl">Mutation types</div></div>
</div>
</div>

<div class="section">
<div class="section-title">Distribution Charts</div>
<img class="chart" src="data:image/png;base64,{cgc_chart}">
</div>

<div class="section">
<div class="cards cards-2">
  <div class="card">
    <div class="section-title">Top 20 Genes</div>
    {top_g2_bars}
  </div>
  <div class="card">
    <div class="section-title">Mutation Types</div>
    {mut_type_bars}
  </div>
</div>
</div>

<div class="section">
<div class="section-title">How to Load</div>
<code>import pandas as pd

cgc = pd.read_csv(
    "cosmic/Cosmic_MutantCensus_Tsv_v103_GRCh37/"
    "Cosmic_MutantCensus_v103_GRCh37.tsv",
    sep="\\t", low_memory=False, nrows=300_000,
    usecols=["GENE_SYMBOL","PRIMARY_SITE","HISTOLOGY",
             "MUTATION_DESCRIPTION","FATHMM_PREDICTION","TIER"]
)
# Mutation type distribution
print(cgc["MUTATION_DESCRIPTION"].value_counts().head(10))

# Tier 1 genes only
tier1 = cgc[cgc["TIER"] == 1]["GENE_SYMBOL"].unique()
print(f"Tier 1 CGC genes in sample: {{len(tier1)}}")</code>
</div>
"""
    with open(os.path.join(OUT,"03_cosmic_cgc_profile.html"),"w",encoding="utf-8") as f:
        f.write(html_shell("COSMIC CGC Profile","#52B788",cgc_content,"cosmic_cgc"))
    print("   ✓ 03_cosmic_cgc_profile.html")


# ══════════════════════════════════════════════════════════════
# 4. HENECON OWL
# ══════════════════════════════════════════════════════════════
print("\n[4/4] Profiling HeNeCOn OWL...")
owl_path = find_file(HNC_DIR,"",ext=".owl")
hnc_classes, hnc_sc_edges, hnc_obj_props = {}, [], []
domain_counts = Counter()

if owl_path:
    from rdflib import Graph as RDFGraph, RDFS, OWL, RDF, Namespace
    g_owl = RDFGraph()
    g_owl.parse(owl_path)

    for s,_,_ in g_owl.triples((None, RDF.type, OWL.Class)):
        label = g_owl.value(s, RDFS.label)
        defn  = g_owl.value(s, RDFS.comment)
        if label:
            hnc_classes[str(s)] = {"label":str(label),"defn":str(defn) if defn else ""}
            # infer domain from URI fragment
            frag = str(s).split("/")[-1].split("#")[-1].lower()
            if any(x in frag for x in ["treat","therap","chemo","radio","surg"]):
                domain_counts["Treatment"] += 1
            elif any(x in frag for x in ["stage","tnm","clin"]):
                domain_counts["Staging"] += 1
            elif any(x in frag for x in ["hist","morph","type","carcin"]):
                domain_counts["Histology"] += 1
            elif any(x in frag for x in ["anat","site","region","neck","head","oral","laryn","phary"]):
                domain_counts["Anatomy"] += 1
            elif any(x in frag for x in ["risk","factor","tobacco","hpv","alco"]):
                domain_counts["Risk Factor"] += 1
            else:
                domain_counts["Other"] += 1

    for s,_,o in g_owl.triples((None, RDFS.subClassOf, None)):
        sl = hnc_classes.get(str(s),{}).get("label")
        ol = hnc_classes.get(str(o),{}).get("label")
        if sl and ol: hnc_sc_edges.append((sl,ol))

    for s,_,_ in g_owl.triples((None, RDF.type, OWL.ObjectProperty)):
        lbl = g_owl.value(s, RDFS.label)
        if lbl: hnc_obj_props.append(str(lbl))

    # Build a class label table
    classes_sample = list(hnc_classes.values())[:200]

# Ontology structure chart
if hnc_classes:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor(DARK)

    # Domain pie
    d_labels = list(domain_counts.keys())
    d_values = list(domain_counts.values())
    d_colors = ["#4C9BE8","#E8724C","#52B788","#F0C040","#8E6BBF","#FF6B6B"]
    axes[0].pie(d_values, labels=d_labels, colors=d_colors[:len(d_labels)],
                autopct='%1.1f%%', startangle=90,
                textprops={"color":TEXT,"fontsize":10})
    axes[0].set_title("Class Domain Distribution", color=TEXT, fontsize=11, pad=8)
    axes[0].set_facecolor(DARK)

    # SubClass edge fan chart (class depth simulation)
    # Count how many children each class has
    child_counts = Counter(o for _,o in hnc_sc_edges)
    top_parents  = sorted(child_counts.items(), key=lambda x:x[1], reverse=True)[:15]
    axes[1].set_facecolor(DARK)
    axes[1].barh([x[0][:25] for x in top_parents][::-1],
                 [x[1] for x in top_parents][::-1], color="#8E6BBF", alpha=0.85)
    axes[1].set_title("Top 15 Parent Classes (by children)", color=TEXT, fontsize=11, pad=8)
    axes[1].tick_params(colors=TEXT, labelsize=8)
    for s in axes[1].spines.values(): s.set_edgecolor(BORDER)

    plt.tight_layout()
    hnc_chart = fig_to_b64(fig)

    class_rows = "".join(
        f"<tr><td style='color:#8E6BBF'>{c['label']}</td>"
        f"<td style='font-size:11px;color:#aaa'>{c['defn'][:120] if c['defn'] else '—'}</td></tr>"
        for c in classes_sample
    )
    prop_pills = "".join(f"<span class='pill'>{p}</span>" for p in hnc_obj_props[:30])

    hnc_content = f"""
<h1>🟣 HeNeCOn — Head and Neck Cancer Ontology</h1>
<p class="subtitle">OWL ontology providing a formal semantic model for Head &amp; Neck Cancer clinical data</p>

<div class="section">
<div class="desc">
<b>HeNeCOn</b> (Head and Neck Cancer Ontology) is the first disease-specific OWL ontology dedicated entirely
to Head and Neck Cancer (HNC). It was developed by the <b>BD2Decide consortium</b> (Universidad Politécnica de Madrid)
to harmonise heterogeneous clinical data from multiple European cancer registries. The ontology provides
<b>502 formally defined classes</b> with <b>283 semantic definitions</b> (rdfs:comment), a hierarchical subclass taxonomy,
and cross-references to major biomedical ontologies. It enables structured data integration, NLP entity extraction,
and machine-readable clinical knowledge representation for HNC research.
</div>
</div>

<div class="section">
<div class="section-title">Key Metrics</div>
<div class="cards cards-4">
  <div class="card"><div class="metric-num">{len(hnc_classes):,}</div><div class="metric-lbl">OWL Classes</div></div>
  <div class="card"><div class="metric-num">{len(hnc_sc_edges):,}</div><div class="metric-lbl">SubClass relations</div></div>
  <div class="card"><div class="metric-num">{len(hnc_obj_props)}</div><div class="metric-lbl">Object properties</div></div>
  <div class="card"><div class="metric-num">283</div><div class="metric-lbl">Semantic definitions</div></div>
  <div class="card"><div class="metric-num">4</div><div class="metric-lbl">External ontologies mapped</div><div class="metric-sub">SNOMED·ICD-O·NCIt·UBERON</div></div>
  <div class="card"><div class="metric-num">OWL2</div><div class="metric-lbl">Specification</div></div>
  <div class="card"><div class="metric-num">CC BY</div><div class="metric-lbl">Licence</div></div>
  <div class="card"><div class="metric-num">{len(g_owl):,}</div><div class="metric-lbl">RDF Triples</div></div>
</div>
</div>

<div class="section">
<div class="section-title">Ontology Structure</div>
<img class="chart" src="data:image/png;base64,{hnc_chart}">
</div>

<div class="section">
<div class="section-title">Object Properties (Relations)</div>
<div class="card">{prop_pills if prop_pills else "<span style='color:#888'>Properties not labelled in this file</span>"}</div>
</div>

<div class="section">
<div class="section-title">Class Sample (first 200 of {len(hnc_classes)})</div>
<div class="card" style="padding:0;overflow:hidden;max-height:400px;overflow-y:auto">
<table><tr><th>Class Label</th><th>Definition (truncated)</th></tr>
{class_rows}
</table></div>
</div>

<div class="section">
<div class="section-title">How to Load</div>
<code>from rdflib import Graph, RDFS, OWL, RDF
import pandas as pd

g = Graph()
g.parse("hencon/HeNeCOn.owl")
print(f"Triples: {{len(g):,}}")

# Extract all classes with labels + definitions
classes = []
for s, _, _ in g.triples((None, RDF.type, OWL.Class)):
    label = g.value(s, RDFS.label)
    defn  = g.value(s, RDFS.comment)
    if label:
        classes.append({{"uri": str(s), "label": str(label),
                         "definition": str(defn) if defn else ""}})

df = pd.DataFrame(classes)
print(df.shape)   # ({len(hnc_classes)}, 3)
print(df.head())

# Extract subclass hierarchy (edges)
edges = []
for s, _, o in g.triples((None, RDFS.subClassOf, None)):
    sl = g.value(s, RDFS.label)
    ol = g.value(o, RDFS.label)
    if sl and ol:
        edges.append({{"child": str(sl), "parent": str(ol)}})

df_edges = pd.DataFrame(edges)
print(f"SubClass edges: {{len(df_edges):,}}")</code>
</div>

<div class="section">
<div class="section-title">Mapped External Ontologies</div>
<div class="cards cards-4">
  <div class="card"><div class="metric-num" style="font-size:18px">SNOMED CT</div><div class="metric-lbl">Clinical terminology</div></div>
  <div class="card"><div class="metric-num" style="font-size:18px">ICD-O-3</div><div class="metric-lbl">Histology &amp; topography codes</div></div>
  <div class="card"><div class="metric-num" style="font-size:18px">NCIt</div><div class="metric-lbl">NCI Thesaurus concepts</div></div>
  <div class="card"><div class="metric-num" style="font-size:18px">UBERON</div><div class="metric-lbl">Multi-species anatomy</div></div>
</div>
</div>
"""
    with open(os.path.join(OUT,"04_hencon_profile.html"),"w",encoding="utf-8") as f:
        f.write(html_shell("HeNeCOn Profile","#8E6BBF",hnc_content,"hencon"))
    print("   ✓ 04_hencon_profile.html")


# ══════════════════════════════════════════════════════════════
# 5. OVERVIEW DASHBOARD
# ══════════════════════════════════════════════════════════════
print("\n[5/5] Building overview dashboard...")

# summary chart — 4 databases side by side
fig, axes = plt.subplots(1, 4, figsize=(16, 5))
fig.patch.set_facecolor(DARK)
db_data = [
    ("CancerMine", [len(cm), cm[GENE_COL].nunique(), cm[CANCER_COL].nunique()],
     ["Triples","Genes","Cancers"], "#4C9BE8"),
    ("COSMIC CMC", [len(cmc), cmc["gene"].nunique() if not cmc.empty and "gene" in cmc.columns else 0,
                    cmc["site"].nunique() if not cmc.empty and "site" in cmc.columns else 0],
     ["Rows","Genes","Sites"], "#E8724C"),
    ("COSMIC CGC", [len(cgc), cgc["gene"].nunique() if not cgc.empty and "gene" in cgc.columns else 0,
                    cgc["site"].nunique() if not cgc.empty and "site" in cgc.columns else 0],
     ["Rows","Genes","Sites"], "#52B788"),
    ("HeNeCOn", [len(hnc_classes), len(hnc_sc_edges), len(hnc_obj_props)],
     ["Classes","SubClass edges","Properties"], "#8E6BBF"),
]
for i, (name, vals, lbls, col) in enumerate(db_data):
    axes[i].set_facecolor(DARK)
    bars = axes[i].bar(lbls, vals, color=col, alpha=0.85, width=0.5)
    for bar, val in zip(bars, vals):
        axes[i].text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.02,
                     f"{val:,}", ha="center", va="bottom", fontsize=9, color=TEXT)
    axes[i].set_title(name, color=col, fontsize=12, pad=8, fontweight="bold")
    axes[i].tick_params(colors=TEXT, labelsize=9)
    axes[i].set_facecolor(DARK)
    for s in axes[i].spines.values(): s.set_edgecolor(BORDER)
    axes[i].yaxis.set_visible(False)
plt.tight_layout()
overview_chart = fig_to_b64(fig)

overview_content = f"""
<h1>🧬 Cancer Knowledge Graph — Database Overview</h1>
<p class="subtitle">Three complementary databases integrated into a multi-relational knowledge graph</p>

<div class="section">
<div class="section-title">Database Comparison</div>
<img class="chart" src="data:image/png;base64,{overview_chart}">
</div>

<div class="section">
<div class="section-title">Database Summary Cards</div>
<div class="cards cards-2">

  <div class="card" style="border-color:#4C9BE855">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🔵</span>
      <div><div style="font-size:15px;font-weight:600;color:#4C9BE8">CancerMine</div>
      <div style="font-size:11px;color:{MUTED}">Literature-mined gene roles</div></div>
    </div>
    <div class="cards cards-3" style="margin-bottom:10px">
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#4C9BE8">{len(cm):,}</div><div class="metric-lbl">Triples</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#4C9BE8">{cm[GENE_COL].nunique():,}</div><div class="metric-lbl">Genes</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#4C9BE8">{cm[CANCER_COL].nunique():,}</div><div class="metric-lbl">Cancers</div></div>
    </div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">NLP text-mined from PubMed. Categorises genes as drivers, oncogenes, or tumor suppressors per cancer type. CC0 licence — no login required.</div>
    <a href="01_cancermine_profile.html" style="display:inline-block;padding:6px 16px;background:#4C9BE822;color:#4C9BE8;border:1px solid #4C9BE855;border-radius:6px;font-size:12px;text-decoration:none">View full profile →</a>
  </div>

  <div class="card" style="border-color:#E8724C55">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🟠</span>
      <div><div style="font-size:15px;font-weight:600;color:#E8724C">COSMIC — Cancer Mutation Census</div>
      <div style="font-size:11px;color:{MUTED}">Somatic mutation catalogue v103</div></div>
    </div>
    <div class="cards cards-3" style="margin-bottom:10px">
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#E8724C">38M+</div><div class="metric-lbl">Mutations</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#E8724C">1.4M+</div><div class="metric-lbl">Samples</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#E8724C">29K+</div><div class="metric-lbl">Publications</div></div>
    </div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">Expert-curated somatic mutations with FATHMM pathogenicity scores and tissue/histology metadata. Free for academics.</div>
    <a href="02_cosmic_cmc_profile.html" style="display:inline-block;padding:6px 16px;background:#E8724C22;color:#E8724C;border:1px solid #E8724C55;border-radius:6px;font-size:12px;text-decoration:none">View full profile →</a>
  </div>

  <div class="card" style="border-color:#52B78855">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🟢</span>
      <div><div style="font-size:15px;font-weight:600;color:#52B788">COSMIC — MutantCensus (CGC)</div>
      <div style="font-size:11px;color:{MUTED}">Cancer Gene Census with significance scoring</div></div>
    </div>
    <div class="cards cards-3" style="margin-bottom:10px">
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#52B788">723</div><div class="metric-lbl">CGC Genes</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#52B788">Tier 1/2</div><div class="metric-lbl">Confidence</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#52B788">v103</div><div class="metric-lbl">Version</div></div>
    </div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">Significance-scored mutations in the 723 Cancer Gene Census genes. Tier 1 = highest confidence cancer drivers.</div>
    <a href="03_cosmic_cgc_profile.html" style="display:inline-block;padding:6px 16px;background:#52B78822;color:#52B788;border:1px solid #52B78855;border-radius:6px;font-size:12px;text-decoration:none">View full profile →</a>
  </div>

  <div class="card" style="border-color:#8E6BBF55">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🟣</span>
      <div><div style="font-size:15px;font-weight:600;color:#8E6BBF">HeNeCOn</div>
      <div style="font-size:11px;color:{MUTED}">Head &amp; Neck Cancer OWL Ontology</div></div>
    </div>
    <div class="cards cards-3" style="margin-bottom:10px">
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#8E6BBF">{len(hnc_classes):,}</div><div class="metric-lbl">Classes</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#8E6BBF">283</div><div class="metric-lbl">Definitions</div></div>
      <div style="text-align:center"><div class="metric-num" style="font-size:18px;color:#8E6BBF">4</div><div class="metric-lbl">Ontologies mapped</div></div>
    </div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">First HNC-specific OWL ontology. Covers anatomy, histology, staging, treatments and risk factors. CC BY licence.</div>
    <a href="04_hencon_profile.html" style="display:inline-block;padding:6px 16px;background:#8E6BBF22;color:#8E6BBF;border:1px solid #8E6BBF55;border-radius:6px;font-size:12px;text-decoration:none">View full profile →</a>
  </div>

</div>
</div>

<div class="section">
<div class="section-title">How the Databases Connect in the Knowledge Graph</div>
<div class="card">
<table>
<tr><th>Source</th><th>Node Types Created</th><th>Edge Relations Created</th><th>Key linking field</th></tr>
<tr><td style="color:#4C9BE8">CancerMine</td><td>Gene, Cancer</td><td>driver, oncogene, tumor_suppressor</td><td>gene_normalized × cancer_normalized</td></tr>
<tr><td style="color:#E8724C">COSMIC CMC</td><td>Gene, Tissue, Mutation</td><td>mutated_in, has_mutation</td><td>GENE_SYMBOL × PRIMARY_SITE</td></tr>
<tr><td style="color:#52B788">COSMIC CGC</td><td>Gene, Tissue</td><td>mutated_in (Tier-scored)</td><td>GENE_SYMBOL × PRIMARY_SITE</td></tr>
<tr><td style="color:#8E6BBF">HeNeCOn</td><td>HNC Concept</td><td>subClassOf, mapped_to_ontology</td><td>rdfs:label match to Gene/Cancer labels</td></tr>
</table>
</div>
</div>

<div class="section">
<div class="section-title">Quick Start</div>
<code># 1. Build the knowledge graph from all 3 databases
python build_cancer_kg.py
# → kg_output/cancer_kg_nodes.csv
# → kg_output/cancer_kg_edges.csv
# → kg_output/cancer_kg.graphml

# 2. Generate the enhanced interactive visualisation
python enhance_cancer_kg.py
# → kg_output/cancer_kg_enhanced.html  ← open in browser

# 3. Profile each database individually
python describe_databases.py
# → db_profiles/00_overview_dashboard.html  ← this page
# → db_profiles/01_cancermine_profile.html
# → db_profiles/02_cosmic_cmc_profile.html
# → db_profiles/03_cosmic_cgc_profile.html
# → db_profiles/04_hencon_profile.html</code>
</div>
"""

with open(os.path.join(OUT,"00_overview_dashboard.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("Cancer DB Overview","#a0c4ff",overview_content,"overview"))
print("   ✓ 00_overview_dashboard.html")

print(f"""
══════════════════════════════════════════════════
  ✅  Database profiles complete!
  📂  Open: db_profiles/00_overview_dashboard.html
══════════════════════════════════════════════════
""")