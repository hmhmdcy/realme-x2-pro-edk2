"""One-time 315 source preparation; edit the resulting sources thereafter."""
from pathlib import Path
import shutil, subprocess
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kernel313'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel315');PRIVATE.mkdir(exist_ok=True)
TREE=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
KERNEL=Path('/home/cy122/x2pro-linux/camera314-streams-kernel')
assert not (HERE/'pipeline').exists()
shutil.copytree(OLD/'pipeline',HERE/'pipeline')
# The prototype incorrectly labelled CSI reception as exposure. Retain its
# diagnostic diff privately, and restore only these five prototype files.
names=['camss-vfe-17x.c','camss-vfe.c','camss-vfe.h','camss-video.c','camss-video.h']
paths=['drivers/media/platform/qcom/camss/'+name for name in names]
(PRIVATE/'discarded-soe-prototype.patch').write_bytes(subprocess.check_output(['git','-C',str(KERNEL),'diff','--',*paths]))
for name in paths:
 (KERNEL/name).write_bytes(subprocess.check_output(['git','-C',str(KERNEL),'show','HEAD:'+name]))
for name in ['include/libcamera/internal/v4l2_device.h','src/libcamera/v4l2_device.cpp']:
 p=HERE/'framework'/name;p.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(TREE/name,p)
header=HERE/'framework/include/libcamera/internal/v4l2_device.h'
s=header.read_text().replace('Signal<uint32_t> frameStart;', 'Signal<uint32_t> frameStart;\n\tSignal<uint32_t, uint64_t> frameStartTimestamp;')
header.write_text(s)
source=HERE/'framework/src/libcamera/v4l2_device.cpp'
s=source.read_text().replace('\tframeStart.emit(event.u.frame_sync.frame_sequence);', '''\tconst uint64_t timestamp = uint64_t(event.timestamp.tv_sec) * 1000000000ULL
\t\t\t\t + event.timestamp.tv_nsec;
\tframeStartTimestamp.emit(event.u.frame_sync.frame_sequence, timestamp);
\tframeStart.emit(event.u.frame_sync.frame_sequence);''')
where=s.index('/**\n * \\var V4L2Device::frameStart')
s=s[:where]+'''/**
 * \\var V4L2Device::frameStartTimestamp
 * \\brief Signal a frame-sync event with its CLOCK_MONOTONIC timestamp
 *
 * The arguments are the received frame sequence and the kernel event timestamp
 * in nanoseconds. This marks reception of a frame, not start of exposure.
 */

'''+s[where:]
source.write_text(s)
print('Prepared315 userspace; kernel timestamp prototype discarded before build/deployment.')
