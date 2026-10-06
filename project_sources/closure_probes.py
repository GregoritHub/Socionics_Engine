#!/usr/bin/env python3
"""
closure_probes.py  --  2026-10-06
Kernel halves of the note-register jobs that a run on R21B can settle, done so the
open items can be sorted for the final build.

usage:  python3 closure_probes.py <path to baseline/HLE_Rebuild_R21B>

Runs against the UNMODIFIED R21B rebuild kernel inside HLE_Full_Crux_C7_Source_v2
(hle.model_a, hle.relations, relation_labels.json); hashes printed.  The sealed
5.2.1 pyref was NOT supplied: every "pyref rerun" clause stays owed.
Hand-coded, not kernel: the sixteen signed Model G stacks, the positivist/negativist
labels and the position attributes, copied from Model G on the Model A Carrier v0.4
(Tables 1 and 2), which cites socioniks.net (accessed 2026-09-26).  The site was not
re-read in this session.
Blocks:  M = MG-3 (R21B half) and the facts behind register C1, C2, C3 (one pole);
         R = MG-4 / RS-1 (R21B half);  B = RS-2;  P = process/result pole.
Labels CL1.. are note-local.  D-series number owed.  This probe closes nothing by
itself; the ledger records what was closed on instruction.
"""
import hashlib, json, os, sys
from itertools import permutations

ROOT = sys.argv[1] if len(sys.argv) > 1 else "baseline/HLE_Rebuild_R21B"
sys.path.insert(0, ROOT)
from hle.model_a import TYPES, POSITION, BY_POSITION, ELEMENT, stack, fields, character
from hle.relations import all_relations, extended_group

print("kernel files (sha256, first 16):")
for f in ("hle/model_a.py", "hle/relations.py", "hle/gf2.py",
          "baseline/crossing/sources/relation_labels.json"):
    print("  ", hashlib.sha256(open(os.path.join(ROOT, f), "rb").read()).hexdigest()[:16], f)
print()
LABELS = json.load(open(os.path.join(ROOT, "baseline/crossing/sources/relation_labels.json")))

results = []


def check(label, ok, text):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {label}  {text}")


# ------------------------------------------------------------ source table (MG note v0.4, Table 2)
RAW = """
ILE +Ne -Te +Se -Fe +Ti -Si +Fi -Ni positivist
SEI -Si +Fi -Ni +Ti -Fe +Ne -Te +Se negativist
ESE +Fe -Se +Te -Ne +Si -Ti +Ni -Fi positivist
LII -Ti +Ni -Fi +Si -Ne +Fe -Se +Te negativist
EIE -Fe +Ne -Te +Se -Ni +Ti -Si +Fi negativist
LSI +Ti -Si +Fi -Ni +Se -Fe +Ne -Te positivist
SLE -Se +Te -Ne +Fe -Ti +Ni -Fi +Si negativist
IEI +Ni -Fi +Si -Ti +Fe -Se +Te -Ne positivist
SEE +Se -Fe +Ne -Te +Fi -Ni +Ti -Si positivist
ILI -Ni +Ti -Si +Fi -Te +Se -Fe +Ne negativist
LIE +Te -Ne +Fe -Se +Ni -Fi +Si -Ti positivist
ESI -Fi +Si -Ti +Ni -Se +Te -Ne +Fe negativist
LSE -Te +Se -Fe +Ne -Si +Fi -Ni +Ti negativist
EII +Fi -Ni +Ti -Si +Ne -Te +Se -Fe positivist
IEE -Ne +Fe -Se +Te -Fi +Si -Ti +Ni negativist
SLI +Si -Ti +Ni -Fi +Te -Ne +Fe -Se positivist
"""
G_STACK, G_SIGN, G_LABEL = {}, {}, {}
for line in RAW.strip().splitlines():
    w = line.split()
    t = w[0].lower()
    G_STACK[t] = tuple(x[1:].lower() for x in w[1:9])
    G_SIGN[t] = tuple(x[0] for x in w[1:9])
    G_LABEL[t] = w[9]
assert set(G_STACK) == set(TYPES)

# source attributes of the eight G positions (MG note v0.4, Table 1)
G_NAME = {1: "Leading", 2: "Creative", 3: "Role-playing", 4: "Launching",
          5: "Demonstrative", 6: "Manipulative", 7: "Braking", 8: "Controlling"}
G_BLOCK = {"Social mission": (1, 2), "Social adaptation": (3, 4),
           "Creative self-realization": (5, 6), "Inflation": (7, 8)}
G_POL = {1: "LSE", 2: "LUE", 3: "DSE", 4: "DUE", 5: "LUI", 6: "DSI", 7: "DUI", 8: "LSI"}
#        Leading/Driven, Stable/Unstable, External/Internal
G_GRADE = {1: 3, 5: 3, 2: 2, 6: 2, 3: 1, 7: 1, 4: 0, 8: 0}

P8 = tuple(range(1, 9))

# ============================================================ M. MG-3 on the kernel
fits = []
for pi in permutations(P8):
    if all(G_STACK[t][k] == stack(t)[pi[k] - 1] for t in TYPES for k in range(8)):
        fits.append(pi)
PI = fits[0] if fits else None
check("CL1", fits == [(1, 8, 3, 6, 2, 5, 4, 7)],
      "MG Thm 1 on kernel stacks: one permutation of positions carries all 128 published Model G cells "
      "onto hle.model_a.stack, and it is the only one of 40,320")
A_OF = {k + 1: PI[k] for k in range(8)}                      # G position -> A position
ok = all((G_POL[g][0] == "L") == fields(a)["strong"] and (G_POL[g][1] == "S") == fields(a)["accepting"]
         and (G_POL[g][2] == "E") == fields(a)["bold"] for g, a in A_OF.items())
check("CL2", ok, "MG Thm 2 on kernel fields: leading = strong, stable = accepting, external = bold")

bits = lambda p: POSITION[p]
pos = lambda b: BY_POSITION[b]
beta = {p: pos((1 ^ bits(p)[0], 1 ^ bits(p)[0] ^ bits(p)[1] ^ bits(p)[2], 1 ^ bits(p)[2])) for p in P8}
gamma = {p: pos((1 ^ bits(p)[0], bits(p)[1] ^ bits(p)[2], bits(p)[2])) for p in P8}
blocks_A = {name: frozenset(A_OF[g] for g in gs) for name, gs in G_BLOCK.items()}
grade_A = {A_OF[g]: v for g, v in G_GRADE.items()}
ok = all(beta[a] in blk and beta[a] != a for blk in blocks_A.values() for a in blk)
ok &= all(grade_A[gamma[a]] == grade_A[a] and gamma[a] != a for a in P8)
ok &= all((grade_A[a] & 1) == (1 ^ bits(a)[2]) and (grade_A[a] >> 1) == (1 ^ bits(a)[1] ^ (bits(a)[0] & bits(a)[2]))
          for a in P8)
check("CL3", ok and blocks_A == {"Social mission": frozenset({1, 8}), "Social adaptation": frozenset({3, 6}),
                                 "Creative self-realization": frozenset({2, 5}), "Inflation": frozenset({4, 7})},
      "MG Thms 3-5 on kernel coordinates: beta pairs the source blocks, gamma pairs the equal grades, "
      "grade bits = (1+v+a*r, 1+r); blocks are A{1,8}, A{3,6}, A{2,5}, A{4,7}")

POSITIVIST = (1, 1, 1, 0)
ok = all((G_LABEL[t] == "positivist") == (character(POSITIVIST, t) == 1) for t in TYPES)
ok &= all((G_SIGN[t][k] == "+") == ((G_LABEL[t] == "positivist") != (fields(PI[k])["ring"] == "vital"))
          for t in TYPES for k in range(8))
check("CL4", ok, "MG Thm 6 on the kernel: the published positivist label is kernel character (1,1,1,0) = 1 "
                 "for all 16 types, and all 128 signs obey '+ iff positivist XOR vital'")
check("CL5", {g: (G_NAME[g], A_OF[g]) for g in (3, 5, 8)} ==
      {3: ("Role-playing", 3), 5: ("Demonstrative", 2), 8: ("Controlling", 7)},
      "facts behind register C1/C2: G3 Role-playing = A3, G5 Demonstrative = A2, G8 Controlling = A7; "
      "block assignment as in CL3 (names and blocks are the cited source's, transcribed)")

# ============================================================ R. MG-4 / RS-1 on the kernel
def perm_of(aff): return tuple(BY_POSITION[aff(POSITION[p])] for p in P8)
def mul(g, h): return tuple(g[h[p - 1] - 1] for p in P8)


def inv(g):
    out = [0] * 8
    for p in P8:
        out[g[p - 1] - 1] = p
    return tuple(out)


def close(gens):
    found, pending = {P8}, [P8]
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


G16 = {perm_of(g) for g in all_relations()}
G64 = {perm_of(g) for g in extended_group()}
from_bits = lambda fn: tuple(pos(fn(*bits(p))) for p in P8)
ZETA = from_bits(lambda a, v, r: (a, v ^ r, r))
SIGMA = from_bits(lambda a, v, r: (r, v, a))
SE = from_bits(lambda a, v, r: (a, v ^ 1, r))
BETA, GAMMA = tuple(beta[p] for p in P8), tuple(gamma[p] for p in P8)
H = close(list(G16) + [ZETA])
comm = {mul(mul(g, h), mul(inv(g), inv(h))) for g in H for h in H}
centre = lambda G: {g for g in G if all(mul(g, h) == mul(h, g) for h in G)}
check("CL6", len(H) == 32 and H == close(list(G16) + [GAMMA]) == close(list(G16) + [BETA])
      and BETA not in G16 and GAMMA not in G16 and H < G64
      and centre(H) == {P8, SE} and comm == {P8, SE} and {mul(g, g) for g in H} == {P8, SE}
      and sum(order(g) == 2 for g in H) == 19 and sum(order(g) == 4 for g in H) == 12,
      "RS Thms A-B inside R21B's extended_group(): <relations, zeta> = <relations, gamma> = <relations, beta>, "
      "order 32, centre = derived subgroup = set of squares = {Identity, Super-Ego}, 19 involutions, "
      "12 of order four: extraspecial of plus type")
MENTAL, VITAL = (1, 2, 3, 4), (5, 6, 7, 8)
ok = True
for h in H - G16:
    twin = [g for g in G16 if all(h[p - 1] == g[p - 1] for p in MENTAL)]
    ok &= len(twin) == 1 and all(h[p - 1] == mul(SE, twin[0])[p - 1] for p in VITAL)
check("CL7", ok, "ring-split table: each of the 16 new elements is one classical relation on the mental ring "
                 "and its Super-Ego twist on the vital ring")
conj = {mul(mul(x, g), inv(x)) for g in G16 for x in G64}
check("CL8", SIGMA in G64 and SIGMA not in H and G64 == H | {mul(SIGMA, h) for h in H}
      and close(list(conj)) == H and conj != G16 and len(centre(G64)) == 2
      and any(order(c) == 2 and c not in (P8, SE)
              for c in {mul(mul(g, h), mul(inv(g), inv(h))) for g in G64 for h in G64}),
      "RS Thm C: extended_group() = H split by the swap sigma; H is the normal closure of the relations; "
      "centre of order two; commutators leave the centre, so the order-64 group is neither "
      "2^(1+4) x C2 nor extraspecial")

# ============================================================ B. RS-2 benefit direction
ring = ["ile", "eie", "see", "lse"]
check("CL9", all(LABELS[f"{ring[i]}:{ring[(i + 1) % 4]}"]["relation"] == "benefit" for i in range(4))
      and all(LABELS[f"{ring[(i + 1) % 4]}:{ring[i]}"]["relation"] == "benefit_inverse" for i in range(4)),
      "RS-2: the kernel's own label file names ILE>EIE>SEE>LSE 'benefit' in that direction, "
      "the same direction the Ring-Split note took from the published ring")

# ============================================================ P. process/result pole
PROCESS = {"ile", "sei", "eie", "lsi", "see", "ili", "lse", "eii"}       # published list (as in V17)
vals = {character((0, 1, 1, 1), t) for t in PROCESS}
check("CL10", len(vals) == 1 and {character((0, 1, 1, 1), t) for t in set(TYPES) - PROCESS} == {1 - min(vals)},
      f"the published process list is one pole of kernel character (0,1,1,1): process = {min(vals)}")

print(f"\n{sum(results)}/{len(results)} passed  (R21B kernel; pyref rerun owed)")
