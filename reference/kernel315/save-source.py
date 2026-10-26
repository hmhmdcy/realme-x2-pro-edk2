"""Record only the changed candidate sources and their incremental patch."""
from pathlib import Path
import difflib,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel313'
TREE=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
KERNEL=Path('/home/cy122/x2pro-linux/camera314-streams-kernel')
files={'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp':HERE/'pipeline/camss_vfe.cpp',
 'include/libcamera/internal/v4l2_device.h':HERE/'framework/include/libcamera/internal/v4l2_device.h',
 'src/libcamera/v4l2_device.cpp':HERE/'framework/src/libcamera/v4l2_device.cpp'}
patch=[];hashes={}
for name,p in files.items():
 data=p.read_bytes();assert (TREE/name).read_bytes()==data
 after=data.decode();hashes[name]=hashlib.sha256(data).hexdigest()
 if name.endswith('camss_vfe.cpp'):before=(OLD/'pipeline/camss_vfe.cpp').read_text()
 elif name.endswith('.h'):before=after.replace('\n\tSignal<uint32_t, uint64_t> frameStartTimestamp;','')
 else:
  before=after
  a=before.index('/**\n * \\var V4L2Device::frameStartTimestamp');b=before.index('/**\n * \\var V4L2Device::frameStart\n',a)
  before=before[:a]+before[b:]
  before=before.replace('\tconst uint64_t timestamp = uint64_t(event.timestamp.tv_sec) * 1000000000ULL\n\t\t\t\t + event.timestamp.tv_nsec;\n\tframeStartTimestamp.emit(event.u.frame_sync.frame_sequence, timestamp);\n','')
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(HERE/'hardware-raw.patch').write_text(''.join(patch))
subprocess.run(['git','-C',str(KERNEL),'diff','--quiet'],check=True)
subprocess.run(['git','-C',str(KERNEL),'switch','samurai-raw314'],check=True,capture_output=True)
build=json.loads((HERE/'build-validation.json').read_text())
report=dict(stage=315,sdk_tree=str(TREE),changed_source_sha256=hashes,base_userspace_stage=313,
 ipa_stage=313,profiles_stage=313,kernel_source_stage=314,
 kernel_commit=subprocess.check_output(['git','-C',str(KERNEL),'rev-parse','HEAD'],text=True).strip(),
 final_build_attempt=build['attempt'],kernel_dt_sensor_sources_changed=False,
 system_install=False,raw_capture_copy=False,raw_only_internal_processed_stream=True,
 pairing='Independent line kernel sequences map to standard FRAME_SYNC CLOCK_MONOTONIC event times; require delta <= min(1ms,observed frame period/8). Software event timing, not an exposure timestamp or hardware frame ID.',
 source_patch='hardware-raw.patch',goal_complete=False)
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
