import pandas as pd, numpy as np
sh=pd.read_csv('pums_shares.csv',index_col=0).iloc[:,0]
w1=pd.read_csv('wave1.csv',index_col=0).iloc[:,0]
ratio=881937/851244
# ---------------- SNAP
E=61985            # May-Jun 2026 excess beyond trend (office), from snap_calc.py
apr26=752497; sep26=640932
out={}
for tlname in ['tl','tl_strict']:
    s=sh[tlname]; pool26=s*apr26; rate=E/pool26
    low=rate*(pool26-E); high=rate*s*sep26; mid=(low+high)/2
    w2={'low':low,'mid':mid*ratio,'high':high*ratio}
    print(tlname,f'pool {pool26:,.0f} rate {rate:.3f} wave2', {k:round(v) for k,v in w2.items()})
    out[tlname]={k:w1[k]+w2[k] for k in w2}
for k,v in out.items(): print('SNAP off Dec 2028',k,{a:round(b) for a,b in v.items()})
snap=out['tl']
print('SNAP fed $ 2028 mid', snap['mid']*195*12/1e6,'M')
# ---------------- Medicaid
base=364204; nc_il=9300; nc_sh={'low':0.44,'mid':0.59968,'high':0.59968}
wr={'low':.18,'mid':.29,'high':.42}; rd={'low':.08,'mid':.15,'high':.15}; pw={'low':0,'mid':.03,'high':.06}
pmpm=700e6/69768/12; print('PMPM',pmpm)
months=pd.period_range('2026-10','2028-12',freq='M')
res={}
for sc in ['low','mid','high']:
    nc=nc_il*nc_sh[sc]
    a=sh['share_a']; subj=base*a; paper=base*(1-a)*pw[sc]; subj_rate=(wr[sc]*base-paper)/subj
    rows=[]
    for m in months:
        # work req: cohorts renew Mar 2027..Feb 2028, loss month after (Apr 2027..Mar 2028)
        k_wr=sum(1 for i in range(12) if pd.Period('2027-04','M')+i<=m)
        k_rd=sum(1 for i in range(12) if pd.Period('2027-10','M')+i<=m)
        rows.append(nc+wr[sc]*base*k_wr/12+rd[sc]*base*k_rd/12)
    s=pd.Series(rows,index=months); res[sc]=s
    mm28=s['2028-01':'2028-12'].sum()
    print(sc,f'noncit {nc:,.0f} subj_rate {subj_rate:.3f} off Dec2028 {s.iloc[-1]:,.0f}; 2028 member-months {mm28:,.0f}; fed $ {mm28*pmpm*.9/1e9:.3f}B; state $ {mm28*pmpm*.1/1e6:.0f}M')
# alt: renewals applied to people still enrolled (after WR + noncit)
for sc in ['low','mid','high']:
    nc=nc_il*nc_sh[sc]; alt=nc+wr[sc]*base+rd[sc]*(base-nc-wr[sc]*base)
    print('alt renewals-on-remaining',sc,round(alt))
# ---------------- overlap (mid) crude: independence within ACA-like adults
m=res['mid'].iloc[-1]; sn=snap['mid']
print('mid Medicaid',round(m),'SNAP',round(sn))
pd.DataFrame({'snap':snap,'mcd':{k:v.iloc[-1] for k,v in res.items()}}).to_csv('my_results.csv')
