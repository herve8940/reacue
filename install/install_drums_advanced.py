"""Cross-platform isolated installer: python install/install_drums_advanced.py."""
from pathlib import Path
import io
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reacue_adt import CODE_REV, MODEL_REV, VARIANT


def main():
    uv = shutil.which('uv')
    if not uv:
        raise SystemExit('Install ReaCue first: uv is required / Installe ReaCue : uv est requis.')
    env = ROOT / '.venv-drums-advanced'
    py = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    subprocess.run([uv, 'venv', '--python', '3.12', str(env)], check=True) if not py.exists() else None
    cmd = [uv, 'pip', 'install', '--python', str(py), '-r', str(ROOT / 'requirements-drums-advanced.txt')]
    if sys.platform.startswith('linux'):
        cmd += ['--torch-backend', 'cpu']
    subprocess.run(cmd, check=True)
    ready = ROOT / 'drums/adt-str-model/.ready'
    ready.unlink(missing_ok=True)
    dest = ROOT / 'drums/ADT_STR'
    dest.mkdir(parents=True, exist_ok=True)
    url = f'https://github.com/pier-maker92/ADT_STR/archive/{CODE_REV}.zip'
    print('Downloading pinned ADT_STR code / Téléchargement du code ADT_STR', flush=True)
    with urllib.request.urlopen(url, timeout=120) as response:
        z = zipfile.ZipFile(io.BytesIO(response.read()))
    prefix = z.namelist()[0]
    for entry in z.infolist():
        rel = Path(entry.filename.removeprefix(prefix))
        if entry.is_dir() or rel.is_absolute() or '..' in rel.parts:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(entry))
    # Only inference weights/config for this variant, never the training dataset.
    code = '''from huggingface_hub import snapshot_download
snapshot_download("Pierfrancesco/adt-str", revision=REV, local_dir=DEST,
                  allow_patterns=[VARIANT + "/*", "LICENSE*", "README.md"])
'''.replace('REV', repr(MODEL_REV)).replace('DEST', repr(str(ROOT / 'drums/adt-str-model'))).replace('VARIANT', repr(VARIANT))
    subprocess.run([str(py), '-c', code], check=True)
    print('Checking model loading and inference / Test du modèle', flush=True)
    # One full 2.56 s chunk: exercises the actual decoder and not just imports.
    code = '''import sys, torch, tempfile
sys.path[:0] = [ROOT, SOURCE]
import reacue_metal
reacue_metal.configure()
from adt_transcriber import ADTTranscriber
model = ADTTranscriber.from_pretrained(MODEL, variant=VARIANT, device="cpu")
with tempfile.TemporaryDirectory() as temp:
    model.transcribe(torch.zeros(61440), sample_rate=24000, output_dir=temp, batch_size=1)
'''
    for name, value in [('SOURCE',str(dest)),('ROOT',str(ROOT)),('MODEL',str(ROOT / 'drums/adt-str-model')),('VARIANT',VARIANT)]:
        code = code.replace(name, repr(value))
    subprocess.run([str(py), '-c', code], check=True)
    (ROOT / 'drums/adt-str-model/.ready').write_text(CODE_REV + '\n' + MODEL_REV)
    print('ADT_STR_READY — advanced engine enabled in Auto / moteur avancé activé en Auto')


if __name__ == '__main__':
    main()
