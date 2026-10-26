"""Only change socket binding to allow the previously observed AP port tuple."""
from pathlib import Path
import base64,importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel245');s=(R.parent/'kernel244/diag_transport_boot.py').read_text()
s=s.replace(' def __init__(self,output,observed_control=None):',' def __init__(self,output,observed_control=None,fixed_ports=None):')
s=s.replace('   for i in range(4):','   for i in range(4 if fixed_ports is None else 0):')
old="   for name in ['control','data','dci','command']:\n    s=socket.socket(42,socket.SOCK_DGRAM);s.bind((s.getsockname()[0],0));self.sockets.append(s)"
new="   if fixed_ports is not None:assert len(fixed_ports)==4 and len(set(fixed_ports))==4 and all(16384<=p<65536 for p in fixed_ports)\n   for i,name in enumerate(['control','data','dci','command']):\n    s=socket.socket(42,socket.SOCK_DGRAM);self.sockets.append(s);s.bind((s.getsockname()[0],0 if fixed_ports is None else fixed_ports[i]))"
assert old in s;s=s.replace(old,new);compile(s,'diag_fixed.py','exec');(R/'diag_fixed.py').write_text(s)
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel244/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import base64,hashlib,json,os
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k244-runtime/boot-id-private.txt').read_bytes();p=r/'k245-tools/diag_fixed.py';assert not p.exists();b=base64.b64decode(PAYLOAD);compile(b,'diag_fixed.py','exec');p.write_bytes(b)
print(json.dumps(dict(stage=245,staged=True,source_sha256=hashlib.sha256(b).hexdigest(),fixed_ports_must_be_previously_observed=True)))
'''.replace('PAYLOAD',repr(base64.b64encode(s.encode()).decode()))
x=host.ssh('python3 -',input=code.encode(),timeout=15);(P/'fixed-prepare-private.log').write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout);(R/'fixed-library-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
