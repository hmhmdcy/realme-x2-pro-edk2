"""Finite dark RAW / digital-white tests; no room light or flash is used."""
from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==3 and sys.argv[1] in ['isolated','system'] and sys.argv[2] in ['dark-raw','dark-rgb','white-raw','white-rgb']
mode,test=sys.argv[1:];tag=mode+'-'+test
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,shutil,signal,stat,subprocess,time
os.umask(0o077);base=Path('/var/lib/samurai/k214-baseline');stage=Path('/var/lib/samurai/k214-package-candidates')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
mode=__MODE__;test=__TEST__;kind=test.split('-')[1];white=test.startswith('white');tag=mode+'-'+test
out=Path('/var/lib/samurai/k214-'+tag)
if out.exists():
    assert tag=='isolated-dark-raw' and (out/'library-resolution-private.txt').is_file() and not (out/'dmesg-before-private.txt').exists() and not (out/'stdout-private.json').exists()
    archived=out.with_name(out.name+'-preflight-soname');assert not archived.exists();out.rename(archived)
out.mkdir(mode=0o700)
prefix=Path('/run/samurai-camera214-full') if mode=='isolated' else Path('/')
manifest=json.loads((stage/'forward-manifest.json').read_text())
for package in manifest['packages']:
    for name,item in package['files'].items():
        if name.startswith('etc/'):continue
        p=prefix/name
        if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
        else:assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
config=Path('/etc/libcamera/configuration.yaml');assert hashlib.sha256(config.read_bytes()).hexdigest()=='771c516f85cb3c408e42a561beaa4a4bd56f2db9890c81d40e28468205ecc12e'
assert stat.S_IMODE(config.parent.stat().st_mode)==0o755
if mode=='isolated':assert Path('/lib/apk/db/installed').read_bytes()==(base/'apk-installed-before-private.txt').read_bytes()
else:
    installed={}
    for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
        fields={line[:1]:line[2:] for line in block.splitlines() if len(line)>1 and line[1]==':' and line[0] in 'PV'}
        if 'P' in fields:installed[fields['P']]=fields['V']
    assert all(installed[p['name']]==p['version'] for p in manifest['packages'])
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
def node(name):
    found=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()==name];assert len(found)==1
    return '/dev/'+found[0].name
sensor=node('imx471 7-0010');csid=node('msm_csid0');names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern']
def controls():
    text=subprocess.check_output(['v4l2-ctl','-d',sensor,'--get-ctrl='+','.join(names)],text=True,timeout=10)
    return {k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',text)}
saved=controls();assert set(saved)==set(names) and saved['test_pattern']==0
assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True,timeout=10))
media_before=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],timeout=10);(out/'media-before-private.txt').write_bytes(media_before)
probe_name='csid-known-input-sync-probe' if white else 'raw-dark-sync-probe'
probes=Path('/run/samurai-camera214-probes');probes.mkdir(mode=0o755,exist_ok=True);probes.chmod(0o755)
source=stage/'probes'/probe_name;probe=probes/probe_name
if not probe.exists():shutil.copyfile(source,probe);probe.chmod(0o755)
assert hashlib.sha256(probe.read_bytes()).digest()==hashlib.sha256(source.read_bytes()).digest()
user=pwd.getpwuid(10000);sessions=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:sessions.append(p)
    except OSError:pass
assert len(sessions)==1
entries=dict(p.split(b'=',1) for p in (sessions[0]/'environ').read_bytes().split(b'\0') if b'=' in p)
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR=entries[b'XDG_RUNTIME_DIR'].decode(),LIBCAMERA_LOG_LEVELS='*:INFO,Debayer:DEBUG')
if mode=='isolated':
    env.update(LD_LIBRARY_PATH=str(prefix/'usr/lib'),LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa'))
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
ldd=subprocess.run(['ldd',str(probe)],preexec_fn=demote,env=env,capture_output=True,text=True,timeout=10);(out/'library-resolution-private.txt').write_text(ldd.stdout+ldd.stderr)
assert ldd.returncode==0
resolved=re.search(r'^\s*libcamera\.so\.0\.7(?:\.2)?\s+=>\s+(\S+)',ldd.stdout,re.M);assert resolved
assert Path(resolved[1]).resolve()==(prefix/'usr/lib/libcamera.so.0.7.2').resolve()
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
timed_out=False;killed=False
try:
    process=subprocess.Popen([str(probe),csid if white else sensor,kind,'4' if white else '0'],preexec_fn=demote,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:stdout,stderr=process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        timed_out=True;process.send_signal(signal.SIGINT)
        try:stdout,stderr=process.communicate(timeout=10)
        except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=5)
finally:
    subprocess.run(['v4l2-ctl','-d',csid,'--set-ctrl=test_pattern=0'],capture_output=True,check=True,timeout=10)
    if white:subprocess.run(['media-ctl','-d','/dev/media0','--links','"msm_csiphy2":1 -> "msm_csid0":0 [1]'],capture_output=True,check=True,timeout=10)
    for group in [['test_pattern','vertical_blanking'],['exposure','analogue_gain','digital_gain']]:
        subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl='+','.join(k+'='+str(saved[k]) for k in group)],capture_output=True,check=True,timeout=10)
assert controls()==saved
assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True,timeout=10))
media_after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],timeout=10);(out/'media-after-private.txt').write_bytes(media_after)
assert media_after==media_before
(out/'stdout-private.json').write_bytes(stdout);(out/'stderr-private.txt').write_bytes(stderr)
time.sleep(2);after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
data=json.loads(stdout) if process.returncode==0 else None
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report=dict(stage=214,mode=mode,test=test,uid=10000,room_lights_off=True,external_illumination_used=False,dma_buf_sync_start_end_read=True,all_active_raw_pixels_examined=kind=='raw',raw_row_padding_excluded=kind=='raw',default_system_libraries_used=mode=='system',library_resolution_verified=True,default_cpu_configuration_used=True,program_exit=process.returncode,timed_out=timed_out,forced_kill=killed,stream_geometry={k:data[k] for k in ['width','height','stride']} if data else {},frames=data['frames'] if data else [],test_patterns_and_sensor_controls_restored=True,media_graph_restored_byte_exact=True,camera_devices_suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults,error_line_count=sum('ERROR' in l for l in stderr.decode(errors='replace').splitlines()),sensor_helper_missing_warning=b'No IPA found for' in stderr or b'Failed to create camera sensor helper' in stderr,static_sensor_properties_missing_warning=b'No static properties available for' in stderr)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('__MODE__',repr(mode)).replace('__TEST__',repr(test))
p=host.ssh('python3 -',input=code.encode(),timeout=110);(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(tag+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
