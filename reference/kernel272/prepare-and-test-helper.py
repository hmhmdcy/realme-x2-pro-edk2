"""Compile a candidate helper against retained r20 SDK; no APK/phone changes."""
from pathlib import Path
import difflib,hashlib,json,shutil,struct,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
b='/work/libcamera271-r20-built/src/libcamera-v0.7.2';source=SDK/(b.lstrip('/')+'/src/ipa/libipa/camera_sensor_helper.cpp')
before=source.read_text();assert 'REGISTER_CAMERA_SENSOR_HELPER("s5k3m5"' in before
assert 'REGISTER_CAMERA_SENSOR_HELPER("s5kgw1"' not in before
needle='class CameraSensorHelperS5k3m5 : public CameraSensorHelper';assert before.count(needle)==1
helper='''class CameraSensorHelperS5kgw1 : public CameraSensorHelper
{
public:
	CameraSensorHelperS5kgw1()
	{
		/* Native code 0x20 is 1x; normal-mode maximum 0x400 is 32x. */
		gain_ = AnalogueGainLinear{ 1, 0, 0, 32 };
	}
};
REGISTER_CAMERA_SENSOR_HELPER("s5kgw1", CameraSensorHelperS5kgw1)

'''
after=before.replace(needle,helper+needle)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/src/ipa/libipa/camera_sensor_helper.cpp',tofile='b/src/ipa/libipa/camera_sensor_helper.cpp'))
(R/'0025-s5kgw1-native-gain-helper.patch').write_text(patch)
binary=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-modules/com.qti.sensor.s5kgw1.so')
raw=binary.read_bytes()
expected={0x12dc:0xd2e8080e,0x12e4:0x1e661007,0x12fc:0x7100251f,
 0x1324:0xd2e8120f,0x1328:0xd2e81010,0x1330:0x1e59ec89,0x1338:0xd2e7f411,0x1374:0x1e790b1a}
for offset,word in expected.items():assert struct.unpack_from('<I',raw,offset)[0]==word,hex(offset)
# 0x4040... = 32, 0x4090... = 1024, 0x4080... = 512, 0x3fa0... = 1/32.
assert [struct.unpack('<d',struct.pack('<Q',n))[0] for n in [0x4040000000000000,0x4090000000000000,0x4080000000000000,0x3fa0000000000000]]==[32,1024,512,1/32]
work=SDK/'private/gw1-helper272';work.mkdir(mode=0o700)
(work/'camera_sensor_helper.cpp').write_text(after);shutil.copyfile(R/'gain-helper-test.cpp',work/'gain-helper-test.cpp')
common=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',
 '-DLIBCAMERA_PRIVATE','-DLIBCAMERA_BASE_PRIVATE','-include',b+'/output/config.h',
 '-I'+b+'/include','-I'+b+'/output/include','-I'+b+'/src/ipa','-I'+b+'/src/ipa/libipa',
 '-I'+b+'/output/include/libcamera/ipa','-I'+b+'/output/include/libcamera']
results={}
for name,candidate in [('candidate',True),('negative-r20',False)]:
 target='/private/gw1-helper272/test-'+name
 cmd=common+['/private/gw1-helper272/gain-helper-test.cpp']
 if candidate:cmd+=['/private/gw1-helper272/camera_sensor_helper.cpp']
 cmd+=[b+'/output/src/ipa/libipa/libipa.a','-L'+b+'/output/src/libcamera','-L'+b+'/output/src/libcamera/base','-lcamera','-lcamera-base','-o',target]
 q=subprocess.run(cmd,capture_output=True,timeout=180);(host.PRIVATE/(name+'-helper-build-private.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,'Inspect helper compiler log'
 q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+b+'/output/src/libcamera:'+b+'/output/src/libcamera/base',target],capture_output=True,timeout=30)
 (host.PRIVATE/(name+'-helper-run-private.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==(0 if candidate else 3),(name,'Inspect helper result')
 results[name]=dict(exit=q.returncode,report=json.loads(q.stdout) if q.stdout else None)
assert source.read_text()==before and binary.read_bytes()==raw
report=dict(stage=272,source_before_sha256=hashlib.sha256(before.encode()).hexdigest(),source_after_sha256=hashlib.sha256(after.encode()).hexdigest(),
 patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),oem_library_sha256=hashlib.sha256(raw).hexdigest(),
 original_instructions_checked=[hex(n) for n in expected],oem_library_not_executed=True,
 normal_mode_gain_codes=[32,1024],real_gain_range=[1,32],hdr_mode9_not_supported_by_candidate=True,
 actual_compiled_cpp_factory_test=True,arm_emulated_cpp=True,results=results,
 prior_r20_sources_and_libraries_unchanged=True,no_apk_built_or_installed=True,phone_unchanged=True,
 physical_gw1_gain_response_pending=True)
(R/'helper-candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
