"""Finite physical capture, numerical statistics only, restore graph/formats."""
from pathlib import Path
import fcntl,hashlib,json,os,pwd,re,signal,struct,subprocess,sys,time,resource
resource.setrlimit(resource.RLIMIT_CORE,(0,0))

os.umask(0o077)
kind,pattern,width,height,cell,library=sys.argv[1:7]
profile=sys.argv[7];assert profile in ['threaded','isolated']
pattern,width,height,cell=map(int,[pattern,width,height,cell])
assert kind in ['raw','rgb'] and pattern in [0,2] and library in ['system','candidate']
assert (width,height,cell) in [(1920,1088,1),(1928,1088,1),(2304,1728,1),(2296,1728,1),(4608,3456,2)]
root=Path('/var/lib/samurai');guard=root/'k225-baseline/boot-id-private.txt'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==guard.read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
tag=f'manual-controls-r13-system-{kind}-{width}x{height}-{sys.argv[7]}'
out=root/('k225-capture-'+tag);assert not out.exists();out.mkdir(mode=0o700)
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
nodes={p.name:(p/'name').read_text().strip() for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
sensor='/dev/'+next(k for k,v in nodes.items() if v=='imx471 7-0010')
csid='/dev/'+next(k for k,v in nodes.items() if v=='msm_csid0')
names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern','horizontal_blanking','pixel_rate']
def controls():
    text=subprocess.check_output(['v4l2-ctl','-d',sensor,'--get-ctrl='+','.join(names)],text=True,timeout=10)
    return {k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',text)}
saved=controls();assert saved['test_pattern']==0
assert re.search(r'^test_pattern:\s*0(?:\s|\(|$)',subprocess.check_output(['v4l2-ctl','-d',csid,'--get-ctrl=test_pattern'],text=True))
def formats():
    result=[]
    for node,name in nodes.items():
        fd=os.open('/dev/'+node,os.O_RDWR|os.O_CLOEXEC)
        try:
            for pad in range(32):
                buf=bytearray(88);struct.pack_into('II',buf,0,1,pad)
                try:fcntl.ioctl(fd,0xc0585604,buf,True)
                except OSError as error:
                    assert error.errno in [22,25];break
                result.append((node,name,pad,bytes(buf)))
        finally:os.close(fd)
    return result
saved_formats=formats()
assert saved_formats
media_before=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],timeout=10)
(out/'media-before-private.txt').write_bytes(media_before)
links=[];entity=None;pad=None
for line in media_before.decode().splitlines():
    m=re.match(r'^- entity \d+: (.*?) \(',line)
    if m:entity=m[1];continue
    m=re.match(r'\s+pad(\d+):',line)
    if m:pad=int(m[1]);continue
    m=re.match(r'\s+-> "(.*?)":(\d+) \[(.*?)\]',line)
    if m and 'IMMUTABLE' not in m[3]:links.append((entity,pad,m[1],int(m[2]),int('ENABLED' in m[3])))
user=pwd.getpwuid(10000)
env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG,SimplePipeline:DEBUG,IPAManager:DEBUG')
if library=='candidate':
    prefix=Path('/run/samurai-camera225-r13')
    assert (prefix/'usr/lib/libcamera.so.0.7.2').is_file()
    env.update(LD_LIBRARY_PATH=str(prefix/'usr/lib'),XDG_CONFIG_HOME=str(prefix/('config-isolated' if profile=='isolated' else 'config-default')),
               LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa'))
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
stdout=b'';stderr=b'';timed=False;killed=False;restore_errors=[];dma_exporters=set()
try:
    process=subprocess.Popen(['/run/samurai-camera225-probes/manual-control-probe-r13',kind,str(width),str(height)],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    for _ in range(8):
        if process.poll() is not None:break
        for fdinfo in Path('/proc',str(process.pid),'fdinfo').glob('*'):
            try:
                for line in fdinfo.read_text().splitlines():
                    if line.startswith('exp_name:'):dma_exporters.add(line.split(':',1)[1].strip())
            except OSError:pass
        time.sleep(0.05)
    active_controls=controls()
    maps=''
    try:maps=Path('/proc',str(process.pid),'maps').read_text()
    except FileNotFoundError:pass
    actual_prefix=str(prefix/'usr/lib') if library=='candidate' else '/usr/lib'
    library_maps='\n'.join(l for l in maps.splitlines() if 'libcamera.so.' in l or 'libcamera-base.so.' in l)
    candidate_libraries_verified=all(actual_prefix+'/'+name in library_maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2']) and '(deleted)' not in library_maps
    try:stdout,stderr=process.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        timed=True;process.send_signal(signal.SIGINT)
        try:stdout,stderr=process.communicate(timeout=5)
        except subprocess.TimeoutExpired:killed=True;process.kill();stdout,stderr=process.communicate(timeout=3)
finally:
    subprocess.run(['v4l2-ctl','-d',csid,'--set-ctrl=test_pattern=0'],capture_output=True,check=True,timeout=10)
    def setlink(link,enabled):
        a,p,b,q,_=link
        subprocess.run(['media-ctl','-d','/dev/media0','--links',f'"{a}":{p} -> "{b}":{q} [{enabled}]'],capture_output=True,check=True,timeout=10)
    for link in links:setlink(link,0)
    def rank(item):
        name=item[1]
        return next((i for i,prefix in enumerate(['imx471','msm_csiphy','msm_csid','msm_ispif','msm_vfe']) if name.startswith(prefix)),5),item[2]
    for node,name,pad,buf in sorted(saved_formats,key=rank):
        fd=os.open('/dev/'+node,os.O_RDWR|os.O_CLOEXEC)
        try:
            current=bytearray(88);struct.pack_into('II',current,0,1,pad);fcntl.ioctl(fd,0xc0585604,current,True)
            if bytes(current)!=buf:
                try:fcntl.ioctl(fd,0xc0585605,bytearray(buf),True)
                except OSError as error:restore_errors.append(dict(node=node,pad=pad,errno=error.errno))
        finally:os.close(fd)
    for link in links:
        if link[4]:setlink(link,1)
    for group in [['test_pattern','vertical_blanking'],['exposure','analogue_gain','digital_gain']]:
        subprocess.run(['v4l2-ctl','-d',sensor,'--set-ctrl='+','.join(k+'='+str(saved[k]) for k in group)],capture_output=True,check=True,timeout=10)
(out/'stdout-private.json').write_bytes(stdout);(out/'stderr-private.txt').write_bytes(stderr)
after_formats=formats();restored_formats=after_formats==saved_formats
media_after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],timeout=10);(out/'media-after-private.txt').write_bytes(media_after)
time.sleep(2);after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
data=json.loads(stdout) if process.returncode==0 else None
report=dict(stage=225,metadata_only=True,active_controls=active_controls,candidate_libraries_verified=candidate_libraries_verified,ipa_isolation_forced_observed=b'forced through configuration' in stderr,requested=[width,height],kind=kind,sensor_pattern=pattern,cfa_cell=cell,library=library,
            program_exit=process.returncode,timed_out=timed,forced_kill=killed,stream_geometry={k:data[k] for k in ['width','height','stride']} if data else {},
            frames=data['frames'] if data else [],manual_test_passed=data['passed'] if data else False,manual_phases=data['phases'] if data else 0,all_formats_restored=restored_formats,media_graph_restored=media_after==media_before,
            sensor_controls_restored=controls()==saved,restore_errors=restore_errors,
            camera_devices_suspended=all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices),
            dma_exporters_observed=sorted(dma_exporters),
            taint=int(Path('/proc/sys/kernel/tainted').read_text()),fault_delta=faults,
            room_lights_off=True,no_flash_or_external_illumination=True,no_scene_images_saved=True,
            dma_sync_read_start_end=False,no_client_pixel_buffer_access=True,all_active_raw_pixels_examined=False,raw_padding_excluded=False)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
