"""Build the four R12 deliverables from validated source and saved evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(root):
    return sorted(p for p in root.rglob("*") if p.is_file()
                  and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".tmp"))


def archive(root, target, prefix):
    pending = target.with_suffix(target.suffix + ".tmp")
    with ZipFile(pending, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for p in files(root):
            info = ZipInfo(prefix + "/" + p.relative_to(root).as_posix(), (2026, 9, 17, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(pending) as z:
        if z.testzip() is not None:
            raise RuntimeError("archive CRC validation failed")
    pending.replace(target)


def main():
    summary = json.loads((ROOT / "evidence/r12/summary.json").read_text())
    final = json.loads((ROOT / "evidence/r12/final/summary.json").read_text())
    if not summary["completed"] or not final["passed"]:
        raise ValueError("release is not validated")
    manifest_files = []
    for p in files(ROOT):
        rel = p.relative_to(ROOT).as_posix()
        if rel == "release_manifest.json" or "evidence" in p.relative_to(ROOT).parts:
            continue
        if rel in ("baseline/crossing/results/r10.json", "baseline/crossing/results/r11.json"):
            continue
        manifest_files.append({"path": rel, "sha256": sha(p), "bytes": p.stat().st_size})
    manifest = {"release": "R12 developmental contracts", "version": "1.2.0-contracts",
        "base_runtime": "42 unchanged R11 modules; new contracts are not a new behavioral controller",
        "schema": "hle-r12-source-manifest-v1", "files": manifest_files}
    (ROOT / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    result = subprocess.run([sys.executable, "tools/validate_release.py"], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    (ROOT / "evidence/r12/release_integrity.json").write_text(result.stdout)

    out = ROOT.parent / "output"
    out.mkdir(exist_ok=True)
    engine = out / "HolonicLivingEngine_Rebuild_R12_v1.zip"
    archive(ROOT, engine, "HLE_Rebuild_R12")
    evidence = out / "HLE_New_Build_Step_R12_Evidence_v1.zip"
    with tempfile.TemporaryDirectory() as temp:
        stage = Path(temp)
        shutil.copytree(ROOT / "evidence/r12", stage / "executed")
        shutil.copytree(ROOT / "docs/r12", stage / "declarations_and_reports")
        shutil.copy2(ROOT / "release_manifest.json", stage / "release_manifest.json")
        fresh = stage / "fresh_study_outputs"
        fresh.mkdir()
        for name in ("r10.json", "r11.json"):
            shutil.copy2(ROOT / "baseline/crossing/results" / name, fresh / name)
        (stage / "engine_pin.json").write_text(json.dumps({"file": engine.name,
            "sha256": sha(engine), "bytes": engine.stat().st_size}, indent=2) + "\n")
        (stage / "README.md").write_text(
            "# R12 evidence\n\nSource is in the paired R12 engine archive identified by engine_pin.json.\n"
            "The executed directory contains new commands, logs, results and repairs.\n"
            "The declarations_and_reports directory contains frozen contracts and progress.\n"
            "Historical probe summaries inside the source archive remain historical; their full panels were not rerun.\n"
            "The 480-case future panel is a specification with no executed future cases.\n")
        archive(stage, evidence, "HLE_R12_Evidence_v1")
    report = out / "HLE_New_Build_Step_R12_Report_v1.md"
    roadmap = out / "HLE_New_Build_Progress_and_Remaining_Steps_After_R12.md"
    shutil.copy2(ROOT / "docs/r12/Step_R12_Report.md", report)
    shutil.copy2(ROOT / "docs/r12/Progress_After_R12.md", roadmap)
    for p in (engine, evidence, report, roadmap):
        print(json.dumps({"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p)}))


if __name__ == "__main__":
    main()
