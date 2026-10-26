"""Installed cam/GStreamer validation with exact media graph restoration."""
from pathlib import Path
import gzip,hashlib,host,json,shlex,sys
here=Path(__file__).resolve().parent
assert len(sys.argv)==2 and sys.argv[1] in ['cam','gstreamer'];client=sys.argv[1]
assert json.loads((here/'wireplumber-reload-validation.json').read_text())['new_r6_camera_libraries_loaded']
if client=='gstreamer':
 data=(host.PRIVATE/'probes/gst-camera219-probe').read_bytes();sha=json.loads((here/'gst-client-build-validation.json').read_text())['sha256'];assert hashlib.sha256(data).hexdigest()==sha
 payload=gzip.compress(data,mtime=0);assert len(payload)<=65536
 code="from pathlib import Path;import gzip,hashlib,sys;root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes();p=Path('/run/samurai-camera219-probes/gst-camera219-probe');assert not p.exists();d=gzip.decompress(sys.stdin.buffer.read());assert hashlib.sha256(d).hexdigest()=="+repr(sha)+";p.write_bytes(d);p.chmod(0o755)"
 host.ssh('python3 -c '+shlex.quote(code),input=payload,timeout=30)
code=(here/'native-mode-runner.py').read_text().replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'",'tag='+repr('installed-r6-standard-'+client))
original="process=subprocess.Popen(['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)"
camera='/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10'
args=(['cam','--camera',camera,'--stream=role=viewfinder,width=2296,height=1728,pixelformat=RGB888','--capture=6'] if client=='cam' else ['/run/samurai-camera219-probes/gst-camera219-probe',camera])
assert code.count(original)==1;code=code.replace(original,'process=subprocess.Popen('+repr(args)+',env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)')
if client=='gstreamer':code=code.replace('def demote():',"env['GST_REGISTRY']='/run/user/10000/samurai-camera219-r6-client-registry.bin'\nassert not Path(env['GST_REGISTRY']).exists()\ndef demote():")
old="data=json.loads(stdout) if process.returncode==0 else None"
if client=='cam':
 new="data=dict(width=width,height=height,stride=None,frames=stdout.count(b'seq:')) if process.returncode==0 else None\nassert not data or re.search(r'configuring streams: \\(0\\) 2296x1728-RGB888',stderr.decode())"
else:new="data=json.loads(stdout) if process.returncode==0 else None\nif data:data['stride']=None;assert data['width']==width and data['height']==height and data['bus_errors']==0 and data['format']=='RGB'"
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("frames=data['frames'] if data else []", "frame_count=data['frames'] if data else 0")
code=code.replace('dma_sync_read_start_end=True,','dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True,')
code=code.replace('report=dict(stage=219,','report=dict(stage=219,standard_client='+repr(client)+',default_installed_libraries_and_config=True,no_loader_or_ipa_override=True,')
compile(code,'native-standard-r6-client','exec')
p=host.ssh('python3 - rgb 0 2296 1728 1 system',input=code.encode(),timeout=100)
(host.PRIVATE/('standard-'+client+'-host-private.log')).write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/('standard-'+client+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
assert r['program_exit']==0 and r['frame_count']==6 and r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored']
assert r['camera_devices_suspended'] and r['taint']==0 and not any(r['fault_delta'].values())
