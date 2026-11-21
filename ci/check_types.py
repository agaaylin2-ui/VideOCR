"""Check tracked sources with the type environment of the current interpreter."""
import subprocess
import sys

if __name__ == "__main__":
    sources = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "*.py", "*.pyw"]
    ).decode("utf-8").split("\0")[:-1]
    if sys.version_info < (3, 12):
        # Windows 3.12 CI checks the desktop tools and their acceptance tests.
        sources = [p for p in sources if not p.startswith(("amd_experiment/", "tests/", "windows/"))]
    sys.exit(subprocess.call([sys.executable, "-m", "mypy", "--config-file=pyproject.toml", *sources]))
