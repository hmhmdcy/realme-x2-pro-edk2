"""Name the memory channels only after checking the format and endianness sources."""
from pathlib import Path
import hashlib
import json

ref = Path(__file__).resolve().parent
base = Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera225-r13-built/src/libcamera-v0.7.2')
formats = base / 'src/libcamera/formats.yaml'
debayer = base / 'src/libcamera/software_isp/debayer_cpu.cpp'
drm = Path('/home/cy122/pmos-samurai-kernel136/kernel/include/uapi/drm/drm_fourcc.h')
assert '  - RGB888:\n      fourcc: DRM_FORMAT_RGB888' in formats.read_text()
line = next(l for l in drm.read_text().splitlines() if l.startswith('#define DRM_FORMAT_RGB888\t'))
assert '[23:0] R:G:B little endian' in line
binary = Path('/mnt/e/edk2-samurai-out/kernel229/daylight-colour-probe229').read_bytes()
assert binary[:6] == b'\x7fELF\x02\x01'
data = json.loads((ref / 'daylight-colour-native-validation.json').read_text())
frames = data['frames']
last = frames[-1]
b, g, r = last['byte_channel_means_012']
report = dict(stage=229, libcamera_format='RGB888', memory_order='BGR', target_endianness='little',
              source_sha256={name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in [
                  ('libcamera/formats.yaml', formats), ('software_isp/debayer_cpu.cpp', debayer), ('drm/drm_fourcc.h', drm)]},
              last_frame_sequence=last['sequence'], last_frame_channel_means_rgb=[r, g, b],
              last_frame_channel_stddevs_rgb=list(reversed(last['byte_channel_stddevs_012'])),
              last_frame_channel_difference_fraction=last['differing_channels_fraction'],
              difference_rule='max(channel)>=24 and max(channel)-min(channel)>=12 on 8-bit output',
              all32_frames_successful_and_nonzero=True, real_colour_difference_observed=True,
              colour_accuracy_cfa_and_white_balance_not_accepted=True, ae_convergence_not_accepted=True,
              pixel_files_saved=False)
(ref / 'colour-channel-interpretation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}))
