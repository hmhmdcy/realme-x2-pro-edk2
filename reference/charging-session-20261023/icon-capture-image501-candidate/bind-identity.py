"""Default source check only. Bind only real passed postboot/adoption originals."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('icon501',HERE/'launcher.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def bind(adoption_dir,postboot_dir):
 a,p=Path(adoption_dir),Path(postboot_dir)
 assert a==m.PINS.parent and not m.PINS.exists()
 paths={'adoption':Path('/mnt/e/edk2-samurai-out/charging-management-20261023/boot-adoption-private.json'),
  'adopt_request':a/'adopt-request-private.json','adopt_result':a/'adoption-result-private.json','endpoint':a/'new-endpoint-private.json',
  'postboot':p/'stdout-private.json','receiver':p/'receiver-result-private.json','transport':HERE/'transport.py',
  'key_transport':Path('/mnt/e/RealmeX2Pro edk2/reference/kernel184/host.py')}
 entries={n:{'path':str(v),'sha256':hashlib.sha256(v.read_bytes()).hexdigest()} for n,v in paths.items()}
 temp=a/'icon-identity-pins-next-private.json'
 with temp.open('x') as f:json.dump(entries,f,indent=2);f.flush();os.fsync(f.fileno())
 m.adopt_local(pins=temp)
 assert not m.PINS.exists();temp.rename(m.PINS)
 fd=os.open(a,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return {'bound_actual_identity':True,'pins_sha256':m.sha(m.PINS.read_bytes()),'device_accessed':False}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--adoption-directory');parser.add_argument('--postboot-directory');parser.add_argument('--execute-bind',action='store_true');args=parser.parse_args()
 if args.execute_bind:print(json.dumps(bind(args.adoption_directory,args.postboot_directory)))
 else:print(json.dumps({'template_only':True,'runtime_pins_created':False,'device_accessed':False}))
