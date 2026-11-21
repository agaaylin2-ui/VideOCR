"""Start the original window under the private desktop runtime."""
import os
import runpy
import sys
import traceback
from pathlib import Path

root = Path(__file__).resolve().parent
sys.argv = [str(root / 'VideOCR.py'), '--amd-desktop']
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except Exception:
    import ctypes

    log = Path(os.environ['LOCALAPPDATA']) / 'VideOCR-AMD' / 'startup.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(traceback.format_exc(), encoding='utf-8')
    ctypes.windll.user32.MessageBoxW(None, f'VideOCR could not open. Details are in {log}', 'VideOCR AMD', 16)
    sys.exit(1)
