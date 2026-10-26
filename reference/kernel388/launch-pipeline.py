"""Upload and dispatch exactly one guarded held-failure experiment."""
from pathlib import Path
import hashlib,io,json,re,shlex,struct,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
root='/var/lib/samurai/k388-pipeline-'+run
preflight=json.loads((HERE/'runtime-preflight-validation.json').read_text());assert preflight['passed'] and preflight['run']==run
assert json.loads((HERE/'runtime-build-validation.json').read_text())['passed']
build=json.loads((HERE/'intree-build-validation.json').read_text());region=build['firmware_region']
modules={r['name']:r for r in build['modules']}
files={name:Path(modules[key]['private_path']) for name,key in [('core.ko','qcom-camss-icp-a5-core'),('helper.ko','v4l2-mem2mem'),('adapter.ko','camss-icp-a5-m2m'),('test.ko','camss-icp-a5-boot-test')]}
files.update({'worker.py':HERE/'pipeline-worker.py','snapshot-collector.py':HERE/'snapshot-collector.py','dump_decoder.py':HERE.parent/'kernel368/decode-start-dump.py','firmware.elf':P.parent/'kernel352/CAMERA_ICP.elf-private','camera-client.py':HERE/'camera-client.py','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','pipeline-smoke':P/'pipeline-smoke','libcamera.so.0.7.2':P/'libcamera.so.0.7.2'})
assert hashlib.sha256(files['libcamera.so.0.7.2'].read_bytes()).hexdigest()==json.loads((HERE/'runtime-build-validation.json').read_text())['library_sha256']
for row in build['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256'] and row['intree']=='Y'
fw=files['firmware.elf'].read_bytes();phoff=struct.unpack_from('<I',fw,28)[0];stride,count=struct.unpack_from('<HH',fw,42)
segment=next(s for i in range(count) if (s:=struct.unpack_from('<8I',fw,phoff+i*stride))[0]==1 and s[2]==0 and s[4]>=4096)
manifest=dict(kernel_release=build['modules'][0]['vermagic'].split()[0],
 **{n:region[k] for n,k in [('camss@acb3000','camss'),('clock-controller@ad00000','camcc'),('iommu@15000000','smmu')]},
 **{k:region[k] for k in ['interrupt_parent','firmware_region_path','firmware_physical','firmware_bytes','existing_firmware_phandle']},
 boot_guard=json.loads((P.parent/'kernel378/recovered-boot-adoption-private.json').read_text())['guard_path'],
 snapshot_profile=json.loads((HERE.parent/'kernel386/firmware-context-validation.json').read_text()),
 payload_sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},firmware_sha256=hashlib.sha256(fw).hexdigest(),
 firmware_code_page_sha256=hashlib.sha256(fw[segment[1]:segment[1]+4096]).hexdigest())
assert manifest['firmware_sha256']=='a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63'
cached={name:'/var/lib/samurai/k387-pipeline-r5/'+name for name in ['libcamera.so.0.7.2','pipeline-smoke','pipeline-fixture']}
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for name,path in files.items():
  if name not in cached:tar.add(path,arcname=name)
 data=json.dumps(manifest).encode();info=tarfile.TarInfo('manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
code='''from pathlib import Path
import io,tarfile,sys,os,hashlib,shutil
root=Path(ROOT);assert not root.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()
cached=CACHED;digests=DIGESTS
for name,path in cached.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digests[name]
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers()
assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for member in members:
 with root.joinpath(member.name).open('xb') as stream:stream.write(tar.extractfile(member).read());stream.flush();os.fsync(stream.fileno())
for name,path in cached.items():
 shutil.copyfile(path,root/name)
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digests[name]
d=os.open(root,os.O_RDONLY|os.O_DIRECTORY);os.fsync(d);os.close(d)
print('Prepared388 direct DMA pipeline snapshot transaction.')
'''.replace('ROOT',repr(root)).replace('GUARD',repr(manifest['boot_guard'])).replace('NAMES',repr((set(files)-set(cached))|{'manifest.json'})) .replace('CACHED',repr(cached)).replace('DIGESTS',repr(manifest['payload_sha256']))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=30);print(q.stdout.decode())
code="from pathlib import Path;import subprocess,json,os;root=Path(ROOT);assert not (root/'state.json').exists();log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);data=dict(pid=child.pid,root=str(root));f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))".replace('ROOT',repr(root))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=15);(P/('launch-'+run+'-private.json')).write_bytes(q.stdout);print(q.stdout.decode())
