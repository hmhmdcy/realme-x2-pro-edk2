"""Fresh transaction after the first pre-mutation failure and old-provider recovery."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
assert json.loads((R/'preflight-recovery-validation.json').read_text())['old_provider_restored']
text=(R/'install-gain-pair.py').read_text()
for a,b in [('k271-gain-transaction','k271-gain-transaction-r2'),('gain-install-response-private.log','gain-install-r2-response-private.log'),('gain-install-validation.json','gain-install-r2-validation.json')]:text=text.replace(a,b)
a="if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)"
b="if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:result.append(p)"
assert text.count(a)==1;text=text.replace(a,b)
a="  stopped.append(name)\n  assert not processes(name),'Unexpected daemon restart; inspect manager before mutation'"
b="  stopped.append(name)\n  for _ in range(50):\n   if not processes(name):break\n   time.sleep(.1)\n  assert not processes(name),'Unexpected live daemon restart; inspect manager before mutation'"
assert text.count(a)==1;text=text.replace(a,b)
exec(compile(text,'install-gain-pair-r2-generated.py','exec'),dict(__file__=str(R/'install-gain-pair-r2-generated.py')))
