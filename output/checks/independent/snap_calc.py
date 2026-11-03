import pandas as pd, numpy as np
d=pd.read_csv('snap_cook_series.csv'); d['t']=pd.PeriodIndex(d.month,freq='M')
d=d.set_index('t'); P=d.persons
def mi(p): return (p.year-2024)*12+p.month-1
# Judgment: pre-trend = log-linear OLS, Jan 2024-Jun 2025 (before the Jul 2025 specialty-office break)
pre=P[(P.index>=pd.Period('2024-01','M'))&(P.index<=pd.Period('2025-06','M'))]
x=np.array([mi(p) for p in pre.index]); b=np.polyfit(x,np.log(pre.values),1)[0]
r=np.exp(b)-1; print('trend rate/mo',r)
# alt: simple endpoint rate
print('endpoint rate', (P['2025-06']/P['2024-01'])**(1/17)-1)
ratio=881937/851244; print('county/office ratio',ratio)
sep=P['2026-09']
def lost(start, flat=False):
    base=pd.Period(start,'M')-1; n=mi(pd.Period('2026-09','M'))-mi(base)
    cf=P[base]*(1 if flat else (1+r)**n); return cf-sep, cf
res={}
for sc,start,flat,adj in [('low','2026-02',False,1.0),('mid','2025-12',False,ratio),('high','2025-10',True,ratio)]:
    l,cf=lost(start,flat); res[sc]=l*adj
    print(sc,'office',round(l),'resid',round(l*adj),'cf',round(cf))
# year-over-year check
print('YoY Sep26 vs Sep25', P['2026-09']-P['2025-09'])
# calibration excess May-Jun 2026 beyond mid trend (office basis): drop Apr->Jun minus trend
apr=P['2026-04']; exc=(apr*(1+r)**2)-P['2026-06']; print('May-Jun excess office',round(exc))
pd.Series(res).to_csv('wave1.csv')
print('r=',r)
