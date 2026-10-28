"""Isolated ADT_STR worker. Raw GM notes/velocities/times are preserved in JSON."""
from pathlib import Path
import argparse
import json
import os
import sys
import time

CODE_REV = '77dbef225e7029478ebfb916f20c7a00274f0f12'
MODEL_REV = 'a33c5c6b191a4ca1e0f6dc22140947485eb36ce8'
VARIANT = 'setting-tau-0.8'
ROOT = Path(__file__).resolve().parent


def analyze(audio, output):
    import reacue_performance
    reacue_performance.configure()
    import reacue_metal
    reacue_metal.configure()
    import torch
    import soundfile as sf
    import pretty_midi
    reacue_performance.configure_torch(torch)
    sys.path.insert(0, str(ROOT / 'drums' / 'ADT_STR'))
    from adt_transcriber import ADTTranscriber
    device = 'cuda' if torch.cuda.is_available() else reacue_metal.device(torch)
    started = time.time()
    model = ADTTranscriber.from_pretrained(str(ROOT / 'drums' / 'adt-str-model'), variant=VARIANT, device=device)
    y, sr = sf.read(audio, dtype='float32', always_2d=True)
    wav = torch.from_numpy(y.mean(axis=1).copy())
    import tempfile
    with tempfile.TemporaryDirectory(prefix='reacue_adt_') as tmp:
        try:
            midi = model.transcribe(wav, sample_rate=sr, output_dir=tmp, batch_size=1)
        except (RuntimeError, NotImplementedError):
            if str(device) != 'mps':
                raise
            model.device = torch.device('cpu')
            model.model.to('cpu')
            midi = model.transcribe(wav, sample_rate=sr, output_dir=tmp, batch_size=1)
        notes = [{'t': n.start, 'end': n.end, 'pitch': n.pitch, 'velocity': n.velocity}
                 for inst in pretty_midi.PrettyMIDI(str(midi)).instruments for n in inst.notes
                 if 0 <= n.start < len(y) / sr and n.velocity > 0]
    notes.sort(key=lambda n: (n['t'], n['pitch']))
    data = dict(engine='adt-str', notes=notes, onsets={}, model_revision=MODEL_REV,
                code_revision=CODE_REV, variant=VARIANT, seconds=round(time.time()-started, 2))
    out = Path(output)
    temp = out.with_suffix('.tmp')
    temp.write_text(json.dumps(data), encoding='utf-8')
    os.replace(temp, out)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['analyze'])
    p.add_argument('--input', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--status')
    a = p.parse_args()
    analyze(a.input, a.out)
