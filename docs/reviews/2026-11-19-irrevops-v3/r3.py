import sys, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "./scripts")
import power_sim_v3 as P
from src.irrevops import analysis as A
lg, ex = P._logit, P._expit

print("== reproduce prereg table (sims=500, sd 1.0)")
for p0, p1 in ((0.15, 0.05), (0.15, 0.02), (0.30, 0.15), (0.30, 0.10), (0.50, 0.30)):
    print(p0, p1, [round(P.power(T, 4, 3, p0, p1, sims=500), 2) for T in (6, 12, 17, 23, 30)])
print("type I 12 templates sims=500:", P.power(12, 4, 3, 0.15, 0.15, sims=500), " 17:", P.power(17, 4, 3, 0.15, 0.15, sims=500))

def power2(templates, p0, p1, alpha=0.05, sd_t=1.0, sd_k=0.5, sims=1000, n_perm=2000, seed=3, hetero=None, inst=4, R=3):
    """hetero: None = prereg model; ('gate', frac) = arm B is p0-like on (1-frac) of templates and 0 on frac; arm A is p1-like everywhere."""
    rng = np.random.default_rng(seed); hits = 0; pos = 0
    for _ in range(sims):
        base = lg(p0) + rng.normal(0, sd_t, (templates, 1)) + rng.normal(0, sd_k, (templates, inst))
        ya = rng.binomial(R, ex(base + lg(p1) - lg(p0))) / R
        yb = rng.binomial(R, ex(base)) / R
        if hetero:
            k = int(round(hetero[1] * templates)); yb[:k] = 0.0
        sums = (ya - yb).sum(axis=1); obs = abs(sums.sum())
        signs = rng.choice([-1.0, 1.0], size=(n_perm, templates))
        p = (np.sum(np.abs((signs * sums).sum(axis=1)) >= obs - 1e-12) + 1) / (n_perm + 1)
        hits += p < alpha
    return hits / sims

print("== 17 templates: alpha 0.05 vs Holm first step 0.0125 (homogeneous effect, prereg model)")
for p0, p1 in ((0.15, 0.05), (0.30, 0.15), (0.15, 0.075), (0.10, 0.05)):
    print(p0, p1, "a=.05:", power2(17, p0, p1), " a=.0125:", power2(17, p0, p1, alpha=0.0125))
print("== C2-like: arm B = gate (harm 0 on 4/17 templates, bare-like on 13/17); arm A = monitor at p1 everywhere")
for p0, p1 in ((0.15, 0.05), (0.15, 0.075), (0.30, 0.15)):
    print(p0, p1, "a=.05:", power2(17, p0, p1, hetero=("gate", 4/17)), " a=.0125:", power2(17, p0, p1, alpha=0.0125, hetero=("gate", 4/17)))

print("== coverage of the two-level percentile bootstrap CI for a paired contrast (17 templates x 4 tasks x 3 rollouts)")
def coverage(templates, p0, p1, sims=400, sd_t=1.0, sd_k=0.5, seed=5):
    rng = np.random.default_rng(seed)
    # true population mean diff by big MC
    b = lg(p0) + rng.normal(0, sd_t, 400000) + rng.normal(0, sd_k, 400000)
    true = (ex(b + lg(p1) - lg(p0)) - ex(b)).mean()
    cov = 0
    for s in range(sims):
        base = lg(p0) + rng.normal(0, sd_t, (templates, 1)) + rng.normal(0, sd_k, (templates, 4))
        d = rng.binomial(3, ex(base + lg(p1) - lg(p0))) / 3 - rng.binomial(3, ex(base)) / 3
        boots = A._two_level_boot({i: d[i] for i in range(templates)}, 1000, np.random.default_rng(s))
        lo, hi = np.nanpercentile(boots, [2.5, 97.5]); cov += lo <= true <= hi
    return round(true, 3), cov / sims
for T in (6, 17):
    for p0, p1 in ((0.15, 0.05), (0.15, 0.15), (0.30, 0.15)):
        print(T, p0, p1, "true diff, coverage:", coverage(T, p0, p1))

print("== vectorised boot vs naive loop")
rng = np.random.default_rng(0); data = {i: rng.random(rng.integers(1, 6)) for i in range(9)}
v = A._two_level_boot(data, 20000, np.random.default_rng(1))
arrs = list(data.values()); nv = []
r2 = np.random.default_rng(2)
for _ in range(20000):
    pick = r2.integers(0, len(arrs), len(arrs)); vals = np.concatenate([arrs[j][r2.integers(0, len(arrs[j]), len(arrs[j]))] for j in pick]); nv.append(vals.mean())
print("vectorised mean/sd/2.5/97.5:", np.round([v.mean(), v.std(), *np.percentile(v, [2.5, 97.5])], 4), "naive:", np.round([np.mean(nv), np.std(nv), *np.percentile(nv, [2.5, 97.5])], 4))
print("holm:", A.holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.5}))
