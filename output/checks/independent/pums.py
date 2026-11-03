import pandas as pd, numpy as np
R='../../../data/raw/pums/'
cols=['SERIALNO','SPORDER','ADJINC','PWGTP','AGEP','DRAT','FER','HINS3','HINS4','MIL','PAP','RELSHIPP','SCH','SSIP','WKHP','WKL','DIS','ESR','PERNP','RACAIAN']
p=pd.read_csv(R+'pums_2024_5yr_cook.csv',usecols=cols,dtype={'SERIALNO':str})
h=pd.read_csv(R+'pums_2024_5yr_housing_cook.csv',usecols=['SERIALNO','FS'],dtype={'SERIALNO':str})
p=p.merge(h,on='SERIALNO',how='left')
print('persons',len(p),'weighted pop',p.PWGTP.sum())
for c in ['FER','PAP','SSIP','WKHP','PERNP','DRAT','SCH','WKL','ESR']: p[c]=pd.to_numeric(p[c],errors='coerce')
g=p.groupby('SERIALNO')
p['hh_kid18']=g.AGEP.transform(lambda a:(a<18).sum())>0
p['hh_kid14']=g.AGEP.transform(lambda a:(a<14).sum())>0
p['hh_ndis']=g.DIS.transform(lambda d:(d==1).sum())
p['other_dis']=(p.hh_ndis-(p.DIS==1).astype(int))>0
emp=p.ESR.isin([1,2,4,5])
earn=p.PERNP.fillna(0)*p.ADJINC/1e6/12
w80=(p.WKHP.fillna(0)>=20)&(p.WKL==1)
compliant=w80|(earn>=580)|p.SCH.isin([2,3])
gq=p.RELSHIPP.isin([37,38])
# --- Medicaid ACA-like, broad universe
caret=p.RELSHIPP.isin([20,21,22,23,24])&p.hh_kid18
U=(p.AGEP.between(19,64))&(p.HINS4==1)&(p.HINS3==2)&~(p.SSIP.fillna(0)>0)&~caret
ex=(p.FER==1)|(p.DIS==1)|((p.MIL.isin([2,3]))&(p.DRAT==5))|(p.RACAIAN==1)|p.other_dis \
   |((p.PAP.fillna(0)>0)&emp)|((p.FS==1)&w80)
W=p.PWGTP
u=W[U].sum(); a=W[U&~ex].sum()/u*(1-0.02); b=W[U&~ex&~compliant].sum()/u*(1-0.02)
print(f'ACA-like weighted {u:,.0f} ({u/364204:.0%} of HFS); share a {a:.3f}; share b {b:.3f}')
# --- SNAP time-limited (H.R.1 ABAWD: 18-64, no child<14 in hh, not unfit/pregnant/AIAN/caregiver)
S=(p.FS==1)&~gq
tl=S&p.AGEP.between(18,64)&~p.hh_kid14&(p.DIS!=1)&~(p.SSIP.fillna(0)>0)&(p.FER!=1)&(p.RACAIAN!=1)&~p.other_dis
tl_strict=tl&~(emp&(p.WKHP.fillna(0)>=30))&~p.SCH.isin([2,3])
for nm,m in [('time-limited (broad)',tl),('time-limited excl 30h workers & students',tl_strict),('time-limited & not 80h',tl&~w80)]:
    print(f'{nm}: {W[m].sum():,.0f} = {W[m].sum()/W[S].sum():.3f} of SNAP persons {W[S].sum():,.0f}')
pd.Series({'share_a':a,'share_b':b,'tl':W[tl].sum()/W[S].sum(),'tl_strict':W[tl_strict].sum()/W[S].sum()}).to_csv('pums_shares.csv')
