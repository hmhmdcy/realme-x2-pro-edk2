"""Static independent review only; no author import/entrypoint/test/transport."""
from pathlib import Path
import ast,hashlib,json
H=Path(__file__).resolve().parent;R=H.parents[1]
A=R/'charging-oem-audit-20261023/image502-logdump-activation-candidate'
BASE=R/'charging-session-20261023/gauge-image501-activation-candidate'
PAIR=R/'charging-session-20261023/gauge-image501-fastboot-pair-candidate'
EXPECTED_DELIVERY='05a4b5a6bd053dcf2696a09051a30abc808fc78260b8774700349fa8fae4df9c'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  while b:=f.read(1048576):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def function(s,n):
 node=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef) and x.name==n)
 return '\n'.join(s.splitlines()[node.lineno-1:node.end_lineno])
def windows(p):
 assert str(p).startswith('/mnt/e/')
 return Path('E:/'+str(p)[len('/mnt/e/'):])
def main():
 assert EXPECTED_DELIVERY is not None,'WIP is not an independently signed review'
 assert sha(A/'delivery.json')==EXPECTED_DELIVERY
 d=load(A/'delivery.json')
 assert d['passed'] and d['frozen'] and d['only_write_partition']=='logdump'
 for n,digest in d['files'].items():assert sha(A/n)==digest,n
 t=load(A/'test-result.json');assert t['passed'] and t['cases']==22 and t['affected_groups']==5
 for n,digest in t['tested_files'].items():assert sha(A/n)==digest,n
 assert t['old_suites_reused_not_rerun'] and not t['device_SSH_USB_fastboot_or_build_executed']
 prov=load(A/'source-provenance.json')
 for n,digest in prov['source_501'].items():assert sha(BASE/n)==digest,n
 assert sha(PAIR/'fastboot-operator.py')==prov['source_pair_sha256']
 assert sha(A/'prepare-tools.py')==prov['source_generator_sha256']
 unchanged={}
 for key,digest in t['unchanged_functions'].items():
  n,fun=key.split('::');old=BASE if n=='controller.py' else PAIR
  current=function((A/n).read_text(),fun);original=function((old/n).read_text(),fun)
  assert current==original,key
  assert hashlib.sha256((current+'\n').encode()).hexdigest()==digest,key
  unchanged[key]=digest
 assert len(unchanged)==28
 for n,digest in t['old_receipts'].items():assert sha(R/n)==digest,n
 text={n:(A/n).read_text() for n in ['controller.py','remote.py','guard-fragment.py','eud-quiesce.py','eud-restart.py','fastboot-operator.py','materialize.py']}
 oldc=(BASE/'controller.py').read_text();oldp=(PAIR/'fastboot-operator.py').read_text()
 # New transaction/schema literals do not change the original dispatch control.
 assert function(text['controller.py'],'run').replace('image502-notify-live-001','image501-[a-z0-9-]{8,64}')==function(oldc,'run')
 assert function(text['controller.py'],'export_context').replace('samurai-image502-notify-fastboot-context-v1','samurai-image501-fastboot-context-v1')==function(oldc,'export_context')
 for fun in ['worker','main']:
  assert function(text['fastboot-operator.py'],fun).replace('samurai-image502-notify-fastboot-action-v1','samurai-image501-fastboot-action-v1')==function(oldp,fun),fun
 assert function(text['fastboot-operator.py'],'fetch')==function(oldp,'fetch')
 marker="r=Path('/var/lib/samurai')"
 tails={}
 for n in ['eud-quiesce.py','eud-restart.py']:
  suffix=text[n].rsplit(marker,1)[1]
  assert suffix.replace('image502-notify-activation','image501-activation')==(BASE/n).read_text().rsplit(marker,1)[1]
  tails[n]=hashlib.sha256(suffix.encode()).hexdigest()
  assert '/dev/mem' not in text[n] and 'mmap' not in text[n]
  # Existing ath10k quiesce unbind is part of the unchanged hardware suffix;
  # the EUD-off check has no EUD unbind or CSR/mapping operation.
  assert "qcom_eud_com/unbind" not in text[n]
 operator=ast.parse(text['fastboot-operator.py']);run=next(n for n in operator.body if isinstance(n,ast.FunctionDef) and n.name=='run_action')
 part_loops=[tuple(ast.literal_eval(n.iter)) for n in ast.walk(run) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='part' and isinstance(n.iter,ast.Tuple)]
 assert part_loops==[('boot','logdump'),('logdump',)],part_loops
 assert "read_json(ACTIVATION / 'activation-pins.json')" in function(text['fastboot-operator.py'],'pinned_tools')
 assert "f.read(1048576)" in function(text['materialize.py'],'sha')
 assert 'hashlib.file_digest' in function(text['fastboot-operator.py'],'sha')
 assert "if sys.flags.optimize:raise RuntimeError" in text['controller.py'] and "if sys.flags.optimize:raise RuntimeError" in text['remote.py']
 assert "allow_inhibit=d['action'] in ['inspect-restart','restart']" in text['remote.py']
 assert "q['terminal'] and q['exit_code']==0 and summary['taint']==0" in text['guard-fragment.py']
 assert "all(q[k]==summary[k]==meta[k] for k in ['transaction_id','token','boot_id'])" in text['guard-fragment.py']
 M=windows(d['materialization_path']);assert sha(M/'materialization.json')==d['materialization_sha256']
 m=load(M/'materialization.json');assert m['passed'] and m['no_device_action_performed']
 for n,digest in m['source_files'].items():assert sha(A/n)==digest,n
 for n,digest in m['files'].items():assert sha(M/n)==digest==d['materialized_files'][n],n
 assert m['worker_hashes']==d['worker_hashes']
 for n in ['guard-fragment.py','eud-quiesce.py','eud-restart.py']:
  assert (M/n).read_bytes()==text[n].replace('__MATERIALIZE_LOGDUMP_SHA256__',d['candidate_logdump_sha256']).encode()
 c=load(M/'prepare-contract.json');g=c['fixed_guard_fields']
 assert c['write_scope']==g['partitions']==['logdump'] and c['boot_is_readonly_invariant']
 assert g['schema']==c['schema']=='samurai-image502-notify-activation-v1'
 assert c['transaction_id']=='image502-notify-live-001'
 assert g['unchanged_boot_sha256']==d['unchanged_boot_sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
 assert g['candidate_logdump_sha256']==d['candidate_logdump_sha256']=='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
 assert g['rollback_logdump_sha256']==d['rollback_logdump_sha256']=='7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9'
 assert g['boot_bytes']==100663296 and g['logdump_bytes']==67108864
 assert g['old_boot_guard_path']=='/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
 assert load(M/'activation-pins.json')=={n:m['files'][n] for n in ['prepare-contract.json','eud-restart.py']}
 F=R/'charging-session-20261023/gauge-image502-logdump-candidate'
 assert sha(F/'delivery.json')==m['fat_delivery_sha256']=='eb615331fcb75fbb4cfb21064cea5a8effeffe386ad5ce8839989c7c359420ce'
 assert sha(F/'logdump-result.json')==m['fat_report_sha256']=='c08d98309b9c789f1f499d08b03ab53c1648c2d5e1efb39359dd7371570e6758'
 fat=load(F/'logdump-result.json');assert fat['passed'] and fat['private_result_sha256']==m['fat_private_result_sha256']
 assert sha(windows('/mnt/e/edk2-samurai-out/charging-management-20261023/gauge-image502-logdump-private-01/result.json'))==m['fat_private_result_sha256']
 assert c['source_and_payload_proof']['logdumps']==m['logdumps']
 for row in load(A/'baseline-input-pins.json').values():assert sha(windows(row['path']))==row['sha256']
 checks=load(A/'local-check-result.json');assert checks['passed'] and checks['controller_exit_code']==checks['operator_exit_code']==0
 assert checks['materialization_sha256']==d['materialization_sha256'] and not checks['device_prepare_quiesce_restart_flash_executed']
 out=dict(verdict='no_new_blocker_within_reviewed_executable_scope',author_delivery_sha256=EXPECTED_DELIVERY,
  author_materialization_sha256=d['materialization_sha256'],contract_sha256=sha(M/'prepare-contract.json'),worker_hashes=m['worker_hashes'],
  actual_affected_case_receipt_sha256=sha(A/'test-result.json'),author_local_checks_sha256=sha(A/'local-check-result.json'),
  unchanged_function_count=28,unchanged_function_hashes=unchanged,additional_literal_only_control_bodies=['controller.run','controller.export_context','operator.worker','operator.main','operator.fetch'],
  quiesce_restart_suffix_hashes=tails,hardware_tail_unchanged_except_work_label=True,
  only_flash_partition='logdump',rollback='current501 7e5 only',boot97811_readonly_invariant=True,
  old501_transactions_proven_ended_not_replayed=True,unknown_same_child_fetch_only=True,
  pins_directory_bug_found_and_author_fixed=True,pins_single_materialized_directory=True,
  FAT_and_Image_frozen_receipts_bound=True,large_payload_hashes_streamed=True,
  actions=dict(author_import_or_entrypoint=False,tests_rerun=False,build_or_SDK=False,device_SSH_fastboot=False,author_files_modified=False,materializer_executed=False),
  limits=['Not a live prepare/quiesce/restart/fastboot or physical latency acceptance.','Fresh exact current runtime guard and explicit exclusive window remain required.','Fresh sole serial/msmnile/geometry required per USB action; SSH/armed phase is not bootloader success.','Postboot502/full FAT/R8/camera/protection acceptance remains separate.'],
  reviewer_source_sha256=sha(Path(__file__)))
 (H/'review-result.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps(dict(verdict=out['verdict'],receipt_sha256=sha(H/'review-result.json'))))
 return out
if __name__=='__main__':main()
