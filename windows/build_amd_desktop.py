"""Assemble the portable Windows x64 desktop edition using CPython 3.12 with Tk."""
import argparse
import hashlib
import io
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
TASKBAR = 'e9400333a2f34c68eca3ce2daed711b1a748db7d'
TASKBAR_HASH = '2c2feb8c8fa8254a9cab1d79a3418fbcf8ec68ccdd1c63dd7fcc6158eb312cc8'


def install_packages(target: Path, wheelhouses: list[Path] | None) -> None:
    locks = ROOT / 'amd_experiment' / 'locks'
    lines = []
    for name in ('directml', 'real-ocr-extra', 'video', 'gui'):
        lines.extend((locks / f'{name}-win-py312.txt').read_text().splitlines())
    with tempfile.TemporaryDirectory() as temp:
        extra = []
        if wheelhouses:
            extra = ['--no-index']
            for directory in wheelhouses:
                extra += ['--find-links', str(directory.resolve())]
            # The published wheel comes from the upstream release. Keep its locked hash.
            lines = ['simplejpeg==1.9.1 ' + line[line.index('--hash='):]
                     if line.startswith('simplejpeg @ ') else line for line in lines]
        lock = Path(temp) / 'wheels.txt'
        lock.write_text('\n'.join(lines) + '\n', encoding='ascii')
        staged = Path(temp) / 'packages'
        subprocess.run([sys.executable, '-m', 'pip', '--disable-pip-version-check', 'install',
                        '--no-compile', '--require-hashes', '--only-binary=:all:', '--no-deps',
                        '--target', str(staged), *extra, '-r', str(lock)], check=True)
        target.mkdir()
        for item in staged.iterdir():
            # Generated console scripts contain the build machine's Python path.
            if item.name.lower() not in ('bin', 'scripts'):
                shutil.move(str(item), target / item.name)


def build(out: Path, image_run: Path | None, wheelhouses: list[Path] | None, taskbar_zip: Path | None, model_directory: Path | None = None) -> None:
    if os.name != 'nt' or sys.version_info[:2] != (3, 12) or struct.calcsize('P') != 8:
        raise RuntimeError('Build with Windows CPython 3.12 x64 including Tcl/Tk.')
    sys.path.insert(0, str(ROOT / 'amd_experiment'))
    from video_backend import verified_model_directory, verified_models
    if model_directory is not None:
        models = verified_model_directory(model_directory)
    elif image_run is not None:
        models = verified_models(image_run)
    else:
        raise ValueError("Specify a model directory or an image run.")
    out.mkdir(parents=True, exist_ok=False)
    runtime = out / 'runtime'
    runtime.mkdir()
    base = Path(sys.base_prefix)
    for name in ('python.exe', 'pythonw.exe', 'python3.dll', 'python312.dll', 'LICENSE.txt',
                 'vcruntime140.dll', 'vcruntime140_1.dll'):
        shutil.copy2(base / name, runtime)
    for name in ('Lib', 'DLLs', 'tcl'):
        shutil.copytree(base / name, runtime / name, ignore=shutil.ignore_patterns(
            'site-packages', '__pycache__', '*.pyc', '*.pdb', 'test', 'tests'))
    site = runtime / 'Lib' / 'site-packages'
    install_packages(site, wheelhouses)
    # Use the same PyTaskbar fork as VideOCR's Windows dependency.
    if taskbar_zip:
        data = taskbar_zip.read_bytes()
    else:
        with urlopen(f'https://codeload.github.com/timminator/PyTaskbar/zip/{TASKBAR}', timeout=60) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != TASKBAR_HASH:
        raise ValueError('PyTaskbar archive hash mismatch')
    with zipfile.ZipFile(io.BytesIO(data)) as bundle:
        taskbar = site / 'PyTaskbar'
        taskbar.mkdir()
        for name in ('PyTaskbar/__init__.py', 'PyTaskbar/ProgressAPI.py', 'LICENSE'):
            (taskbar / Path(name).name).write_bytes(bundle.read(f'PyTaskbar-{TASKBAR}/{name}'))
    app = out / 'app'
    app.mkdir()
    for name in ('VideOCR.py', '_version.py', 'CLI/videocr_cli.py'):
        dest = app / name
        dest.parent.mkdir(exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    for name in ('CLI/videocr', 'languages'):
        shutil.copytree(ROOT / name, app / name, ignore=shutil.ignore_patterns('__pycache__'))
    worker = app / 'amd_experiment'
    worker.mkdir()
    for name in ('video_export', 'video_backend', 'dxgi_adapters', 'paddlex_runtime', 'real_image_compare', 'ocr_metrics'):
        shutil.copy2(ROOT / 'amd_experiment' / (name + '.py'), worker)
    for kind in ('det', 'rec'):
        dest = app / 'models' / kind
        dest.mkdir(parents=True)
        for name in ('inference.onnx', 'inference.yml'):
            shutil.copy2(models / kind / name, dest)
    for name in ('VideOCR.ico', 'VideOCR.png'):
        shutil.copy2(ROOT / 'Installer' / name, app)
    shutil.copy2(ROOT / 'windows/desktop.pyw', app)
    shutil.copy2(ROOT / 'LICENSE', out)
    shutil.copy2(ROOT / 'AMD_DESKTOP.md', out)
    shutil.copy2(ROOT / 'windows/PP-OCR-LICENSE.txt', app / 'models' / 'LICENSE.txt')
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    subprocess.run([str(compiler), '/nologo', '/optimize+', '/platform:x64', '/target:winexe',
                    '/reference:System.Windows.Forms.dll', f'/win32icon:{app / "VideOCR.ico"}',
                    f'/out:{out / "VideOCR-AMD.exe"}', str(ROOT / 'windows/DesktopLauncher.cs')], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True, help='New, empty destination')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--image-run', type=Path, help='Previous successful export with model configs')
    source.add_argument('--models', type=Path, help='Verified model directory containing det and rec')
    parser.add_argument('--wheelhouse', type=Path, action='append')
    parser.add_argument('--taskbar-zip', type=Path)
    args = parser.parse_args()
    build(args.output.resolve(), args.image_run, args.wheelhouse, args.taskbar_zip, args.models)
