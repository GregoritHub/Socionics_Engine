#!/usr/bin/env python3
"""
below_dcnh_probes.py  --  2026-10-06
Question under test: the finite geometry reaches DCNH and stops.  Where do
energy (Model G grade, reserve) and functional conditioning (the 2+1 subtype
formulas, the profile) sit relative to that stop?

usage:  python3 below_dcnh_probes.py <path to baseline/HLE_Rebuild_R21B>

STATUS.  Blocks K, T, Q, E, S import the UNMODIFIED R21B rebuild kernel
(hle.model_a, hle.relations, hle.processing) from HLE_Full_Crux_C7_Source_v2;
hashes are printed.  The sealed 5.2.1 pyref was not supplied; rerun owed.
Hand-coded, not kernel: the Model G grade classes (from Model G on the Model A
Carrier v0.4, Theorem 4) and the DCNH 2+1 formulas (from UMA section 15).
Block R reimplements the kernel's route geometry with a swappable price; it is
the probe's own protocol and is validated against the kernel before use.
First run 2026-10-06: 15/17.  Both failures were the probe author's expectations, not
the kernel: QE7 had contact's sign vector written (+,-,+,-) where the kernel gives
(-,+,+,-) (still even); QE13 claimed two carriers of the spine in G64 where there are
four (two in H).  Both corrected to what the kernel returned; recorded here, not hidden.
Labels QE1.. are note-local (prefix not seen in the registers supplied to this
session; collision not excluded).  D-series number owed.  Nothing here closes
any register item.
"""
import hashlib, os, re, sys, glob
from fractions import Fraction
from itertools import product, permutations

ROOT = sys.argv[1] if len(sys.argv) > 1 else "baseline/HLE_Rebuild_R21B"
sys.path.insert(0, ROOT)
from hle.model_a import (TYPES, POSITION, BY_POSITION, ELEMENT, frame, stack, fields,
                         position_of, element_at, shortest_paths)
from hle.relations import all_relations, extended_group
from hle.processing import _route_geometry
from hle.crux import Polarity

print("kernel files (sha256, first 16):")
for f in ("hle/model_a.py", "hle/relations.py", "hle/processing.py", "hle/gf2.py"):
    print("  ", hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest()[:16], f)
print()

results = []


def check(label, ok, text):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}  {text}")


P8 = tuple(range(1, 9))
SE = {1: 3, 3: 1, 2: 4, 4: 2, 5: 7, 7: 5, 6: 8, 8: 6}          # Super-Ego partner (flip v)
AXES = ((1, 3), (2, 4), (5, 7), (6, 8))                          # (valued pole, unvalued pole)


def perm_of(aff):                      # an affine map of the position cube as a permutation of 1..8
    return tuple(BY_POSITION[aff(POSITION[p])] for p in P8)


def mul(g, h):                         # g after h
    return tuple(g[h[p - 1] - 1] for p in P8)


def close(gens):
    ident = P8
    found, pending = {ident}, [ident]
    while pending:
        cur = pending.pop()
        for g in gens:
            c = mul(g, cur)
            if c not in found:
                found.add(c); pending.append(c)
    return found


def order(g):
    n, x = 1, g
    while x != P8:
        x = mul(g, x); n += 1
    return n


def from_bits(fn):                     # a map on (a,v,r) as a permutation of positions
    return tuple(BY_POSITION[fn(*POSITION[p])] for p in P8)


G16 = {perm_of(g) for g in all_relations()}
G64 = {perm_of(g) for g in extended_group()}
ZETA = from_bits(lambda a, v, r: (a, v ^ r, r))                  # ring twist (Ring-Split Group, def.)
SIGMA = from_bits(lambda a, v, r: (r, v, a))                     # the a<->r swap
CZ = from_bits(lambda a, v, r: (a, v ^ (a & r), r))              # the quadratic move
SEPERM = from_bits(lambda a, v, r: (a, v ^ 1, r))
H = close(list(G16) + [ZETA])

# ============================================================ K. where DCNH sits in the kernel
DCNH = {"D": {"te", "fe"}, "C": {"se", "ne"}, "N": {"ti", "fi"}, "H": {"si", "ni"}}
ok = all(frame(t).linear[0][1] == 0 and frame(t).linear[1][1] == 0 and frame(t).linear[2][1] == 1
         for t in TYPES)
ok &= all({frozenset(stack(t)[p - 1] for p in ax) for ax in AXES} ==
          {frozenset(c) for c in DCNH.values()} for t in TYPES)
check("QE1", ok, "every kernel frame sends the Super-Ego direction e_v to e_n: in all 16 types the four "
                 "Super-Ego axes {1,3},{2,4},{5,7},{6,8} hold exactly the four DCNH core pairs")

centre = {g for g in H if all(mul(g, h) == mul(h, g) for h in H)}
check("QE2", len(G16) == 16 and len(G64) == 64 and len(H) == 32 and G16 < H < G64
      and centre == {P8, SEPERM}
      and sum(order(g) == 2 for g in H) == 19 and sum(order(g) == 4 for g in H) == 12,
      "on the R21B kernel: <relations, zeta> has order 32, sits between G16 and extended_group(), "
      "centre {Identity, Super-Ego}, 19 involutions, 12 of order four")
check("QE3", all(mul(g, SEPERM) == mul(SEPERM, g) for g in G64),
      "so DCNH = E/<e_n> is the IE-side picture of positions modulo the centre of the kinematic group")

# ============================================================ T. the tower above the estafette
def affine_perm(g):
    pts = [POSITION[p] for p in P8]
    img = {POSITION[p]: POSITION[g[p - 1]] for p in P8}
    o = img[(0, 0, 0)]
    x = lambda u, w: tuple(a ^ b for a, b in zip(u, w))
    return all(x(img[x(u, w)], o) == x(x(img[u], o), x(img[w], o)) for u in pts for w in pts)


B4 = {g for g in permutations(P8) if all(g[SE[p] - 1] == SE[g[p - 1]] for p in P8)}
G128 = close(list(G64) + [CZ])
check("QE4", len(B4) == 384 and sum(affine_perm(g) for g in B4) == 192 and not affine_perm(CZ)
      and CZ in B4 and len(G128) == 128 and G64 < G128 <= B4,
      "permutations of the positions that respect the Super-Ego axes: 384 (hyperoctahedral B4); "
      "192 are affine; CZ = 'flip value where producing and vital' is not; <G64, CZ> has order 128 "
      "= the full 2-part of 384")

# ============================================================ Q. the quaternion carrier
ONE, I_, J_, K_ = (1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)


def qmul(x, y):
    a1, b1, c1, d1 = x; a2, b2, c2, d2 = y
    return (a1*a2 - b1*b2 - c1*c2 - d1*d2, a1*b2 + b1*a2 + c1*d2 - d1*c2,
            a1*c2 - b1*d2 + c1*a2 + d1*b2, a1*d2 + b1*c2 - c1*b2 + d1*a2)


def neg(x): return tuple(-c for c in x)
def conj(x): return (x[0], -x[1], -x[2], -x[3])


PHI = {1: ONE, 3: neg(ONE), 2: I_, 4: neg(I_), 5: J_, 7: neg(J_), 6: K_, 8: neg(K_)}   # valued pole = +
INV = {v: k for k, v in PHI.items()}
Q8 = list(PHI.values())
LR = {tuple(INV[qmul(qmul(p, PHI[x]), q)] for x in P8) for p in Q8 for q in Q8}
check("QE5", LR == H,
      "with positions read as the quaternion units (1,3 = +-1; 2,4 = +-i; 5,7 = +-j; 6,8 = +-k), "
      "the 32 maps x -> p x q (p, q in Q8) are exactly H: the ring-split group is Q8 o Q8, "
      "left and right multiplication")


def antihom(g):
    return all(PHI[g[INV[qmul(x, y)] - 1]] == qmul(PHI[g[INV[y] - 1]], PHI[g[INV[x] - 1]])
               for x in Q8 for y in Q8)


BAR = tuple(INV[conj(PHI[p])] for p in P8)
check("QE6", antihom(SIGMA) and antihom(CZ) and BAR in {mul(CZ, h) for h in H}
      and not affine_perm(BAR) and BAR not in G64,
      "the estafette swap sigma (i<->j) and CZ (k -> -k) both reverse products, i.e. exchange left and "
      "right; CZ is quaternion conjugation x -> x^-1 up to an element of H; conjugation is the one "
      "symmetry the affine group cannot see")

# ---- fields as vectors on the four axes
def tilt(fn):                          # value at valued pole minus value at unvalued pole, per axis
    return tuple(fn(p) - fn(q) for p, q in AXES)


def load(fn):
    return tuple(fn(p) + fn(q) for p, q in AXES)


GRADE = {1: 3, 2: 3, 5: 2, 8: 2, 3: 1, 4: 1, 6: 0, 7: 0}        # Model G note v0.4, Theorem 4
valued = lambda p: int(fields(p)["valued"])
strong = lambda p: int(fields(p)["strong"])
contact = lambda p: int(fields(p)["contact"])
high = lambda p: GRADE[p] >> 1
dim = lambda p: fields(p)["dimensionality"]

signs = {name: tilt(fn) for name, fn in
         (("valued", valued), ("strong", strong), ("contact", contact), ("grade-high", high))}
parity = {n: sum(c < 0 for c in s) % 2 for n, s in signs.items()}
check("QE7", signs == {"valued": (1, 1, 1, 1), "strong": (1, 1, -1, -1), "contact": (-1, 1, 1, -1),
                       "grade-high": (1, 1, 1, -1)}
      and parity == {"valued": 0, "strong": 0, "contact": 0, "grade-high": 1},
      "as sign vectors on the four axes: valued (+,+,+,+), strong (+,+,-,-), contact (-,+,+,-) are even; "
      "the Model G high-grade bit (+,+,+,-) is odd")
anti = [s for s in product((1, -1), repeat=4)]
aff_signs = {s for s in anti
             if affine_perm(tuple((AXES[i][0] if s[i] > 0 else AXES[i][1]) if p == AXES[i][0] else
                                  (AXES[i][1] if s[i] > 0 else AXES[i][0])
                                  for p in P8 for i in range(4) if p in AXES[i]))}
check("QE8", aff_signs == {s for s in anti if sum(c < 0 for c in s) % 2 == 0} and len(aff_signs) == 8,
      "a pole-flip pattern on the axes is affine iff it flips an even number of axes: "
      "F2-affine geometry holds exactly the even half of the 16 sign vectors")
check("QE9", all(high(p) == (valued(p) if fields(p)["accepting"] else strong(p)) for p in P8)
      and all((GRADE[p] & 1) == (fields(p)["ring"] == "mental") for p in P8),
      "grade = 2*[valued if accepting else strong] + [mental]: energy ranks intake by value "
      "and output by strength (equivalent to 'value by mental ring, contact by vital ring')")
check("QE10", tilt(lambda p: GRADE[p]) == (2, 2, 2, -2) and load(lambda p: GRADE[p]) == (4, 4, 2, 2)
      and tilt(dim) == (2, 2, -2, -2) and load(dim) == (6, 4, 4, 6),
      "grade vs kernel dimensionality: same on the mental axes; opposite on the accumulation axis {5,7}; "
      "same on the expenditure axis {6,8}.  Grade vs value: opposite only on {6,8}")

# ---- the 24
half = [tuple(Fraction(s, 2) for s in v) for v in anti]
units = [tuple(Fraction(c) for c in q) for q in Q8]
T24 = set(units) | set(half)
closed = all(qmul(x, y) in T24 for x in T24 for y in T24)
u = tuple(Fraction(1, 2) for _ in range(4))                      # the value field, normalised
even = {tuple(Fraction(c, 2) for c in s) for s in aff_signs}
odd = set(half) - even
coset = lambda w: {qmul(tuple(Fraction(c) for c in q), w) for q in Q8}
check("QE11", closed and len(T24) == 24 and coset(u) == even and coset(conj(u)) == odd
      and qmul(u, conj(u)) == tuple(Fraction(c) for c in ONE),
      "positions (8) + even fields (8) + odd fields (8) = the 24 Hurwitz units, closed under "
      "multiplication; the even fields are the coset Q8.u of the value field u, the odd fields the "
      "inverse coset Q8.u^-1; the quotient is C3 = {position, information class, energy class}")

# ============================================================ E. representation and the spine
def fix(g): return sum(g[p - 1] == p for p in P8)
def flip(g): return sum(g[p - 1] == SE[p] for p in P8)


def burnside(G): return Fraction(sum(fix(g) ** 2 for g in G), len(G))
def tiltnorm(G): return Fraction(sum(((fix(g) - flip(g)) // 2) ** 2 for g in G), len(G))


check("QE12", (burnside(H), burnside(G64), burnside(G128), burnside(B4)) == (5, 4, 4, 3)
      and all(tiltnorm(G) == 1 for G in (H, G64, G128, B4)),
      "a real-valued profile on the eight positions splits as 4 axis-loads + 4 axis-tilts; the tilt part "
      "is one irreducible 4-dimensional module of H (the quaternions); invariant quadratic forms on a "
      "profile: 5 under H, 4 under G64 and G128, 3 under B4")

spine_H = [g for g in H if g[6 - 1] == 1 and g[1 - 1] == 8]
spine_64 = [g for g in G64 if g[6 - 1] == 1 and g[1 - 1] == 8]
Lk = tuple(INV[qmul(neg(K_), PHI[x])] for x in P8)
Rk = tuple(INV[qmul(PHI[x], neg(K_))] for x in P8)


def cycles(g):
    seen, out = set(), []
    for p in P8:
        if p not in seen:
            c, x = [], p
            while x not in seen:
                seen.add(x); c.append(x); x = g[x - 1]
            out.append(tuple(c))
    return out


check("QE13", set(spine_H) == {Lk, Rk} and len(spine_64) == 4
      and all(cycles(g)[0] == (1, 8, 3, 6) for g in spine_64)
      and cycles(Lk) == [(1, 8, 3, 6), (2, 7, 4, 5)] and cycles(Rk) == [(1, 8, 3, 6), (2, 5, 4, 7)]
      and sorted(sorted(len(c) for c in cycles(g)) for g in spine_64 if g not in H) == [[1, 1, 2, 4]] * 2,
      "Model G's spine A6 -> A1 -> A8 is two steps of ONE quarter-turn 6>1>8>3 on Model G's external "
      "plane (forced for any map that respects the Super-Ego axes).  Four elements of G64 carry it; "
      "two lie in H -- left and right multiplication by -k -- and run the internal plane {2,4,5,7} in "
      "opposite senses (5>2>7>4, 5>4>7>2); the two outside H hold one internal axis still and flip the other")

# ============================================================ S. the 2+1 formulas
FORMULA = {"D": ("te", "se", "fe"), "C": ("fe", "ne", "se"),      # UMA section 15: PF+E, EI+F, LS+R, TR+S
           "N": ("ti", "si", "fi"), "H": ("ni", "fi", "si")}
ok = True
for s, els in FORMULA.items():
    e_bit = {ELEMENT[x][1] for x in els}
    face = {x for x in ELEMENT if ELEMENT[x][1] in e_bit}
    ok &= len(e_bit) == 1 and DCNH[s] < set(els) and (face - set(els)) <= {"ne", "ni", "te", "ti"}
    ok &= (set(els) - DCNH[s]) <= {"se", "si", "fe", "fi"}
check("QE14", ok, "each 2+1 formula is a face of constant vertness minus one vertex; the vertex left out "
                  "is always an N or T element, the auxiliary always an S or F element")
EXT, INT = {1, 3, 6, 8}, {2, 4, 5, 7}                             # Model G planes (bold / cautious)
ok, rows = True, {}
for t in TYPES:
    for s, els in FORMULA.items():
        pos = {position_of(t, x) for x in els}
        plane = "ext" if pos <= EXT else "int" if pos <= INT else None
        same_vert = ELEMENT[els[0]][1] == ELEMENT[stack(t)[0]][1]
        ok &= plane == ("ext" if same_vert else "int")
        rows[(t, s)] = sorted(pos)
check("QE15", ok, "in every type each 2+1 formula fills three of the four positions of ONE Model G plane: "
                  "the two subtypes of the type's own vertness load the external plane (G1-G4), the other "
                  "two the internal plane (G5-G8)")

# ============================================================ R. pricing A/B (probe's own protocol)
def geometry(tim, active, target, polarity, price_of_position):
    supports = (5, 7) if polarity == Polarity.ACCUMULATION else (6, 8)
    price = lambda e: price_of_position(position_of(tim, e))
    cands = []
    for seat in supports:
        support = element_at(tim, seat)
        for first in shortest_paths(tim, active, support):
            for second in shortest_paths(tim, support, target):
                path = first + second[1:]
                units = tuple(price(e) for e in path[1:])
                cands.append((sum(units), len(path), path, seat, len(first) - 1, units))
    total, _, path, seat, _, units = min(cands)
    return path, seat, total


by_dim = lambda p: 5 - fields(p)["dimensionality"]
by_grade = lambda p: 4 - GRADE[p]
cases = [(t, a, b, pol) for t in TYPES for a in ELEMENT for b in ELEMENT
         for pol in (Polarity.ACCUMULATION, Polarity.EXPENDITURE)]
control = all(geometry(t, a, b, pol, by_dim)[0] == _route_geometry(t, a, b, pol, True)[0]
              for t, a, b, pol in cases)
dpath = sum(geometry(*c, by_dim)[0] != geometry(*c, by_grade)[0] for c in cases)
dseat = sum(geometry(*c, by_dim)[1] != geometry(*c, by_grade)[1] for c in cases)
tot_d = sum(geometry(*c, by_dim)[2] for c in cases)
tot_g = sum(geometry(*c, by_grade)[2] for c in cases)
check("QE16", control and dpath > 0,
      f"[probe protocol] reimplemented route geometry reproduces the kernel on all {len(cases)} cases; "
      f"pricing steps by Model G grade instead of dimensionality changes the chosen path in {dpath} "
      f"and the support seat in {dseat}; total price {tot_d} -> {tot_g}")

# ============================================================ W. the engine's two currencies
pat = re.compile(r"ResourceAmount\(ENERGY,\s*([^)]+)\)\s*,\s*ResourceAmount\(TIME,\s*([^)]+)\)")
pairs = []
for f in sorted(glob.glob(os.path.join(ROOT, "hle", "*.py"))):
    for m in pat.finditer(open(f).read()):
        pairs.append((os.path.basename(f), m.group(1).strip(), m.group(2).strip()))
spend = [p for p in pairs if not (p[1].endswith(".energy") and p[2].endswith(".time"))]
check("QE17", len(spend) > 0 and all(a == b for _, a, b in spend),
      f"[source scan] R21B hle/: {len(spend)} expenditure records name energy and time; every one spends "
      f"the same amount of each -- the engine carries two currencies and so far uses them as one")

print("\nPer-type positions of the 2+1 formulas (IEE):",
      {s: rows[("iee", s)] for s in "DCNH"})
print(f"\n{sum(results)}/{len(results)} passed  (R21B kernel; pyref rerun owed)")
