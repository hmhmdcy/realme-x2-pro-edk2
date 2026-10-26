from pathlib import Path
import json,shutil
import host

ref=Path(__file__).resolve().parent
path=ref/'auto-install-validation.json';saved=ref/'auto-install-template-stage-r1-validation.json'
assert not saved.exists();shutil.copyfile(path,saved)
code='''from pathlib import Path
import json
path=Path('/var/lib/samurai/k189-deploy/summary.json')
record=json.loads(path.read_text());assert record['stage']==188 and record['persistent_files_installed']
saved=path.with_name('summary-template-stage-r1-private.json');assert not saved.exists();saved.write_bytes(path.read_bytes())
record.update(stage=189,installer_source_stage=188);path.write_text(json.dumps(record,indent=2)+'\\n')
print(json.dumps(record))
'''
p=host.ssh('python3 -',input=code.encode());path.write_bytes(p.stdout);print(p.stdout.decode())
