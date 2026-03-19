"""
download_all_cancer_datasets.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Downloads HeNeCOn + CancerMine + COSMIC into DATASET_KG/

Run from your Dataset_KG folder:
    python download_all_cancer_datasets.py

Requirements:
    pip install requests gget rdflib tqdm
"""

import os, sys, json, shutil, zipfile, getpass, subprocess, time
import requests
from tqdm import tqdm

BASE = os.path.dirname(os.path.abspath(__file__))
DIRS = {
    "cancermine": os.path.join(BASE, "cancermine"),
    "hencon":     os.path.join(BASE, "hencon"),
    "cosmic":     os.path.join(BASE, "cosmic"),
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

def download_file(url, dest, label=""):
    """Stream-download with progress bar."""
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    with open(dest, "wb") as f, tqdm(
        desc=label or os.path.basename(dest),
        total=total, unit="B", unit_scale=True, unit_divisor=1024
    ) as bar:
        for chunk in r.iter_content(65536):
            f.write(chunk)
            bar.update(len(chunk))
    return dest


# ══════════════════════════════════════════════════════════════
# 1.  CANCERMINE  — CC0, no login required
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  [1/3] CancerMine  (Zenodo CC0 — no login needed)")
print("="*60)

ZENODO_RECORD = "https://zenodo.org/api/records/7524290"
try:
    meta  = requests.get(ZENODO_RECORD, timeout=30).json()
    files = meta["files"]
    for f in files:
        fname = f["key"]
        dest  = os.path.join(DIRS["cancermine"], fname)
        if os.path.exists(dest):
            print(f"  ✓ Already exists: {fname}  (skipping)")
            continue
        print(f"\n  → Downloading: {fname}")
        download_file(f["links"]["self"], dest, fname)
        print(f"    Saved → {dest}")
    print("\n  ✅ CancerMine complete")
except Exception as e:
    print(f"  ✗ CancerMine error: {e}")
    print("  Manual fallback:")
    print("    python -m zenodo_get 10.5281/zenodo.1156241")
    print(f"    Then move the 3 TSV files to: {DIRS['cancermine']}")


# ══════════════════════════════════════════════════════════════
# 2.  HENCON  — Open Access paper, OWL via Zenodo/direct URL
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  [2/3] HeNeCOn OWL Ontology")
print("="*60)

HENCON_URLS = [
    # Primary: Zenodo record linked from paper
    ("https://zenodo.org/record/8356871/files/HeNeCOn.owl", "HeNeCOn.owl"),
    # Fallback 1: Zenodo search result
    ("https://zenodo.org/record/8356871/files/hencon.owl",  "hencon.owl"),
    # Fallback 2: OBO Foundry
    ("https://raw.githubusercontent.com/BD2Decide/HeNeCOn/main/hencon.owl", "hencon.owl"),
]

hencon_done = False
for url, fname in HENCON_URLS:
    dest = os.path.join(DIRS["hencon"], fname)
    if os.path.exists(dest):
        print(f"  ✓ Already exists: {fname}  (skipping)")
        hencon_done = True
        break
    try:
        print(f"  → Trying: {url}")
        r = requests.head(url, timeout=10, allow_redirects=True)
        if r.status_code == 200:
            download_file(url, dest, fname)
            print(f"    Saved → {dest}")
            hencon_done = True
            break
        else:
            print(f"    HTTP {r.status_code} — trying next...")
    except Exception as e:
        print(f"    Error: {e} — trying next...")

if not hencon_done:
    print("\n  ⚠️  HeNeCOn OWL not found at auto-download URLs.")
    print("  The OWL file is attached as supplementary to the paper.")
    print()
    print("  Two options to get it:")
    print()
    print("  OPTION A — Email authors (fastest, they must share it — CC BY license):")
    print("    To: giuseppe.fico@upm.es")
    print("    Subject: HeNeCOn OWL file request")
    print("    Body: Requesting the HeNeCOn.owl supplementary file from")
    print("          DOI: 10.1016/j.ijmedinf.2023.105284")
    print()
    print("  OPTION B — Download from ScienceDirect (if you have access):")
    print("    1. Go to: https://www.sciencedirect.com/science/article/pii/S1386505623003027")
    print("    2. Scroll to 'Supplementary data' section at the bottom")
    print("    3. Download mmc1.zip")
    print(f"    4. Extract the .owl file into: {DIRS['hencon']}")
    print()
    print("  OPTION C — Zenodo search:")
    print("    Go to: https://zenodo.org/search?q=HeNeCOn&type=dataset")
    print(f"    Download the .owl file and place it in: {DIRS['hencon']}")


# ══════════════════════════════════════════════════════════════
# 3.  COSMIC  — Free registration required
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  [3/3] COSMIC (Free academic account required)")
print("="*60)

try:
    import gget
except ImportError:
    print("  Installing gget...")
    subprocess.run([sys.executable, "-m", "pip", "install", "gget", "-q"])
    import gget

COSMIC_FILES = {
    "cancer":  "CosmicMutantExport  (all somatic mutations ~2 GB)",
    "census":  "CancerGeneCensus    (723 curated cancer genes, small)",
}

print()
print("  COSMIC requires a free academic account.")
print("  Register at: https://cancer.sanger.ac.uk/cosmic/register")
print()

email = input("  Enter your COSMIC email (or press Enter to skip): ").strip()
if not email:
    print("  ⏭  Skipping COSMIC. Run this script again after registering.")
    print(f"     Files will be saved to: {DIRS['cosmic']}")
else:
    password = getpass.getpass("  Enter your COSMIC password: ")
    print()
    for project, label in COSMIC_FILES.items():
        print(f"  → Downloading: {label}")
        try:
            gget.cosmic(
                searchterm=None,
                download_cosmic=True,
                cosmic_project=project,
                out=DIRS["cosmic"],
                email=email,
                password=password,
                verbose=True,
            )
            print(f"    ✅ {project} saved to {DIRS['cosmic']}")
        except TypeError:
            # Older gget versions don't accept email/password as args
            # Set env vars instead
            os.environ["COSMIC_EMAIL"]    = email
            os.environ["COSMIC_PASSWORD"] = password
            try:
                gget.cosmic(
                    searchterm=None,
                    download_cosmic=True,
                    cosmic_project=project,
                    out=DIRS["cosmic"],
                    verbose=True,
                )
                print(f"    ✅ {project} saved to {DIRS['cosmic']}")
            except Exception as e2:
                print(f"    ✗ Error: {e2}")
        except Exception as e:
            print(f"    ✗ Error: {e}")


# ══════════════════════════════════════════════════════════════
# 4.  SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  FINAL STATUS")
print("="*60)

expected = {
    "cancermine/cancermine_collated.tsv":     "CancerMine — gene-cancer roles",
    "cancermine/cancermine_sentences.tsv":    "CancerMine — source sentences",
    "cancermine/cancermine_unfiltered.tsv":   "CancerMine — raw predictions",
    "hencon/hencon.owl":                      "HeNeCOn — OWL ontology",
    "hencon/HeNeCOn.owl":                     "HeNeCOn — OWL ontology (alt name)",
    "cosmic/CancerGeneCensus.csv":            "COSMIC — Cancer Gene Census (723 genes)",
    "cosmic/CosmicMutantExport.tsv.gz":       "COSMIC — All somatic mutations",
}

for rel_path, label in expected.items():
    full = os.path.join(BASE, rel_path)
    if os.path.exists(full):
        size = os.path.getsize(full)
        print(f"  ✅  {rel_path:<42} {size/1024/1024:.1f} MB  — {label}")
    else:
        # Check for any file in the directory
        folder = os.path.join(BASE, rel_path.split("/")[0])
        files_in_dir = os.listdir(folder) if os.path.exists(folder) else []
        if files_in_dir:
            for f in files_in_dir:
                fp = os.path.join(folder, f)
                size = os.path.getsize(fp)
                print(f"  ✅  {rel_path.split('/')[0]}/{f:<38} {size/1024/1024:.1f} MB")
            break
        else:
            print(f"  ❌  {rel_path:<42} NOT FOUND — {label}")

print()
print("  Dataset folder:", BASE)
print("="*60)