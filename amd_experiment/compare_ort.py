"""Compare raw ONNX tensors; profiling evidence is not full OCR accuracy."""
import argparse
import collections
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort


def summarize_profile(path):
    events = json.loads(Path(path).read_text(encoding="utf-8"))
    counts = collections.Counter()
    durations = collections.Counter()
    nodes = []
    for event in events:
        args = event.get("args", {})
        provider = args.get("provider")
        if event.get("cat") == "Node" and provider:
            counts[provider] += 1
            durations[provider] += event.get("dur", 0)
            nodes.append({"name": event.get("name"), "op_name": args.get("op_name"), "provider": provider, "duration_us": event.get("dur", 0)})
    return {"node_events": dict(counts), "node_duration_us": dict(durations), "nodes": nodes}


def create_session(model, provider, adapter, profile_prefix):
    opts = ort.SessionOptions()
    opts.enable_mem_pattern = False
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    opts.enable_profiling = True
    opts.profile_file_prefix = str(profile_prefix)
    providers = [("DmlExecutionProvider", {"device_id": adapter}), "CPUExecutionProvider"] if provider == "DmlExecutionProvider" else [provider]
    sess = ort.InferenceSession(str(model), sess_options=opts, providers=providers)
    sess.disable_fallback()
    if provider not in sess.get_providers():
        raise RuntimeError(f"Requested {provider}; session providers: {sess.get_providers()}")
    return sess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--input", required=True, type=Path, help="NPZ whose array names match all model inputs")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--adapter", type=int, default=0, help="DXGI adapter index, not necessarily the RX 9070 XT")
    p.add_argument("--cpu-only", action="store_true")
    p.add_argument("--rtol", type=float, default=1e-3)
    p.add_argument("--atol", type=float, default=1e-4)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    report = {"model_sha256": hashlib.sha256(a.model.read_bytes()).hexdigest(), "input_sha256": hashlib.sha256(a.input.read_bytes()).hexdigest(), "platform": platform.platform(), "ort_version": ort.__version__, "available_providers": ort.get_available_providers(), "adapter_index": a.adapter, "note": "Node assignment is ORT evidence, not independent proof of physical GPU activity or OCR accuracy.", "runs": {}}
    report_path = a.out / "comparison.json"
    try:
        with np.load(a.input, allow_pickle=False) as archive:
            inputs = {key: archive[key] for key in archive.files}
        providers = ["CPUExecutionProvider"] + ([] if a.cpu_only else ["DmlExecutionProvider"])
        outputs = {}
        for provider in providers:
            if provider not in ort.get_available_providers():
                raise RuntimeError(f"{provider} is not available")
            sess = create_session(a.model, provider, a.adapter, a.out / provider)
            expected = {x.name for x in sess.get_inputs()}
            if set(inputs) != expected:
                raise ValueError(f"NPZ keys {list(inputs)} do not match model inputs {sorted(expected)}")
            outputs[provider] = sess.run(None, inputs)
            profile = sess.end_profiling()
            summary = summarize_profile(profile)
            report["runs"][provider] = {"session_providers": sess.get_providers(), "profile_file": str(Path(profile).resolve()), "profile": summary}
            if provider == "DmlExecutionProvider" and not summary["node_events"].get(provider):
                raise RuntimeError("No DirectML node execution recorded; GPU execution not established")
        if not a.cpu_only:
            left, right = outputs[providers[0]], outputs[providers[1]]
            if len(left) != len(right):
                raise ValueError("Output count mismatch")
            comparisons = []
            for i, (x, y) in enumerate(zip(left, right)):
                if x.shape != y.shape:
                    raise ValueError(f"Output {i} shape mismatch: {x.shape} vs {y.shape}")
                finite = bool(np.isfinite(x).all() and np.isfinite(y).all())
                ok = finite and bool(np.allclose(x, y, rtol=a.rtol, atol=a.atol))
                comparisons.append({"index": i, "shape": list(x.shape), "finite": finite, "max_absolute_difference": float(np.max(np.abs(x - y))) if x.size else 0.0, "allclose": ok})
            report["comparison"] = {"rtol": a.rtol, "atol": a.atol, "outputs": comparisons}
            if not all(c["allclose"] for c in comparisons):
                raise RuntimeError("Tensor comparison failed")
        report["status"] = "cpu_only" if a.cpu_only else "profile_and_tensor_checks_passed"
        return 0
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(report["error"], file=sys.stderr)
        return 1
    finally:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report: {report_path}")


if __name__ == "__main__":
    sys.exit(main())
