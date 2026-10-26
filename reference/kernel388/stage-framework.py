"""Stage one guarded temporary SG transaction; dispatch is a separate operation."""
from pathlib import Path
import ast,hashlib,io,json,re,shlex,struct,subprocess,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
root='/var/lib/samurai/k388-framework-'+run
for name in ['dma','transfer','intree-build','export-owner','export-client-build']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
build=json.loads((HERE/'intree-build-validation.json').read_text());region=build['firmware_region'];modules={r['name']:r for r in build['modules']}
files={};cache={};digests={}
def add(name,path,cached=None):
 path=Path(path);digest=hashlib.sha256(path.read_bytes()).hexdigest();digests[name]=digest
 if cached:cache[name]=cached
 else:files[name]=path
for suite,worker in [('native','m2m-worker.py'),('pipeline','pipeline-worker.py')]:
 payload={}
 def item(name,path,cached=None):
  add(suite+'/'+name,path,cached);payload[name]=digests[suite+'/'+name]
 for name,key in [('core.ko','qcom-camss-icp-a5-core'),('helper.ko','v4l2-mem2mem'),('adapter.ko','camss-icp-a5-m2m'),('test.ko','camss-icp-a5-boot-test')]:
  row=modules[key];assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
  item(name,row['private_path'],'/var/lib/samurai/k388-dma-r2/'+name if name!='adapter.ko' else None)
 item('worker.py',HERE/worker);item('snapshot-collector.py',HERE/'snapshot-collector.py');item('dump_decoder.py',HERE.parent/'kernel368/decode-start-dump.py')
 item('firmware.elf',P.parent/'kernel352/CAMERA_ICP.elf-private','/var/lib/samurai/k388-dma-r2/firmware.elf')
 if suite=='native':
  item('m2m-client',json.loads((HERE.parent/'kernel386/client-build-validation.json').read_text())['private_path'],'/var/lib/samurai/k388-dma-r2/m2m-client')
  item('export-lifetime-client',P/'export-lifetime-client')
 else:
  item('camera-client.py',HERE/'camera-client.py')
  for name,path in [('pipeline-fixture',P.parent/'kernel363/pipeline-fixture'),('pipeline-smoke',P/'pipeline-smoke'),('libcamera.so.0.7.2',P/'libcamera.so.0.7.2')]:item(name,path,'/var/lib/samurai/k387-pipeline-r5/'+name)
 fw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes();phoff=struct.unpack_from('<I',fw,28)[0];stride,count=struct.unpack_from('<HH',fw,42)
 segment=next(s for i in range(count) if (s:=struct.unpack_from('<8I',fw,phoff+i*stride))[0]==1 and s[2]==0 and s[4]>=4096)
 manifest=dict(kernel_release=build['modules'][0]['vermagic'].split()[0],**{n:region[k] for n,k in [('camss@acb3000','camss'),('clock-controller@ad00000','camcc'),('iommu@15000000','smmu')]},
  **{k:region[k] for k in ['interrupt_parent','firmware_region_path','firmware_physical','firmware_bytes','existing_firmware_phandle']},
  boot_guard=json.loads((P.parent/'kernel378/recovered-boot-adoption-private.json').read_text())['guard_path'],
  snapshot_profile=json.loads((HERE.parent/'kernel386/firmware-context-validation.json').read_text()),payload_sha256=payload,firmware_sha256=hashlib.sha256(fw).hexdigest(),firmware_code_page_sha256=hashlib.sha256(fw[segment[1]:segment[1]+4096]).hexdigest())
 manifest_path=P/(suite+'-framework-manifest.json');manifest_path.write_text(json.dumps(manifest,indent=2)+'\n');add(suite+'/manifest.json',manifest_path)
assert manifest['firmware_sha256']=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
sg=Path(modules['videobuf2-dma-sg']['private_path']);add('sg.ko',sg)
note=P/'sg-build-id.note';subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',str(sg),str(note)],check=True)
proof=dict(stage=388,baseline=json.loads((P/'sg-runtime-baseline-private.json').read_text()),boot_guard=manifest['boot_guard'],sg_sha256=digests['sg.ko'],sg_note_sha256=hashlib.sha256(note.read_bytes()).hexdigest())
proofpath=P/'framework-proof-private.json';proofpath.write_text(json.dumps(proof,indent=2)+'\n');add('proof.json',proofpath)
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':388")
source=prefix+'\n'+(HERE/'framework-worker-body.py').read_text();ast.parse(source)
worker=P/'framework-worker.py';worker.write_text(source);add('worker.py',worker)
preflight=r'''from pathlib import Path
import hashlib,json
root=Path(ROOT);proof=PROOF
assert not root.exists(),'Existing transaction: inspect, do not repeat'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for n,row in proof['baseline'].items():
 assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['file_sha256']
 assert hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest()==row['note_sha256']
assert sorted(p.name for p in Path('/sys/module/videobuf2_dma_sg/holders').iterdir())==['qcom_camss']
assert not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem'])
for name,path in CACHE.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==DIGESTS[name],name
print('Exact original framework and cached payloads verified.')
'''.replace('ROOT',repr(root)).replace('PROOF',repr(proof)).replace('CACHE',repr(cache)).replace('DIGESTS',repr(digests))
print(host.ssh('python3 -c '+shlex.quote(preflight),timeout=25).stdout.decode())
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for name,path in files.items():tar.add(path,arcname=name)
code=r'''from pathlib import Path
import io,tarfile,sys,os,hashlib,shutil,json
root=Path(ROOT);assert not root.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers()
assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for member in members:
 target=root/member.name;target.parent.mkdir(mode=0o700,exist_ok=True)
 with target.open('xb') as f:f.write(tar.extractfile(member).read());f.flush();os.fsync(f.fileno())
for name,path in CACHE.items():shutil.copyfile(path,root/name)
for name,digest in DIGESTS.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
for folder in [root/'native',root/'pipeline',root]:
 d=os.open(folder,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
print(json.dumps(dict(staged=True,root=str(root),files=len(DIGESTS))))
'''.replace('ROOT',repr(root)).replace('GUARD',repr(manifest['boot_guard'])).replace('NAMES',repr(set(files))).replace('CACHE',repr(cache)).replace('DIGESTS',repr(digests))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=45)
(P/('framework-staging-'+run+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
(HERE/'framework-staging-validation.json').write_text(json.dumps(dict(stage=388,run=run,root=root,upload_bytes=len(payload.getvalue()),staged=json.loads(q.stdout)['staged'],framework_not_loaded=True,passed=True),indent=2)+'\n')
