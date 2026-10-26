from pathlib import Path
import ast,hashlib,json,host
ref=Path(__file__).resolve().parent;data=host.PRIVATE/'assistance/server-1-private.bin'
digest=hashlib.sha256(data.read_bytes()).hexdigest();assert digest=='303702930b278083fa4e52eeeb99787f511b4b2e150a4dba5161e46f06f335f4'
assert not json.loads((ref/'orbit-current-validity-validation.json').read_text())['currently_valid']
host.ssh('mkdir -m700 /var/lib/samurai/k201-assistance')
host.upload(data,'/var/lib/samurai/k201-assistance/xtra-private.bin')
s=(ref.parent/'kernel191/test-mm-assistance-injection.py').read_text().replace('k191','k201').replace('stage=191','stage=201').replace('k189r2-reboot-runtime','k201-baseline').replace('e905a7291990c20324210b3bb405d84f8088da283f969255e2b28e34676d4008',digest)
s=s.replace(" control.SetLogging('DEBUG')", " pass  # Keep normal daemon logging; independent validity query verifies firmware acceptance.")
ast.parse(s);(ref/'test-mm-assistance-injection.py').write_text(s)
print('K201_CURRENT_TLS_DATA_STAGED_FOR_ONE_STANDARD_MM_INJECTION')
