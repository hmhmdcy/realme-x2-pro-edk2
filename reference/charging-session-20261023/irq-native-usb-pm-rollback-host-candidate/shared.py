"""Pinned source-only helpers for current cold rollback host adapters."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('non-optimized Python required')
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def need(value,message):
 if not value:raise ValueError(message)
def local(path):
 text=str(path).replace('\\','/')
 if os.name!='nt' and re.match(r'^[A-Za-z]:/',text):text='/mnt/'+text[0].lower()+text[2:]
 return Path(text).resolve()
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,local(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def encode(value):return (json.dumps(value,indent=2)+'\n').encode()
def source_check():
 pins=json.loads((HERE/'source-pins.json').read_bytes())
 for name,row in pins.items():
  raw=local(row['path']).read_bytes();need(sha(raw)==row['sha256'] and len(raw)==row['bytes'],'source changed: '+name)
 for delivery,source,filename in [('worker_delivery','worker','restore-worker.py'),('retained_delivery','retained','reviewer.py'),
  ('device_delivery','operator','fastboot-operator.py'),('auth_delivery','auth_host','host.py')]:
  report=json.loads(local(pins[delivery]['path']).read_bytes());need(report['passed'] is True and report['frozen'] is True,
   'source is not frozen: '+delivery)
  need(report['files'][filename]['sha256']==pins[source]['sha256'],'source/delivery mismatch: '+source)
 need(pins['worker']['sha256']=='6818939b88a51ccd9d0455438c73ac3ad51c26332acdf8d1ea31096bdfc80c47' and
  pins['payload']['sha256']=='6ff66d182f7b0dc7ac32e3e58ae756e259c246b4edddf85d48878ff561835ab8','exact current worker/inverse')
 return pins
