from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
q=host.ssh('v4l2-ctl -d /dev/v4l-subdev15 --get-ctrl=analogue_gain,exposure,vertical_blanking',check=False,timeout=15)
(host.PRIVATE/'cached-main-controls-private.log').write_bytes(q.stdout+q.stderr);print(q.stdout.decode()+q.stderr.decode())
W=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera273-r21-built/src/libcamera-v0.7.2')
for name in ['src/ipa/simple/algorithms/agc.cpp','src/ipa/simple/soft_simple.cpp','src/libcamera/software_isp/software_isp.cpp']:
 lines=(W/name).read_text().splitlines();selected=set()
 for i,line in enumerate(lines):
  if any(term in line for term in ['ExposureTimeMode','AnalogueGainMode','getSensorControls','queueRequest','frameContext.agc','frameContext.exposure','manualGain']):selected.update(range(max(0,i-3),min(len(lines),i+8)))
 print(name)
 for i in sorted(selected):print(str(i+1)+':'+lines[i])
