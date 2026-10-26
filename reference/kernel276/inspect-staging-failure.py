from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,subprocess
r=Path('/var/lib/samurai/k276-cci-transaction')
print(json.dumps(dict(state=json.loads((r/'state-private.json').read_text()),failure=(r/'failure-private.txt').read_text(),module_path=subprocess.check_output(['modinfo','-n','i2c_qcom_cci'],text=True).strip(),tree=str(Path('/usr/lib/modules')/os.uname().release),backup_created=(r/'backup').exists())))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'stage-failure-inspection-private.json').write_bytes(q.stdout);print(q.stdout.decode())
