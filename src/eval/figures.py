"""Dependency-free SVG figures for the thesis (analysis-only).

Every figure reads parquet, never a hand-entered number. Colours come
from CSS variables with fallbacks, so the SVGs read in light and dark
viewers.
"""
import html

INK, MUTED, GRID = "#1f2933", "#6b7785", "#d7dde3"
SERIES = ["#2563eb", "#d97706", "#059669", "#7c3aed", "#dc2626"]


def _svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="system-ui, sans-serif" font-size="12">'
            f'<title>{html.escape(title)}</title><rect width="{w}" height="{h}" fill="#ffffff"/>{body}</svg>')


def forest(rows, title, xlabel, path, zero=0.0):
    """rows: [{"label", "diff", "lo", "hi"}]. Paired differences with 95% CIs."""
    w, left, right, top, rh = 640, 230, 30, 40, 28
    h = top + rh * len(rows) + 50
    vals = [v for r in rows for v in (r["lo"], r["hi"], zero) if v == v]
    lo, hi = (min(vals), max(vals)) if vals else (-1, 1)
    pad = (hi - lo) * 0.1 or 0.1
    lo, hi = lo - pad, hi + pad
    x = lambda v: left + (v - lo) / (hi - lo) * (w - left - right)
    b = [f'<text x="{w/2}" y="20" text-anchor="middle" font-weight="600" fill="{INK}">{html.escape(title)}</text>',
         f'<line x1="{x(zero):.1f}" y1="{top-10}" x2="{x(zero):.1f}" y2="{top+rh*len(rows)}" stroke="{MUTED}" stroke-dasharray="4 3"/>']
    for i, r in enumerate(rows):
        y = top + rh * i + rh / 2
        b.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" fill="{INK}">{html.escape(r["label"])}</text>')
        if r["lo"] == r["lo"]:
            b.append(f'<line x1="{x(r["lo"]):.1f}" y1="{y:.1f}" x2="{x(r["hi"]):.1f}" y2="{y:.1f}" stroke="{SERIES[0]}" stroke-width="2"/>')
            b.append(f'<circle cx="{x(r["diff"]):.1f}" cy="{y:.1f}" r="4.5" fill="{SERIES[0]}"/>')
            b.append(f'<text x="{w-right}" y="{y+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="10">'
                     f'{r["diff"]:+.3f} [{r["lo"]:+.3f}, {r["hi"]:+.3f}]</text>')
    yb = top + rh * len(rows) + 8
    for t in (lo + (hi - lo) * k / 4 for k in range(5)):
        b.append(f'<text x="{x(t):.1f}" y="{yb+12}" text-anchor="middle" fill="{MUTED}" font-size="10">{t:+.2f}</text>')
    b.append(f'<text x="{(left + w - right)/2:.1f}" y="{yb+34}" text-anchor="middle" fill="{INK}">{html.escape(xlabel)}</text>')
    open(path, "w").write(_svg(w, h, "".join(b), title))


def reliability(series, title, path, n_bins=10):
    """series: {label: [(confidence, outcome01), ...]} -> reliability diagram."""
    w, h, m = 420, 420, 50
    s = w - 2 * m
    X = lambda v: m + v * s
    Y = lambda v: h - m - v * s
    b = [f'<text x="{w/2}" y="22" text-anchor="middle" font-weight="600" fill="{INK}">{html.escape(title)}</text>',
         f'<rect x="{m}" y="{m}" width="{s}" height="{s}" fill="none" stroke="{GRID}"/>',
         f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(1)}" y2="{Y(1)}" stroke="{MUTED}" stroke-dasharray="4 3"/>']
    for k in range(6):
        v = k / 5
        b.append(f'<text x="{X(v):.1f}" y="{h-m+16}" text-anchor="middle" fill="{MUTED}" font-size="10">{v:.1f}</text>')
        b.append(f'<text x="{m-8}" y="{Y(v)+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="10">{v:.1f}</text>')
    for i, (label, pairs) in enumerate(series.items()):
        c = SERIES[i % len(SERIES)]
        pts = []
        for k in range(n_bins):
            lo, hi = k / n_bins, (k + 1) / n_bins
            inb = [(p, o) for p, o in pairs if (lo <= p < hi) or (k == n_bins - 1 and p == 1.0)]
            if inb:
                pts.append((sum(p for p, _ in inb) / len(inb), sum(o for _, o in inb) / len(inb), len(inb)))
        if pts:
            b.append(f'<polyline fill="none" stroke="{c}" stroke-width="2" points="' +
                     " ".join(f"{X(p):.1f},{Y(o):.1f}" for p, o, _ in pts) + '"/>')
            for p, o, n in pts:
                b.append(f'<circle cx="{X(p):.1f}" cy="{Y(o):.1f}" r="{2.5 + min(4, n ** 0.5 / 3):.1f}" fill="{c}"/>')
        b.append(f'<text x="{m+8}" y="{m+16+14*i}" fill="{c}">{html.escape(label)} (n={len(pairs)})</text>')
    b.append(f'<text x="{w/2}" y="{h-12}" text-anchor="middle" fill="{INK}">stated P(innocent)</text>')
    b.append(f'<text x="14" y="{h/2}" text-anchor="middle" fill="{INK}" transform="rotate(-90 14 {h/2})">observed innocent rate</text>')
    open(path, "w").write(_svg(w, h, "".join(b), title))


def stacked(rows, cats, title, path):
    """rows: [{"label", cat: count, ...}] -> 100% stacked bars (confusion matrix)."""
    w, left, top, rh = 640, 150, 40, 30
    h = top + rh * len(rows) + 60
    bw = w - left - 20
    b = [f'<text x="{w/2}" y="20" text-anchor="middle" font-weight="600" fill="{INK}">{html.escape(title)}</text>']
    for i, r in enumerate(rows):
        y = top + rh * i
        tot = sum(r.get(c, 0) for c in cats) or 1
        x = left
        b.append(f'<text x="{left-8}" y="{y+18}" text-anchor="end" fill="{INK}">{html.escape(r["label"])} (n={tot})</text>')
        for j, c in enumerate(cats):
            wd = bw * r.get(c, 0) / tot
            if wd > 0:
                b.append(f'<rect x="{x:.1f}" y="{y+4}" width="{wd:.1f}" height="{rh-10}" fill="{SERIES[j % len(SERIES)]}"/>')
            x += wd
    ly = top + rh * len(rows) + 20
    for j, c in enumerate(cats):
        lx = left + j * (bw / len(cats))
        b.append(f'<rect x="{lx:.1f}" y="{ly}" width="10" height="10" fill="{SERIES[j % len(SERIES)]}"/>'
                 f'<text x="{lx+14:.1f}" y="{ly+9}" fill="{INK}" font-size="11">{html.escape(c)}</text>')
    open(path, "w").write(_svg(w, h, "".join(b), title))


def curve(series, title, xlabel, ylabel, path):
    """series: {label: [(x, y), ...]} on [0,1]x[0,1] (risk-coverage)."""
    w, h, m = 460, 380, 52
    sx, sy = w - 2 * m, h - 2 * m
    X = lambda v: m + v * sx
    Y = lambda v: h - m - v * sy
    b = [f'<text x="{w/2}" y="22" text-anchor="middle" font-weight="600" fill="{INK}">{html.escape(title)}</text>',
         f'<rect x="{m}" y="{m}" width="{sx}" height="{sy}" fill="none" stroke="{GRID}"/>']
    for k in range(6):
        v = k / 5
        b.append(f'<text x="{X(v):.1f}" y="{h-m+16}" text-anchor="middle" fill="{MUTED}" font-size="10">{v:.1f}</text>')
        b.append(f'<text x="{m-8}" y="{Y(v)+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="10">{v:.1f}</text>')
    for i, (label, pts) in enumerate(series.items()):
        c = SERIES[i % len(SERIES)]
        pts = sorted(pts)
        if pts:
            b.append(f'<polyline fill="none" stroke="{c}" stroke-width="2" points="' +
                     " ".join(f"{X(a):.1f},{Y(o):.1f}" for a, o in pts) + '"/>')
        b.append(f'<text x="{m+8}" y="{m+16+14*i}" fill="{c}">{html.escape(label)}</text>')
    b.append(f'<text x="{w/2}" y="{h-12}" text-anchor="middle" fill="{INK}">{html.escape(xlabel)}</text>')
    b.append(f'<text x="14" y="{h/2}" text-anchor="middle" fill="{INK}" transform="rotate(-90 14 {h/2})">{html.escape(ylabel)}</text>')
    open(path, "w").write(_svg(w, h, "".join(b), title))
