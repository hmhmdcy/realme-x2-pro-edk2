from pathlib import Path
import gzip,hashlib,host,io,json,os,shlex,shutil,subprocess,tarfile

os.umask(0o077)
here=Path(__file__).resolve().parent;private=host.PRIVATE
root=Path('/home/cy122/x2pro-linux/libcamera214-root');build=root/'work/libcamera218/output'
assert json.loads((here/'candidate-build-validation.json').read_text())['candidate_simple_virtual_cpu_egl_build_passed']
proof=json.loads((here/'candidate-source-validation.json').read_text())
assert all(hashlib.sha256((root/'work/libcamera218'/name).read_bytes()).hexdigest()==digest for name,digest in proof['files'].items())
prefix=root/'private/cpu218-runtime';assert not prefix.exists();(prefix/'usr/lib').mkdir(parents=True)
sources={
    'usr/lib/libcamera.so.0.7.2':build/'src/libcamera/libcamera.so.0.7.2',
    'usr/lib/libcamera-base.so.0.7.2':build/'src/libcamera/base/libcamera-base.so.0.7.2',
    **{'bin/'+name:build/'test'/name for name in ['native-quad','native-quad-cpu','quad-bayer','bayer-format']},
}
records={}
for name,source in sources.items():
    dest=prefix/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
    subprocess.run(['chroot',str(root),'/usr/bin/strip','--strip-debug','/private/cpu218-runtime/'+name],check=True,capture_output=True)
    dest.chmod(0o755);data=dest.read_bytes();assert data[:4]==b'\x7fELF' and int.from_bytes(data[18:20],'little')==183
    records[name]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),mode=0o755)
for name,target in [('libcamera.so.0.7','libcamera.so.0.7.2'),('libcamera-base.so.0.7','libcamera-base.so.0.7.2')]:
    (prefix/'usr/lib'/name).symlink_to(target);records['usr/lib/'+name]=dict(target=target)
for name,enabled in [('config-disabled',False),('config-enabled',True)]:
    file=prefix/name/'libcamera/configuration.yaml';file.parent.mkdir(parents=True)
    file.write_text('version: 1\nconfiguration:\n  software_isp:\n    mode: cpu\n    threads: 4\n    experimental_imx471_native_quad: '+str(enabled).lower()+'\n');file.chmod(0o644)
    records[str(file.relative_to(prefix))]=dict(sha256=hashlib.sha256(file.read_bytes()).hexdigest(),bytes=file.stat().st_size,mode=0o644)
(prefix/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
archive=private/'cpu-runtime-private.tar.gz'
assert not archive.exists()
with tarfile.open(archive,'w:gz',dereference=False) as tar:
    for path in sorted(prefix.rglob('*')):
        if path.is_file() or path.is_symlink():tar.add(path,arcname=str(path.relative_to(prefix)),recursive=False)
data=archive.read_bytes();sha=hashlib.sha256(data).hexdigest()
code=r'''
from pathlib import Path
root=Path('/var/lib/samurai');out=root/'k218-cpu-isp-tests'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not out.exists();out.mkdir(mode=0o700);(out/'runtime.tar.gz').touch(mode=0o600)
print('ready')
'''
assert host.ssh('python3 -',input=code.encode(),timeout=30).stdout.strip()==b'ready'
destination='/var/lib/samurai/k218-cpu-isp-tests/runtime.tar.gz'
for offset in range(0,len(data),65536):
    chunk=data[offset:offset+65536]
    code="import sys,hashlib;from pathlib import Path;p=Path("+repr(destination)+");b=sys.stdin.buffer.read();assert len(b)=="+str(len(chunk))+" and hashlib.sha256(b).hexdigest()=="+repr(hashlib.sha256(chunk).hexdigest())+";assert p.stat().st_size=="+str(offset)+";p.open('ab').write(b);print('ok')"
    assert host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30).stdout.strip()==b'ok'
code=r'''
from pathlib import Path,PurePosixPath
import hashlib,json,os,pwd,re,resource,subprocess,tarfile,time
root=Path('/var/lib/samurai');out=root/'k218-cpu-isp-tests';prefix=Path('/run/samurai-camera218-cpu')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k218-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not prefix.exists()
assert hashlib.sha256((out/'runtime.tar.gz').read_bytes()).hexdigest()==ARCHIVE_SHA
prefix.mkdir(mode=0o755)
with tarfile.open(out/'runtime.tar.gz') as tar:
    for member in tar.getmembers():
        p=PurePosixPath(member.name);assert not p.is_absolute() and '..' not in p.parts and not member.isdev()
        if member.issym():assert '/' not in member.linkname and member.linkname not in ['.','..']
    tar.extractall(prefix,filter='data')
for directory in [prefix]+[p for p in prefix.rglob('*') if p.is_dir()]:directory.chmod(0o755)
manifest=json.loads((prefix/'manifest.json').read_text())
for name,record in manifest.items():
    p=prefix/name
    if 'target' in record:assert p.is_symlink() and os.readlink(p)==record['target']
    else:assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'];p.chmod(record['mode'])
before=subprocess.check_output(['dmesg'])
def demote():
    resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(180,180));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    user=pwd.getpwuid(10000);os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
tests={}
for name,enabled,args in [('native-quad',False,[]),('quad-bayer',False,[]),('bayer-format',False,[]),('native-quad-cpu-default',False,[]),('native-quad-cpu-enabled',True,['--enabled'])]:
    executable='native-quad-cpu' if name.startswith('native-quad-cpu-') else name
    env=dict(PATH='/usr/bin:/bin',HOME=pwd.getpwuid(10000).pw_dir,
             XDG_CONFIG_HOME=str(prefix/('config-enabled' if enabled else 'config-disabled')),
             LD_LIBRARY_PATH=str(prefix/'usr/lib'),LIBCAMERA_LOG_LEVELS='*:ERROR')
    probe=prefix/'bin'/executable
    ld=subprocess.run(['ldd',str(probe)],preexec_fn=demote,env=env,capture_output=True,text=True,timeout=10)
    (out/(name+'-ldd-private.log')).write_text(ld.stdout+ld.stderr)
    assert ld.returncode==0
    for lib in ['libcamera','libcamera-base']:
        match=re.search(r'^\s*'+lib+r'\.so\.0\.7\s+=>\s+(\S+)',ld.stdout,re.M)
        assert match and Path(match[1]).resolve()==(prefix/'usr/lib'/(lib+'.so.0.7.2')).resolve()
    p=subprocess.run([str(probe)]+args,preexec_fn=demote,env=env,capture_output=True,timeout=150)
    (out/(name+'-stdout-private.log')).write_bytes(p.stdout);(out/(name+'-stderr-private.log')).write_bytes(p.stderr)
    assert p.returncode==0, name+' failed; inspect private logs before another attempt'
    tests[name]=json.loads(p.stdout) if name.startswith('native-quad') else dict(exit=0)
after=subprocess.check_output(['dmesg'])
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k218-baseline/installed-before-private.txt').read_bytes()
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
report=dict(stage=218,tests=tests,run_uid=10000,isolated_candidate_library_resolution_verified=True,
            real_libcamera_cpu_isp_and_dma_heap_test=True,synthetic_inputs_only=True,
            no_camera_sensor_or_gpu_started=True,no_installed_packages_changed=True,
            real_sensor_full_mode_still_unverified=True,taint=0,fault_counts=faults)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('ARCHIVE_SHA',repr(sha))
p=host.ssh('python3 -',input=code.encode(),timeout=210)
(private/'cpu-isp-tests-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'cpu-isp-tests-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
