"""Correct executable service permissions; preserve the first offline package."""
from pathlib import Path
import gzip,hashlib,importlib.util,inspect,io,json,tarfile
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('profile_prepare_original',HERE/'prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.OUT=m.BASE/'protection-observed-2719-cohort-private-02'
def packet(entries):
 output=io.BytesIO()
 with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0,compresslevel=9) as compressed:
  with tarfile.open(fileobj=compressed,mode='w',format=tarfile.USTAR_FORMAT) as archive:
   for name,raw in entries:
    info=tarfile.TarInfo(name.lstrip('/'));info.size=len(raw);info.mode=0o755 if name==m.SERVICE else 0o600;info.uid=info.gid=0;info.uname=info.gname='root';info.mtime=0;archive.addfile(info,io.BytesIO(raw))
 raw=output.getvalue()
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  members=archive.getmembers();assert len(members)==3
  for entry,(name,value) in zip(members,entries):
   assert '/'+entry.name==name and entry.isfile() and entry.mode==(0o755 if name==m.SERVICE else 0o600) and entry.uid==entry.gid==0 and entry.mtime==0 and not entry.pax_headers
   assert archive.extractfile(entry).read()==value
 return raw
m.packet=packet
original_write=m.write
def write(path,raw):
 if path in [HERE/'samurai-charging.py',HERE/'service-opt-in.patch'] and path.exists():assert path.read_bytes()==raw
 else:original_write(path,raw)
m.write=write
source=inspect.getsource(m.main);assert source.count("HERE/'cohort-result.json'")==1
source=source.replace("HERE/'cohort-result.json'","HERE/'cohort-r2-result.json'")
exec(compile(source,'<permission-corrected-original-materializer>','exec'),m.__dict__)
if __name__=='__main__':m.main()
