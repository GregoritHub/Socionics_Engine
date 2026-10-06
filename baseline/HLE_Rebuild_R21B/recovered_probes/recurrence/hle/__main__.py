"""Run the inspectable organization lifecycle in the R11 release."""
import json
from . import __version__, MILESTONE
from .organization_demo import run_organization_demo

def main():
    w, summary, _ = run_organization_demo()
    demonstration = summary.pop('milestone')
    summary.pop('next', None)
    print(json.dumps({"version": __version__, 'release_milestone': MILESTONE,
        'demonstration_milestone': demonstration, **summary,
        'semantic_processing': 'paid Model A routes with exclusive actor processing',
        'active_elements': {a.key:w.processing_state(a).active for a in w.config.actors},
        'sustained_evaluation': 'python -I tools/r11_evidence.py --output /tmp/hle-r11-evidence'}, indent=2))

if __name__ == "__main__": main()
