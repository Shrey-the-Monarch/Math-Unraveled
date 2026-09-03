#!/usr/bin/env python3
"""
fixfigs.py -- repair glued code fences AND set fig-height on {dot} cells.

  python3 fixfigs.py index.qmd            # report only, changes nothing
  python3 fixfigs.py index.qmd --fix      # repair fences + write fig-height

Repairs the bug where a closing ``` ended up on the same line as the last
line of a graph (e.g. "}```"), which leaves the code block unterminated.
Sizes are computed from pinned pos="x,y!" coords, so Graphviz is not needed.
"""
import re, sys, shutil

PAD = 0.12

def repair_fences(src):
    """Split any line that ends with ``` but is not a bare fence."""
    out, n = [], 0
    for line in src.split("\n"):
        if line.endswith("```") and line.strip() != "```":
            out.append(line[:-3].rstrip()); out.append("```"); n += 1
        else:
            out.append(line)
    return "\n".join(out), n

def estimate(graph):
    pts = [(float(a), float(b)) for a, b in
           re.findall(r'pos\s*=\s*"\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*!?\s*"', graph)]
    if len(pts) < 2: return None
    widths = [float(w) for w in re.findall(r'width\s*=\s*([\d.]+)', graph)]
    d = widths[0] if widths else 0.75
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (max(xs)-min(xs)+d+PAD, max(ys)-min(ys)+d+PAD)

BLOCK = re.compile(r'```\{dot\}[ \t]*\n(.*?)\n```[ \t]*$', re.S | re.M)

def process(src):
    rows = []
    def repl(m):
        body = m.group(1)
        lines = body.split("\n")
        opts  = [l for l in lines if l.lstrip().startswith('//|')]
        graph = [l for l in lines if not l.lstrip().startswith('//|')]
        lab = next((l.split(':',1)[1].strip() for l in opts if 'label' in l), '?')
        def opt(n):
            v = next((l.split(':',1)[1].strip() for l in opts if l.lstrip().startswith(f'//| {n}')), None)
            try: return float(v)
            except (TypeError, ValueError): return None
        fw, fh = opt('fig-width'), opt('fig-height')
        est = estimate("\n".join(graph))
        if not est:
            rows.append((lab, fw, fh, None, 'not pinned - leave size unset'))
            return m.group(0)
        nw, nh = est
        w  = fw if fw else round(nw, 2)
        wh = round(w * (nh/nw), 2)
        ok = fh is not None and abs(fh-wh) <= max(0.12, 0.10*wh)
        rows.append((lab, fw, fh, f"{nw:.2f}x{nh:.2f}", 'ok' if ok else f'fig-height -> {wh}'))
        keep = [l for l in opts if not re.match(r'\s*//\|\s*fig-(width|height)\b', l)]
        newbody = "\n".join(keep + [f'//| fig-width: {w}', f'//| fig-height: {wh}'] + graph)
        return "```{dot}\n" + newbody + "\n```"
    return BLOCK.sub(repl, src), rows

if __name__ == '__main__':
    write = '--fix' in sys.argv
    for path in [a for a in sys.argv[1:] if not a.startswith('--')]:
        src = open(path).read()
        src, nfix = repair_fences(src)
        new, rows = process(src)
        print(f"\n=== {path} ===")
        print(f"glued closing fences repaired: {nfix}")
        for lab, fw, fh, nat, st in rows:
            print(f"  {lab:<26}{str(fw or '-'):>6}{str(fh or '-'):>6} | natural {str(nat or '?'):>12} | {st}")
        if write:
            shutil.copy(path, path + '.bak')
            open(path, 'w').write(new)
            print(f"WROTE {path}   (backup at {path}.bak)")
