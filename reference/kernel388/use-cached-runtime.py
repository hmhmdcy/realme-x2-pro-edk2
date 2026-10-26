from pathlib import Path
HERE=Path(__file__).resolve().parent;p=HERE/'launch-pipeline.py';s=p.read_text()
needle="payload=io.BytesIO()";assert s.count(needle)==1
s=s.replace(needle,"cached={name:'/var/lib/samurai/k387-pipeline-r5/'+name for name in ['libcamera.so.0.7.2','pipeline-smoke','pipeline-fixture']}\n"+needle)
s=s.replace(" for name,path in files.items():tar.add(path,arcname=name)"," for name,path in files.items():\n  if name not in cached:tar.add(path,arcname=name)")
s=s.replace('import io,tarfile,sys,os','import io,tarfile,sys,os,hashlib,shutil')
s=s.replace("root=Path(ROOT);assert not root.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()","root=Path(ROOT);assert not root.exists();assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(GUARD).read_bytes()\ncached=CACHED;digests=DIGESTS\nfor name,path in cached.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digests[name]")
s=s.replace("d=os.open(root,os.O_RDONLY|os.O_DIRECTORY)","for name,path in cached.items():\n shutil.copyfile(path,root/name)\n assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digests[name]\nd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)")
s=s.replace("repr(set(files)|{'manifest.json'})","repr((set(files)-set(cached))|{'manifest.json'})) .replace('CACHED',repr(cached)).replace('DIGESTS',repr(manifest['payload_sha256'])")
compile(s,'launch-pipeline.py','exec');p.write_text(s)
print('Prepared digest-checked reuse of installed private r5 library and probes.')
