from pathlib import Path
import base64,gzip,hashlib,host,json
here=Path(__file__).resolve().parent;proof=json.loads((here/'sof-candidate-build-validation.json').read_text());assert proof['checkpatch_exit']==0
data=(host.PRIVATE/'qcom-camss-sof223.ko').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['compiled_module_sha256'];compressed=gzip.compress(data)
code="from pathlib import Path\nimport os\nos.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k223-baseline/boot-id-private.txt').read_bytes()\np=root/'k223-sof-modules';assert not p.exists();p.mkdir(mode=0o700);(p/'candidate.gz').touch(mode=0o600)\n"
host.ssh('python3 -',input=code.encode(),timeout=25)
for offset in range(0,len(compressed),32768):
 part=compressed[offset:offset+32768]
 code="from pathlib import Path\nimport base64\np=Path('/var/lib/samurai/k223-sof-modules/candidate.gz');assert p.stat().st_size=="+str(offset)+"\nwith p.open('ab') as output:output.write(base64.b64decode("+repr(base64.b64encode(part).decode())+"))\n"
 host.ssh('python3 -',input=code.encode(),timeout=25)
code="from pathlib import Path\nimport gzip,hashlib\np=Path('/var/lib/samurai/k223-sof-modules');data=gzip.decompress((p/'candidate.gz').read_bytes());assert hashlib.sha256(data).hexdigest()=="+repr(proof['compiled_module_sha256'])+"\n(p/'qcom-camss-candidate.ko').write_bytes(data)\n"
host.ssh('python3 -',input=code.encode(),timeout=30)
code=(here.parent/'kernel219/native-mode-runner.py').read_text().replace('k219-runtime/boot-id-private.txt','k223-baseline/boot-id-private.txt')
code=code.replace("[(2304,1728,1)","[(1920,1088,1),(1928,1088,1),(2304,1728,1)")
code=code.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'","tag=f'paired-sof-{kind}-{width}x{height}'").replace("'k219-capture-'","'k223-capture-'")
code=code.replace("LIBCAMERA_LOG_LEVELS='*:INFO'","LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG,SimplePipeline:DEBUG'")
old="['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)]";assert code.count(old)==1
code=code.replace(old,"['/run/samurai-camera223-probes/paired-frame-probe',kind,str(width),str(height)]").replace('report=dict(stage=219,','report=dict(stage=223,metadata_only=True,').replace('dma_sync_read_start_end=True','dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True').replace("all_active_raw_pixels_examined=kind=='raw'","all_active_raw_pixels_examined=False").replace("raw_padding_excluded=kind=='raw'","raw_padding_excluded=False")
compile(code,'paired-runner223','exec')
upload="from pathlib import Path\np=Path('/var/lib/samurai/k223-sof-modules/paired-runner.py');assert not p.exists();p.write_bytes("+repr(code.encode())+")\n"
host.ssh('python3 -',input=upload.encode(),timeout=30)
r=dict(stage=223,candidate_staged_privately=True,candidate_sha256=proof['compiled_module_sha256'],compressed_transfer_chunk_bytes=32768,installed_module_and_boot_unchanged=True,experiment_not_yet_started=True)
(here/'sof-candidate-staging-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
