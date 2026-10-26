"""Only reject ambiguous/malformed marker-prefix histories; preserve R1/R2."""
from pathlib import Path
import ast,difflib,hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent;R2=HERE.parent/'eud-postboot-readonly-candidate-r2'
R1=HERE.parent/'eud-postboot-readonly-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R2/'device.py')=='e491f1dba68f532ed1c4543c90f121e92da9fedb25facd663fb8bc71027e7f1a'
before={str(p):sha(p) for folder in [R1,R2] for p in folder.iterdir() if p.is_file()}
for name in ['device-body.py','payload.py','prepare.py','contract.json']:
 assert not (HERE/name).exists(),name
 shutil.copy2(R2/name,HERE/name)
body=(HERE/'device-body.py').read_text()
marker=" receipts=[line.decode('ascii') for line in history.splitlines() if re.fullmatch("
assert body.count(marker)==1
body=body.replace(marker," prefix_records=[line for line in history.splitlines() if b'[SAMURAI-EUD-OFF' in line]\n"+marker,1)
marker=' valid=len(parsed)==1 and '
assert body.count(marker)==1
body=body.replace(marker,' valid=len(prefix_records)==1 and len(parsed)==1 and ',1)
marker="   'receipts':receipts,'parsed':parsed,'raw_sha256':sha(raw),'header':list(fields),"
assert body.count(marker)==1
body=body.replace(marker,"   'marker_prefix_count':len(prefix_records),\n"+marker,1)
(HERE/'device-body.py').write_text(body,newline='\n')
subprocess.run([sys.executable,'-B',str(HERE/'prepare.py')],check=True,capture_output=True)
old=(R2/'device.py').read_text();new=(HERE/'device.py').read_text()
(HERE/'r2-to-r3.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='r2/device.py',tofile='r3/device.py')),newline='\n')
def functions(source):
 return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
f1,f2=functions(old),functions(new)
assert set(f1)==set(f2)
assert [n for n in f1 if f1[n]!=f2[n]]==['decode_ring']
assert all(sha(Path(p))==digest for p,digest in before.items())
result=dict(offline_only=True,R1_R2_unchanged=True,preserved_file_hashes=before,
 changed_actual_functions=['decode_ring'],device_sha256=sha(HERE/'device.py'),
 base_device_sha256=sha(R2/'device.py'),R2_full_result_sha256=sha(R2/'test-full-result.json'),
 R1_other_groups_receipt_sha256=sha(R1/'test-result.json'),
 unchanged_healthy_charge_mode_sha256=hashlib.sha256(f2['healthy_charge_mode'].encode()).hexdigest(),
 unchanged_check_charging_sha256=hashlib.sha256(f2['check_charging'].encode()).hexdigest(),
 old_suites_rerun=False,device_accessed=False)
(HERE/'revision-source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(device_sha256=result['device_sha256'],changed_functions=['decode_ring'],R1_R2_unchanged=True)))
