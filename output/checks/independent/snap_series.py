import re,glob,os,csv
from txt import text
rows=[]
for f in sorted(glob.glob('../../../data/raw/idhs/offices/snap_offices_*.html')):
    ym=re.search(r'(\d{4})_(\d{2})',f).group(0).replace('_','-')
    s=text(f)
    m=re.search(r'COOK COUNTY\s*\|\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)',s)
    sp=re.search(r'SPECIALTY OFFICES\s*\|\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)',s)
    tot=re.search(r'TOTAL STATE\s*\|\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)',s)
    n=lambda x:int(x.replace(',',''))
    rows.append((ym,n(m.group(1)),n(m.group(2)),n(sp.group(2)) if sp else None,n(tot.group(2))))
with open('snap_cook_series.csv','w',newline='') as fh:
    w=csv.writer(fh); w.writerow(['month','hh','persons','specialty_persons','state_persons']); w.writerows(rows)
for r in rows: print(r)
