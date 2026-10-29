"""Run the pipeline in order; stop at the first script that fails (a failed check raises).

    python src/run_all.py              # everything except the download
    python src/run_all.py --fetch      # include 00_fetch.py
    python src/run_all.py --from 03    # start at step 03
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent
args = sys.argv[1:]
start = args[args.index("--from") + 1] if "--from" in args else "00"

scripts = sorted(p for p in SRC.glob("[0-9][0-9]*.py"))
if "--fetch" not in args:
    scripts = [p for p in scripts if not p.name.startswith("00_fetch")]
scripts = [p for p in scripts if p.name[:len(start)] >= start]

for p in scripts:
    print(f"\n=== {p.name} ===")
    r = subprocess.run([sys.executable, str(p)], cwd=SRC.parent)
    if r.returncode:
        print(f"\nSTOPPED at {p.name} (exit {r.returncode}). See output/checks/report.md")
        sys.exit(r.returncode)
print("\nAll steps passed. See output/checks/report.md")
