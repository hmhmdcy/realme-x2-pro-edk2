"""Finite RGB capture through the installed libcamera as the desktop user."""
from pathlib import Path
import collections,hashlib,json,math,os,pwd,re,shutil,signal,stat,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-user-libcamera';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
sessions=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if (p/'comm').read_text().strip()=='phosh' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:sessions.append(p)
    except OSError:pass
assert len(sessions)==1
entries=dict(p.split(b'=',1) for p in (sessions[0]/'environ').read_bytes().split(b'\0') if b'=' in p)
runtime=Path(entries[b'XDG_RUNTIME_DIR'].decode()).resolve();st=runtime.stat();assert stat.S_ISDIR(st.st_mode) and st.st_uid==10000 and stat.S_IMODE(st.st_mode)&0o077==0
output=runtime/'samurai-camera-211';assert not output.exists();output.mkdir(mode=0o700);user=pwd.getpwuid(10000);os.chown(output,user.pw_uid,user.pw_gid)
env={'PATH':'/usr/bin:/bin','HOME':user.pw_dir,'XDG_RUNTIME_DIR':str(runtime),'LIBCAMERA_LOG_LEVELS':'*:INFO'}
for key in ['DBUS_SESSION_BUS_ADDRESS','PIPEWIRE_RUNTIME_DIR','XDG_SESSION_TYPE']:
    if key.encode() in entries:env[key]=entries[key.encode()].decode()
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid);os.umask(0o077)
patterns={}
for p in Path('/sys/class/video4linux').glob('v4l-subdev*'):
    name=(p/'name').read_text().strip()
    if name in ['imx471 7-0010','msm_csid0']:
        q=subprocess.run(['v4l2-ctl','-d','/dev/'+p.name,'--get-ctrl=test_pattern'],capture_output=True,text=True,timeout=10);assert q.returncode==0
        match=re.search(r'test_pattern:\s*(\d+)',q.stdout);assert match;patterns[name]=int(match[1])
assert len(patterns)==2 and not any(patterns.values())
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
args=['/usr/bin/cam','--camera','1','--stream','role=viewfinder,width=1928,height=1088,pixelformat=RGB888','--capture=3','--file='+str(output/'frame-#.ppm'),'--metadata']
process=subprocess.Popen(args,preexec_fn=demote,cwd=output,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
timed_out=False;killed=False
try:stdout,stderr=process.communicate(timeout=30)
except subprocess.TimeoutExpired:
    timed_out=True;process.send_signal(signal.SIGINT)
    try:stdout,stderr=process.communicate(timeout=10)
    except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=5)
(out/'cam-stdout-private.txt').write_bytes(stdout);(out/'cam-stderr-private.txt').write_bytes(stderr)
images=out/'images-private';images.mkdir(mode=0o700);frames=[]
for p in sorted(output.glob('*.ppm')):
    assert not p.is_symlink() and p.stat().st_uid==10000;data=p.read_bytes();parts=data.split(b'\n',3)
    if len(parts)!=4 or parts[0]!=b'P6' or parts[2]!=b'255':continue
    width,height=map(int,parts[1].split());pixels=parts[3];assert len(pixels)==width*height*3
    target=images/p.name;target.write_bytes(data);hist=collections.Counter(pixels[::max(1,len(pixels)//65536)]);total=sum(hist.values());entropy=-sum(n/total*math.log2(n/total) for n in hist.values())
    frames.append(dict(width=width,height=height,rgb_bytes=len(pixels),byte_min=min(hist),byte_max=max(hist),sample_entropy_bits=round(entropy,4),nonconstant=len(hist)>1))
time.sleep(2)
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
report=dict(stage=211,uid=10000,actual_phosh_environment_used=True,camera_stream_role='viewfinder',requested_pixel_format='RGB888',requested_size=[1928,1088],camera_and_csid_test_patterns=patterns,cam_exit=process.returncode,timed_out=timed_out,forced_kill=killed,frames=frames,three_rgb_frames_captured=process.returncode==0 and len(frames)==3 and all(f['nonconstant'] for f in frames),sensor_runtime_status=Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip(),camss_runtime_status=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),cci_runtime_status=Path('/sys/bus/platform/devices/ac4b000.cci/power/runtime_status').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults,error_lines=[l for l in stderr.decode(errors='replace').splitlines() if any(x in l for x in ['ERROR','Failed','in use','busy'])],raw_scene_images_kept_private=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
