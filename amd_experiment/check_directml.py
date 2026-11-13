"""Report whether the DirectML execution provider is available."""
import sys


def main():
    import numpy  # noqa: F401
    import onnxruntime

    providers = onnxruntime.get_available_providers()
    print("Available providers:", ", ".join(providers))
    if "DmlExecutionProvider" not in providers:
        print("DirectML is not available in this Python environment.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
