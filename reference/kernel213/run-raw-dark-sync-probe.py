from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent;assert len(sys.argv)==4 and sys.argv[1] in ['helper','lut'] and sys.argv[2] in ['raw','rgb'] and sys.argv[3] in ['0','2'];variant=sys.argv[1];kind=sys.argv[2];pattern=int(sys.argv[3]);tag=variant+'-'+kind+'-p'+str(pattern)+'-sync'
assert json.loads((here/'raw-dark-sync-probe-build-validation.json').read_text())['raw10_dark_statistics_probe_built']
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,signal,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
variant=VARIANT;kind=KIND;pattern=PATTERN;tag=TAG;out=root/('k213-'+tag);out.mkdir(mode=0o700)
for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']:assert Path(p,'power/runtime_status').read_text().strip()=='suspended'
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1;node='/dev/'+nodes[0].name
names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern']
def controls():
    p=subprocess.run(['v4l2-ctl','-d',node,'--get-ctrl='+','.join(names)],capture_output=True,text=True,timeout=10);assert p.returncode==0
    return {k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',p.stdout)}
saved=controls();assert set(saved)==set(names) and saved['test_pattern']==0
prefix=Path('/run/samurai-camera213-'+variant);proof=json.loads((root/('k213-libcamera-build/'+variant+'-candidate-summary.json')).read_text())
assert all(hashlib.sha256((prefix/name).read_bytes()).hexdigest()==digest for name,digest in proof['products'].items())
user=pwd.getpwuid(10000);sessions=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:sessions.append(p)
    except OSError:pass
assert len(sessions)==1
entries=dict(p.split(b'=',1) for p in (sessions[0]/'environ').read_bytes().split(b'\0') if b'=' in p)
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR=entries[b'XDG_RUNTIME_DIR'].decode(),LD_LIBRARY_PATH=str(prefix/'usr/lib'),LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa'),LIBCAMERA_LOG_LEVELS='*:INFO,Debayer:DEBUG')
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
timed_out=False;killed=False
try:
    process=subprocess.Popen(['/run/samurai-camera213-raw-dark-sync-probe',node,kind,str(pattern)],preexec_fn=demote,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:stdout,stderr=process.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        timed_out=True;process.send_signal(signal.SIGINT)
        try:stdout,stderr=process.communicate(timeout=10)
        except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=5)
finally:
    for group in [['test_pattern','vertical_blanking'],['exposure','analogue_gain','digital_gain']]:
        p=subprocess.run(['v4l2-ctl','-d',node,'--set-ctrl='+','.join(k+'='+str(saved[k]) for k in group)],capture_output=True,timeout=10);assert p.returncode==0
assert controls()==saved
(out/'stdout-private.json').write_bytes(stdout);(out/'stderr-private.txt').write_bytes(stderr)
time.sleep(2);after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
data=json.loads(stdout) if process.returncode==0 else None
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report=dict(stage=213,variant=variant,uid=10000,room_lights_off=True,requested_sensor_pattern=pattern,capture_kind=kind,test_pattern_effectiveness_not_assumed=True,all_active_raw10_pixels_examined=kind=='raw',raw_row_padding_excluded=kind=='raw',stream_geometry={k:data[k] for k in ['width','height','stride']} if data else {},external_illumination_used=False,program_exit=process.returncode,timed_out=timed_out,forced_kill=killed,frames=data['frames'] if data else [],test_pattern_and_sensor_controls_restored=True,dma_buf_sync_start_end_read=True,camera_devices_suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults,error_lines=[l for l in stderr.decode(errors='replace').splitlines() if 'ERROR' in l],system_camera_products_not_replaced=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('VARIANT',repr(variant)).replace('KIND',repr(kind)).replace('PATTERN',repr(pattern)).replace('TAG',repr(tag))
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/(tag+'-probe-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/(tag+'-probe-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
