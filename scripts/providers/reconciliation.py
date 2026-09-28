from __future__ import annotations

def _close(a,b,abs_tol=1e-6,rel_tol=1e-6):
    if a is None or b is None: return a == b
    try:
        da=abs(float(a)-float(b)); scale=max(abs(float(a)),abs(float(b)),1.0)
        return da <= max(abs_tol, rel_tol*scale)
    except Exception:
        return a == b

def reconcile(a,b, absolute_tolerance=1e-6, relative_tolerance=1e-6):
    keys=lambda r:(r.get('listing_id'),r.get('trade_date'))
    A={keys(r):r for r in a}; B={keys(r):r for r in b}; allk=set(A)|set(B); same=[]; different=[]
    fields=['open','high','low','close','volume','turnover']
    for k in sorted(allk):
      if k in A and k in B:
        diffs={f:(A[k].get(f),B[k].get(f)) for f in fields if not _close(A[k].get(f),B[k].get(f),absolute_tolerance,relative_tolerance)}
        (same if not diffs else different).append({'key':k,'fields':diffs})
    return {'same':len(same),'different':len(different),'missing_a':len(set(B)-set(A)),'missing_b':len(set(A)-set(B)),'differences':different,'absolute_tolerance':absolute_tolerance,'relative_tolerance':relative_tolerance}
