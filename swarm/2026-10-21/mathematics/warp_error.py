# CPU check of BIDIRECTIONAL-AS-MATHEMATICS.md section 12.6: the backward-warp
# shortcut's positional error on the A side and on the B side, for a flow with
# a constant gradient f(x) = f0 + g*x (1-D). The shader samples A at p - t f(p)
# and B at p + (1-t) f(p). The true material point at p at time t is x_A with
# x_A + t f(x_A) = p, and its B position is x_A + f(x_A).
import numpy as np
f0, g = 16.0, 0.05          # px per interval, per px
for t in (0.2, 0.4, 0.5, 0.6, 0.8):
    p = 100.0
    xA = (p - t*f0) / (1 + t*g)             # exact solve of x + t(f0 + g x) = p
    xB = xA + f0 + g*xA
    usedA = p - t*(f0 + g*p)
    usedB = p + (1-t)*(f0 + g*p)
    fp = f0 + g*p
    errA, errB = xA - usedA, xB - usedB
    predA, predB_doc, predB_true = t*t*g*fp, (1-t)**2*g*fp, -t*(1-t)*g*fp
    print(f"t={t:.1f}  errA={errA:+.4f} (t^2 g f: {predA:+.4f})   errB={errB:+.4f}  "
          f"doc (1-t)^2 g f: {predB_doc:+.4f}   corrected -t(1-t) g f: {predB_true:+.4f}")
