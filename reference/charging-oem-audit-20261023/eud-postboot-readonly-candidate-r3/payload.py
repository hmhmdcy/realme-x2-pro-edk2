"""Prepare read-only source for root's existing pinned-key transport; no SSH."""
from pathlib import Path
import argparse,ast,base64,hashlib,json,os,re,sys
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
FIXED={'candidate_boot_sha256':'4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf',
 'rollback_boot_sha256':'a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280',
 'image363_sha256':'15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468',
 'logdump_sha256':'aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da',
 'camera481_expected_sha256':'1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705',
 'charging_manifest_sha256':'320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'}

def make_request(context_path,camera_path,endpoint,window_confirmed,original_key_verified):
 assert window_confirmed is True and original_key_verified is True
 assert isinstance(endpoint,str) and endpoint and not any(x.isspace() for x in endpoint)
 cp=Path(context_path);assert cp.is_absolute() and cp.is_file() and not cp.is_symlink()
 context_raw=cp.read_bytes();context=json.loads(context_raw)
 assert context['schema']=='samurai-eud-fastboot-context-v1'
 item=context['files']['guard'];assert item['path']=='guard-private.json'
 gp=cp.parent/item['path'];assert gp.is_file() and not gp.is_symlink()
 guard_raw=gp.read_bytes();guard=json.loads(guard_raw)
 assert sha(guard_raw)==item['sha256']==context['guard_sha256']
 assert guard['schema']=='samurai-eud-boot-activation-v1'
 assert guard['transaction_id']==context['transaction_id'] and guard['token']==context['token']
 assert guard['boot_id']==context['old_boot_id']
 assert re.fullmatch(r'eud-boot-[a-z0-9-]{8,64}',guard['transaction_id'])
 assert all(guard[k]==v for k,v in FIXED.items())
 camera_raw=Path(camera_path).read_bytes();assert sha(camera_raw)==FIXED['camera481_expected_sha256']
 camera=json.loads(camera_raw);assert camera['validated']
 return {'schema':'samurai-eud-postboot-readonly-v1','new_endpoint':endpoint,
   'original_key_transport_verified':True,'context_sha256':sha(context_raw),
   'guard_sha256':sha(guard_raw),'guard':guard,'camera':camera}

def make_payload(request):
 source=(HERE/'device.py').read_bytes();ast.parse(source)
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
   ring=report.get('raw',{}).get('ring',{})
   if 'raw_b64' in ring:
    raw=base64.b64decode(ring['raw_b64'],validate=True);assert len(raw)==0x14000
    with (out/'eud-ring-private.bin').open('xb') as f:f.write(raw)
    public['ring_raw_sha256']=sha(raw)
   public['passed']=exit_code==0 and result.get('passed') is True
   public['checks']={name:value.get('ready',True) for name,value in checks.items()}
   public['error_classes']={name:value.get('error') for name,value in result.get('errors',{}).items()}
   receipt=checks.get('EUD_ring_receipt',{})
   public['EUD_ring_receipt']={k:receipt[k] for k in ['ready','marker_state','receipts','parsed','header','raw_sha256','history_assumption','receipt_absence_is_not_callback_failure','callback_success_independently_proven'] if k in receipt}
   if 'collection_error' in result:public['collection_error']=result['collection_error']
  except Exception as e:public['decode_error_class']=type(e).__name__
  with (out/'receiver-result-private.json').open('x') as f:json.dump(public,f,indent=2);f.write('\n')
  return public
 finally:os.umask(old_mask)

def check_local():
 result=json.loads((HERE/'source-result.json').read_bytes())
 assert sha((HERE/'device.py').read_bytes())==result['device_sha256']
 for name in ['device.py','payload.py','device-body.py']:ast.parse((HERE/name).read_text())
 code=(HERE/'device.py').read_text()
 tree=ast.parse(code)
 forbidden={'write_text','write_bytes','pack_into','write','writelines','system','Popen','mkdir','unlink','remove'}
 assert not any(isinstance(x,ast.Attribute) and x.attr in forbidden for x in ast.walk(tree))
 assert 'O_RDWR' not in code and 'PROT_WRITE' not in code and '0x088e' not in code.lower()
 assert code.count("os.open('/dev/mem'")==1
 return {'local_checks_passed':True,'device_sha256':result['device_sha256'],
         'device_accessed':False,'SSH_implemented':False,'guard_created':False}

def main():
 if sys.flags.optimize:raise RuntimeError('optimized Python disables required checks')
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--check-local',action='store_true');p.add_argument('--emit-payload',action='store_true')
 p.add_argument('--execute',action='store_true');p.add_argument('--window-confirmed',action='store_true')
 p.add_argument('--original-key-verified',action='store_true');p.add_argument('--new-endpoint')
 p.add_argument('--context-private');p.add_argument('--camera-private')
 a=p.parse_args();check=check_local()
 if not a.emit_payload:
  print(json.dumps(check));return 0
 assert a.execute and a.window_confirmed and a.original_key_verified and a.new_endpoint
 request=make_request(a.context_private,a.camera_private,a.new_endpoint,True,True)
 # Output is private executable source only. Root supplies the exact three
 # execution argv flags through its own verified transport; this tool never runs it.
 sys.stdout.buffer.write(make_payload(request));return 0

if __name__=='__main__':raise SystemExit(main())
