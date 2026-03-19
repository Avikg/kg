"""
diagnose_cosmic.py
Prints exact column names from your COSMIC files.
Run: python diagnose_cosmic.py
"""
import os, sys

BASE    = os.path.dirname(os.path.abspath(__file__))
CSM_DIR = os.path.join(BASE, "cosmic")

print("=" * 65)
print("COSMIC COLUMN DIAGNOSTICS")
print("=" * 65)

found = False
for root, dirs, files in os.walk(CSM_DIR):
    for fname in sorted(files):
        if not fname.endswith(".tsv"):
            continue
        found = True
        path  = os.path.join(root, fname)
        size  = os.path.getsize(path) / 1024 / 1024
        print(f"\nFILE : {fname}")
        print(f"SIZE : {size:.1f} MB")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                header = fh.readline().strip().split("\t")
                row1   = fh.readline().strip().split("\t")
                row2   = fh.readline().strip().split("\t")
            print(f"COLS : {len(header)}")
            print(f"\n{'#':>4}  {'COLUMN NAME':<45}  SAMPLE VALUE")
            print("-" * 90)
            for i, (col, val) in enumerate(zip(header, row1)):
                print(f"{i:>4}  {col:<45}  {val[:40]}")
        except Exception as e:
            print(f"ERROR reading: {e}")

if not found:
    print(f"No TSV files found in: {CSM_DIR}")
    print("Check folder structure under cosmic/")

print("\n" + "=" * 65)
print("Copy the column names above and share them to fix describe_databases.py")
print("=" * 65)