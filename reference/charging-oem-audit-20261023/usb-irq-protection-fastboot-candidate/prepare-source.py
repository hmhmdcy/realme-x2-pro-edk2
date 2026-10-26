"""Build a static boot-only specialization of the frozen once/wait operator.
Source generation only. Does not create runtime identities or call fastboot.
"""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASE=REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate/fastboot-operator.py'
raw=BASE.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='7f473d8698e2e2f83ff768db98de167998a6d7b53e948421b8019fec141d2121'
source=raw.decode()
special=(HERE/'operator-specialization.inc').read_text()
def funcs(text):
 lines=text.splitlines(True)
 return {node.name:''.join(lines[node.lineno-1:node.end_lineno]) for node in ast.parse(text).body if isinstance(node,ast.FunctionDef)}
original=funcs(source);changed=funcs(special)
for name,body in changed.items():
 if name in original:
  assert source.count(original[name])==1
  source=source.replace(original[name],body)
 else:
  source=source.replace('\ndef pinned_tools():','\n'+body+'\n\ndef pinned_tools():',1)
old='"""One-shot logdump-only Image502 fastboot operator. Default is offline, read-only check-local."""'
assert old in source
source=source.replace(old,'"""One-shot IRQ boot-only operator. Default check-local never accesses USB or binds a future identity."""')
source=source.replace("MATERIALIZED = PRIVATE / 'image502-notify-materialized-001'\nACTIVATION = MATERIALIZED\nIMAGES = {}",'''RESTART = REF / 'charging-session-20261023/usb-irq-protection-restart-candidate'
STAGE_PROOF = REF / 'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/stage-proof.py'
IRQ_BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
ORIGINAL_BOOT = '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
LOGDUMP502 = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
IMAGES = {'candidate': {'boot': (PRIVATE / 'usb-input-irq-boot-private-01/boot-usb-input-irq-private.img', IRQ_BOOT, 100663296)},
          'original': {'boot': (PRIVATE / 'gauge-image501-boot-private-01/boot-gauge501-private.img', ORIGINAL_BOOT, 100663296)}}''')
source=source.replace('# Explicit logdump-only operation, no automatic reboot, recovery or second attempt.', '# Explicit boot-only operation; no rootfs rollback, automatic reboot or second attempt.')
source=source.replace('samurai-image502-notify-fastboot-action-v1','samurai-usb-irq-protection-fastboot-action-v1')
ast.parse(source)
dest=HERE/'fastboot-operator.py'
if dest.exists():
 assert dest.read_text()==source,'existing source differs; review the source delta rather than overwrite'
else:
 dest.write_text(source)
new=funcs(source)
unchanged={name:hashlib.sha256(body.encode()).hexdigest() for name,body in original.items() if new.get(name)==body}
proof={'baseline_sha256':hashlib.sha256(raw).hexdigest(),'unchanged_functions':unchanged,
 'changed_functions':[name for name in original if name not in unchanged],
 'new_functions':[name for name in new if name not in original],
 'operator_sha256':hashlib.sha256(source.encode()).hexdigest(),
 'schema_only_changes_in_worker_and_main':True,'device_accessed':False}
(HERE/'source-reuse.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'generated':True,'unchanged_functions':len(unchanged),'source_sha256':proof['operator_sha256']}))
