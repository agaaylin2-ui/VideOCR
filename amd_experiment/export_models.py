"""Export exact baseline model directories using the pinned Paddle2ONNX converter."""
import argparse
import hashlib
import json
import subprocess
import sys

import onnx
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--opset", type=int, default=17)
    a = p.parse_args()
    report = {}
    for kind, name in (("det", "PP-OCRv6_small_det"), ("rec", "PP-OCRv6_small_rec")):
        src = (a.models / kind / name).resolve(strict=True)
        if not src.is_dir():
            raise ValueError(f"Not a model directory: {src}")
        dst = (a.out / kind).resolve()
        dst.mkdir(parents=True, exist_ok=True)
        if any(dst.iterdir()):
            raise ValueError(f"Output directory must be empty: {dst}")
        cmd = [str(Path(sys.executable).with_name("paddle2onnx.exe" if sys.platform == "win32" else "paddle2onnx")), "--model_dir", str(src), "--model_filename", "inference.json", "--params_filename", "inference.pdiparams", "--save_file", str(dst / "inference.onnx"), "--opset_version", str(a.opset), "--optimize_tool", "None"]
        print("Running:", subprocess.list2cmdline(cmd), flush=True)
        subprocess.run(cmd, check=True)
        files = list(dst.rglob("*.onnx"))
        if len(files) != 1:
            raise RuntimeError(f"Expected one ONNX file in {dst}; found {files}")
        model = onnx.load(str(files[0]))
        onnx.checker.check_model(model)
        opsets = {entry.domain or "ai.onnx": entry.version for entry in model.opset_import}
        report[kind] = {"actual_opsets": opsets, "source_files": {str(f.relative_to(src)): digest(f) for f in sorted(src.rglob("*")) if f.is_file()}, "onnx_file": str(files[0]), "onnx_sha256": digest(files[0]), "requested_opset": a.opset, "command": cmd}
    (a.out / "export_manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
