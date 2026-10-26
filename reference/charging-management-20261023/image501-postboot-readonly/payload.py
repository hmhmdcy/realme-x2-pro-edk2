"""Build a read-only postboot payload; root supplies the original strict-key transport."""
from pathlib import Path
import ast,base64,hashlib,importlib.util,json,os,sys
HERE=Path(__file__).resolve().parent
PAIR=HERE.parent.parent/'charging-session-20261023/gauge-image501-fastboot-pair-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
CAMERA='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'


def make_request(context_path,camera_path,endpoint,window_confirmed,original_key_verified):
 assert window_confirmed is True and original_key_verified is True
 assert isinstance(endpoint,str) and endpoint and not any(x.isspace() for x in endpoint)
 spec=importlib.util.spec_from_file_location('image501_pair',PAIR/'fastboot-operator.py')
 pair=importlib.util.module_from_spec(spec);spec.loader.exec_module(pair)
 context_path=Path(context_path);context=pair.validate_context(context_path)
 camera_raw=Path(camera_path).read_bytes();assert sha(camera_raw)==CAMERA
 camera=json.loads(camera_raw);assert camera['validated']
 guard_raw=(context_path.parent/context['files']['guard']['path']).read_bytes()
 return {'schema':'samurai-image501-postboot-readonly-v1','new_endpoint':endpoint,
   'original_key_transport_verified':True,'context_sha256':sha(context_path.read_bytes()),
   'guard_sha256':sha(guard_raw),'guard':json.loads(guard_raw),'camera':camera}


def make_payload(request):
 check_local()
 source=(HERE/'device.py').read_bytes()
 prefix='POSTBOOT_REQUEST=__import__("json").loads(__import__("base64").b64decode('+repr(base64.b64encode(json.dumps(request).encode()).decode())+'))\n'
 return prefix.encode()+source


def save_response(out,stdout,stderr,exit_code,payload_bytes):
 """Root calls after its single strict transport; preserve even failed bytes.
 Only local private files are written. No network/control/recovery is performed.
 """
 out=Path(out);assert out.is_absolute() and not out.exists()
 old_mask=os.umask(0o077)
 try:
  out.mkdir(mode=0o700)
  for name,raw in [('executed-device-source.py',payload_bytes),('stdout-private.json',stdout),('stderr-private.txt',stderr)]:
   with (out/name).open('xb') as f:f.write(raw)
  public={'passed':False,'transport_exit':exit_code,'private_evidence_directory':str(out),
          'guard_created':False,'hardware_writes':0,'physical_route_or_SDP500_or_icon_accepted':False}
  try:
   report=json.loads(stdout);result=report['result'];checks=result.get('checks',{})
   public['passed']=exit_code==0 and result.get('passed') is True
   public['checks']={name:value.get('ready',True) for name,value in checks.items()}
   public['error_classes']={name:value.get('error') for name,value in result.get('errors',{}).items()}
   if 'collection_error' in result:public['collection_error']=result['collection_error']
  except Exception as e:public['decode_error_class']=type(e).__name__
  with (out/'receiver-result-private.json').open('x') as f:json.dump(public,f,indent=2);f.write('\n')
  return public
 finally:os.umask(old_mask)


def check_local():
 source=(HERE/'device.py').read_bytes();tree=ast.parse(source)
 forbidden={'write_text','write_bytes','pack_into','write','writelines','system','Popen','mkdir','unlink','remove'}
 assert not any(isinstance(x,ast.Attribute) and x.attr in forbidden for x in ast.walk(tree))
 text=source.decode()
 assert '/dev/mem' not in text and 'mmap' not in text and 'O_RDWR' not in text
 assert 'PROT_WRITE' not in text and '0x088e' not in text.lower()
 return {'passed':True,'device_sha256':sha(source),'device_accessed':False,'guard_created':False}


if __name__=='__main__':print(json.dumps(check_local()))
