from pathlib import Path
import base64,gzip,hashlib,host,json,re
here=Path(__file__).resolve().parent
proof=json.loads((here/'gap-probe-build-validation.json').read_text());data=(host.PRIVATE/'request-gap-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['sha256']
upload="from pathlib import Path\nimport base64,gzip,hashlib\np=Path('/run/samurai-camera222-probes/request-gap-probe');assert not p.exists();p.parent.mkdir(mode=0o755,exist_ok=True)\nd=gzip.decompress(base64.b64decode("+repr(base64.b64encode(gzip.compress(data)).decode())+"));assert hashlib.sha256(d).hexdigest()=="+repr(proof['sha256'])+"\np.write_bytes(d);p.chmod(0o755)\n"
host.ssh('python3 -',input=upload.encode(),timeout=30)
code=(here.parent/'kernel219/native-mode-runner.py').read_text()
code=code.replace('k219-runtime/boot-id-private.txt','k222-baseline/boot-id-private.txt').replace("[(2304,1728,1)","[(1920,1088,1),(2304,1728,1)")
code=code.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'","tag='request-gap-r7'").replace("'k219-capture-'","'k222-capture-'")
code=code.replace("LIBCAMERA_LOG_LEVELS='*:INFO'","LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG,SimplePipeline:DEBUG'")
old="['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)]";assert code.count(old)==1
code=code.replace(old,"['/run/samurai-camera222-probes/request-gap-probe']").replace('report=dict(stage=219,','report=dict(stage=222,metadata_only=True,').replace('dma_sync_read_start_end=True','dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True')
code=code.replace("data=json.loads(stdout) if process.returncode==0 else None", "data=json.loads(stdout) if process.returncode==0 else None\nreads=[tuple(map(int,m)) for m in re.findall(r'Reading Exposure to (\\d+) at index (\\d+)',stderr.decode())]\nframe_start_emitter_observed='Using frameStart signal' in stderr.decode()")
code=code.replace("frames=data['frames'] if data else [],","frames=data['frames'] if data else [],delayed_exposure_reads=reads,frame_start_emitter_observed=frame_start_emitter_observed,")
compile(code,'gap-capture222','exec')
p=host.ssh('python3 - rgb 0 1920 1088 1 system',input=code.encode(),timeout=90);(host.PRIVATE/'gap-capture-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'request-gap-r7-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
assert r['program_exit']==0 and len(r['frames'])==16 and r['sensor_controls_restored'] and r['media_graph_restored'] and r['all_formats_restored'] and r['camera_devices_suspended'] and r['taint']==0 and not any(r['fault_delta'].values())
