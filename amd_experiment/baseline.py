"""Record immutable input hashes and run the existing standalone CPU CLI twice."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exe", required=True, type=Path)
    p.add_argument("--models", required=True, type=Path)
    p.add_argument("--image", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    exe, image = a.exe.resolve(strict=True), a.image.resolve(strict=True)
    det = (a.models / "det/PP-OCRv6_small_det").resolve(strict=True)
    rec = (a.models / "rec/PP-OCRv6_small_rec").resolve(strict=True)
    if not det.is_dir() or not rec.is_dir() or not image.is_file() or not exe.is_file():
        p.error("Model directories, executable or image are invalid")
    a.out.mkdir(parents=True, exist_ok=True)
    hashes = {"executable": sha(exe), "image": sha(image), "models": {}}
    for model in (det, rec):
        hashes["models"][model.name] = {str(f.relative_to(model)): sha(f) for f in sorted(model.rglob("*")) if f.is_file()}
    commands = {
        "detection": [str(exe), "text_detection", "--input", str(image), "--device", "cpu", "--model_dir", str(det), "--model_name", det.name],
        "ocr": [str(exe), "ocr", "--input", str(image), "--device", "cpu", "--lang", "en", "--use_textline_orientation", "false", "--use_doc_orientation_classify", "false", "--use_doc_unwarping", "false", "--text_detection_model_dir", str(det), "--text_detection_model_name", det.name, "--text_recognition_model_dir", str(rec), "--text_recognition_model_name", rec.name],
    }
    report = {"platform": platform.platform(), "python": sys.version, "inputs": hashes, "runs": {}}
    failed = False
    for name, cmd in commands.items():
        start = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        (a.out / (name + ".stdout.txt")).write_text(result.stdout, encoding="utf-8")
        (a.out / (name + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
        report["runs"][name] = {"command": cmd, "exit_code": result.returncode, "seconds": time.perf_counter() - start}
        failed |= result.returncode != 0
    (a.out / "baseline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
