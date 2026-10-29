"""Step 2g: Illinois's announced work-requirement choices vs. the Urban Institute scenario settings (Table A.1).

Each row pairs an Urban scenario setting with what Illinois has actually decided, quoted from HFS documents.
Every quote is checked against the downloaded source file (whitespace-normalized), so the table can't drift from
its sources. Output: output/tables/illinois_vs_urban_scenarios.csv (used in methods and the article).
Root sources behind Urban's behavioral assumptions (Arkansas/New Hampshire) are checked the same way.
"""
import html
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, RAW  # noqa: E402

STEP = "01g_il_vs_urban"
ck = Checks(STEP)


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def pdf_pages(rel):
    with pdfplumber.open(RAW / rel) as pdf:
        return {i + 1: norm(p.extract_text() or "") for i, p in enumerate(pdf.pages)}


def html_text(rel):
    r = (RAW / rel).read_text(encoding="utf-8", errors="replace")
    r = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", r, flags=re.S)
    return {1: norm(html.unescape(re.sub(r"<[^>]+>", " ", r)))}


SRC = {
    "urban": ("rwjf/urban_medicaid_work_req_2028.pdf", "Urban Institute for RWJF (Buettgens, Karpman, Haley, Carter, Kenney), Mar 2026"),
    "hfs_mod3": ("hfs/hr1_module3_work_requirements.pdf", "HFS HR1 Webinar Series Module 3: Work Requirements (draft), Jul 14 2026"),
    "hfs_faq": ("hfs/faq_how_will_fed_changes_impact_medicaid.html", "HFS FAQ: How will federal changes impact Medicaid"),
    "hfs_notice": ("hfs/aca_adult_customer_notice_2026_08.pdf", "HFS ACA Adult customer notice, Aug 31 2026"),
    "kff": ("kff/integration_medicaid_nonhealth_eligibility_systems.html", "KFF: Integration of Medicaid and Non-health Program Eligibility Systems (as of Jan 2026)"),
    "sommers": ("evidence/sommers_2019_nejm_arkansas.pdf", "Sommers et al., NEJM 381:1073-82 (2019), doi:10.1056/NEJMsr1901772"),
    "brookings": ("evidence/brookings_arkansas_style_work_requirement_2025.pdf", "Brookings working paper on Arkansas-style work requirement enrollment effects (2025)"),
}
TEXT = {k: (pdf_pages(f) if f.endswith(".pdf") else html_text(f)) for k, (f, _) in SRC.items()}


def find(src, quote, page=None):
    q = norm(quote)
    pages = TEXT[src] if page is None else {page: TEXT[src].get(page, "")}
    hit = [n for n, t in pages.items() if q in t]
    ok = ck.true(f"quote found in {src}{' p' + str(page) if page else ''}: {quote[:60]}", bool(hit))
    return hit[0] if ok else None


# dimension, Urban high / medium / low, Urban quote (A.1 p55), Illinois choice, IL source, IL quote, page, match
ROWS = [
    ("Months of compliance required", "1 month", "3 months", "3 months", "1 month 3 months 3 months",
     "One compliant month per 6-month period", "hfs_mod3", "Illinois has chosen one month.", 11, "high"),
    ("Self-employed: data and/or self-attestation", "Yes", "No", "No", None,
     "Self-attestation accepted for anything its data can't verify (2027)", "hfs_mod3",
     "the state will accept self-attestation of activities which cannot be verified through our interfaces/data sources",
     22, "high"),
    ("Students identifiable in data", "Yes, 50%", "Yes, 20%", "No", "Yes, 50% Yes, 20% No",
     "Enrollment status from the National Student Clearinghouse", "hfs_mod3",
     "through the National Student Clearinghouse", 19, "high (data source in place; coverage share unknown)"),
    ("SNAP data match (exemption for SNAP work-rule participants)", "95% integrated / 67% other",
     "75% / 33%", "67% / 20%", "S NAP match, integrated states 95% 75% 67%",
     "Shared HFS-DHS eligibility system; SNAP exemption applied automatically", "hfs_faq",
     "HFS and DHS share the same eligibility system", None,
     "high, or better than Urban assumed: KFF (used by Urban) lists Illinois as not integrated for SNAP"),
    ("Medical frailty", "Claims data + self-attestation of ADL difficulty, broad", "Claims data, broad",
     "No claims data or self-attestation, narrow", None,
     "Broad definition incl. difficulty with daily activities; verification method awaits CMS guidance", "hfs_faq",
     "makes it hard for you to perform daily activities", None, "high (definition); verification method not yet set"),
]

out = []
for dim, hi, md, lo, uq, il, src, q, pg, match in ROWS:
    if uq:
        find("urban", uq, 55)
    page = find(src, q, pg)
    out.append(dict(dimension=dim, urban_high_mitigation=hi, urban_medium=md, urban_low_mitigation=lo,
                    illinois_choice=il, illinois_quote=q, illinois_source=SRC[src][1],
                    illinois_file=SRC[src][0], illinois_page=page, illinois_matches_urban=match))

# KFF row that Urban used to classify Illinois
find("kff", "Illinois SBM No No No No")
# behavioral assumptions (not state choices) and their roots
BEHAV = [
    ("Share of manual verifiers who do not respond", "65%", "75%", "87%", "urban", "Share of manual verifiers who do not 65% 75% 87%", 55),
    ("Re-enroll after removal", "30%", "25%", "20%", "urban", "Share of those disenrolled from work 30% 25% 20%", 55),
    ("Arkansas/NH: share auto-cleared by data; noncompliant among the rest", "", "", "", "urban",
     "72 percent in Arkansas and 82 percent in New Hampshire", None),
    ("Arkansas: removed from Medicaid by Dec 2018", "", "", "", "sommers", "nearly 17,000", None),
    ("Arkansas: >95% of those targeted were working or exempt", "", "", "", "urban",
     "more than 95 percent of enrollees who had been subject to Arkansas's work requirement appeared to qualify", None),
    ("Arkansas: return rate of removed enrollees (8.4% first month, 3.4% after)", "", "", "", "brookings", "8.4% rate", None),
]
for name, hi, md, lo, src, q, pg in BEHAV:
    page = find(src, q, pg)
    out.append(dict(dimension=name, urban_high_mitigation=hi, urban_medium=md, urban_low_mitigation=lo,
                    illinois_choice="not a state choice (behavior)", illinois_quote=q, illinois_source=SRC[src][1],
                    illinois_file=SRC[src][0], illinois_page=page, illinois_matches_urban=""))

# HFS's own estimate (triangulation only; method not published)
page = find("hfs_mod3", "Internal estimates show that between 165,000 and 330,000 Illinoisans will lose Medicaid coverage", 8)
find("hfs_mod3", "About 700,000 Illinoisans (ACA Adults) will be subject to Medicaid work requirements", 8)
tab = pd.DataFrame(out)
tab.to_csv(OUT / "tables" / "illinois_vs_urban_scenarios.csv", index=False)
n_high = tab.illinois_matches_urban.str.startswith("high").sum()
ck.equal("Illinois matches Urban's high-mitigation setting on all 5 decided dimensions", int(n_high), 5)
print(tab[["dimension", "illinois_choice", "illinois_matches_urban"]].to_string(index=False))
ck.finish()
