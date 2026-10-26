"""Prepare a fresh-peer-only transport; never negotiate with a deleted peer."""
from pathlib import Path
import base64,hashlib,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel244')
s=(R.parent/'kernel243/diag_transport.py').read_text()
s=s.replace('  self.log_mask_active=False;self.log_mask_reset_sent=False','  self.log_mask_active=False;self.log_mask_reset_sent=False;self.deleted_peers=[]')
old="    if cmd==4 and service==4097 and instance==1 and node==0 and port:self.remote_cmd=(node,port)\n    continue"
new="""    if cmd==4 and service==4097 and instance==1 and node==0 and port:self.remote_cmd=(node,port)
    if cmd==5 and service==4097 and instance==1 and (node,port)==self.remote_cmd:self.remote_cmd=None
    if cmd==6:
     deleted=struct.unpack_from('<II',data,4);self.deleted_peers.append(deleted)
     if deleted==self.control_peer:
      self.record('control_peer_deleted');self.control_peer=None;self.sent_features=False
     if deleted==self.remote_cmd:self.remote_cmd=None
    continue"""
assert old in s;s=s.replace(old,new)
old="   if self.observed_control and self.remote_cmd and not self.sent_features and time.monotonic()-self.began>2:\n    peer,mask,n=self.observed_control\n    self.negotiate(peer,mask,n,'same_boot_observed_peer_no_fresh_announcement')\n"
assert old in s;s=s.replace(old,'')
s=s.replace("   except OSError as e:errors.append(e.errno)\n  for i,instance", "   except Exception as e:errors.append(getattr(e,'errno',type(e).__name__))\n  for i,instance")
compile(s,'diag_transport.py','exec');(R/'diag_transport.py').write_text(s)
spec=importlib.util.spec_from_file_location('diag244',R/'diag_transport.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d);d.regression()
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
o=r/'k244-diag-python-r1';assert not o.exists();o.mkdir(mode=0o700)
b=base64.b64decode(PAYLOAD);compile(b,'diag_transport.py','exec');(o/'diag_transport.py').write_bytes(b)
print(json.dumps(dict(stage=244,source_sha256=hashlib.sha256(b).hexdigest(),fresh_peer_only=True,library_staged_only=True)))
'''.replace('PAYLOAD',repr(base64.b64encode(s.encode()).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=15);(P/'prepare-diag-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'diag-library-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
