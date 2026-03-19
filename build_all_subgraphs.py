"""
build_all_subgraphs.py
════════════════════════════════════════════════════════════════
Builds SEPARATE knowledge graphs for each database PLUS a combined one.
Produces one unified HTML explorer with 5 tabs:

  Tab 1: CancerMine KG      (genes + cancers + roles from literature)
  Tab 2: COSMIC KG          (genes + tissues + mutations from tumour samples)
  Tab 3: HeNeCOn KG         (clinical concepts + ontology hierarchy)
  Tab 4: Combined KG        (all three merged)
  Tab 5: Curated subgraphs  (TP53, KRAS, HNC, Breast Cancer deep-dives)

Run:
  python build_all_subgraphs.py
  python serve_kg.py
  Open: http://localhost:8000/kg_output/all_subgraphs.html
"""
import os, json, warnings
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from rdflib import Graph, RDFS
warnings.filterwarnings("ignore")

BASE    = os.path.dirname(os.path.abspath(__file__))
NODES_F = os.path.join(BASE, "kg_output", "cancer_kg_nodes.csv")
EDGES_F = os.path.join(BASE, "kg_output", "cancer_kg_edges.csv")
OUT     = os.path.join(BASE, "kg_output", "all_subgraphs.html")

print("Loading full KG...")
nodes_df = pd.read_csv(NODES_F).fillna("")
edges_df = pd.read_csv(EDGES_F).fillna("")
if "src" in edges_df.columns:
    edges_df.rename(columns={"src":"source","tgt":"target"}, inplace=True)
print(f"  Total nodes: {len(nodes_df):,}   Total edges: {len(edges_df):,}")


def load_henecon_owl(owl_path):
    print("  Parsing HeNeCOn.owl ...")
    g = Graph()
    g.parse(owl_path)

    new_nodes = []
    new_edges = []

    seen_nodes = set()

    for s, p, o in g:
        # Node extraction (labels)
        if p == RDFS.label:
            sid = str(s)
            if sid not in seen_nodes:
                seen_nodes.add(sid)
                new_nodes.append({
                    "id": sid,
                    "label": str(o),
                    "node_type": "hnc_class",
                    "source_db": "HeNeCOn",
                    "definition": ""
                })

        # Edge extraction (hierarchy)
        if p == RDFS.subClassOf:
            new_edges.append({
                "source": str(s),
                "target": str(o),
                "relation": "subclassof",
                "source_db": "HeNeCOn",
                "weight": 1
            })

    print(f"    Loaded {len(new_nodes)} nodes, {len(new_edges)} edges from OWL")
    return new_nodes, new_edges

# ── Load HeNeCOn OWL ─────────────────────────────
OWL_PATH = os.path.join(BASE, "hencon", "HeNeCOn.owl")

if os.path.exists(OWL_PATH):
    hn_nodes, hn_edges = load_henecon_owl(OWL_PATH)

    nodes_df = pd.concat([nodes_df, pd.DataFrame(hn_nodes)], ignore_index=True)
    edges_df = pd.concat([edges_df, pd.DataFrame(hn_edges)], ignore_index=True)

    print(f"  After HeNeCOn merge → nodes: {len(nodes_df):,}, edges: {len(edges_df):,}")
else:
    print("  WARNING: HeNeCOn.owl not found!")

# ── Build graph index AFTER OWL merge ────────────
node_by_id = {r["id"]: r.to_dict() for _, r in nodes_df.iterrows()}

edges_by_src = defaultdict(list)
edges_by_tgt = defaultdict(list)

for _, e in edges_df.iterrows():
    ed = e.to_dict()
    edges_by_src[ed["source"]].append(ed)
    edges_by_tgt[ed["target"]].append(ed)

# ── palette ───────────────────────────────────────────────────
NODE_COLORS = {
    "gene":      "#4C9BE8",
    "cancer":    "#E8724C",
    "mutation":  "#F0C040",
    "hnc_class": "#8E6BBF",
    "tissue":    "#52B788",
}
EDGE_COLORS = {
    "driver":             "#FF6B6B",
    "oncogene":           "#FFD93D",
    "tumor_suppressor":   "#6BCB77",
    "mutated_in":         "#4ECDC4",
    "has_mutation":       "#C77DFF",
    "subclassof":         "#ADB5BD",
    "mapped_to_ontology": "#F8961E",
}
REL_DESC = {
    "driver":             "Driver: gene is frequently mutated and actively promotes cancer",
    "oncogene":           "Oncogene: activating mutation makes the gene over-active",
    "tumor_suppressor":   "Tumor suppressor: when broken, this brake on cell division is lost",
    "mutated_in":         "Mutated in: COSMIC somatic mutations detected in this tissue",
    "has_mutation":       "Has mutation: this specific COSV variant found in this gene",
    "subclassof":         "SubClassOf: child concept is a specialisation of parent (HeNeCOn)",
    "mapped_to_ontology": "Ontology cross-link: label matches a HeNeCOn clinical concept",
}

# ── helpers ───────────────────────────────────────────────────
def node_to_vis(r, seed=False):
    ntype = str(r.get("node_type","gene"))
    return {
        "id":         r["id"],
        "label":      str(r.get("label",""))[:18],
        "full_label": str(r.get("label","")),
        "node_type":  ntype,
        "color":      NODE_COLORS.get(ntype,"#888"),
        "size":       28 if seed else 14,
        "borderWidth":3 if seed else 1,
        "seed":       seed,
        "definition": str(r.get("definition",""))[:200],
        "source_db":  str(r.get("source_db","")),
    }

def edge_to_vis(e):
    rel = str(e.get("relation","")).lower()
    try:    w = max(1.0, min(6.0, float(e.get("weight",1))*5))
    except: w = 1.5
    try:    cite = int(float(e.get("citation_count",0)))
    except: cite = 0
    return {
        "from":           e["source"],
        "to":             e["target"],
        "relation":       str(e.get("relation","")),
        "color":          EDGE_COLORS.get(rel,"#555"),
        "width":          w,
        "citation_count": cite,
        "source_db":      str(e.get("source_db","")),
    }

def sample_graph(node_ids, edge_list, max_n=120, max_e=150, seed_ids=None):
    seed_ids = seed_ids or set()
    # Prioritise seed nodes + their direct neighbours
    all_nodes = set(node_ids) & set(node_by_id.keys())
    if len(all_nodes) > max_n:
        # Keep seeds first, then sample
        keep = set(seed_ids) & all_nodes
        rest = list(all_nodes - keep)
        np.random.seed(42)
        np.random.shuffle(rest)
        keep.update(rest[:max_n - len(keep)])
        all_nodes = keep

    seen_e = set()
    uniq = []
    for e in edge_list:
        if e["source"] in all_nodes and e["target"] in all_nodes:
            k = (e["source"],e["target"],e.get("relation",""))
            if k not in seen_e:
                seen_e.add(k); uniq.append(e)
    uniq = uniq[:max_e]
    # Only keep nodes referenced by edges + seeds
    ref = set(seed_ids)
    for e in uniq:
        ref.add(e["source"]); ref.add(e["target"])
    all_nodes &= ref

    vis_n = [node_to_vis(node_by_id[nid], nid in seed_ids)
             for nid in all_nodes if nid in node_by_id]
    vis_e = [edge_to_vis(e) for e in uniq
             if e["source"] in all_nodes and e["target"] in all_nodes]
    return vis_n, vis_e




# ════════════════════════════════════════════════════════════
# TAB 1: CancerMine-only subgraph
# genes → cancers via driver/oncogene/tumor_suppressor
# ════════════════════════════════════════════════════════════
print("\n[1/5] Building CancerMine subgraph...")
cm_db_edges = [e.to_dict() for _, e in edges_df.iterrows()
               if str(e.get("source_db","")).lower().startswith("cancermine")
               or str(e.get("relation","")).lower() in
               ("driver","oncogene","tumor_suppressor")]

cm_db_node_ids = set()
for e in cm_db_edges:
    cm_db_node_ids.add(e["source"]); cm_db_node_ids.add(e["target"])
cm_db_node_ids = {n for n in cm_db_node_ids if n in node_by_id}

# Sample: top 60 genes by degree + all their cancer connections
gene_deg = Counter()
for e in cm_db_edges:
    if str(node_by_id.get(e["source"],{}).get("node_type","")) == "gene":
        gene_deg[e["source"]] += 1
top_genes = {g for g,_ in gene_deg.most_common(60)}
top_cancers = set()
for e in cm_db_edges:
    if e["source"] in top_genes:
        top_cancers.add(e["target"])
cm_nodes, cm_edges_vis = sample_graph(
    top_genes | top_cancers, cm_db_edges, max_n=120, max_e=150
)
print(f"  CancerMine: {len(cm_nodes)} nodes, {len(cm_edges_vis)} edges")

# ════════════════════════════════════════════════════════════
# TAB 2: COSMIC-only subgraph
# genes → tissues (mutated_in) + mutations (has_mutation)
# ════════════════════════════════════════════════════════════
print("[2/5] Building COSMIC subgraph...")
cosmic_db_edges = [e.to_dict() for _, e in edges_df.iterrows()
                   if str(e.get("source_db","")).lower().startswith("cosmic")
                   or str(e.get("relation","")).lower() in
                   ("mutated_in","has_mutation")]

cosmic_node_ids = set()
for e in cosmic_db_edges:
    cosmic_node_ids.add(e["source"]); cosmic_node_ids.add(e["target"])
cosmic_node_ids = {n for n in cosmic_node_ids if n in node_by_id}

# Sample: top genes by mutation count
cosmic_gene_deg = Counter()
for e in cosmic_db_edges:
    if str(node_by_id.get(e["source"],{}).get("node_type","")) == "gene":
        cosmic_gene_deg[e["source"]] += 1
top_cg = {g for g,_ in cosmic_gene_deg.most_common(50)}
top_tissues = set(); top_muts = set()
for e in cosmic_db_edges:
    if e["source"] in top_cg:
        nt = str(node_by_id.get(e["target"],{}).get("node_type",""))
        if nt == "tissue":   top_tissues.add(e["target"])
        if nt == "mutation": top_muts.add(e["target"])
cosmic_nodes, cosmic_edges_vis = sample_graph(
    top_cg | top_tissues | set(list(top_muts)[:30]),
    cosmic_db_edges, max_n=120, max_e=150
)
print(f"  COSMIC:     {len(cosmic_nodes)} nodes, {len(cosmic_edges_vis)} edges")

# ════════════════════════════════════════════════════════════
# TAB 3: HeNeCOn-only subgraph
# hnc_class nodes + subclassof + mapped_to_ontology edges
# ════════════════════════════════════════════════════════════
print("[3/5] Building HeNeCOn subgraph...")
hnc_db_edges = [e.to_dict() for _, e in edges_df.iterrows()
                if ("hen" in str(e.get("source_db","")).lower()
                or str(e.get("relation","")).lower() in ("subclassof","mapped_to_ontology"))]

hnc_node_ids = set()
for e in hnc_db_edges:
    hnc_node_ids.add(e["source"]); hnc_node_ids.add(e["target"])
hnc_node_ids = {n for n in hnc_node_ids if n in node_by_id}

# Find top parent nodes in hierarchy
# ── Use real ontology nodes directly (NO sampling loss)
hnc_class_nodes = {
    nid for nid, n in node_by_id.items()
    if n.get("node_type") == "hnc_class"
}

# Take a subset (otherwise too big)
hnc_class_nodes = set(list(hnc_class_nodes)[:120])

# Filter edges inside this subset
hnc_edges_filtered = [
    e for e in hnc_db_edges
    if e["source"] in hnc_class_nodes and e["target"] in hnc_class_nodes
]

hnc_nodes, hnc_edges_vis = sample_graph(
    hnc_class_nodes,
    hnc_edges_filtered,
    max_n=120,
    max_e=150,
    seed_ids=hnc_class_nodes   # ⭐ IMPORTANT FIX
)


print(f"  HeNeCOn:    {len(hnc_nodes)} nodes, {len(hnc_edges_vis)} edges")

# ════════════════════════════════════════════════════════════
# TAB 4: Combined — one subgraph per database merged together
# Seed: TP53 + head-and-neck cancer node + top HNC concept
# ════════════════════════════════════════════════════════════
print("[4/5] Building Combined subgraph...")
tp53_id   = "GENE:TP53"
hnc_c_id  = next((n for n in node_by_id
                  if "head and neck" in str(node_by_id[n].get("label","")).lower()
                  and node_by_id[n].get("node_type")=="cancer"), None)
top_hnc_p = next(iter(hnc_class_nodes), None)

seeds_combined = {s for s in [tp53_id, hnc_c_id, top_hnc_p] if s and s in node_by_id}
all_combined_edges = []
combined_nodes_raw = set(seeds_combined)
for sid in seeds_combined:
    for e in edges_by_src.get(sid,[]):
        all_combined_edges.append(e)
        combined_nodes_raw.add(e["target"])
    for e in edges_by_tgt.get(sid,[]):
        all_combined_edges.append(e)
        combined_nodes_raw.add(e["source"])

comb_nodes, comb_edges_vis = sample_graph(
    combined_nodes_raw, all_combined_edges,
    max_n=130, max_e=160, seed_ids=seeds_combined
)
print(f"  Combined:   {len(comb_nodes)} nodes, {len(comb_edges_vis)} edges")

# ════════════════════════════════════════════════════════════
# TAB 5: Curated subgraphs (TP53, KRAS, HNC, Breast Cancer)
# ════════════════════════════════════════════════════════════
print("[5/5] Building curated subgraphs...")

def make_ego(seed_id, max_e=100):
    nbr_nodes = {seed_id}
    nbr_edges = []
    for e in edges_by_src.get(seed_id,[]):
        nbr_nodes.add(e["target"]); nbr_edges.append(e)
    for e in edges_by_tgt.get(seed_id,[]):
        nbr_nodes.add(e["source"]); nbr_edges.append(e)
    return sample_graph(nbr_nodes, nbr_edges, max_n=110, max_e=max_e,
                        seed_ids={seed_id})

curated = []

if tp53_id in node_by_id:
    n,e = make_ego(tp53_id)
    curated.append({
        "key":"tp53","label":"TP53","color":"#4C9BE8",
        "subtitle":"Guardian of the Genome — mutated in 50% of all cancers",
        "description":"TP53 encodes the cell's primary damage sensor (p53). When DNA is damaged p53 halts cell division and triggers repair or apoptosis. It connects to every cancer type where it has a confirmed role in CancerMine, plus COSMIC mutation variants and HeNeCOn ontology links.",
        "steps":[
            ["What is TP53?","TP53 (Tumour Protein P53) is the most important tumour suppressor gene in humans. Its protein product p53 acts as a transcription factor that activates DNA repair, cell cycle arrest, and apoptosis when it detects damaged DNA. Cells with broken TP53 can divide with damaged genomes, accumulating the mutations that drive cancer."],
            ["Why is it the centre?","TP53 has the highest degree (most connections) in the entire knowledge graph. Each edge represents a cancer type where CancerMine literature evidence confirms TP53 plays a role — as a driver (red), oncogene (yellow), or tumour suppressor (green). The node size reflects this central importance."],
            ["Reading edge colours & thickness","Red = driver (TP53 mutations actively push cells toward cancer). Green = tumour suppressor (normal TP53 prevents cancer; broken TP53 fails to). Yellow = oncogene. Thicker lines = more citations supporting that specific TP53-cancer link. Click any cancer node to see its citation count."],
            ["COSMIC mutation variants","Small amber circles are specific COSV mutation IDs from COSMIC — individual DNA typos in TP53 found in real patient tumours. Purple edges (has_mutation) connect TP53 to these variants. Each variant has a unique stable ID so researchers can track it across studies."],
            ["ML use of this subgraph","In a Graph Neural Network, TP53's neighbourhood features form a rich vector: which cancers it connects to, with what roles, with what citation weights. This vector distinguishes TP53 from other genes even without handcrafted features — the graph structure IS the feature."],
        ],
        "nodes":n,"edges":e
    })

kras_id = "GENE:KRAS"
if kras_id in node_by_id:
    n,e = make_ego(kras_id)
    curated.append({
        "key":"kras","label":"KRAS","color":"#FFD93D",
        "subtitle":"The RAS Oncogene — mutated in ~25% of all cancers",
        "description":"KRAS is a molecular switch controlling cell growth. Oncogenic mutations lock it permanently ON, causing uncontrolled proliferation. KRAS was considered 'undruggable' until 2021 when sotorasib (KRAS G12C inhibitor) was FDA-approved.",
        "steps":[
            ["What is KRAS?","KRAS (Kirsten RAS) encodes a small GTPase — a molecular switch that cycles between GTP-bound (active) and GDP-bound (inactive) states. It sits downstream of growth factor receptors and relays the 'grow' signal into the cell. Oncogenic mutations (G12D, G12V, G12C) prevent GTP hydrolysis, trapping KRAS in its active ON state permanently."],
            ["Oncogene vs tumour suppressor","Unlike TP53 (which causes cancer when it breaks/loses function), KRAS causes cancer when it gains function — the mutant is too active. This is why KRAS edges are predominantly yellow (oncogene) rather than green (TSG). The only green edges appear when KRAS loss has been reported in unusual contexts."],
            ["Teal edges — COSMIC tissue data","Teal lines (mutated_in) connect KRAS to tissue nodes from COSMIC. These mean real somatic KRAS mutations were found in patient tumour samples from that tissue. KRAS dominates in pancreatic (~90%), colorectal (~40%), and lung adenocarcinoma (~30%) — visible as the thickest teal edges."],
            ["The drug target breakthrough","KRAS G12C has a unique cysteine residue that sotorasib covalently binds, locking KRAS in its inactive state. This was the first successful direct KRAS inhibitor after 40 years of failed attempts. In the graph, COSV variants encoding G12C appear as amber nodes with the highest edge weights."],
        ],
        "nodes":n,"edges":e
    })

if hnc_c_id and hnc_c_id in node_by_id:
    n,e = make_ego(hnc_c_id)
    curated.append({
        "key":"hnc","label":"Head & Neck","color":"#8E6BBF",
        "subtitle":"Unique — has dedicated HeNeCOn clinical ontology",
        "description":"Head and neck cancer (HNC) is the only cancer in this KG with a dedicated OWL clinical ontology (HeNeCOn). This enables cross-links between gene evidence and formal clinical concepts like anatomy, staging (TNM), and treatment.",
        "steps":[
            ["Why HNC is uniquely connected","HNC is the only cancer type in this KG cross-linked to a clinical ontology. Orange dashed edges (mapped_to_ontology) connect the HNC cancer node to HeNeCOn OWL concepts. This means you can traverse from a gene → its cancer associations → formal clinical definitions, all in one graph."],
            ["Key HNC driver genes","The thickest red (driver) edges point to the most literature-supported HNC driver genes. Look for TP53, CDKN2A (a cell cycle regulator), PIK3CA (PI3K pathway oncogene), and EGFR (growth factor receptor). These represent the most actionable targets in HNC therapy."],
            ["NOTCH1 — context-dependent roles","NOTCH1 is a critical case study: it is an oncogene in T-cell leukaemia (activating mutations) but a tumour suppressor in HNC (loss-of-function mutations). If your graph shows NOTCH1 connected to both cancers with different edge colours, that's the KG capturing this real biological paradox."],
            ["HPV and treatment implications","HPV-positive oropharyngeal cancer (tonsil/base of tongue) has a completely different driver gene landscape than HPV-negative HNC. HPV+ tumours have fewer TP53 mutations but more PI3K pathway alterations. The citation weights on different gene-HNC edges reflect this split biology in the literature."],
        ],
        "nodes":n,"edges":e
    })

breast_id = next((n for n in node_by_id
                  if str(node_by_id[n].get("label","")).lower().strip()=="breast cancer"
                  and node_by_id[n].get("node_type")=="cancer"), None)
if breast_id:
    brca1 = "GENE:BRCA1"; brca2 = "GENE:BRCA2"
    seeds = {s for s in [breast_id,brca1,brca2] if s in node_by_id}
    nbr_nodes = set(seeds); nbr_edges = []
    for sid in seeds:
        for e in edges_by_src.get(sid,[]):
            nbr_nodes.add(e["target"]); nbr_edges.append(e)
        for e in edges_by_tgt.get(sid,[]):
            nbr_nodes.add(e["source"]); nbr_edges.append(e)
    n,e = sample_graph(nbr_nodes, nbr_edges, max_n=110, max_e=100, seed_ids=seeds)
    curated.append({
        "key":"breast","label":"Breast Cancer","color":"#E8724C",
        "subtitle":"BRCA1/2 TSG landscape — 4 molecular subtypes",
        "description":"Multi-seed subgraph: breast cancer node + BRCA1 + BRCA2 (the large bordered nodes). Shows the full driver landscape including germline risk genes and somatic oncogenes across all four molecular subtypes.",
        "steps":[
            ["Multi-seed subgraphs","This subgraph anchors on 3 seeds simultaneously: breast cancer, BRCA1, BRCA2 (large bordered nodes). Seeds act as anchors — the graph shows all nodes connected to any of them. This reveals how genes relate to each other through shared cancer connections, a powerful pattern for drug combination discovery."],
            ["BRCA1 and BRCA2 — DNA repair","BRCA1 (chr17q21) and BRCA2 (chr13q12) encode proteins that repair DNA double-strand breaks via homologous recombination. When mutated, DNA repair fails, causing genomic instability. Germline (inherited) BRCA1/2 mutations confer 70-80% lifetime breast cancer risk. Green edges mark them as tumour suppressors — they must be broken for cancer to develop."],
            ["Four molecular subtypes","The full breast cancer gene landscape reflects 4 subtypes: Luminal A (ESR1/PGR-driven, best prognosis), Luminal B (ESR1+ with high proliferation), HER2-enriched (ERBB2 amplified, 15-20% of cases), Triple-negative (TNBC, no ER/PR/HER2 — BRCA1 mutations most common here). Click each gene to see which subtype its citations emphasise."],
            ["Clinical applications","BRCA1/2 mutations guide treatment decisions: PARP inhibitors (olaparib, niraparib) exploit the DNA repair defect via synthetic lethality. ERBB2/HER2 amplification is targeted by trastuzumab (Herceptin) and pertuzumab. ESR1 mutations drive endocrine therapy resistance. The KG encodes all these relationships via citation-weighted edges."],
        ],
        "nodes":n,"edges":e
    })

print(f"  Curated:    {len(curated)} subgraphs")

# ════════════════════════════════════════════════════════════
# BUILD THE HTML — single self-contained file
# All data embedded as a JS object at the top of the script
# No external data files needed
# ════════════════════════════════════════════════════════════
print("\nBuilding HTML...")

tabs_data = [
    {
        "key":   "cancermine",
        "label": "CancerMine KG",
        "icon":  "CM",
        "color": "#4C9BE8",
        "description": "Knowledge graph built entirely from CancerMine literature mining. Every edge represents a gene-cancer-role triple backed by at least one scientific paper. Node size scales with citation count. Edge colour encodes role type.",
        "nodes": cm_nodes,
        "edges": cm_edges_vis,
        "legend": [
            {"color":"#4C9BE8","label":"Gene (blue)"},
            {"color":"#E8724C","label":"Cancer (orange)"},
            {"color":"#FF6B6B","label":"Driver edge"},
            {"color":"#FFD93D","label":"Oncogene edge"},
            {"color":"#6BCB77","label":"Tumor suppressor edge"},
        ],
        "explain": [
            ["Source","CancerMine v51 — NLP-mined from PubMed + PMC. 38,204 gene-cancer-role triples across 426 cancer types and 1,218 genes."],
            ["What nodes mean","Blue circles = genes. Orange boxes = cancer types. Node size scales with total citation count — bigger = more papers."],
            ["What edges mean","Each coloured line = one confirmed gene-cancer relationship. Red = driver (broken gene pushes cell toward cancer). Yellow = oncogene (over-active gene drives growth). Green = tumour suppressor (broken gene removes a brake on division)."],
            ["Edge thickness","Thicker = more independent papers support that specific gene-cancer-role combination. A thick red edge from TP53 to lung cancer means hundreds of papers confirm TP53 drives lung cancer."],
            ["How this KG was built","1. Read cancermine_collated.tsv row by row. 2. Create Gene node for each unique gene_normalized. 3. Create Cancer node for each unique cancer_normalized. 4. Create edge with relation=role, weight=log10(citation_count)/max_per_cancer."],
        ]
    },
    {
        "key":   "cosmic",
        "label": "COSMIC KG",
        "icon":  "CO",
        "color": "#E8724C",
        "description": "Knowledge graph built from COSMIC v103 MutantCensus and Cancer Mutation Census. Connects genes to the tissues where somatic mutations were detected in real patient tumour samples.",
        "nodes": cosmic_nodes,
        "edges": cosmic_edges_vis,
        "legend": [
            {"color":"#4C9BE8","label":"Gene (blue)"},
            {"color":"#52B788","label":"Tissue (green)"},
            {"color":"#F0C040","label":"Mutation variant (amber)"},
            {"color":"#4ECDC4","label":"Mutated in (teal edge)"},
            {"color":"#C77DFF","label":"Has mutation (purple edge)"},
        ],
        "explain": [
            ["Source","COSMIC v103 — 1.4M+ tumour samples, 38M+ somatic mutations from 29,000+ publications. Two files: MutantCensus (723 CGC genes) and CancerMutationCensus (all genes)."],
            ["What nodes mean","Blue circles = genes. Green boxes = primary tissues (body sites where tumours were collected). Small amber circles = individual mutation variants (COSV IDs — unique stable identifiers for each DNA change)."],
            ["Teal edges — mutated_in","A teal line from gene → tissue means: at least one somatic mutation in this gene was found in a tumour sample from this tissue. Edge width scales with how many unique samples carried that mutation."],
            ["Purple edges — has_mutation","A purple line from gene → amber circle means: this specific DNA variant (e.g., KRAS p.G12D = COSV51765119) was found in this gene. Each COSV ID is traceable across all COSMIC versions."],
            ["How this KG was built","1. Read MutantCensus TSV. 2. Create Gene nodes from GENE_SYMBOL. 3. Create Tissue nodes from PRIMARY_SITE (if available). 4. Create Mutation nodes from GENOMIC_MUTATION_ID. 5. Create mutated_in edges (gene→tissue) and has_mutation edges (gene→mutation)."],
        ]
    },
    {
        "key":   "hencon",
        "label": "HeNeCOn KG",
        "icon":  "HN",
        "color": "#8E6BBF",
        "description": "Knowledge graph built from the HeNeCOn OWL ontology — a formal clinical taxonomy for Head & Neck Cancer. Every node is a clinically defined concept. Edges show is-a hierarchical relationships.",
        "nodes": hnc_nodes,
        "edges": hnc_edges_vis,
        "legend": [
            {"color":"#8E6BBF","label":"HNC concept (purple)"},
            {"color":"#4C9BE8","label":"Gene (blue, cross-linked)"},
            {"color":"#E8724C","label":"Cancer (orange, cross-linked)"},
            {"color":"#ADB5BD","label":"SubClassOf (grey edge)"},
            {"color":"#F8961E","label":"Ontology cross-link (orange)"},
        ],
        "explain": [
            ["Source","HeNeCOn OWL2 ontology — 502 clinical classes, 283 semantic definitions, mapped to SNOMED CT, ICD-O-3, NCIt, and UBERON. Built by the BD2Decide EU consortium (Madrid)."],
            ["What nodes mean","Purple boxes = formally defined HNC clinical concepts. Domain breakdown: Anatomy (oral cavity, larynx, pharynx), Staging (T1-T4, N0-N3, M0-M1), Histology (squamous cell carcinoma, adenocarcinoma), Treatment (radiotherapy, surgery, chemotherapy), Risk factors (HPV, tobacco, alcohol)."],
            ["Grey edges — SubClassOf","A grey line from child→parent means the child is a specialisation of the parent. Example: 'oral squamous cell carcinoma' → 'squamous cell carcinoma' → 'carcinoma' → 'malignant neoplasm'. This hierarchy lets computers do reasoning: if a drug treats carcinoma, it logically applies to all subtypes."],
            ["Orange edges — ontology cross-links","Orange dashed lines appear where a gene or cancer label from CancerMine/COSMIC exactly matches a HeNeCOn concept label. This bridges experimental evidence (gene X causes cancer Y, backed by papers) with formal clinical knowledge (what Y means, how it is staged, what anatomy it involves)."],
            ["How this KG was built","1. Parse HeNeCOn.owl with rdflib. 2. Extract OWL classes → HNC concept nodes. 3. Extract rdfs:subClassOf triples → subclassof edges. 4. String-match CancerMine/COSMIC labels against HeNeCOn rdfs:labels → mapped_to_ontology edges."],
        ]
    },
    {
        "key":   "combined",
        "label": "Combined KG",
        "icon":  "ALL",
        "color": "#F0C040",
        "description": "All three databases merged into one knowledge graph. Seed nodes are TP53, head-and-neck cancer, and a top HeNeCOn concept — showing how evidence flows across databases.",
        "nodes": comb_nodes,
        "edges": comb_edges_vis,
        "legend": [
            {"color":"#4C9BE8","label":"Gene"},
            {"color":"#E8724C","label":"Cancer"},
            {"color":"#52B788","label":"Tissue"},
            {"color":"#F0C040","label":"Mutation"},
            {"color":"#8E6BBF","label":"HNC concept"},
        ],
        "explain": [
            ["Three databases, one graph","The combined KG merges CancerMine gene-cancer roles, COSMIC gene-tissue mutations, and HeNeCOn clinical ontology into a single connected graph. Nodes from different databases are linked wherever they share labels (e.g., the gene 'TP53' appears in all three)."],
            ["Seed nodes","This view is anchored on 3 seeds (large bordered nodes): TP53 (gene — appears in CancerMine and COSMIC), head-and-neck cancer (CancerMine cancer node, cross-linked to HeNeCOn), and the top HeNeCOn parent concept. Everything within 1 hop of any seed is shown."],
            ["Cross-database evidence","Look for nodes with BOTH teal edges (COSMIC mutation evidence) AND red/yellow/green edges (CancerMine literature evidence). These genes have double-validated cancer roles — experimental mutation data AND published functional evidence. They are the highest-confidence targets for ML prediction models."],
            ["The unique power of integration","Neither CancerMine nor COSMIC alone tells you: 'this gene has 2,104 papers confirming it drives lung cancer AND somatic mutations in 37% of lung tumour samples AND maps to the formal HeNeCOn concept for pulmonary malignancy.' The combined KG answers all three simultaneously."],
            ["Overall KG statistics","Total: 176,956 nodes | 200,727 edges. Node types: 1,218 genes, ~40,000 cancers, ~30 tissues, ~130,000 mutations, 502 HNC concepts. Edge types: 7 relation types across 3 source databases."],
        ]
    },
]

print(f"  Tab sizes: CM={len(cm_nodes)}n/{len(cm_edges_vis)}e  "
      f"CO={len(cosmic_nodes)}n/{len(cosmic_edges_vis)}e  "
      f"HN={len(hnc_nodes)}n/{len(hnc_edges_vis)}e  "
      f"ALL={len(comb_nodes)}n/{len(comb_edges_vis)}e  "
      f"curated={len(curated)}")

# Serialise
tabs_json    = json.dumps(tabs_data,    ensure_ascii=False)
curated_json = json.dumps(curated,      ensure_ascii=False)
rel_json     = json.dumps(REL_DESC,     ensure_ascii=False)

# ── Build final HTML ──────────────────────────────────────────
html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cancer KG Explorer</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',sans-serif;background:#0a0a14;color:#e0e0e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}

/* top nav */
#topnav{background:#12122a;border-bottom:1px solid #2d2d4e;padding:0 16px;display:flex;align-items:stretch;gap:2px;flex-shrink:0;height:46px}
.logo{font-size:13px;font-weight:700;color:#a0c4ff;display:flex;align-items:center;margin-right:12px;white-space:nowrap}
.tab-btn{padding:0 16px;border:none;border-bottom:3px solid transparent;background:transparent;color:#888;font-size:12px;cursor:pointer;transition:all .15s;white-space:nowrap;font-weight:500;display:flex;align-items:center;gap:6px}
.tab-btn:hover{color:#ccc;background:#ffffff08}
.tab-btn.on{color:#e0e0e0;border-bottom-color:#a0c4ff}
.tab-icon{width:22px;height:22px;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;flex-shrink:0}

/* main split */
#main{flex:1;display:flex;overflow:hidden}

/* left panel */
#left{width:320px;min-width:320px;display:flex;flex-direction:column;overflow:hidden;border-right:1px solid #2d2d4e}
#tab-header{padding:12px 14px;border-bottom:1px solid #2d2d4e;flex-shrink:0;background:#0f0f1a}
#tab-header h2{font-size:14px;font-weight:600;margin-bottom:4px}
#tab-header p{font-size:11px;color:#777;line-height:1.5}
#explain-scroll{flex:1;overflow-y:auto;padding:12px}
.exp-card{background:#12122a;border-radius:7px;border-left:3px solid #a0c4ff;padding:10px 12px;margin-bottom:8px;cursor:pointer;transition:background .1s}
.exp-card:hover{background:#1a1a3a}
.exp-card.open{background:#1a1a3a}
.exp-title{font-size:11px;font-weight:600;color:#a0c4ff;margin-bottom:0}
.exp-body{font-size:11px;color:#aaa;line-height:1.6;margin-top:6px;display:none}
.exp-body.show{display:block}
.legend-section{padding:10px 14px;border-top:1px solid #2d2d4e;flex-shrink:0;background:#0f0f1a}
.leg-title{font-size:9px;font-weight:600;color:#555;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
.leg-rows{display:flex;flex-wrap:wrap;gap:5px 12px}
.lr{display:flex;align-items:center;gap:4px;font-size:10px;color:#aaa}
.lc{width:9px;height:9px;border-radius:50%;flex-shrink:0}
.ll{width:16px;height:2.5px;flex-shrink:0;border-radius:1px}

/* curated panel (tab 5) */
#curated-panel{flex:1;overflow-y:auto;padding:12px;display:none}
.cur-btn{width:100%;text-align:left;background:#12122a;border:1px solid #2d2d4e;border-radius:8px;padding:10px 12px;margin-bottom:7px;cursor:pointer;transition:all .15s}
.cur-btn:hover{background:#1a1a3a;border-color:#3a3a6e}
.cur-btn.on{border-color:#a0c4ff;background:#1a1a3a}
.cur-label{font-size:13px;font-weight:600}
.cur-sub{font-size:11px;color:#777;margin-top:2px}
#cur-detail{padding:12px 14px;border-top:1px solid #2d2d4e;flex-shrink:0;overflow-y:auto;max-height:250px;background:#0f0f1a}
#step-nav{display:flex;align-items:center;gap:6px;padding:8px 12px;border-bottom:1px solid #2d2d4e;flex-shrink:0;background:#0f0f1a}
.sarrow{background:transparent;border:1px solid #2d2d4e;color:#888;padding:3px 8px;border-radius:4px;cursor:pointer;font-size:12px}
.sarrow:hover{background:#12122a;color:#e0e0e0}
#step-dots{display:flex;gap:4px}
.sdot{width:6px;height:6px;border-radius:50%;cursor:pointer;background:#2d2d4e;flex-shrink:0}
.sdot.on{background:#a0c4ff}
#step-num{font-size:10px;color:#666;margin-left:auto}

/* graph area */
#right{flex:1;position:relative}
#graph-canvas{width:100%;height:100%;background:#080812}
#graph-btns{position:absolute;top:8px;right:10px;display:flex;gap:5px;z-index:10}
.gbtn{background:#12122acc;border:1px solid #2d2d4e;color:#aaa;padding:4px 10px;border-radius:5px;font-size:11px;cursor:pointer}
.gbtn:hover{background:#1a1a2e;color:#e0e0e0}
.gbtn.on{background:#a0c4ff;color:#06060f;border-color:#a0c4ff;font-weight:600}
#graph-stats{position:absolute;bottom:8px;left:10px;display:flex;gap:5px;z-index:10}
.spill{background:#12122acc;border:1px solid #2d2d4e;border-radius:12px;padding:3px 9px;font-size:10px;color:#888}
.spill b{color:#a0c4ff}
#insp{position:absolute;bottom:8px;right:10px;background:#12122acc;border:1px solid #2d2d4e;border-radius:8px;padding:9px 11px;font-size:10px;z-index:10;max-width:220px;max-height:200px;overflow-y:auto;display:none}
#insp-name{font-size:11px;font-weight:600;margin-bottom:5px}
.irow{display:flex;gap:5px;margin-bottom:2px}
.ik{color:#555;min-width:55px}
.iv{color:#ccc}

::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-track{background:#0a0a14}
::-webkit-scrollbar-thumb{background:#2d2d4e;border-radius:2px}
</style>
</head>
<body>

<div id="topnav">
  <span class="logo">Cancer KG Explorer</span>
  <div id="tab-btns" style="display:flex;align-items:stretch"></div>
</div>

<div id="main">
  <div id="left">
    <div id="tab-header">
      <h2 id="tab-h2">Loading...</h2>
      <p id="tab-p"></p>
    </div>

    <!-- Explanation cards (tabs 1-4) -->
    <div id="explain-scroll">
      <div id="explain-inner"></div>
    </div>

    <!-- Curated subgraph list (tab 5) -->
    <div id="curated-panel">
      <div id="cur-list"></div>
    </div>

    <!-- Step viewer (tab 5) -->
    <div id="step-nav" style="display:none">
      <button class="sarrow" onclick="prevStep()">&#8592;</button>
      <div id="step-dots"></div>
      <button class="sarrow" onclick="nextStep()">&#8594;</button>
      <span id="step-num"></span>
    </div>
    <div id="cur-detail" style="display:none"></div>

    <!-- Legend -->
    <div class="legend-section" id="legend-section">
      <div class="leg-title">Legend</div>
      <div class="leg-rows" id="legend-rows"></div>
    </div>
  </div>

  <div id="right">
    <div id="graph-canvas"></div>
    <div id="graph-btns">
      <button class="gbtn" onclick="network&&network.fit()">Reset</button>
      <button class="gbtn on" id="phys-btn" onclick="togglePhysics()">Physics ON</button>
    </div>
    <div id="graph-stats">
      <div class="spill">Nodes: <b id="nc">0</b></div>
      <div class="spill">Edges: <b id="ec">0</b></div>
    </div>
    <div id="insp">
      <div id="insp-name">Node inspector</div>
      <div id="insp-body"></div>
    </div>
  </div>
</div>

<script>
// ── Data ──────────────────────────────────────────────────────
var TABS    = __TABS_JSON__;
var CURATED = __CURATED_JSON__;
var REL_DESC= __REL_JSON__;

// ── State ─────────────────────────────────────────────────────
var network = null, physOn = true;
var curTab = 0, curCurated = 0, curStep = 0;

// ── Build top tabs ────────────────────────────────────────────
var tabWrap = document.getElementById('tab-btns');
TABS.forEach(function(t, i) {
  var btn = document.createElement('button');
  btn.className = 'tab-btn' + (i===0?' on':'');
  btn.innerHTML = '<span class="tab-icon" style="background:'+t.color+'22;color:'+t.color+'">'+t.icon+'</span>'+t.label;
  btn.onclick = function(){ switchTab(i); };
  tabWrap.appendChild(btn);
});
// Curated tab
var curBtn = document.createElement('button');
curBtn.className = 'tab-btn';
curBtn.innerHTML = '<span class="tab-icon" style="background:#a0c4ff22;color:#a0c4ff">SUB</span>Curated';
curBtn.onclick = function(){ switchTab(TABS.length); };
tabWrap.appendChild(curBtn);

// ── Switch tab ────────────────────────────────────────────────
function switchTab(idx) {
  curTab = idx;
  document.querySelectorAll('.tab-btn').forEach(function(b,i){ b.classList.toggle('on',i===idx); });

  var isCurated = (idx === TABS.length);
  document.getElementById('explain-scroll').style.display  = isCurated ? 'none' : '';
  document.getElementById('curated-panel').style.display   = isCurated ? '' : 'none';
  document.getElementById('step-nav').style.display        = isCurated ? '' : 'none';
  document.getElementById('cur-detail').style.display      = isCurated ? '' : 'none';
  document.getElementById('legend-section').style.display  = isCurated ? 'none' : '';

  if (isCurated) {
    document.getElementById('tab-h2').textContent = 'Curated Subgraphs';
    document.getElementById('tab-p').textContent  = 'Deep-dive subgraphs with step-by-step explanations.';
    buildCuratedList();
    loadCurated(curCurated);
  } else {
    var t = TABS[idx];
    document.getElementById('tab-h2').style.color = t.color;
    document.getElementById('tab-h2').textContent = t.label;
    document.getElementById('tab-p').textContent  = t.description;
    buildExplain(t);
    buildLegend(t);
    buildGraph(t.nodes, t.edges);
  }
}

// ── Explanation cards ─────────────────────────────────────────
function buildExplain(t) {
  var inner = document.getElementById('explain-inner');
  inner.innerHTML = '';
  (t.explain||[]).forEach(function(pair, i) {
    var card = document.createElement('div');
    card.className = 'exp-card' + (i===0?' open':'');
    card.innerHTML = '<div class="exp-title">'+pair[0]+'</div>'+
      '<div class="exp-body'+(i===0?' show':'')+'">'+pair[1]+'</div>';
    card.onclick = function() {
      var body = card.querySelector('.exp-body');
      var isOpen = body.classList.contains('show');
      inner.querySelectorAll('.exp-body').forEach(function(b){ b.classList.remove('show'); });
      inner.querySelectorAll('.exp-card').forEach(function(c){ c.classList.remove('open'); });
      if (!isOpen) { body.classList.add('show'); card.classList.add('open'); }
    };
    inner.appendChild(card);
  });
}

// ── Legend ────────────────────────────────────────────────────
function buildLegend(t) {
  var rows = document.getElementById('legend-rows');
  rows.innerHTML = '';
  (t.legend||[]).forEach(function(item) {
    var isEdge = item.label.toLowerCase().includes('edge') ||
                 item.label.toLowerCase().includes('in (') ||
                 item.label.toLowerCase().includes('mutation (');
    var row = document.createElement('div');
    row.className = 'lr';
    var icon = isEdge
      ? '<div class="ll" style="background:'+item.color+'"></div>'
      : '<div class="lc" style="background:'+item.color+'"></div>';
    row.innerHTML = icon + item.label;
    rows.appendChild(row);
  });
}

// ── Curated list ──────────────────────────────────────────────
function buildCuratedList() {
  var list = document.getElementById('cur-list');
  list.innerHTML = '';
  CURATED.forEach(function(c, i) {
    var btn = document.createElement('div');
    btn.className = 'cur-btn' + (i===curCurated?' on':'');
    btn.innerHTML = '<div class="cur-label" style="color:'+c.color+'">'+c.label+'</div>'+
      '<div class="cur-sub">'+c.subtitle+'</div>';
    btn.onclick = function(){ curCurated=i; loadCurated(i); };
    list.appendChild(btn);
  });
}

function loadCurated(idx) {
  curCurated = idx; curStep = 0;
  document.querySelectorAll('.cur-btn').forEach(function(b,i){ b.classList.toggle('on',i===idx); });
  var c = CURATED[idx];
  document.getElementById('tab-h2').style.color = c.color;
  document.getElementById('tab-h2').textContent = c.label;
  document.getElementById('tab-p').textContent  = c.description;
  renderCurSteps();
  buildGraph(c.nodes, c.edges);
}

function renderCurSteps() {
  var c = CURATED[curCurated];
  var steps = c.steps||[];
  var dots = document.getElementById('step-dots');
  dots.innerHTML = '';
  steps.forEach(function(_, i) {
    var d = document.createElement('div');
    d.className = 'sdot'+(i===curStep?' on':'');
    d.onclick = (function(j){ return function(){ curStep=j; renderCurSteps(); }; })(i);
    dots.appendChild(d);
  });
  document.getElementById('step-num').textContent = steps.length ? (curStep+1)+'/'+steps.length : '';
  var detail = document.getElementById('cur-detail');
  if (steps[curStep]) {
    detail.innerHTML = '<div style="font-size:11px;font-weight:600;color:#a0c4ff;margin-bottom:5px">'+(curStep+1)+'. '+steps[curStep][0]+'</div>'+
                       '<div style="font-size:11px;color:#aaa;line-height:1.65">'+steps[curStep][1]+'</div>';
  }
}
window.prevStep = function(){ if(CURATED[curCurated]){ curStep=Math.max(0,curStep-1); renderCurSteps(); } };
window.nextStep = function(){ if(CURATED[curCurated]){ curStep=Math.min((CURATED[curCurated].steps||[]).length-1,curStep+1); renderCurSteps(); } };

// ── Build vis.Network ─────────────────────────────────────────
function buildGraph(raw_nodes, raw_edges) {
  var container = document.getElementById('graph-canvas');
  var vnodes = new vis.DataSet(raw_nodes.map(function(n) {
    var tt = document.createElement('div');
    tt.style.cssText = 'background:#12122a;border:1px solid #3a3a6e;border-radius:7px;padding:7px 10px;font-size:11px;max-width:190px;line-height:1.55;font-family:Segoe UI,sans-serif;color:#e0e0e0';
    tt.innerHTML = '<b style="color:'+n.color+'">'+n.full_label+'</b><br><span style="color:#666">'+n.node_type+'</span>'+
      (n.source_db ? '<br><span style="color:#555;font-size:10px">'+n.source_db+'</span>' : '')+
      (n.definition && n.definition.trim() ? '<br><span style="font-size:10px;color:#999">'+n.definition.slice(0,100)+'...</span>' : '');
    return {
      id:n.id, label:n.label, title:tt,
      color:{background:n.color+(n.seed?'':'aa'),border:n.color,
             highlight:{background:'#ffffff',border:n.color},
             hover:{background:'#ffffff',border:n.color}},
      size:n.size, borderWidth:n.borderWidth,
      font:{color:'#ffffff',size:n.seed?12:9,strokeWidth:2,strokeColor:'#00000088'},
      _data:n
    };
  }));
  var vedges = new vis.DataSet(raw_edges.map(function(e,i) {
    var tt = document.createElement('div');
    tt.style.cssText = 'background:#12122a;border:1px solid #3a3a6e;border-radius:7px;padding:6px 10px;font-size:11px;color:#e0e0e0;font-family:Segoe UI,sans-serif;line-height:1.55;max-width:200px';
    var rdesc = REL_DESC[e.relation.toLowerCase()]||e.relation;
    tt.innerHTML = '<b style="color:#a0c4ff">'+e.relation+'</b><br>'+rdesc+
      (e.citation_count ? '<br><span style="color:#666">'+e.citation_count+' citations</span>' : '')+
      '<br><span style="color:#555;font-size:10px">'+e.source_db+'</span>';
    return {
      id:i, from:e.from, to:e.to, title:tt,
      color:{color:e.color,highlight:'#ffffff',hover:e.color+'cc'},
      width:e.width,
      arrows:{to:{enabled:true,scaleFactor:0.45}},
      smooth:{type:'dynamic'},
      _data:e
    };
  }));

  if (network) network.destroy();
  physOn = true;
  document.getElementById('phys-btn').textContent='Physics ON';
  document.getElementById('phys-btn').classList.add('on');

  network = new vis.Network(container,{nodes:vnodes,edges:vedges},{
    physics:{
      stabilization:{iterations:150,updateInterval:25},
      barnesHut:{gravitationalConstant:-7000,springConstant:0.001,
                 springLength:95,damping:0.92,avoidOverlap:0.1}
    },
    interaction:{hover:true,tooltipDelay:80,hideEdgesOnDrag:true,
                 navigationButtons:false,keyboard:false},
    nodes:{shadow:{enabled:true,size:5,color:'#00000033'}},
    edges:{shadow:false,smooth:{type:'dynamic'}}
  });

  document.getElementById('nc').textContent = raw_nodes.length;
  document.getElementById('ec').textContent = raw_edges.length;
  document.getElementById('insp').style.display = 'none';

  network.on('stabilizationIterationsDone', function() {
    network.setOptions({physics:{enabled:false}});
    physOn=false;
    document.getElementById('phys-btn').textContent='Physics OFF';
    document.getElementById('phys-btn').classList.remove('on');
  });

  network.on('click', function(params) {
    if (!params.nodes.length) { document.getElementById('insp').style.display='none'; return; }
    var nid=params.nodes[0], nd=vnodes.get(nid);
    if (!nd||!nd._data) return;
    showInspector(nid, nd._data, raw_edges);
  });
}

function showInspector(nid, n, raw_edges) {
  var conE = raw_edges.filter(function(e){ return e.from===nid||e.to===nid; });
  var relC = {};
  conE.forEach(function(e){ relC[e.relation]=(relC[e.relation]||0)+1; });
  var html = '<div class="irow"><span class="ik">Type</span><span class="iv" style="color:'+n.color+'">'+n.node_type+'</span></div>'+
    '<div class="irow"><span class="ik">Edges</span><span class="iv">'+conE.length+'</span></div>'+
    (n.source_db?'<div class="irow"><span class="ik">Source</span><span class="iv">'+n.source_db+'</span></div>':'')+
    Object.keys(relC).map(function(r){
      return '<div class="irow"><span class="ik" style="color:#666">'+r+'</span><span class="iv">x'+relC[r]+'</span></div>';
    }).join('')+
    (n.definition&&n.definition.trim()?'<div style="margin-top:4px;font-size:10px;color:#888;line-height:1.5">'+n.definition.slice(0,120)+'</div>':'');
  document.getElementById('insp-name').style.color = n.color;
  document.getElementById('insp-name').textContent = n.full_label.slice(0,26);
  document.getElementById('insp-body').innerHTML = html;
  document.getElementById('insp').style.display = '';
}

window.togglePhysics = function() {
  physOn=!physOn;
  if(network) network.setOptions({physics:{enabled:physOn}});
  var btn=document.getElementById('phys-btn');
  btn.textContent=physOn?'Physics ON':'Physics OFF';
  btn.classList.toggle('on',physOn);
};

// ── Init ──────────────────────────────────────────────────────
window.addEventListener('load', function() { switchTab(0); });
</script>
</body>
</html>'''

html = html.replace('__TABS_JSON__',    tabs_json)
html = html.replace('__CURATED_JSON__', curated_json)
html = html.replace('__REL_JSON__',     rel_json)

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = os.path.getsize(OUT) // 1024
print(f"\nWritten: {OUT}")
print(f"Size:    {size_kb} KB")
print()
print("Run: python serve_kg.py")
print("Open: http://localhost:8000/kg_output/all_subgraphs.html")