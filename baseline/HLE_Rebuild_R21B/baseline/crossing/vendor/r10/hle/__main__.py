"""Run the inspectable organization lifecycle in the R10 release."""
import json
from . import __version__, MILESTONE
from .organization_demo import run_organization_demo

def main():
    _, summary, _ = run_organization_demo()
    demonstration = summary.pop('milestone')
    summary.pop('next', None)
    print(json.dumps({"version": __version__, 'release_milestone': MILESTONE,
        'demonstration_milestone': demonstration, **summary,
        'sustained_evaluation': 'python -I tools/r10_evidence.py --output /tmp/hle-r10-evidence'}, indent=2))

if __name__ == "__main__": main()
