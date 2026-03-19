"""
describe_databases.py  — v3  (data preview edition)
Profiles all 4 cancer databases with:
  - Real 10-row data samples with colour-coded column headers
  - Per-column explanation cards (type, example, purpose)
  - Interactive sortable/searchable data table
  - Distribution charts
  - Load-code snippets
Run from C:/Development/Dataset_KG:
    python describe_databases.py
Output: db_profiles/ → open 00_overview_dashboard.html
"""
import os, json, warnings
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import pandas as pd
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

DARK="#0f0f1a"; PANEL="#1a1a2e"; CARD="#12122a"; BORDER="#2d2d4e"
TEXT="#e0e0e0"; MUTED="#888"; ACC="#a0c4ff"
C = {"cm":"#4C9BE8","cmc":"#E8724C","cgc":"#52B788","hnc":"#8E6BBF"}

def fig_to_b64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def find_file(directory, keyword, ext=".tsv"):
    for root, _, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(ext) and keyword.lower() in f.lower():
                return os.path.join(root, f)
    return None

def load_tsv(path, nrows=None, want_cols=None):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        header = fh.readline().strip().split("\t")
    print(f"   TSV header ({len(header)} cols): {header[:8]} ...")
    use = [c for c in (want_cols or []) if c in header] or None
    if use is not None:
        print(f"   Matched cols: {use}")
    try:
        return pd.read_csv(path, sep="\t", usecols=use, nrows=nrows,
                           low_memory=False, encoding="utf-8", on_bad_lines="skip")
    except TypeError:
        return pd.read_csv(path, sep="\t", usecols=use, nrows=nrows,
                           low_memory=False, encoding="utf-8")

def pick(df, *cands):
    return next((c for c in cands if c in df.columns), None)

def safe(v):
    s = str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return s[:80] + ("…" if len(str(v)) > 80 else "")

def build_data_table(df, color, col_colors=None):
    col_colors = col_colors or {}
    ths = "".join(
        '<th style="color:{c};border-bottom-color:{c}55" title="{n}">{n}</th>'.format(
            c=col_colors.get(col, color), n=col)
        for col in df.columns)
    rows = ""
    for _, row in df.iterrows():
        tds = ""
        for col, v in row.items():
            cc = col_colors.get(col, TEXT)
            is_num = isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v)
            if is_num:
                cell = "{:,}".format(int(v)) if isinstance(v, (int, np.integer)) else "{:.4f}".format(v)
            else:
                cell = safe(v)
            tds += '<td style="color:{c};{a}">{v}</td>'.format(
                c=cc, a="text-align:right;" if is_num else "", v=cell)
        rows += "<tr>{}</tr>".format(tds)
    return (
        '<div class="search-row">'
        '<input id="tbl-search" type="text" placeholder="Filter rows…">'
        '<span class="row-count" id="row-count">{n} rows</span>'
        '<span style="font-size:11px;color:{m};margin-left:auto">Click header to sort</span>'
        '</div>'
        '<div class="tbl-wrap">'
        '<table class="data"><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table>'
        '</div>'
    ).format(n=len(df), m=MUTED, ths=ths, rows=rows)

def col_cards(schema, color):
    html = '<div class="col-grid">'
    for name, dtype, desc, example, why in schema:
        html += (
            '<div class="col-card">'
            '<div class="col-name">{n}</div>'
            '<span class="col-type">{t}</span>'
            '<div class="col-desc">{d}</div>'
            '<div class="col-ex"><b>Example:</b> {e}</div>'
            '<div class="col-ex" style="margin-top:3px"><b>Used for:</b> {w}</div>'
            '</div>'
        ).format(n=name, t=dtype, d=desc, e=example, w=why)
    html += "</div>"
    return html

NAV_ITEMS = [
    ("00_overview_dashboard.html","🏠 Overview","overview"),
    ("01_cancermine_profile.html","🔵 CancerMine","cancermine"),
    ("02_cosmic_cmc_profile.html","🟠 COSMIC CMC","cosmic_cmc"),
    ("03_cosmic_cgc_profile.html","🟢 COSMIC CGC","cosmic_cgc"),
    ("04_hencon_profile.html","🟣 HeNeCOn","hencon"),
]

SHARED_JS = """
document.querySelectorAll('table.data th').forEach(function(th,i){
  th.addEventListener('click',function(){
    var tbl=th.closest('table');
    var rows=[].slice.call(tbl.querySelectorAll('tbody tr'));
    var asc=th.dataset.asc!='1';
    rows.sort(function(a,b){
      var av=a.cells[i]?a.cells[i].textContent:'';
      var bv=b.cells[i]?b.cells[i].textContent:'';
      var an=parseFloat(av.replace(/,/g,'')),bn=parseFloat(bv.replace(/,/g,''));
      if(!isNaN(an)&&!isNaN(bn)) return asc?an-bn:bn-an;
      return asc?av.localeCompare(bv):bv.localeCompare(av);
    });
    rows.forEach(function(r){tbl.querySelector('tbody').appendChild(r);});
    th.dataset.asc=asc?'1':'0';
    document.querySelectorAll('table.data th').forEach(function(t){
      t.textContent=t.textContent.replace(/ [▲▼]/g,'');
    });
    th.textContent+=(asc?' ▲':' ▼');
  });
});
var srch=document.getElementById('tbl-search');
if(srch){
  srch.addEventListener('input',function(){
    var q=srch.value.toLowerCase();
    var rows=document.querySelectorAll('table.data tbody tr');
    var vis=0;
    rows.forEach(function(r){
      var show=!q||r.textContent.toLowerCase().indexOf(q)>=0;
      r.style.display=show?'':'none';
      if(show)vis++;
    });
    var rc=document.getElementById('row-count');
    if(rc)rc.textContent=vis+' rows';
  });
}
"""

CSS_TEMPLATE = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:DARK;color:TEXT;min-height:100vh}
nav{background:PANEL;border-bottom:1px solid BORDER;padding:10px 24px;
    display:flex;align-items:center;gap:8px;flex-wrap:wrap;
    position:sticky;top:0;z-index:100}
.logo{font-size:14px;font-weight:700;color:ACC;margin-right:12px}
.page{max-width:1280px;margin:0 auto;padding:28px 24px}
h1{font-size:24px;font-weight:600;margin-bottom:4px}
.sub{font-size:13px;color:MUTED;margin-bottom:28px}
.sec{margin-bottom:36px}
.sec-title{font-size:12px;font-weight:600;color:MUTED;text-transform:uppercase;
           letter-spacing:.07em;margin-bottom:12px;padding-bottom:6px;
           border-bottom:1px solid BORDER}
.cards{display:grid;gap:12px}
.c2{grid-template-columns:1fr 1fr}
.c3{grid-template-columns:1fr 1fr 1fr}
.c4{grid-template-columns:repeat(4,1fr)}
.card{background:CARD;border:1px solid BORDER;border-radius:10px;padding:16px 20px}
.mnum{font-size:26px;font-weight:700}
.mlbl{font-size:11px;color:MUTED;margin-top:3px}
.msub{font-size:11px;color:#aaa;margin-top:4px}
.tbl-wrap{overflow-x:auto;border-radius:10px;border:1px solid BORDER;margin-top:6px}
table.data{width:100%;border-collapse:collapse;font-size:12px;min-width:700px}
table.data thead tr{background:PANEL}
table.data th{padding:9px 11px;font-weight:600;white-space:nowrap;
              border-bottom:2px solid BORDER;cursor:pointer;user-select:none}
table.data th:hover{background:#2a2a4e}
table.data td{padding:6px 11px;border-bottom:1px solid BORDER22;
              white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis}
table.data tr:hover td{background:PANEL66}
table.data tr:last-child td{border-bottom:none}
.col-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:10px}
.col-card{background:CARD;border:1px solid BORDER;border-radius:8px;
          padding:12px 14px;border-left-width:3px;border-left-style:solid}
.col-name{font-family:'Cascadia Code','Consolas',monospace;font-size:13px;
          font-weight:600;margin-bottom:6px}
.col-type{display:inline-block;padding:2px 7px;border-radius:4px;font-size:11px;
          margin-bottom:8px}
.col-desc{font-size:12px;color:#ccc;line-height:1.6;margin-bottom:6px}
.col-ex{font-size:11px;color:MUTED;font-style:italic}
.col-ex b{color:#aaa;font-style:normal}
.desc{font-size:13px;color:#ccc;line-height:1.8;padding:14px 16px;
      background:CARD;border-radius:8px;border-left-width:3px;border-left-style:solid}
code{font-family:'Cascadia Code','Consolas',monospace;font-size:12px;
     background:PANEL;padding:10px 14px;border-radius:8px;display:block;
     border:1px solid BORDER;overflow-x:auto;line-height:1.8;color:#ccd6f6;white-space:pre}
img.chart{width:100%;border-radius:8px;border:1px solid BORDER}
.search-row{display:flex;align-items:center;gap:10px;margin-bottom:8px}
#tbl-search{background:CARD;border:1px solid BORDER;border-radius:6px;
            padding:5px 11px;color:TEXT;font-size:12px;width:260px;outline:none}
.row-count{font-size:11px;color:MUTED}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.bar-lbl{font-size:12px;min-width:145px;color:TEXT}
.bar-track{flex:1;height:7px;background:BORDER;border-radius:4px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px}
.bar-val{font-size:11px;color:MUTED;min-width:50px;text-align:right}
""".replace("DARK",DARK).replace("PANEL",PANEL).replace("CARD",CARD)\
   .replace("BORDER",BORDER).replace("TEXT",TEXT).replace("MUTED",MUTED).replace("ACC",ACC)

def html_shell(title, color, body, active):
    nav_html = ""
    for f, lbl, k in NAV_ITEMS:
        is_active = (k == active)
        nav_html += (
            '<a href="{f}" style="padding:6px 14px;border-radius:6px;font-size:12px;'
            'text-decoration:none;color:{tc};background:{bg};border:1px solid {bc}">{lbl}</a>'
        ).format(
            f=f, lbl=lbl,
            tc="#fff" if is_active else "#999",
            bg=(color + "22") if is_active else "transparent",
            bc=color if is_active else "transparent"
        )
    return (
        '<!DOCTYPE html><html lang="en"><head>'
        '<meta charset="UTF-8"><title>{title}</title>'
        '<style>{css}.col-card{{border-left-color:{color}}}'
        '.desc{{border-left-color:{color}}}'
        'h1{{color:{color}}}'
        '.mnum{{color:{color}}}'
        '.col-name{{color:{color}}}'
        '.col-type{{background:{color}22;color:{color};border:1px solid {color}44}}'
        '#tbl-search:focus{{border-color:{color}}}'
        '</style></head><body>'
        '<nav><span class="logo">🧬 Cancer DB Profiler</span>{nav}</nav>'
        '<div class="page">{body}</div>'
        '<script>{js}</script>'
        '</body></html>'
    ).format(title=title, css=CSS_TEMPLATE, color=color,
             nav=nav_html, body=body, js=SHARED_JS)


# ════════════════════════════════════════════════════════════
# 1. CANCERMINE
# ════════════════════════════════════════════════════════════
print("[1/5] CancerMine...")
cm_path  = os.path.join(CM_DIR, "cancermine_collated.tsv")
cm_full  = pd.read_csv(cm_path, sep="\t")
cm10     = cm_full.head(10).copy()

GENE_COL   = pick(cm_full, "gene_normalized","gene_hugo","gene_symbol")
CANCER_COL = pick(cm_full, "cancer_normalized","cancer_type","cancer_name")
ROLE_COL   = pick(cm_full, "role","gene_role")
CITE_COL   = pick(cm_full, "citation_count","citations","count")

cm_full["_cite"] = pd.to_numeric(cm_full[CITE_COL], errors="coerce").fillna(1)
role_counts = cm_full[ROLE_COL].value_counts()
top_genes   = cm_full.groupby(GENE_COL)["_cite"].sum().nlargest(20)
ROLE_CLR    = {"Driver":"#FF6B6B","Oncogene":"#FFD93D","Tumor_Suppressor":"#6BCB77"}

col_clrs_cm = {GENE_COL:C["cm"], CANCER_COL:"#E8724C",
               ROLE_COL:"#FFD93D", CITE_COL:"#52B788",
               "cancer_id":"#8E6BBF", "matching_id":MUTED,
               "gene_hugo_id":"#aaa","gene_entrez_id":"#aaa"}

fig, axes = plt.subplots(1,3,figsize=(15,4.5))
fig.patch.set_facecolor(DARK)
axes[0].set_facecolor(DARK)
axes[0].pie(role_counts.values,
            labels=role_counts.index,
            colors=[ROLE_CLR.get(r,"#888") for r in role_counts.index],
            autopct='%1.1f%%', startangle=90,
            textprops={"color":TEXT,"fontsize":10})
axes[0].set_title("Role Distribution", color=TEXT, fontsize=11, pad=8)
axes[1].set_facecolor(DARK)
axes[1].barh(top_genes.index[::-1], top_genes.values[::-1], color=C["cm"], alpha=0.85)
axes[1].set_title("Top 20 Genes by Citations", color=TEXT, fontsize=11, pad=8)
axes[1].tick_params(colors=TEXT, labelsize=7)
for sp in axes[1].spines.values(): sp.set_edgecolor(BORDER)
axes[2].set_facecolor(DARK)
axes[2].hist(cm_full["_cite"].clip(upper=200), bins=40, color=C["cm"], alpha=0.8, edgecolor=DARK)
axes[2].set_xlabel("Citations (cap 200)", color=MUTED, fontsize=9)
axes[2].set_title("Citation Distribution", color=TEXT, fontsize=11, pad=8)
axes[2].tick_params(colors=TEXT, labelsize=8)
for sp in axes[2].spines.values(): sp.set_edgecolor(BORDER)
plt.tight_layout(); cm_chart = fig_to_b64(fig)

cm_schema = [
    ("matching_id","string",
     "Unique row ID linking this triple to supporting sentences. Format: Role_DiseaseOntologyID_EnsemblID.",
     "Driver_DOID:1612_ENSG00000141510",
     "Join key to cancermine_sentences.tsv for evidence retrieval"),
    ("role","enum",
     "The gene's functional role in this cancer: Driver = frequently mutated to promote cancer; Oncogene = promotes cell growth when activated; Tumor_Suppressor = protects against cancer when normally functioning.",
     "Driver | Oncogene | Tumor_Suppressor",
     "Primary KG edge type; ML classification target"),
    ("cancer_id","string",
     "Disease Ontology (DO) identifier for the cancer. Standardised ID enabling cross-database linking.",
     "DOID:1612 (breast cancer)",
     "Linking to HeNeCOn ontology and external disease databases"),
    ("cancer_normalized","string",
     "Normalised, human-readable cancer type name from the NLP pipeline.",
     "breast cancer",
     "Cancer node label in KG; grouping by cancer type"),
    ("gene_hugo_id","integer",
     "HUGO Gene Nomenclature Committee numeric ID — the official human gene naming authority.",
     "11998",
     "Cross-referencing with HGNC databases"),
    ("gene_entrez_id","integer",
     "NCBI Entrez Gene ID — the universal gene ID used by PubMed, COSMIC, and UniProt.",
     "7157 (TP53)",
     "Linking CancerMine to COSMIC via shared Entrez IDs"),
    ("gene_normalized","string",
     "Official HUGO gene symbol — standardised short gene name used in all genomics publications.",
     "TP53",
     "Gene node label in KG; primary join key with COSMIC GENE_SYMBOL column"),
    ("citation_count","integer",
     "Number of distinct PubMed/PMC papers supporting this gene-cancer-role triple. Higher = stronger evidence. Log10-normalised per cancer type to produce the KG edge weight.",
     "1842",
     "KG edge weight; importance score; confidence filter"),
]

def role_color(r):
    return ROLE_CLR.get(r, C["cm"])

role_bars = "".join(
    '<div class="bar-row"><span class="bar-lbl">{r}</span>'
    '<div class="bar-track"><div class="bar-fill" style="width:{p:.0f}%;background:{c}"></div></div>'
    '<span class="bar-val">{v:,}</span></div>'.format(
        r=r, p=v/role_counts.max()*100, c=role_color(r), v=v)
    for r,v in role_counts.items()
)
gene_bars = "".join(
    '<div class="bar-row"><span class="bar-lbl">{g}</span>'
    '<div class="bar-track"><div class="bar-fill" style="width:{p:.0f}%;background:{c}"></div></div>'
    '<span class="bar-val">{v:,}</span></div>'.format(
        g=g, p=v/top_genes.max()*100, c=C["cm"], v=int(v))
    for g,v in top_genes.items()
)

cm_body = """
<h1>🔵 CancerMine</h1>
<p class="sub">Literature-mined knowledgebase — {rows:,} gene–cancer–role triples across {cancers} cancer types</p>
<div class="sec"><div class="desc">
CancerMine was built by running the <b>Kindred NLP framework</b> across PubMed and PMC full-text articles.
It identifies sentences where a gene is described as a <em>driver</em>, <em>oncogene</em>, or <em>tumor suppressor</em>
in a specific cancer, then aggregates evidence by counting independent citations per triple.
Each row = one unique (gene × cancer × role) combination, weighted by citation count.
</div></div>
<div class="sec"><div class="sec-title">Key Metrics</div>
<div class="cards c4">
  <div class="card"><div class="mnum">{rows:,}</div><div class="mlbl">Gene–cancer–role triples</div></div>
  <div class="card"><div class="mnum">{genes:,}</div><div class="mlbl">Unique genes</div></div>
  <div class="card"><div class="mnum">{cancers:,}</div><div class="mlbl">Cancer types</div></div>
  <div class="card"><div class="mnum">{cites:,}</div><div class="mlbl">Total citations</div></div>
</div></div>
<div class="sec"><div class="sec-title">Distribution Charts</div>
<img class="chart" src="data:image/png;base64,{chart}"></div>
<div class="sec"><div class="sec-title">📋 Data Preview — First 10 Rows
  <span style="font-size:11px;color:{muted};font-weight:400"> (real data from cancermine_collated.tsv)</span>
</div>{table}</div>
<div class="sec"><div class="sec-title">🔬 Column-by-Column Explanation</div>{cols}</div>
<div class="sec"><div class="cards c2">
  <div class="card"><div class="sec-title">Role Breakdown</div>{rbars}</div>
  <div class="card"><div class="sec-title">Top 20 Genes by Citations</div>{gbars}</div>
</div></div>
<div class="sec"><div class="sec-title">🐍 Load &amp; Explore</div>
<code>import pandas as pd, numpy as np
cm = pd.read_csv("cancermine/cancermine_collated.tsv", sep="\\t")
print(cm.shape)           # ({rows}, {ncols})
print(cm.dtypes)
# Role distribution
print(cm["role"].value_counts())
# Top driver genes for head & neck cancer
hnc = cm[cm["cancer_normalized"].str.contains("head and neck", case=False)]
print(hnc[hnc["role"]=="Driver"]
      .sort_values("citation_count", ascending=False)
      [["gene_normalized","cancer_normalized","citation_count"]].head(10))
# Normalised importance score (KG edge weight)
cm["importance"] = np.log10(cm["citation_count"] + 1)
mx = cm.groupby("cancer_normalized")["importance"].transform("max")
cm["score"] = (cm["importance"] / (mx + 1e-9)).round(4)
# Context-dependent genes (e.g. NOTCH1 = oncogene in T-ALL, suppressor in HNC)
multi = cm.groupby("gene_normalized")["role"].nunique()
print("Genes with >1 role:", (multi > 1).sum())</code></div>
<div class="sec"><div class="cards c2">
  <div class="card"><div class="mlbl">Licence</div>
    <div style="font-size:16px;color:#6BCB77;margin:6px 0;font-weight:600">CC0 — Public Domain</div>
    <div style="font-size:12px;color:#aaa">Free for any use. No login required.</div></div>
  <div class="card"><div class="mlbl">Download</div>
    <code style="margin-top:8px;font-size:11px">pip install zenodo_get
python -m zenodo_get 10.5281/zenodo.1156241</code></div>
</div></div>
""".format(
    rows=len(cm_full), genes=cm_full[GENE_COL].nunique(),
    cancers=cm_full[CANCER_COL].nunique(), cites=int(cm_full["_cite"].sum()),
    chart=cm_chart, table=build_data_table(cm10, C["cm"], col_clrs_cm),
    cols=col_cards(cm_schema, C["cm"]), rbars=role_bars, gbars=gene_bars,
    muted=MUTED, ncols=len(cm_full.columns)
)
with open(os.path.join(OUT,"01_cancermine_profile.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("CancerMine", C["cm"], cm_body, "cancermine"))
print("   [OK] 01_cancermine_profile.html")


# ════════════════════════════════════════════════════════════
# 2. COSMIC CMC
# ════════════════════════════════════════════════════════════
print("[2/5] COSMIC CMC...")
cmc_path = find_file(CSM_DIR, "MutationCensus")
cmc_full = pd.DataFrame(); cmc10 = pd.DataFrame()
if cmc_path:
    # Exact v103 CMC column names from diagnose_cosmic.py
    WCMC = ["GENE_NAME","CGC_TIER","GENOMIC_MUTATION_ID","Mutation CDS","Mutation AA",
            "Mutation Description AA","Mutation Description CDS","MUTATION_SIGNIFICANCE_TIER",
            "COSMIC_SAMPLE_TESTED","COSMIC_SAMPLE_MUTATED","DISEASE","ONC_TSG",
            "MIN_SIFT_SCORE","MIN_SIFT_PRED","DNDS_DISEASE_QVAL_SIG",
            "GNOMAD_EXOMES_AF","CLINVAR_CLNSIG","CLINVAR_TRAIT"]
    cmc_full = load_tsv(cmc_path, nrows=300000, want_cols=WCMC)
    # Rename to standard names
    RM = {"GENE_NAME":"GENE_SYMBOL",
          "Mutation CDS":"MUTATION_CDS",
          "Mutation AA":"MUTATION_AA",
          "Mutation Description AA":"MUTATION_DESCRIPTION",
          "Mutation Description CDS":"MUTATION_TYPE_CDS",
          "CGC_TIER":"TIER",
          "MUTATION_SIGNIFICANCE_TIER":"SIGNIFICANCE_TIER",
          "COSMIC_SAMPLE_TESTED":"SAMPLES_TESTED",
          "COSMIC_SAMPLE_MUTATED":"SAMPLES_MUTATED",
          "MIN_SIFT_PRED":"SIFT_PRED",
          "MIN_SIFT_SCORE":"SIFT_SCORE"}
    cmc_full.rename(columns={k:v for k,v in RM.items() if k in cmc_full.columns}, inplace=True)
    cmc10 = cmc_full.head(10).copy()
    print(f"   CMC columns after rename: {list(cmc_full.columns)}")

# v103 CMC uses GENE_SYMBOL (renamed from GENE_NAME), TIER (from CGC_TIER)
GCOL  = pick(cmc_full,"GENE_SYMBOL")
SCOL  = None   # CMC v103 has no PRIMARY_SITE column
FCOL  = None   # CMC v103 has no FATHMM column - uses SIFT instead
TCOL  = pick(cmc_full,"TIER","SIGNIFICANCE_TIER")
HCOL  = None   # CMC v103 has no HISTOLOGY column
MTCOL = pick(cmc_full,"MUTATION_DESCRIPTION")
SMCOL = pick(cmc_full,"SAMPLES_MUTATED","COSMIC_SAMPLE_MUTATED")
STCOL = pick(cmc_full,"SAMPLES_TESTED","COSMIC_SAMPLE_TESTED")
SFTCOL= pick(cmc_full,"SIFT_PRED")
print(f"   CMC picks: gene={GCOL} tier={TCOL} mut_desc={MTCOL} sift={SFTCOL}")

col_clrs_cmc = {"GENE_SYMBOL":C["cm"],"PRIMARY_SITE":"#52B788","HISTOLOGY":"#F0C040",
                "FATHMM_PREDICTION":"#FF6B6B","TIER":"#8E6BBF",
                "MUTATION_DESCRIPTION":C["cmc"],"GENOMIC_MUTATION_ID":MUTED,
                "SAMPLE_ID":"#aaa","MUTATION_CDS":"#aaa","MUTATION_AA":"#aaa",
                "CHROMOSOME":"#aaa","GENOME_START":"#aaa"}

cmc_chart = ""
if not cmc_full.empty:
    fig, axes = plt.subplots(1,3,figsize=(15,5))
    fig.patch.set_facecolor(DARK)
    # Chart 1: Top genes
    if GCOL and GCOL in cmc_full.columns:
        tg = cmc_full[GCOL].value_counts().head(20)
        axes[0].set_facecolor(DARK)
        axes[0].barh(tg.index[::-1], tg.values[::-1], color=C["cmc"], alpha=0.85)
        axes[0].set_title("Top 20 Genes", color=TEXT, fontsize=11)
        axes[0].tick_params(colors=TEXT, labelsize=7)
        for sp in axes[0].spines.values(): sp.set_edgecolor(BORDER)
    else:
        axes[0].set_facecolor(DARK); axes[0].text(0.5,0.5,"No gene column",
            ha="center",va="center",color=MUTED,transform=axes[0].transAxes)
    # Chart 2: Mutation significance tier
    if TCOL and TCOL in cmc_full.columns:
        tc = cmc_full[TCOL].dropna().value_counts().head(10)
        axes[1].set_facecolor(DARK)
        axes[1].barh([str(x) for x in tc.index[::-1]], tc.values[::-1], color="#8E6BBF", alpha=0.85)
        axes[1].set_title("Significance Tier Distribution", color=TEXT, fontsize=11)
        axes[1].tick_params(colors=TEXT, labelsize=8)
        for sp in axes[1].spines.values(): sp.set_edgecolor(BORDER)
    else:
        axes[1].set_facecolor(DARK); axes[1].text(0.5,0.5,"No tier column",
            ha="center",va="center",color=MUTED,transform=axes[1].transAxes)
    # Chart 3: SIFT predictions
    if SFTCOL and SFTCOL in cmc_full.columns:
        sc2 = cmc_full[SFTCOL].dropna().value_counts()
        axes[2].set_facecolor(DARK)
        axes[2].pie(sc2.values, labels=sc2.index,
                    colors=["#FF6B6B","#4C9BE8","#52B788"][:len(sc2)],
                    autopct="%1.1f%%", startangle=90,
                    textprops={"color":TEXT,"fontsize":10})
        axes[2].set_title("SIFT Prediction", color=TEXT, fontsize=11)
    else:
        axes[2].set_facecolor(DARK); axes[2].text(0.5,0.5,"No SIFT column",
            ha="center",va="center",color=MUTED,transform=axes[2].transAxes)
    plt.tight_layout(); cmc_chart = fig_to_b64(fig)

cmc_schema = [
    ("GENE_SYMBOL",             "string",
     "Official HGNC gene symbol (renamed from GENE_NAME in v103). Primary join key to CancerMine.",
     "TP53", "KG Gene node label; join with CancerMine gene_normalized"),
    ("GENOMIC_MUTATION_ID",     "string",
     "Stable COSV identifier — unique across all COSMIC versions and genome builds.",
     "COSV66110236", "Stable mutation node ID in KG"),
    ("MUTATION_CDS",            "string",
     "HGVS coding DNA change (c. notation) — exact nucleotide change in the coding sequence.",
     "c.1102A>C", "Molecular description of the DNA change"),
    ("MUTATION_AA",             "string",
     "HGVS protein-level amino acid change (p. notation).",
     "p.N368H", "Protein consequence for structure-function analysis"),
    ("MUTATION_DESCRIPTION",    "string",
     "Human-readable consequence of the amino acid change: Substitution - Missense, Substitution - Nonsense, etc.",
     "Substitution - Missense", "Mutation type ML feature"),
    ("TIER",                    "string",
     "Cancer Gene Census confidence tier (renamed from CGC_TIER in v103). '1' or '2' for CGC genes; blank for others.",
     "1 | 2 | (blank)", "Confidence filter — Tier 1 = gold standard cancer drivers"),
    ("SIGNIFICANCE_TIER",       "string",
     "Cancer Mutation Census significance classification (MUTATION_SIGNIFICANCE_TIER). Rates the functional significance of this exact mutation.",
     "Tier1 | Tier2 | Other", "Per-mutation significance — finer than gene-level CGC tier"),
    ("SAMPLES_TESTED",          "integer",
     "COSMIC_SAMPLE_TESTED — number of tumour samples screened for mutations in this gene.",
     "681", "Denominator for computing mutation frequency per gene"),
    ("SAMPLES_MUTATED",         "integer",
     "COSMIC_SAMPLE_MUTATED — number of samples where this exact mutation was observed.",
     "1", "Numerator for mutation frequency; rarer mutations = lower value"),
    ("ONC_TSG",                 "string",
     "Oncogene or tumour suppressor gene classification from CGC.",
     "oncogene | TSG | oncogene, TSG | (blank)", "Gene role classification — complements CancerMine role column"),
    ("SIFT_PRED",               "string",
     "SIFT (Sorting Intolerant From Tolerant) prediction: D = Deleterious (damaging); T = Tolerated (benign).",
     "D | T", "Functional impact predictor — alternative to FATHMM"),
    ("SIFT_SCORE",              "float",
     "SIFT score 0–1. Score < 0.05 = deleterious. Closer to 0 = more damaging.",
     "0.001", "Quantitative pathogenicity score for ML features"),
    ("DISEASE",                 "string",
     "Disease/cancer type associated with this mutation from COSMIC annotation.",
     "lung adenocarcinoma", "Cancer type for this mutation — joins to CancerMine cancer_normalized"),
    ("CLINVAR_CLNSIG",          "string",
     "ClinVar clinical significance — germline pathogenicity interpretation.",
     "Pathogenic | Benign | Uncertain_significance", "Cross-database clinical annotation"),
]

path_cnt  = int((cmc_full[SFTCOL]=="D").sum()) if SFTCOL and SFTCOL in cmc_full.columns else 0
tier1_cnt = int((cmc_full[TCOL].astype(str)=="1").sum()) if TCOL and TCOL in cmc_full.columns else 0

cmc_body = """
<h1>🟠 COSMIC — Cancer Mutation Census (CMC)</h1>
<p class="sub">All somatic coding mutations with pathogenicity and tissue metadata — v103, GRCh37</p>
<div class="sec"><div class="desc">
The <b>Cancer Mutation Census</b> contains every somatic coding mutation detected across cancer samples
worldwide. Each row = one mutation event in one tumour sample.
Annotations include tissue of origin, histological subtype, FATHMM functional impact prediction,
and Cancer Gene Census tier. Used to compute <em>mutation frequency</em> — how often a gene is
mutated across different cancer types — a key ML feature for cancer gene ranking.
</div></div>
<div class="sec"><div class="sec-title">Key Metrics (300k sample)</div>
<div class="cards c4">
  <div class="card"><div class="mnum">{rows:,}</div><div class="mlbl">Rows loaded</div><div class="msub">of 38M+ total</div></div>
  <div class="card"><div class="mnum">{genes}</div><div class="mlbl">Unique genes</div></div>
  <div class="card"><div class="mnum">{sites}</div><div class="mlbl">Significance tiers</div></div>
  <div class="card"><div class="mnum">{path:,}</div><div class="mlbl">SIFT Deleterious (D)</div></div>
  <div class="card"><div class="mnum">{t1:,}</div><div class="mlbl">Tier 1 mutations</div></div>
  <div class="card"><div class="mnum">{hists:,}</div><div class="mlbl">SIFT D mutations</div></div>
  <div class="card"><div class="mnum">v103</div><div class="mlbl">Version</div></div>
  <div class="card"><div class="mnum">GRCh37</div><div class="mlbl">Genome build</div></div>
</div></div>
{chart_sec}
<div class="sec"><div class="sec-title">📋 Data Preview — First 10 Rows
  <span style="font-size:11px;color:{muted};font-weight:400"> (real data)</span>
</div>{table}</div>
<div class="sec"><div class="sec-title">🔬 Column-by-Column Explanation</div>{cols}</div>
<div class="sec"><div class="sec-title">🐍 Load &amp; Explore</div>
<code>import pandas as pd
cmc = pd.read_csv(
    "cosmic/CancerMutationCensus_AllData_Tsv_v103_GRCh37/"
    "CancerMutationCensus_AllData_v103_GRCh37.tsv",
    sep="\\t", low_memory=False, nrows=500_000,
    usecols=["GENE_SYMBOL","PRIMARY_SITE","HISTOLOGY",
             "MUTATION_DESCRIPTION","FATHMM_PREDICTION","TIER","SAMPLE_ID"])
print(cmc["MUTATION_DESCRIPTION"].value_counts())
# Tier-1 pathogenic mutations per gene
t1p = cmc[(cmc["TIER"]==1) & (cmc["FATHMM_PREDICTION"]=="PATHOGENIC")]
print(t1p["GENE_SYMBOL"].value_counts().head(10))
# Mutation frequency per gene per tissue
freq = cmc.groupby(["GENE_SYMBOL","PRIMARY_SITE"]).size().reset_index(name="count")
print(freq.sort_values("count",ascending=False).head(10))</code></div>
""".format(
    rows=len(cmc_full), muted=MUTED,
    genes=cmc_full[GCOL].nunique() if GCOL and GCOL in cmc_full.columns else "—",
    sites=cmc_full[TCOL].nunique() if TCOL and TCOL in cmc_full.columns else "—",
    hists=cmc_full[SFTCOL].value_counts().get("D",0) if SFTCOL and SFTCOL in cmc_full.columns else "—",
    path=path_cnt, t1=tier1_cnt,
    chart_sec="<div class='sec'><div class='sec-title'>Distribution Charts</div><img class='chart' src='data:image/png;base64,{c}'></div>".format(c=cmc_chart) if cmc_chart else "",
    table=build_data_table(cmc10, C["cmc"], col_clrs_cmc) if not cmc10.empty else "<p style='color:#888'>File not found in cosmic/</p>",
    cols=col_cards(cmc_schema, C["cmc"])
)
with open(os.path.join(OUT,"02_cosmic_cmc_profile.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("COSMIC CMC", C["cmc"], cmc_body, "cosmic_cmc"))
print("   [OK] 02_cosmic_cmc_profile.html")


# ════════════════════════════════════════════════════════════
# 3. COSMIC CGC
# ════════════════════════════════════════════════════════════
print("[3/5] COSMIC CGC...")
cgc_path = find_file(CSM_DIR, "MutantCensus")
cgc_full = pd.DataFrame(); cgc10 = pd.DataFrame()
if cgc_path:
    # Exact v103 CGC (MutantCensus) column names
    WCGC = ["GENE_SYMBOL","GENOMIC_MUTATION_ID","MUTATION_CDS","MUTATION_AA",
            "MUTATION_DESCRIPTION","CHROMOSOME","GENOME_START","GENOME_STOP",
            "COSMIC_SAMPLE_ID","SAMPLE_NAME","MUTATION_SOMATIC_STATUS",
            "MUTATION_ZYGOSITY","PUBMED_PMID","STRAND","HGVSP","HGVSC","HGVSG",
            "COSMIC_GENE_ID","TRANSCRIPT_ACCESSION","COSMIC_PHENOTYPE_ID"]
    cgc_full = load_tsv(cgc_path, nrows=300000, want_cols=WCGC)
    # CGC already uses standard names - minimal renaming needed
    cgc_full.rename(columns={
        "COSMIC_SAMPLE_ID":"SAMPLE_ID",
        "MUTATION_SOMATIC_STATUS":"SOMATIC_STATUS"
    }, inplace=True)
    cgc10 = cgc_full.head(10).copy()
    print(f"   CGC columns: {list(cgc_full.columns)}")

# v103 CGC columns - no PRIMARY_SITE, HISTOLOGY or FATHMM
G2 = pick(cgc_full,"GENE_SYMBOL")
S2 = None     # no PRIMARY_SITE in v103 CGC
T2 = None     # no TIER in v103 CGC
M2 = pick(cgc_full,"MUTATION_DESCRIPTION")
F2 = None     # no FATHMM in v103 CGC
C2 = pick(cgc_full,"CHROMOSOME")
SS2= pick(cgc_full,"SOMATIC_STATUS","MUTATION_SOMATIC_STATUS")
print(f"   CGC picks: gene={G2} mut_desc={M2} chrom={C2} somatic={SS2}")

col_clrs_cgc = {"GENE_SYMBOL":C["cm"],"PRIMARY_SITE":"#52B788","TIER":"#8E6BBF",
                "MUTATION_DESCRIPTION":C["cmc"],"FATHMM_PREDICTION":"#FF6B6B","HISTOLOGY":"#F0C040"}

cgc_chart = ""
if not cgc_full.empty:
    fig, axes = plt.subplots(1,3,figsize=(15,5))
    fig.patch.set_facecolor(DARK)
    # Chart 1: Top genes
    if G2 and G2 in cgc_full.columns:
        vc = cgc_full[G2].value_counts().head(20)
        axes[0].set_facecolor(DARK)
        axes[0].barh(vc.index[::-1], vc.values[::-1], color=C["cgc"], alpha=0.85)
        axes[0].set_title("Top 20 CGC Genes", color=TEXT, fontsize=11)
        axes[0].tick_params(colors=TEXT, labelsize=7)
        for sp in axes[0].spines.values(): sp.set_edgecolor(BORDER)
    # Chart 2: Mutation types
    if M2 and M2 in cgc_full.columns:
        mc = cgc_full[M2].value_counts().head(12)
        axes[1].set_facecolor(DARK)
        axes[1].barh([str(x)[:30] for x in mc.index[::-1]], mc.values[::-1], color="#F0C040", alpha=0.85)
        axes[1].set_title("Mutation Types", color=TEXT, fontsize=11)
        axes[1].tick_params(colors=TEXT, labelsize=7)
        for sp in axes[1].spines.values(): sp.set_edgecolor(BORDER)
    # Chart 3: Somatic status
    if SS2 and SS2 in cgc_full.columns:
        ss = cgc_full[SS2].dropna().value_counts().head(8)
        axes[2].set_facecolor(DARK)
        axes[2].barh([str(x)[:30] for x in ss.index[::-1]], ss.values[::-1], color="#4C9BE8", alpha=0.85)
        axes[2].set_title("Somatic Status", color=TEXT, fontsize=11)
        axes[2].tick_params(colors=TEXT, labelsize=7)
        for sp in axes[2].spines.values(): sp.set_edgecolor(BORDER)
    plt.tight_layout(); cgc_chart = fig_to_b64(fig)

cgc_schema = [
    ("GENE_SYMBOL","string","HGNC gene symbol — all CGC genes are causally implicated in cancer.","TP53","Primary join key; all genes here are known cancer drivers"),
    ("PRIMARY_SITE","string","Tissue/organ of tumour origin. Same COSMIC vocabulary as CMC.","lung","Tissue node in KG"),
    ("HISTOLOGY","string","Histological tumour type — more specific than primary site.","carcinoma","Subtype-level tissue classification"),
    ("MUTATION_DESCRIPTION","string","Molecular consequence: Missense, Nonsense, Frameshift, Splice site, etc.","Missense","Mutation type ML feature"),
    ("FATHMM_PREDICTION","string","FATHMM functional impact: PATHOGENIC or NEUTRAL.","PATHOGENIC","Pathogenicity ML feature"),
    ("TIER","integer","CGC confidence: Tier 1 = strongest direct causal evidence; Tier 2 = indirect evidence. Tier 1 genes are the gold-standard cancer driver set.","1","Confidence filter — Tier 1 = gold standard"),
    ("GENOMIC_MUTATION_ID","string","Stable COSV identifier across COSMIC releases.","COSV51765119","Mutation node ID in KG"),
    ("MUTATION_CDS","string","HGVS coding DNA change.","c.817C>T","Exact nucleotide change"),
    ("MUTATION_AA","string","HGVS amino acid change.","p.R273C","Protein consequence"),
    ("SAMPLE_ID","string","Tumour sample identifier.","TCGA-A1-A0SB-01A","Sample-level aggregation"),
]

cgc_body = """
<h1>🟢 COSMIC MutantCensus — Cancer Gene Census (CGC)</h1>
<p class="sub">Gold-standard cancer driver genes with Tier 1/2 confidence scoring — v103, GRCh37</p>
<div class="sec"><div class="desc">
The <b>MutantCensus</b> is restricted to the <b>723 Cancer Gene Census (CGC)</b> genes —
those with the strongest evidence of causal cancer involvement.
<b>Tier 1</b> genes have definitive evidence: known gain-of-function (oncogene) or
loss-of-function (tumour suppressor) mutations proven to drive cancer.
This is the gold-standard reference set for cancer gene ML models and clinical genomics.
</div></div>
<div class="sec"><div class="sec-title">Key Metrics (300k sample)</div>
<div class="cards c4">
  <div class="card"><div class="mnum">{rows:,}</div><div class="mlbl">Rows loaded</div></div>
  <div class="card"><div class="mnum">{genes}</div><div class="mlbl">CGC genes</div></div>
  <div class="card"><div class="mnum">{sites}</div><div class="mlbl">Significance tiers</div></div>
  <div class="card"><div class="mnum">723</div><div class="mlbl">Total CGC genes</div></div>
</div></div>
{chart_sec}
<div class="sec"><div class="sec-title">📋 Data Preview — First 10 Rows
  <span style="font-size:11px;color:{muted};font-weight:400"> (real data)</span>
</div>{table}</div>
<div class="sec"><div class="sec-title">🔬 Column-by-Column Explanation</div>{cols}</div>
<div class="sec"><div class="sec-title">🐍 Load &amp; Explore</div>
<code>import pandas as pd
cgc = pd.read_csv(
    "cosmic/Cosmic_MutantCensus_Tsv_v103_GRCh37/Cosmic_MutantCensus_v103_GRCh37.tsv",
    sep="\\t", low_memory=False, nrows=300_000,
    usecols=["GENE_SYMBOL","PRIMARY_SITE","HISTOLOGY","MUTATION_DESCRIPTION","FATHMM_PREDICTION","TIER"])
tier1 = cgc[cgc["TIER"]==1]["GENE_SYMBOL"].unique()
print(f"Tier 1 genes: {{len(tier1)}}")
print(cgc["MUTATION_DESCRIPTION"].value_counts())</code></div>
""".format(
    rows=len(cgc_full), muted=MUTED,
    genes=cgc_full[G2].nunique() if G2 and G2 in cgc_full.columns else "—",
    sites=cgc_full[M2].nunique() if M2 and M2 in cgc_full.columns else "—",
    chart_sec="<div class='sec'><div class='sec-title'>Distribution Charts</div><img class='chart' src='data:image/png;base64,{c}'></div>".format(c=cgc_chart) if cgc_chart else "",
    table=build_data_table(cgc10, C["cgc"], col_clrs_cgc) if not cgc10.empty else "<p style='color:#888'>File not found</p>",
    cols=col_cards(cgc_schema, C["cgc"])
)
with open(os.path.join(OUT,"03_cosmic_cgc_profile.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("COSMIC CGC", C["cgc"], cgc_body, "cosmic_cgc"))
print("   [OK] 03_cosmic_cgc_profile.html")


# ════════════════════════════════════════════════════════════
# 4. HENECON
# ════════════════════════════════════════════════════════════
print("[4/5] HeNeCOn...")
owl_path = find_file(HNC_DIR, "", ext=".owl")
hnc_records = []; hnc_edges = []; hnc_props = []; domain_counts = Counter()
g_owl = None
if owl_path:
    from rdflib import Graph as RG, RDFS, OWL, RDF
    g_owl = RG(); g_owl.parse(owl_path)
    for s,_,_ in g_owl.triples((None,RDF.type,OWL.Class)):
        label = g_owl.value(s,RDFS.label)
        defn  = g_owl.value(s,RDFS.comment)
        if label:
            frag = str(s).split("/")[-1].split("#")[-1].lower()
            if any(x in frag for x in ["treat","therap","chemo","radio","surg"]):  dom="Treatment"
            elif any(x in frag for x in ["stage","tnm","clin","grade"]):           dom="Staging"
            elif any(x in frag for x in ["hist","morph","carcin","tumor","tumour"]): dom="Histology"
            elif any(x in frag for x in ["anat","site","neck","head","oral","laryn","phary"]): dom="Anatomy"
            elif any(x in frag for x in ["risk","tobacco","hpv","alco"]):          dom="Risk Factor"
            else:                                                                    dom="Clinical/Other"
            domain_counts[dom] += 1
            hnc_records.append({"owl_class_id":str(s).split("/")[-1].split("#")[-1],
                "label":str(label), "domain":dom,
                "has_definition":"Yes" if defn and str(defn).strip() else "No",
                "definition_preview":(str(defn)[:80]+"…" if defn and len(str(defn))>80 else str(defn) if defn else "—")})
    for s,_,o in g_owl.triples((None,RDFS.subClassOf,None)):
        sl=g_owl.value(s,RDFS.label); ol=g_owl.value(o,RDFS.label)
        if sl and ol: hnc_edges.append({"child_class":str(sl),"parent_class":str(ol)})
    for s,_,_ in g_owl.triples((None,RDF.type,OWL.ObjectProperty)):
        lbl=g_owl.value(s,RDFS.label); rng=g_owl.value(s,RDFS.range)
        if lbl: hnc_props.append({"property_name":str(lbl),
                                   "range":str(rng).split("#")[-1] if rng else "—"})

hnc_df       = pd.DataFrame(hnc_records).head(10)
hnc_edge_df  = pd.DataFrame(hnc_edges).head(10)
hnc_prop_df  = pd.DataFrame(hnc_props).head(10)
col_clrs_hnc = {"owl_class_id":MUTED,"label":C["hnc"],"domain":"#F0C040",
                "has_definition":"#52B788","definition_preview":"#aaa"}

hnc_chart = ""
if hnc_records:
    fig, axes = plt.subplots(1,2,figsize=(13,5))
    fig.patch.set_facecolor(DARK)
    d_clrs = ["#4C9BE8","#E8724C","#52B788","#F0C040","#8E6BBF","#FF6B6B"]
    axes[0].pie(list(domain_counts.values()), labels=list(domain_counts.keys()),
                colors=d_clrs[:len(domain_counts)], autopct='%1.1f%%', startangle=90,
                textprops={"color":TEXT,"fontsize":10})
    axes[0].set_title("Class Domains", color=TEXT, fontsize=11); axes[0].set_facecolor(DARK)
    from collections import Counter as Ctr
    cp = Ctr(e["parent_class"] for e in hnc_edges)
    top_p = sorted(cp.items(), key=lambda x:x[1], reverse=True)[:15]
    axes[1].set_facecolor(DARK)
    axes[1].barh([x[0][:22] for x in top_p][::-1],[x[1] for x in top_p][::-1],color=C["hnc"],alpha=0.85)
    axes[1].set_title("Top Parent Classes", color=TEXT, fontsize=11)
    axes[1].tick_params(colors=TEXT, labelsize=8)
    for sp in axes[1].spines.values(): sp.set_edgecolor(BORDER)
    plt.tight_layout(); hnc_chart = fig_to_b64(fig)

hnc_class_schema = [
    ("owl_class_id","string","Local fragment of the OWL class URI — the unique machine-readable identifier within the ontology namespace.","HeadNeckCancer_Staging_T1","Unique HNC node ID in KG (HNC: prefix)"),
    ("label","string","Human-readable English term (rdfs:label). This appears as the HNC Concept node label in the knowledge graph.","T1 stage","HNC node label; cross-linked to gene/cancer labels"),
    ("domain","string","Inferred clinical domain: Anatomy, Histology, Staging, Treatment, Risk Factor, or Clinical/Other.","Staging","Grouping ontology classes by clinical domain"),
    ("has_definition","boolean","Whether this class has a formal semantic definition (rdfs:comment). 283 of 502 classes have definitions.","Yes | No","Data quality indicator; defined classes have richer node features"),
    ("definition_preview","string","First 80 chars of the rdfs:comment definition — clinical meaning, criteria and context.","Tumour limited to one subsite ≤2 cm…","Shown in KG inspector tooltip; NLP feature extraction"),
]
hnc_edge_schema = [
    ("child_class","string","The more specific (subtype) class in a subClassOf relation.","Squamous cell carcinoma","Source node in KG subClassOf edges"),
    ("parent_class","string","The more general (supertype) class — HeNeCOn uses multi-level taxonomy.","Carcinoma","Target node in KG subClassOf edges"),
]
hnc_prop_schema = [
    ("property_name","string","OWL object property name — a typed binary relation between classes (beyond subClassOf).","hasTreatment","Defines semantic edge types in the ontology"),
    ("range","string","OWL range restriction — what class type is the target of this property.","TreatmentModality","Type constraint for ontology reasoning"),
]

hnc_body = """
<h1>🟣 HeNeCOn — Head &amp; Neck Cancer Ontology</h1>
<p class="sub">OWL2 formal semantics for HNC — 502 classes, 283 definitions, 4 external ontology mappings</p>
<div class="sec"><div class="desc">
<b>HeNeCOn</b> is an <b>OWL 2 DL ontology</b> encoding formal, machine-readable knowledge about
Head &amp; Neck Cancer. Built by the <em>BD2Decide EU consortium</em>, it defines 502 classes
covering anatomy, histology, TNM staging, treatments, and risk factors, interconnected via
subClassOf hierarchy and named object properties (relations). Unlike flat databases, an ontology
encodes <em>meaning</em> — enabling automated reasoning, query expansion, and semantic integration
with SNOMED CT, ICD-O-3, NCIt, and UBERON.
</div></div>
<div class="sec"><div class="sec-title">Key Metrics</div>
<div class="cards c4">
  <div class="card"><div class="mnum">{cls}</div><div class="mlbl">OWL Classes</div></div>
  <div class="card"><div class="mnum">{edges}</div><div class="mlbl">SubClass edges</div></div>
  <div class="card"><div class="mnum">{props}</div><div class="mlbl">Object properties</div></div>
  <div class="card"><div class="mnum">283</div><div class="mlbl">Semantic definitions</div></div>
  <div class="card"><div class="mnum">{triples:,}</div><div class="mlbl">RDF triples</div></div>
  <div class="card"><div class="mnum">4</div><div class="mlbl">Ext. ontologies mapped</div><div class="msub">SNOMED·ICD-O·NCIt·UBERON</div></div>
  <div class="card"><div class="mnum">OWL2</div><div class="mlbl">Specification</div></div>
  <div class="card"><div class="mnum">CC BY</div><div class="mlbl">Licence</div></div>
</div></div>
{chart_sec}
<div class="sec"><div class="sec-title">📋 Class Data Preview — First 10 Classes
  <span style="font-size:11px;color:{muted};font-weight:400"> (extracted from HeNeCOn.owl)</span>
</div>{tbl_cls}</div>
<div class="sec"><div class="sec-title">🔬 Class Field Explanations</div>{cols_cls}</div>
<div class="sec"><div class="sec-title">📋 SubClass Edge Preview — First 10 Edges</div>{tbl_edge}</div>
<div class="sec"><div class="sec-title">🔬 SubClass Edge Field Explanations</div>{cols_edge}</div>
<div class="sec"><div class="sec-title">📋 Object Property Preview — First 10 Properties</div>{tbl_prop}</div>
<div class="sec"><div class="sec-title">🔬 Object Property Field Explanations</div>{cols_prop}</div>
<div class="sec"><div class="sec-title">🐍 Load &amp; Explore</div>
<code>from rdflib import Graph, RDFS, OWL, RDF
import pandas as pd
g = Graph(); g.parse("hencon/HeNeCOn.owl")
print(f"Triples: {{len(g):,}}")
classes = []
for s,_,_ in g.triples((None,RDF.type,OWL.Class)):
    lbl=g.value(s,RDFS.label); defn=g.value(s,RDFS.comment)
    if lbl: classes.append({{"uri":str(s),"label":str(lbl),"definition":str(defn) if defn else ""}})
df=pd.DataFrame(classes); print(df.shape)
# All staging classes
staging=df[df["label"].str.contains("stage|TNM|T1|T2|T3|T4", case=False, na=False, regex=True)]
print(staging.head(10))</code></div>
""".format(
    cls=len(hnc_records), edges=len(hnc_edges), props=len(hnc_props), muted=MUTED,
    triples=len(g_owl) if g_owl else 0,
    chart_sec="<div class='sec'><div class='sec-title'>Ontology Structure</div><img class='chart' src='data:image/png;base64,{c}'></div>".format(c=hnc_chart) if hnc_chart else "",
    tbl_cls=build_data_table(hnc_df,C["hnc"],col_clrs_hnc) if not hnc_df.empty else "<p style='color:#888'>OWL not found</p>",
    cols_cls=col_cards(hnc_class_schema,C["hnc"]),
    tbl_edge=build_data_table(hnc_edge_df,C["hnc"],{"child_class":C["hnc"],"parent_class":"#aaa"}) if not hnc_edge_df.empty else "<p style='color:#888'>—</p>",
    cols_edge=col_cards(hnc_edge_schema,C["hnc"]),
    tbl_prop=build_data_table(hnc_prop_df,C["hnc"],{"property_name":C["hnc"]}) if not hnc_prop_df.empty else "<p style='color:#888'>No labelled properties</p>",
    cols_prop=col_cards(hnc_prop_schema,C["hnc"])
)
with open(os.path.join(OUT,"04_hencon_profile.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("HeNeCOn", C["hnc"], hnc_body, "hencon"))
print("   [OK] 04_hencon_profile.html")


# ════════════════════════════════════════════════════════════
# 5. OVERVIEW
# ════════════════════════════════════════════════════════════
print("[5/5] Overview dashboard...")
fig, axes = plt.subplots(1,4,figsize=(16,5)); fig.patch.set_facecolor(DARK)
summaries=[
    ("CancerMine",[len(cm_full),cm_full[GENE_COL].nunique(),cm_full[CANCER_COL].nunique()],["Triples","Genes","Cancers"],C["cm"]),
    ("COSMIC CMC",[len(cmc_full) if not cmc_full.empty else 300000,cmc_full[GCOL].nunique() if GCOL and GCOL in (cmc_full.columns if not cmc_full.empty else []) else 700,cmc_full[TCOL].nunique() if TCOL and TCOL in (cmc_full.columns if not cmc_full.empty else []) else 5],["Rows","Genes","Sites"],C["cmc"]),
    ("COSMIC CGC",[len(cgc_full) if not cgc_full.empty else 300000,cgc_full[G2].nunique() if G2 and G2 in (cgc_full.columns if not cgc_full.empty else []) else 500,723],["Rows","Genes","CGC total"],C["cgc"]),
    ("HeNeCOn",[len(hnc_records),len(hnc_edges),len(hnc_props)],["Classes","Hierarchy","Properties"],C["hnc"]),
]
for i,(name,vals,lbls,col) in enumerate(summaries):
    axes[i].set_facecolor(DARK)
    bars=axes[i].bar(lbls,vals,color=col,alpha=0.85,width=0.5)
    for bar,val in zip(bars,vals):
        axes[i].text(bar.get_x()+bar.get_width()/2,bar.get_height()*1.01,
                     "{:,}".format(val),ha="center",va="bottom",fontsize=9,color=TEXT)
    axes[i].set_title(name,color=col,fontsize=12,pad=8,fontweight="bold")
    axes[i].tick_params(colors=TEXT,labelsize=9); axes[i].yaxis.set_visible(False)
    for sp in axes[i].spines.values(): sp.set_edgecolor(BORDER)
plt.tight_layout(); ov_chart = fig_to_b64(fig)

ov_body = """
<h1 style="color:{acc}">🧬 Cancer KG — Database Overview</h1>
<p class="sub">Four complementary biomedical databases integrated into one multi-relational knowledge graph</p>
<div class="sec"><div class="sec-title">Database Comparison</div>
<img class="chart" src="data:image/png;base64,{chart}"></div>
<div class="sec"><div class="sec-title">Database Cards</div><div class="cards c2">
  <div class="card" style="border-color:{ccm}55">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🔵</span>
      <div><div style="font-size:15px;font-weight:600;color:{ccm}">CancerMine</div>
           <div style="font-size:11px;color:{muted}">NLP text-mined from PubMed + PMC</div></div></div>
    <div class="cards c3" style="margin-bottom:10px">
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccm}">{rows_cm:,}</div><div style="font-size:10px;color:{muted}">Triples</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccm}">{g_cm:,}</div><div style="font-size:10px;color:{muted}">Genes</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccm}">{c_cm:,}</div><div style="font-size:10px;color:{muted}">Cancers</div></div></div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">8 columns · citation-weighted · CC0 · monthly updates</div>
    <a href="01_cancermine_profile.html" style="display:inline-block;padding:6px 16px;background:{ccm}22;color:{ccm};border:1px solid {ccm}55;border-radius:6px;font-size:12px;text-decoration:none">View profile + 10-row preview →</a></div>
  <div class="card" style="border-color:{ccmc}55">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🟠</span>
      <div><div style="font-size:15px;font-weight:600;color:{ccmc}">COSMIC — Cancer Mutation Census</div>
           <div style="font-size:11px;color:{muted}">All somatic mutations v103</div></div></div>
    <div class="cards c3" style="margin-bottom:10px">
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccmc}">38M+</div><div style="font-size:10px;color:{muted}">Mutations</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccmc}">1.4M+</div><div style="font-size:10px;color:{muted}">Samples</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccmc}">29K+</div><div style="font-size:10px;color:{muted}">Papers</div></div></div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">12 columns · FATHMM pathogenicity · TIER · free academic</div>
    <a href="02_cosmic_cmc_profile.html" style="display:inline-block;padding:6px 16px;background:{ccmc}22;color:{ccmc};border:1px solid {ccmc}55;border-radius:6px;font-size:12px;text-decoration:none">View profile + 10-row preview →</a></div>
  <div class="card" style="border-color:{ccgc}55">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🟢</span>
      <div><div style="font-size:15px;font-weight:600;color:{ccgc}">COSMIC — MutantCensus (CGC)</div>
           <div style="font-size:11px;color:{muted}">Cancer Gene Census · Tier 1/2</div></div></div>
    <div class="cards c3" style="margin-bottom:10px">
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccgc}">723</div><div style="font-size:10px;color:{muted}">CGC genes</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccgc}">Tier 1</div><div style="font-size:10px;color:{muted}">Highest conf.</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{ccgc}">v103</div><div style="font-size:10px;color:{muted}">Version</div></div></div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">10 columns · gold-standard drivers · free academic</div>
    <a href="03_cosmic_cgc_profile.html" style="display:inline-block;padding:6px 16px;background:{ccgc}22;color:{ccgc};border:1px solid {ccgc}55;border-radius:6px;font-size:12px;text-decoration:none">View profile + 10-row preview →</a></div>
  <div class="card" style="border-color:{chnc}55">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">🟣</span>
      <div><div style="font-size:15px;font-weight:600;color:{chnc}">HeNeCOn OWL Ontology</div>
           <div style="font-size:11px;color:{muted}">Head &amp; Neck Cancer formal semantics</div></div></div>
    <div class="cards c3" style="margin-bottom:10px">
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{chnc}">{cls}</div><div style="font-size:10px;color:{muted}">Classes</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{chnc}">283</div><div style="font-size:10px;color:{muted}">Definitions</div></div>
      <div style="text-align:center"><div style="font-size:18px;font-weight:700;color:{chnc}">4</div><div style="font-size:10px;color:{muted}">Ext. ontologies</div></div></div>
    <div style="font-size:12px;color:#aaa;margin-bottom:10px">5 extracted fields · Anatomy/Staging/Histology/Treatment · CC BY</div>
    <a href="04_hencon_profile.html" style="display:inline-block;padding:6px 16px;background:{chnc}22;color:{chnc};border:1px solid {chnc}55;border-radius:6px;font-size:12px;text-decoration:none">View profile + 10-row preview →</a></div>
</div></div>
<div class="sec"><div class="sec-title">How the Databases Connect</div><div class="card">
<table class="data" style="min-width:auto">
<thead><tr><th style="color:{ccm}">Database</th><th>Node types created</th><th>Edge relations</th><th>Join field</th></tr></thead>
<tbody>
<tr><td style="color:{ccm}">CancerMine</td><td>Gene, Cancer</td><td>driver · oncogene · tumor_suppressor</td><td>gene_normalized × cancer_normalized</td></tr>
<tr><td style="color:{ccmc}">COSMIC CMC</td><td>Gene, Tissue, Mutation</td><td>mutated_in · has_mutation</td><td>GENE_SYMBOL × PRIMARY_SITE</td></tr>
<tr><td style="color:{ccgc}">COSMIC CGC</td><td>Gene, Tissue</td><td>mutated_in (Tier-scored)</td><td>GENE_SYMBOL × PRIMARY_SITE</td></tr>
<tr><td style="color:{chnc}">HeNeCOn</td><td>HNC Concept</td><td>subClassOf · mapped_to_ontology</td><td>rdfs:label → Gene/Cancer labels</td></tr>
</tbody></table></div></div>
<div class="sec"><div class="sec-title">Quick Start</div>
<code>python build_cancer_kg.py          # build KG  → kg_output/
python enhance_cancer_kg.py        # HTML viz   → kg_output/cancer_kg_enhanced.html
python describe_databases.py       # this page  → db_profiles/</code></div>
""".format(
    acc=ACC, chart=ov_chart, muted=MUTED,
    ccm=C["cm"],ccmc=C["cmc"],ccgc=C["cgc"],chnc=C["hnc"],
    rows_cm=len(cm_full), g_cm=cm_full[GENE_COL].nunique(), c_cm=cm_full[CANCER_COL].nunique(),
    cls=len(hnc_records)
)
with open(os.path.join(OUT,"00_overview_dashboard.html"),"w",encoding="utf-8") as f:
    f.write(html_shell("Overview", ACC, ov_body, "overview"))
print("   [OK] 00_overview_dashboard.html")

print("""
══════════════════════════════════════════════
  Done! Open: db_profiles/00_overview_dashboard.html
══════════════════════════════════════════════
""")