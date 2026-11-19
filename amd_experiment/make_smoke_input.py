"""Create deterministic synthetic float input. This is a smoke test, not OCR data."""
import argparse
from pathlib import Path
import numpy as np
import onnxruntime as ort

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--model", required=True, type=Path)
p.add_argument("--shape", required=True, help="Concrete input dimensions, e.g. 1,3,640,640")
p.add_argument("--out", required=True, type=Path)
a = p.parse_args()
s = ort.InferenceSession(str(a.model), providers=["CPUExecutionProvider"])
inputs = s.get_inputs()
if len(inputs) != 1 or inputs[0].type != "tensor(float)":
    raise SystemExit("Expected one float32 input; supply a real NPZ for other models")
shape = tuple(int(x) for x in a.shape.split(","))
if len(shape) != len(inputs[0].shape) or any(x <= 0 for x in shape):
    raise SystemExit(f"Invalid shape {shape}; model shape is {inputs[0].shape}")
for got, expected in zip(shape, inputs[0].shape):
    if isinstance(expected, int) and got != expected:
        raise SystemExit(f"Shape {shape} conflicts with model shape {inputs[0].shape}")
a.out.parent.mkdir(parents=True, exist_ok=True)
np.savez(a.out, **{inputs[0].name: np.random.default_rng(42).random(shape, dtype=np.float32)})
print(f"Saved {inputs[0].name}, shape {shape}, to {a.out}")
