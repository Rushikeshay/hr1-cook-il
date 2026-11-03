"""Step 8b: build the article preview (story/template.html -> output/story/preview.html).

Inlines the data the page needs (ledger values by id, SNAP series, zip results, map shapes) so the page works as a
single file. Every number in the text is a [data-id] filled from the ledger at load time; this step fails if the
template references an id the ledger doesn't have.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, ROOT  # noqa: E402

STEP = "07b_story_preview"
ck = Checks(STEP)
tpl = (ROOT / "story" / "template.html").read_text(encoding="utf-8")
B = json.loads((OUT / "story" / "story_data.json").read_text(encoding="utf-8"))
geo = json.loads((OUT / "story" / "cook_zcta.geojson").read_text(encoding="utf-8"))

values = {r["id"]: r["value"] for r in B["ledger"]}
ids = sorted(set(re.findall(r'data-id="([^"]+)"', tpl)))
ids = sorted(set(ids) | {i for grp in re.findall(r'data-sum="([^"]+)"', tpl) for i in grp.split(",")})
missing = [i for i in ids if i not in values]
ck.equal("every number id in the template exists in the ledger", missing, [], detail=f"{len(ids)} ids used")
zips_used = set(z for grp in re.findall(r'data-zips="([^"]+)"', tpl) for z in grp.split(","))
zip_ids = {z["zcta"] for z in B["zips"]}
ck.equal("every zip named in the text exists in the zip results", sorted(zips_used - zip_ids), [])
geo_ids = {f["properties"]["zcta"] for f in geo["features"]}
ck.equal("map shapes and zip results cover the same 177 zips", sorted(geo_ids ^ zip_ids), [])

# the page also reads these ids in its scripts (scenario totals, people grid), not only in [data-id] spans
script_ids = {k: values[k] for k in values if k.startswith(("ovl_", "mcd_off", "snap_persons_off", "mcd_usd_", "snap_usd_"))}
for k in ["mcd_subject_people", "mcd_subject_noncompliant_people"]:
    script_ids[k] = values[k]
data = {"meta": B["meta"], "values": {i: values[i] for i in ids} | script_ids,
        "snap": B["snap_series"], "monthly": B["monthly"], "zips": B["zips"], "geo": geo,
        "profile_both": B["profile_both"], "triangulation": B["triangulation"]}
ck.equal("Medicaid monthly series covers Oct 2025-Dec 2028 for 3 scenarios", len(B["monthly"]), 117)
payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
assert "/*__DATA__*/" in tpl
html = tpl.replace("/*__DATA__*/", payload)
out = OUT / "story" / "preview.html"
out.write_text(html, encoding="utf-8")
kb = out.stat().st_size / 1024
ck.between("preview size reasonable (< 2 MB)", kb, 50, 2048, detail=f"{kb:.0f} KB")
print(f"preview: {out} ({kb:.0f} KB, {len(ids)} ledger ids in text)")
ck.finish()
