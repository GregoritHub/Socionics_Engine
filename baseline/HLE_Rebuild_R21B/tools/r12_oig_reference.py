"""Compare R12 quotient values with the pinned historical definition offline.

The historical package is extracted into a temporary test directory. It is
never imported by the live engine and supplies no developmental policy.
"""
import json
from itertools import combinations
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hle.contracts import Ref, Kind
from hle.crux import Perspective
from hle.model_a import TYPES
from hle.development_structure import LensContent, QUOTIENTS, quotient


def normalized(value):
    if isinstance(value, Ref):
        return value.key + "@" + str(value.revision)
    if isinstance(value, Perspective):
        return value.value.lower()
    if isinstance(value, (set, frozenset)):
        return frozenset(normalized(x) for x in value)
    if isinstance(value, tuple):
        return tuple(normalized(x) for x in value)
    if value == "*":
        return None
    return value


def main():
    archive = ROOT / "reference/originals/HolonicLivingEngine5_2_1_canon.zip"
    with tempfile.TemporaryDirectory() as tmp:
        with ZipFile(archive) as z:
            for name in z.namelist():
                if name.startswith("clean/pyref/") and name.endswith(".py"):
                    z.extract(name, tmp)
        sys.path.insert(0, str(Path(tmp) / "clean"))
        from pyref.oig import q_class
        domains = [tuple(c) for n in range(5) for c in combinations(Perspective, n)]
        foreigners = [(), (Ref(Kind.MEMORY, "foreign-x", 1),), (Ref(Kind.MEMORY, "foreign-y", 2),)]
        count = 0
        for tim in TYPES:
            for d in domains:
                for f in foreigners:
                    content = LensContent(d, f, Ref(Kind.CONTEXT, "fixture", 1), Ref(Kind.PROTOCOL, "lens-v1", 1))
                    old_content = {normalized(x) for x in d + f}
                    for q in QUOTIENTS:
                        actual = normalized(quotient(tim, content, q))
                        expected = normalized(q_class(tim, old_content, q))
                        if actual != expected:
                            raise AssertionError((tim, d, f, q, actual, expected))
                        count += 1
    result = {"schema": "r12-oig-reference-v1", "passed": True,
              "comparisons": count, "types": len(TYPES), "domain_subsets": len(domains),
              "foreign_cases": len(foreigners), "quotients": len(QUOTIENTS),
              "scope": "Declared quotient representatives only; no runtime content projection or Shell detector assessed."}
    out = ROOT / "evidence/r12/oig_reference.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
