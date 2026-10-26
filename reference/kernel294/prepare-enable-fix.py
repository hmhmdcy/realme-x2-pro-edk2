"""Create an independent k295 candidate and a corrected negative-control harness."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent;NEW=ROOT.parent/'kernel295';assert not NEW.exists();NEW.mkdir()
P=Path('/mnt/e/edk2-samurai-out/kernel295');assert not P.exists();P.mkdir(mode=0o700)
(NEW/'host.py').write_text((ROOT/'host.py').read_text().replace('camera293_transport','camera294_transport').replace("'kernel293/host.py'","'kernel294/host.py'").replace("/kernel294'","/kernel295'"))
s=(ROOT/'test-stats.py').read_text().replace('stage=294','stage=295').replace('memory[0x44/4]&BIT(5)','memory[0x44/4]&BIT(4)')
s=s.replace('import hashlib,json,re,subprocess','import hashlib,json,re,resource,subprocess,sys\nresource.setrlimit(resource.RLIMIT_CORE,(0,0))')
# The prior independent port proof says bit5 belongs to RS and must be preserved.
s=s.replace(' assert(!(memory[0x44/4]&BIT(4)));',' assert((memory[0x44/4]&BIT(5))==(0xa5a5a5a5U&BIT(5)));\n assert(!(memory[0x44/4]&BIT(4)));',1)
needle="assert q.returncode==0,q.stderr.decode()\nreport=dict(stage=295"
replacement="""\nif '--parent' in sys.argv:
 assert q.returncode!=0
 (ROOT/'parent-enable-validation.json').write_text(json.dumps(dict(stage=295,actual_parent_function=True,independent_port_bit_contract=True,expected_failure_observed=True,exit=q.returncode),indent=2)+'\\n')
 print('Pinned bit4 contract rejects the actual k294 implementation.');sys.exit(0)
assert q.returncode==0,q.stderr.decode()
report=dict(stage=295"""
assert needle in s;s=s.replace(needle,replacement)
(NEW/'test-stats.py').write_text(s);compile(s,'test-stats.py','exec')
(NEW/'test-metadata-restart.py').write_text((ROOT/'test-metadata-restart.py').read_text().replace('stage=294','stage=295'))
print('Prepared corrected independent-bit negative control; no kernel/device changes yet.')
