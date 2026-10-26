from pathlib import Path
import re
root=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera218')
files={
 'src/libcamera/software_isp/software_isp.cpp':r'sensorInfo|configure\(|ipa_->|IPAConfigInfo',
 'include/libcamera/ipa/soft.mojom':r'.',
 'src/libcamera/pipeline/simple/simple.cpp':r'controls_|controls\(\)|sensorInfo\(|swIsp_->configure|queueRequest|processStats',
 'src/ipa/simple/algorithms/agc.h':r'.',
 'src/apps/cam/main.cpp':r'list-controls|list-properties|OptListControls|OptInfo',
}
for name,pattern in files.items():
 print('\nFILE',name)
 lines=(root/name).read_text().splitlines();wanted=set()
 for i,line in enumerate(lines):
  if re.search(pattern,line):wanted.update(range(max(0,i-3),min(len(lines),i+5)))
 for i in sorted(wanted):print(f'{i+1}: {lines[i]}')
