import pandas as pd
exec(open('pums.py').read().split('# --- SNAP')[0])
S=(p.FS==1)&~gq
tl=S&p.AGEP.between(18,64)&~p.hh_kid14&(p.DIS!=1)&~(p.SSIP.fillna(0)>0)&(p.FER!=1)&(p.RACAIAN!=1)&~p.other_dis
f=W[U&S].sum()/W[U].sum(); ftl=W[U&tl].sum()/W[U&S].sum(); acainsnap_share=W[U&S].sum()/W[S].sum()
print(f'ACA-like in SNAP hh {f:.3f}; of those time-limited {ftl:.3f}; ACA-like as share of SNAP persons {acainsnap_share:.3f}; tl that are ACA-like {W[U&tl].sum()/W[tl].sum():.3f}')
mcd=165827-5577; snap=229448; snapP=881937  # Sep 2025 residence
# independent: P(snap loss) uniform among SNAP persons
ind=mcd*f*snap/snapP
# correlated: every ACA-like SNAP-household Medicaid loser also loses SNAP, capped by SNAP losers who are ACA-like
hi=min(mcd*f, snap*acainsnap_share)
print('both independent',round(ind),'correlated',round(hi),'mid',round((ind+hi)/2))
c=(ind+hi)/2; print('unique',round(165827+snap-c))
