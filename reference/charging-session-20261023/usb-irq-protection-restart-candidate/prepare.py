"""Compose source-only stage-aware workers. No execution/device/request build."""
from pathlib import Path
import ast,difflib,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
OLD=REF/'charging-oem-audit-20261023/image502-logdump-activation-candidate'
STAGE=REF/'charging-ui-audit-20261023/usb-irq-protection-stage-candidate'
HOST=REF/'charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2'
COHORT=REF/'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def funcs(p):
 text=p.read_text()
 return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}


for folder in [OLD,STAGE,HOST,COHORT]:
 d=json.loads((folder/'delivery.json').read_text())
 for n,row in d['files'].items():assert sha(folder/n)==(row['sha256'] if isinstance(row,dict) else row),n
contract=json.loads((HERE/'prepare-contract.json').read_text())
assert sha(HERE/'prepare-contract.json')=='13bc81d89bfe34e573b4a23287c7841c67cd82c563cfc3266004b9ab3eba0914'
oldguard=funcs(OLD/'guard-fragment.py');stage=funcs(STAGE/'stage-worker.py')
basecollector=funcs(REF/'charging-oem-audit-20261023/image502-postboot-readonly/device.py')
cohort=json.loads((COHORT/'cohort-manifest.json').read_text());manifest=json.loads((COHORT/'manifest.json').read_text())
stage_text=(STAGE/'stage-worker.py').read_text()
checks=next(ast.literal_eval(n.value) for n in ast.parse(stage_text).body if isinstance(n,ast.Assign) and
            any(isinstance(t,ast.Name) and t.id=='CHECKS' for t in n.targets))
oldnotes={n:item['old']['resident_note_sha256'] for n,item in cohort['modules'].items()}
oldnotes['samurai-mp2650']=cohort['unchanged_charger_identity']['resident_note_sha256']
oldfiles={manifest['modules'][n]['target']:item['old']['sha256'] for n,item in cohort['modules'].items()}
oldfiles['/usr/share/samurai-charging/manifest.json']=cohort['old_manifest_sha256']
constants=dict(FIXED=contract['fixed_guard_fields'],EXPECTED_MANIFEST=manifest,
 RELEASE=manifest['release'],VERSION=contract['fixed_guard_fields']['kernel_version'],
 BOOT=cohort['required_carriers']['rollback_boot']['sha256'],LOGDUMP=cohort['required_carriers']['logdump']['sha256'],
 OLD=cohort['old_manifest_sha256'],OLD_NOTES=oldnotes,OLD_FILES=oldfiles,CHECKS=checks,
 PAYLOAD='9dee06ddea1190ea70a188efe47742afb8b104bf53ac31cb57598f079ee4fb3c',
 CAMERA481=contract['fixed_guard_fields']['camera481_expected_sha256'],
 SENSOR468_NOTE='a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13')
reuse=[];bodies=[]
for source,functions in [(OLD/'guard-fragment.py',['secure_file','file_sha','block_sha','camera481_check','eud_off_check','charging_sample_phase']),
                         (STAGE/'stage-worker.py',['validate_adoption','safe_sample','environment']),
                         (REF/'charging-oem-audit-20261023/image502-postboot-readonly/device.py',['active'])]:
 definitions=funcs(source)
 for name in functions:
  value=definitions[name];bodies.append(value)
  reuse.append(dict(name=name,source=str(source.relative_to(REF)),source_sha256=sha(source),
                    function_sha256=hashlib.sha256(value.encode()).hexdigest()))
body=(HERE/'common-body.py').read_text();split=body.index('def need(')
common=body[:split]+'\n'.join(n+'='+repr(v) for n,v in constants.items())+'\n\n'+'\n\n'.join(bodies)+'\n\n'+body[split:]
compile(common,'common.py','exec')
(HERE/'common.py').write_text(common,newline='\n')
metadata=[]
for name in ['eud-quiesce.py','eud-restart.py']:
 original=(OLD/name).read_text()
 header=original[:original.index('# Embedded verbatim')]
 pos=header.index('import ctypes')
 header=header[:pos]+'''if not sys.argv[1:] or sys.argv[1:]==['--check-local']:
 print('{"source_only":true,"device_accessed":false,"request_generated":false}');raise SystemExit(0)
'''+header[pos:]
 suffix=original[original.index("assert len(sys.argv)==4"):]
 suffix=suffix.replace("work='image502-notify-activation'","work='usb-irq-protection-activation'")
 if name=='eud-quiesce.py':
  old=" command(['/usr/sbin/samurai-charging','stop'])"
  assert suffix.count(old)==1
  suffix=suffix.replace(old," # Stage already stopped synchronously; guard reverified INHIBIT under the original service flock.")
  old="for name in ['samurai-charging','samurai-gnss-assist'"
  assert suffix.count(old)==1;suffix=suffix.replace(old,"for name in ['samurai-gnss-assist'",1)
  tail=" pids=subprocess.run(['pgrep','-u','10000']"
  newtail=suffix[suffix.index(tail):].replace("work='usb-irq-protection-activation'","work='image502-notify-activation'")
  oldtail=original[original.index(tail):]
  assert newtail==oldtail
  preserved='hardware tail from original UID10000 quiesce onward, work metadata normalized'
 else:
  tail="assert sys.argv[3] in ['--inspect','--commit-restart2-bootloader']"
  assert suffix[suffix.index(tail):].replace("work='usb-irq-protection-activation'","work='image502-notify-activation'")==original[original.index(tail):]
  preserved='entire original inspect/one-shot freeze/RESTART2/thaw/close body, work metadata normalized'
 result=header+common+'\n\n'+suffix
 compile(result,name,'exec')
 assert all(token not in result for token in ['/dev/mem','mmap','rmmod','insmod'])
 (HERE/name).write_text(result,newline='\n')
 (HERE/(name+'.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),result.splitlines(True),fromfile='old/'+name,tofile='new/'+name)),newline='\n')
 metadata.append(dict(name=name,original_sha256=sha(OLD/name),candidate_sha256=sha(HERE/name),hardware_preservation=preserved))
provenance=dict(source_only=True,reused_functions=reuse,worker_suffixes=metadata,
 source_pins={str(p.relative_to(REF)):sha(p) for p in [OLD/'delivery.json',STAGE/'delivery.json',HOST/'delivery.json',COHORT/'delivery.json',
 REF/'charging-management-20261023/samurai-charging.openrc']},
 fixed_contract_sha256=sha(HERE/'prepare-contract.json'),runtime_request_generated=False,
 stage_new_disk_old_live_comparison_is_independent=True,manager_start_resume_loaded_matches_called=False)
(HERE/'source-reuse.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(dict(prepared=True,workers={r['name']:r['candidate_sha256'] for r in metadata},reused_functions=len(reuse))))
