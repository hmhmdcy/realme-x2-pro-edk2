from pathlib import Path
import hashlib, json, tarfile
import numpy as np

ref = Path(__file__).resolve().parent
archive = Path('E:/edk2-samurai-out/kernel177/k177-all-private.tar.gz')
with tarfile.open(archive) as ar:
    data = np.frombuffer(ar.extractfile('k177-suspend-active/active-capture-private.raw').read(), dtype='<i2').astype(np.float64)
code = [1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0]
template = np.tile(np.r_[np.zeros(25), np.repeat(code, 10), np.zeros(25)], 3)
n = 960
frames = data[:len(data)//n*n].reshape(-1, n)
frames -= frames.mean(axis=1, keepdims=True)
window = np.hanning(n)
kernel = window*np.exp(-2j*np.pi*1511*np.arange(n)/48000)
amplitude = 2*np.abs(frames@kernel)/window.sum()
energy = amplitude**2
peaks = []
for start in range(len(energy)-len(template)+1):
    selected = energy[start:start+len(template)]
    corr = float(np.corrcoef(template, selected)[0, 1]) if selected.std() else 0
    peaks.append((corr, start))
corr, start = max(peaks)
report = dict(stage=177, kernel_build=176, method='1511Hz coherent energy matched to three complete 4-second stereo stimulus blocks',
              capture_duration_seconds=len(data)/48000, template_duration_seconds=12,
              best_contiguous_code_correlation=corr, best_contiguous_code_start_seconds=start*.02,
              method_only_measures_captured_sample_timeline=True,
              independent_wall_clock_alignment_and_lossless_sleep_continuity_not_verified=True,
              human_quality_not_verified=True, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(ref / 'active-code-analysis.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
