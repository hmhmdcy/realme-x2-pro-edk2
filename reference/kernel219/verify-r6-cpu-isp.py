"""Reuse independently checked test binaries against the packaged full r6 core."""
from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'r6-staging-validation.json').read_text())['isolated_full_feature_runtime_staged']
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,resource,subprocess
root=Path('/var/lib/samurai');out=root/'k219-r6-cpu-tests';prefix=Path('/run/samurai-camera219-r6');probes=Path('/run/samurai-camera219-cpu')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not out.exists();out.mkdir(mode=0o700)
manifest=json.loads((probes/'manifest.json').read_text());before=subprocess.check_output(['dmesg'])
def demote():
 resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(180,180));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 user=pwd.getpwuid(10000);os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
tests={}
for name,enabled,args in [('quad-bayer',False,[]),('bayer-format',False,[]),('native-quad-cpu-default',False,[]),('native-quad-cpu-enabled',True,['--enabled'])]:
 executable='native-quad-cpu' if name.startswith('native-quad-cpu-') else name;probe=probes/'bin'/executable
 assert hashlib.sha256(probe.read_bytes()).hexdigest()==manifest['bin/'+executable]['sha256']
 env=dict(PATH='/usr/bin:/bin',HOME=pwd.getpwuid(10000).pw_dir,
          XDG_CONFIG_HOME=str(prefix/('config-full' if enabled else 'config-default')),
          LD_LIBRARY_PATH=str(prefix/'usr/lib'),LIBCAMERA_LOG_LEVELS='*:ERROR')
 ld=subprocess.run(['ldd',str(probe)],preexec_fn=demote,env=env,capture_output=True,text=True,timeout=10)
 (out/(name+'-ldd-private.log')).write_text(ld.stdout+ld.stderr);assert ld.returncode==0
 for lib in ['libcamera','libcamera-base']:
  m=re.search(r'^\s*'+lib+r'\.so\.0\.7\s+=>\s+(\S+)',ld.stdout,re.M)
  assert m and Path(m[1]).resolve()==(prefix/'usr/lib'/(lib+'.so.0.7.2')).resolve()
 p=subprocess.run([str(probe)]+args,preexec_fn=demote,env=env,capture_output=True,timeout=150)
 (out/(name+'-stdout-private.log')).write_bytes(p.stdout);(out/(name+'-stderr-private.log')).write_bytes(p.stderr);assert p.returncode==0,name
 tests[name]=json.loads(p.stdout) if name.startswith('native-quad') else dict(exit=0)
after=subprocess.check_output(['dmesg']);faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k219-baseline/installed-before-private.txt').read_bytes()
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
assert tests['native-quad-cpu-enabled']['cpu_isp_cases']==50 and tests['native-quad-cpu-enabled']['passed']
r=dict(stage=219,tests=tests,run_uid=10000,current_full_r6_libraries_resolution_verified=True,retained_test_binary_hashes_verified=True,
 synthetic_inputs_only=True,no_sensor_or_gpu_started=True,system_heap_configuration_used=True,
 installed_r5_packages_preserved=True,real_scene_colour_calibration_not_claimed=True,taint=0,fault_delta=faults)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=210);(host.PRIVATE/'r6-cpu-tests-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'r6-cpu-isp-tests-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
