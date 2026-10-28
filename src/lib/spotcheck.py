"""Human spot-check sheets: random rows from a parsed table next to where they came from.

The reviewer opens the source (file + page/row) and ticks each row. Sign-offs live in
output/checks/spot_checks.md; a step's sheet is regenerated only if its parsed data changed.

    spot_check("01a_snap_offices", df, source_col="source_ref", n=5, seed=1)
"""
import hashlib

from .common import CHECKS

SHEET = CHECKS / "spot_checks.md"


def spot_check(step, df, source_col, n=5, seed=1, cols=None):
    sample = df.sample(min(n, len(df)), random_state=seed)
    cols = cols or [c for c in df.columns if c != source_col]
    digest = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()[:12]
    header = f"## {step} (data hash {digest})"

    text = SHEET.read_text(encoding="utf-8") if SHEET.exists() else "# Spot checks\n\nOpen each source, compare, tick the box and initial.\n"
    if header in text:
        return  # same data already has a sheet (possibly signed off); keep it
    # drop any older sheet for this step (data changed -> needs fresh review)
    parts = text.split("\n## ")
    text = parts[0] + "".join("\n## " + p for p in parts[1:] if not p.startswith(f"{step} "))

    lines = ["", header, "", "| ok | " + " | ".join(cols) + " | where to look |", "|---" * (len(cols) + 2) + "|"]
    for _, r in sample.iterrows():
        lines.append("| [ ] | " + " | ".join(str(r[c]) for c in cols) + f" | {r[source_col]} |")
    lines += ["", "Reviewed by: ______  date: ______", ""]
    SHEET.write_text(text.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")
    print(f"  spot-check sheet written for {step} ({len(sample)} rows) -> {SHEET.name}")
