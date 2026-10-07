"""Compatible CLI for independent workflow selection reconstruction."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'baseline/HLE_Rebuild_R21B')]
from hle_unified.workflow_selection_audit import *

if __name__=='__main__':
    if sys.argv[1]=='--responsiveness':verify_responsiveness(Path(sys.argv[2]))
    else:verify(Path(sys.argv[1]),int(sys.argv[2]) if len(sys.argv)>2 else 8,
        int(sys.argv[3]) if len(sys.argv)>3 else None)
