from pathlib import Path
import hashlib,host,json,shlex
here=Path(__file__).resolve().parent
proof=json.loads((here/'gst-client-build-validation.json').read_text());binary=(host.PRIVATE/'probes/gst-default-camera-probe').read_bytes();assert hashlib.sha256(binary).hexdigest()==proof['sha256']
for offset in range(0,len(binary),65536):
    chunk=binary[offset:offset+65536]
    code="from pathlib import Path;import sys;p=Path('/run/samurai-camera214-probes/gst-default-camera-probe');"+("assert not p.exists();p.touch(mode=0o755);" if offset==0 else "")+"assert p.stat().st_size=="+str(offset)+";d=sys.stdin.buffer.read();assert len(d)=="+str(len(chunk))+";p.open('ab').write(d);p.chmod(0o755)"
    host.ssh('python3 -c '+shlex.quote(code),input=chunk,timeout=30)
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,re,signal,subprocess,time
os.umask(0o077);base=Path('/var/lib/samurai/k214-baseline');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k214-default-clients');assert not (out/'capture-summary.json').exists()
probe=Path('/run/samurai-camera214-probes/gst-default-camera-probe');assert hashlib.sha256(probe.read_bytes()).hexdigest()==__HASH__
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
listing=(out/'cam-list-stdout-private.txt').read_text();ids=re.findall(r'^\d+: Internal front camera \((.+)\)$',listing,re.M);assert len(ids)==1 and 'cci@ac4b000' in ids[0]
camera_id=ids[0];sensor=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(sensor)==1;sensor='/dev/'+sensor[0].name
names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern']
def controls():return {k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',subprocess.check_output(['v4l2-ctl','-d',sensor,'--get-ctrl='+','.join(names)],text=True,timeout=10))}
saved_controls=controls();assert set(saved_controls)==set(names) and saved_controls['test_pattern']==0
sessions=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:sessions.append(p)
    except OSError:pass
assert len(sessions)==1
saved=dict(item.split(b'=',1) for item in (sessions[0]/'environ').read_bytes().split(b'\0') if b'=' in item);user=pwd.getpwuid(10000)
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR=saved[b'XDG_RUNTIME_DIR'].decode(),LIBCAMERA_LOG_LEVELS='*:INFO',GST_REGISTRY=saved[b'XDG_RUNTIME_DIR'].decode()+'/samurai-camera214-client-registry.bin')
assert not Path(env['GST_REGISTRY']).exists()
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']
before=subprocess.check_output(['dmesg']);(out/'client-dmesg-before-private.txt').write_bytes(before)
results={}
for name,argv in [('cam',['cam','--camera',camera_id,'--stream=role=viewfinder,width=1920,height=1088,pixelformat=RGB888','--capture=6']),('gstreamer',[str(probe),camera_id])]:
    assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
    timed_out=False
    try:
        process=subprocess.Popen(argv,preexec_fn=demote,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:stdout,stderr=process.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            timed_out=True;process.send_signal(signal.SIGINT)
            try:stdout,stderr=process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();stdout,stderr=process.communicate(timeout=5)
    finally:
        for group in [['test_pattern','vertical_blanking'],['exposure','analogue_gain','digital_gain']]:
            subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl='+','.join(k+'='+str(saved_controls[k]) for k in group)],capture_output=True,check=True,timeout=10)
    assert controls()==saved_controls
    (out/(name+'-capture-stdout-private.txt')).write_bytes(stdout);(out/(name+'-capture-stderr-private.txt')).write_bytes(stderr)
    time.sleep(2)
    frames=stdout.count(b'seq:') if name=='cam' else (json.loads(stdout).get('frames',0) if process.returncode==0 else 0)
    results[name]=dict(exit=process.returncode,timed_out=timed_out,frames=frames,camera_devices_suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices),error_line_count=sum('ERROR' in line for line in stderr.decode(errors='replace').splitlines()))
    if process.returncode!=0 or timed_out:break
after=subprocess.check_output(['dmesg']);(out/'client-dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report=dict(stage=214,uid=10000,clients=results,default_system_libraries_and_cpu_config_used=True,no_ipa_or_loader_override=True,headless_no_flash_no_scene_files=True,physical_front_selected_by_id=True,sensor_controls_restored=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults,gst_command_line_tools_absent=True,gstreamer_plugin_tested_through_direct_standard_api=True,unsynchronised_gst_pixel_statistics_not_claimed=True)
(out/'capture-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('__HASH__',repr(proof['sha256']))
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/'default-clients-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'default-clients-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
