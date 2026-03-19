# 🧬 Cancer Knowledge Graph (DATASET\_KG)

> A multi-source biomedical knowledge graph integrating **HeNeCOn**, **CancerMine**, and **COSMIC** for cancer gene analysis, network exploration, and machine-learning-ready feature engineering.

---

## 📁 Project Structure

```
DATASET_KG/
│
├── cancermine/                          # CancerMine dataset files
│   ├── cancermine_collated.tsv          # Gene–cancer role aggregates (3.7 MB)
│   ├── cancermine_sentences.tsv         # Source sentences with PMIDs (85.5 MB)
│   └── cancermine_unfiltered.tsv        # Raw ML predictions (263.5 MB)
│
├── cosmic/                              # COSMIC dataset files
│   ├── CancerMutationCensus_AllData_Tsv_v103_GRCh37/
│   │   └── CancerMutationCensus_AllData_v103_GRCh37.tsv   # All somatic mutations
│   └── Cosmic_MutantCensus_Tsv_v103_GRCh37/
│       └── Cosmic_MutantCensus_v103_GRCh37.tsv            # Cancer Gene Census
│
├── hencon/
│   └── HeNeCOn.owl                      # Head & Neck Cancer Ontology (OWL)
│
├── kg_output/                           # Generated knowledge graph outputs
│   ├── cancer_kg.graphml                # Full graph (Gephi / Cytoscape)
│   ├── cancer_kg.html                   # Interactive visualisation (basic)
│   ├── cancer_kg_enhanced.html          # Interactive visualisation (enhanced)
│   ├── cancer_kg_nodes.csv              # All nodes with attributes
│   ├── cancer_kg_edges.csv              # All edges with relations
│   ├── cancer_kg_stats.txt              # Graph statistics summary
│   └── cancer_kg_plot.png               # Static PNG (top 80 nodes)
│
├── build_cancer_kg.py                   # Step 1: Build the knowledge graph
├── enhance_cancer_kg.py                 # Step 2: Generate enhanced HTML viz
└── README.md                            # This file
```

---

## 🗄️ Databases Used

### 1. HeNeCOn — Head and Neck Cancer Ontology

| Property | Details |
|---|---|
| **Full name** | Head and Neck Cancer Ontology |
| **Type** | OWL ontology (semantic knowledge base) |
| **Format** | `.owl` (XML/RDF serialisation) |
| **Classes** | 502 ontology classes |
| **Definitions** | 283 semantic term definitions |
| **License** | Creative Commons (CC BY) — Open Access |
| **Source paper** | Hernández et al., *Int. J. Medical Informatics*, Vol. 181, Jan 2024 |
| **DOI** | [10.1016/j.ijmedinf.2023.105284](https://doi.org/10.1016/j.ijmedinf.2023.105284) |
| **Direct link** | [ScienceDirect paper page](https://www.sciencedirect.com/science/article/pii/S1386505623003027) |

**What it contains:**
HeNeCOn is the first ontology specifically dedicated to Head and Neck Cancer (HNC). It provides a formal, machine-readable taxonomy of:
- Anatomical sites (tongue, larynx, pharynx, salivary glands, etc.)
- Histological subtypes (squamous cell carcinoma, adenocarcinoma, etc.)
- TNM staging system classes (T1–T4, N0–N3, M0–M1)
- Treatment modalities (surgery, radiotherapy, chemotherapy, immunotherapy)
- Risk factors (HPV, tobacco, alcohol exposure)
- Clinical outcomes and follow-up concepts

**Cross-references mapped to:**
`SNOMED CT` · `ICD-O-3` · `NCI Thesaurus (NCIt)` · `UBERON` (anatomy)

**How to access:**
The OWL file is distributed as supplementary data with the paper. Contact the corresponding author at `giuseppe.fico@upm.es` if direct download is needed, or access via institutional ScienceDirect subscription.

---

### 2. CancerMine — Literature-mined Cancer Gene Roles

| Property | Details |
|---|---|
| **Full name** | CancerMine: A literature-mined resource for drivers, oncogenes and tumor suppressors |
| **Type** | Text-mined knowledgebase (NLP-extracted) |
| **Format** | Tab-separated values (`.tsv`) |
| **Genes catalogued** | 856+ drivers · 2,421+ oncogenes · 2,037+ tumor suppressors |
| **Cancer types** | 426 distinct cancer types |
| **Update frequency** | Monthly (automated re-mining of PubMed + PMC) |
| **License** | Creative Commons Zero (CC0) — No restrictions |
| **Source paper** | Lever et al., *Nature Methods*, 2019 |
| **DOI** | [10.1038/s41592-019-0422-y](https://doi.org/10.1038/s41592-019-0422-y) |
| **Download** | [Zenodo DOI: 10.5281/zenodo.1156241](https://doi.org/10.5281/zenodo.1156241) |
| **Web viewer** | [bionlp.bcgsc.ca/cancermine](http://bionlp.bcgsc.ca/cancermine) |
| **GitHub** | [github.com/jakelever/cancermine](https://github.com/jakelever/cancermine) |

**What it contains:**

| File | Description | Size |
|---|---|---|
| `cancermine_collated.tsv` | One row per (gene, cancer, role) triple with citation counts and normalised importance score | 3.7 MB |
| `cancermine_sentences.tsv` | Every source sentence from PubMed that supports a gene–cancer role, with PMID and journal metadata | 85.5 MB |
| `cancermine_unfiltered.tsv` | All raw ML model predictions above score 0.5 (higher false-positive rate) | 263.5 MB |

**Key columns in `cancermine_collated.tsv`:**

| Column | Description |
|---|---|
| `gene_normalized` | HUGO gene symbol (e.g. `TP53`, `KRAS`) |
| `cancer_normalized` | Normalised cancer type name |
| `cancer_id` | Disease Ontology ID (e.g. `DOID:162`) |
| `role` | `Driver` / `Oncogene` / `Tumor_Suppressor` |
| `citation_count` | Number of papers supporting this gene–cancer–role triple |

**How to download:**
```bash
# Method 1 — zenodo_get CLI
pip install zenodo_get
python -m zenodo_get 10.5281/zenodo.1156241

# Method 2 — Direct URL
# https://zenodo.org/records/16849846/files/cancermine_collated.tsv?download=1
```

---

### 3. COSMIC — Catalogue of Somatic Mutations in Cancer

| Property | Details |
|---|---|
| **Full name** | Catalogue Of Somatic Mutations In Cancer |
| **Type** | Expert-curated somatic variant database |
| **Format** | Tab-separated values (`.tsv.gz`) |
| **Version used** | v103 (GRCh37 coordinates) |
| **Mutations** | 38M+ somatic coding mutations |
| **Tumour samples** | 1.4M+ |
| **Publications curated** | 29,000+ |
| **Cancer Gene Census** | 723 causally implicated genes |
| **License** | Free for academic use (registration required) · Commercial licence via Qiagen |
| **Source paper** | Sondka et al., *Nucleic Acids Research*, 2024 |
| **DOI** | [10.1093/nar/gkad986](https://doi.org/10.1093/nar/gkad986) |
| **Download portal** | [cancer.sanger.ac.uk/cosmic/download](https://cancer.sanger.ac.uk/cosmic/download) |
| **Registration** | [cancer.sanger.ac.uk/cosmic/register](https://cancer.sanger.ac.uk/cosmic/register) |

**Files used in this project:**

| File | Description | Size |
|---|---|---|
| `CancerMutationCensus_AllData_v103_GRCh37.tsv` | All somatic coding mutations with sample, tissue, histology and pathogenicity metadata | ~285 MB |
| `Cosmic_MutantCensus_v103_GRCh37.tsv` | Significance-scored annotations per mutation from the Cancer Mutation Census (CMC) | ~96 MB |

**Key columns:**

| Column | Description |
|---|---|
| `GENE_SYMBOL` | HGNC gene symbol |
| `PRIMARY_SITE` | Tissue / organ of origin |
| `HISTOLOGY` | Histological classification |
| `GENOMIC_MUTATION_ID` | Stable COSV identifier |
| `FATHMM_PREDICTION` | `PATHOGENIC` or `NEUTRAL` functional impact |
| `TIER` | CGC confidence tier (1 = high confidence cancer gene) |

**How to download:**
```bash
pip install gget
python -c "
import gget
# Downloads CancerMutationCensus (~285 MB)
gget.cosmic(searchterm=None, download_cosmic=True,
            cosmic_project='cancer', out='cosmic/')
# Downloads MutantCensus / Cancer Gene Census (~96 MB)
gget.cosmic(searchterm=None, download_cosmic=True,
            cosmic_project='census', out='cosmic/')
"
# Will prompt for your COSMIC email and password
```

---

## 🕸️ Knowledge Graph — Structure & Schema

### Graph Type
**Directed, heterogeneous, multi-relational property graph**
- Built with **NetworkX** (`DiGraph`)
- Exported as **GraphML**, **CSV**, and interactive **HTML**
- Supports **GNN training** via PyTorch Geometric export

### Node Types

| Node Type | Colour | Count (approx.) | Source |
|---|---|---|---|
| 🔵 **Gene** | `#4C9BE8` Blue | ~5,000–8,000 | CancerMine + COSMIC |
| 🟠 **Cancer** | `#E8724C` Coral | ~420+ | CancerMine |
| 🟢 **Tissue** | `#52B788` Teal | ~30–50 | COSMIC |
| 🟡 **Mutation** | `#F0C040` Amber | ~50,000–100,000 | COSMIC |
| 🟣 **HNC Concept** | `#8E6BBF` Purple | 502 | HeNeCOn OWL |

### Edge (Relation) Types

| Relation | Colour | Direction | Source |
|---|---|---|---|
| `driver` | 🔴 Red | Gene → Cancer | CancerMine |
| `oncogene` | 🟡 Yellow | Gene → Cancer | CancerMine |
| `tumor_suppressor` | 🟢 Green | Gene → Cancer | CancerMine |
| `mutated_in` | 🩵 Cyan | Gene → Tissue | COSMIC |
| `has_mutation` | 🟣 Purple | Gene → Mutation | COSMIC |
| `subClassOf` | ⚪ Gray | HNC → HNC | HeNeCOn OWL |
| `mapped_to_ontology` | 🟠 Orange | Gene/Cancer → HNC | Cross-link |

### Graph Schema Diagram

```
                     ┌─────────────────────────────────────┐
                     │         HeNeCOn OWL Ontology         │
                     │  HNC Concept ──subClassOf──▶ HNC     │
                     └────────────────┬────────────────────┘
                                      │ mapped_to_ontology
                                      ▼
 ┌────────────┐    driver/oncogene    ┌────────────┐
 │    GENE    │ ─────────────────────▶│   CANCER   │
 │  (blue)    │ ──tumor_suppressor──▶ │  (coral)   │
 └─────┬──────┘                       └────────────┘
       │ mutated_in
       ▼
 ┌────────────┐
 │   TISSUE   │    (from COSMIC primary sites)
 │  (teal)    │
 └────────────┘
       │
       │ has_mutation (Gene → Mutation)
       ▼
 ┌────────────┐
 │  MUTATION  │    (COSV stable IDs from COSMIC)
 │  (amber)   │
 └────────────┘
```

### Edge Properties

Each edge carries metadata used for ML feature engineering:

| Property | Description |
|---|---|
| `weight` | Normalised importance score (log₁₀ citation count, normalised per cancer type) |
| `citation_count` | Raw number of PubMed papers supporting the relation |
| `pathogenic` | Boolean — FATHMM predicts pathogenic effect (COSMIC edges) |
| `tier` | COSMIC CGC confidence tier (1 or 2) |
| `source_db` | Origin database (`CancerMine`, `COSMIC_CMC`, `HeNeCOn`, `cross_link`) |

---

## 📊 Graph Statistics

```
Total Nodes  : ~8,000–10,000  (depending on COSMIC rows loaded)
Total Edges  : ~50,000–100,000

Node breakdown:
  gene           : ~5,000–8,000
  mutation       : ~40,000–80,000
  cancer         : ~420
  hnc_class      : 502
  tissue         : ~30–50

Top most-connected genes (highest degree):
  TP53, KRAS, PIK3CA, PTEN, BRCA1, BRCA2, EGFR,
  APC, RB1, VHL, CDKN2A, MYC, BRAF, CDH1, NOTCH1
```

*Exact counts depend on how many COSMIC rows are loaded (capped at 300,000 by default).*

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install pandas rdflib networkx pyvis tqdm matplotlib numpy gget
```

### 2. Download datasets
```bash
# CancerMine (free, no login)
python -m zenodo_get 10.5281/zenodo.1156241
# Move the 3 TSV files to cancermine/

# COSMIC (free registration at cancer.sanger.ac.uk/cosmic/register)
python -c "import gget; gget.cosmic(searchterm=None, download_cosmic=True, cosmic_project='cancer', out='cosmic/')"
python -c "import gget; gget.cosmic(searchterm=None, download_cosmic=True, cosmic_project='census', out='cosmic/')"

# HeNeCOn: request from giuseppe.fico@upm.es (CC BY licence)
# or download supplement from DOI: 10.1016/j.ijmedinf.2023.105284
http://ontology.lst.tfo.upm.es/BD2D/
```

### 3. Build the knowledge graph
```bash
python build_cancer_kg.py
```

### 4. Generate enhanced interactive visualisation
```bash
python enhance_cancer_kg.py
```

### 5. Open in browser
```
kg_output/cancer_kg_enhanced.html    # Enhanced interactive graph
kg_output/cancer_kg.html             # Basic interactive graph
```

---

## 🖥️ Interactive Visualisation Features

The enhanced HTML graph (`cancer_kg_enhanced.html`) includes:

| Feature | Description |
|---|---|
| 🔍 **Search bar** | Instantly find any gene, cancer type, or tissue by name |
| 🎛 **Filter panel** | Toggle node types and edge relation types on/off |
| 📊 **Stats tab** | Bar charts of edge breakdown and top genes by connectivity |
| 🔬 **Node inspector** | Click any node to see type, degree, all relations, and clickable neighbours |
| 👁 **Highlight mode** | Hover a node to dim all non-connected nodes |
| 📐 **Citation slider** | Filter CancerMine edges by minimum citation count |
| ⏸ **Physics toggle** | Freeze or unfreeze the force-directed layout |
| ⟳ **Reset view** | Fit the full graph back into view |

---

## 📂 Output Files

| File | Format | Use case |
|---|---|---|
| `cancer_kg_enhanced.html` | HTML (self-contained) | Interactive exploration in any browser |
| `cancer_kg.html` | HTML (self-contained) | Lightweight basic visualisation |
| `cancer_kg.graphml` | GraphML XML | Load in **Gephi** or **Cytoscape** for advanced layout |
| `cancer_kg_nodes.csv` | CSV | Node table for ML feature engineering |
| `cancer_kg_edges.csv` | CSV | Edge table for ML / graph analysis |
| `cancer_kg_stats.txt` | Plain text | Summary statistics |
| `cancer_kg_plot.png` | PNG (150 DPI) | Static image of top 80 nodes |

---

## 🤖 Using the Graph for ML / GNN

The graph is designed to feed directly into graph neural network frameworks:

```python
import pandas as pd
import networkx as nx
from torch_geometric.utils import from_networkx

# Load from CSV outputs
nodes = pd.read_csv('kg_output/cancer_kg_nodes.csv')
edges = pd.read_csv('kg_output/cancer_kg_edges.csv')

# Or load from GraphML
G = nx.read_graphml('kg_output/cancer_kg.graphml')

# Convert to PyTorch Geometric
data = from_networkx(G)
# data.x  = node features
# data.edge_index = connectivity
# data.edge_attr  = edge weights / relation types
```

**Suggested ML tasks on this graph:**
- **Cancer gene classification** — predict driver / oncogene / tumor suppressor role for novel genes
- **Link prediction** — predict new gene–cancer associations not yet in literature
- **Cancer subtype clustering** — cluster cancers by shared gene profiles
- **Drug target discovery** — find highly connected hub genes in specific cancer subgraphs

---

## 📖 Citation

If you use this knowledge graph in your research, please cite the three source databases:

```bibtex
@article{hencon2024,
  title   = {HeNeCOn: An ontology for integrative research in Head and Neck cancer},
  author  = {Hern{\'a}ndez, Liss and Est{\'e}vez-Priego, Estefan{\'i}a and others},
  journal = {International Journal of Medical Informatics},
  volume  = {181},
  year    = {2024},
  doi     = {10.1016/j.ijmedinf.2023.105284}
}

@article{cancermine2019,
  title   = {CancerMine: a literature-mined resource for drivers, oncogenes and tumor suppressors in cancer},
  author  = {Lever, Jake and Zhao, Eric Y and Grewal, Jasleen and Jones, Martin and Jones, Steven},
  journal = {Nature Methods},
  year    = {2019},
  doi     = {10.1038/s41592-019-0422-y}
}

@article{cosmic2024,
  title   = {COSMIC: a curated database of somatic variants and clinical data for cancer},
  author  = {Sondka, Zbyslaw and Bindal Dhir, Nidhi and Carvalho-Silva, Denise and others},
  journal = {Nucleic Acids Research},
  volume  = {52},
  number  = {D1},
  pages   = {D1210--D1217},
  year    = {2024},
  doi     = {10.1093/nar/gkad986}
}
```

---

## 🔗 Key Links

| Resource | URL |
|---|---|
| HeNeCOn paper | https://doi.org/10.1016/j.ijmedinf.2023.105284 |
| CancerMine web viewer | http://bionlp.bcgsc.ca/cancermine |
| CancerMine Zenodo | https://doi.org/10.5281/zenodo.1156241 |
| CancerMine GitHub | https://github.com/jakelever/cancermine |
| COSMIC download portal | https://cancer.sanger.ac.uk/cosmic/download |
| COSMIC registration | https://cancer.sanger.ac.uk/cosmic/register |
| COSMIC paper | https://doi.org/10.1093/nar/gkad986 |

---

## ⚖️ Licences

| Database | Licence | Commercial use |
|---|---|---|
| HeNeCOn | CC BY 4.0 | ✅ Allowed with attribution |
| CancerMine | CC0 (public domain) | ✅ Fully free |
| COSMIC | Free for academics | ❌ Requires commercial licence (Qiagen) |

---

*Built with Python · NetworkX · PyVis · rdflib · pandas · gget*