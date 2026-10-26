from pathlib import Path
import base64,gzip,hashlib,host,json
here=Path(__file__).resolve().parent;proof=json.loads((here/'paired-probe-build-validation.json').read_text());data=(host.PRIVATE/'paired-frame-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['binary_sha256']
code="from pathlib import Path\nimport base64,gzip,hashlib\np=Path('/run/samurai-camera223-probes/paired-frame-probe');assert not p.exists();p.parent.mkdir(mode=0o755,exist_ok=True)\ndata=gzip.decompress(base64.b64decode("+repr(base64.b64encode(gzip.compress(data)).decode())+"));assert hashlib.sha256(data).hexdigest()=="+repr(proof['binary_sha256'])+"\np.write_bytes(data);p.chmod(0o755)\n"
host.ssh('python3 -',input=code.encode(),timeout=25)
code=(here.parent/'kernel219/native-mode-runner.py').read_text().replace('k219-runtime/boot-id-private.txt','k223-baseline/boot-id-private.txt')
code=code.replace("[(2304,1728,1)","[(1920,1088,1),(1928,1088,1),(2304,1728,1)")
code=code.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'","tag='baseline-raw-gap'").replace("'k219-capture-'","'k223-capture-'")
old="['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)]";assert code.count(old)==1
code=code.replace(old,"['/run/samurai-camera223-probes/paired-frame-probe',kind,str(width),str(height)]").replace('report=dict(stage=219,','report=dict(stage=223,metadata_only=True,').replace('dma_sync_read_start_end=True','dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True').replace("all_active_raw_pixels_examined=kind=='raw'","all_active_raw_pixels_examined=False").replace("raw_padding_excluded=kind=='raw'","raw_padding_excluded=False")
p=host.ssh('python3 - raw 0 1928 1088 1 system',input=code.encode(),timeout=90);(host.PRIVATE/'baseline-raw-gap-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'baseline-raw-gap-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
assert r['program_exit']==0 and len(r['frames'])==16 and r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended'] and r['taint']==0 and not any(r['fault_delta'].values())
