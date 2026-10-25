#!/usr/bin/env python3
"""Diagnostics for theory/review-alternatives.md (existing corpora only)."""
import statistics as st
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import human_model as hm

rows = hm.load(); keys = hm.FEATURE_KEYS
H = [r for r in rows if r['batch'] == 'human']
# A: whether AI feature variance follows human feature variance.
hv = np.array([np.var([r[k] for r in H]) for k in keys])
print('A_variance_corr', {b: round(float(np.corrcoef(hv, [np.var([r[k] for r in rows if r['batch']==b]) for k in keys])[0,1]), 3) for b in ['v1','v2','v3']})
# C: directional marker rates (per 1,000 CJK; de/pronouns/connectives/negation).
for b in ['human','v1','v2','v3']:
    rr = [r for r in rows if r['batch']==b]
    print('C_markers', b, {k: round(st.mean(r[k] for r in rr), 2) for k in ['de','pron1','pron2','connective','negation']})
# D: AI distance to human genre centroid versus human genre medoid.
Xall = hm.zmatrix(H); genres = sorted({r['genre'] for r in H})
for b in ['v1','v2','v3']:
    A = [r for r in rows if r['batch']==b]; Xall = hm.zmatrix(H+A); X, XA = Xall[:len(H)], Xall[len(H):]; vals=[]
    for g in genres:
        hi=[i for i,r in enumerate(H) if r['genre']==g]; ai=[i for i,r in enumerate(A) if r['genre']==g]
        med=min(hi, key=lambda i: sum(np.linalg.norm(X[i]-X[j]) for j in hi)); cen=X[hi].mean(0)
        vals.append((np.mean([np.linalg.norm(XA[j]-X[med]) for j,i in enumerate(ai)]), np.mean([np.linalg.norm(XA[j]-cen) for j,i in enumerate(ai)])))
    print('D_medoid_centroid', b, {'medoid':round(float(np.mean([x[0] for x in vals])),2), 'centroid':round(float(np.mean([x[1] for x in vals])),2)})
