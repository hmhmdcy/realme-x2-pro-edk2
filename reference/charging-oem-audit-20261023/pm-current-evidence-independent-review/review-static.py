"""Independent hashes/AST/differences only; never imports author code or tests."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
AUTHOR=REF/'charging-session-20261023/pm-current-evidence-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(AUTHOR/'delivery.json')=='8b49ee7a82e7bb0c13423455ef5b8e1460238d028d5bd3184c5f335d96730c84'
delivery=json.loads((AUTHOR/'delivery.json').read_bytes())
checked={}
for name,row in delivery['files'].items():
 path=AUTHOR/name;assert path.resolve().is_relative_to(AUTHOR.resolve())
 assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'],name
 checked[name]=row['sha256']
old=AUTHOR/'history/revision-1';assert sha(old/'delivery.json')=='59121dd38e9fcff0ddbef534d51629b72ecf32610292156c2036c81a76e3aee6'
before,after=(old/'worker.py').read_text(),(AUTHOR/'worker.py').read_text()
former="functional = {'returned': checks['primitive_returned'],"
fixed="functional = {'returned': primitive.get('mem_returned') is True,"
assert before.count(former)==after.count(fixed)==1 and after.replace(fixed,former)==before
for name in ['prepare-request.py','trace-evidence.py','pm-transaction.py','test-new-boundaries.py']:
 assert (AUTHOR/name).read_bytes()==(old/name).read_bytes(),name
primitive=REF/'charging-ui-audit-20261023/pm-transaction.py'
assert (AUTHOR/'pm-transaction.py').read_bytes()==primitive.read_bytes()
assert sha(primitive)=='fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1'
def functions(path):
 source=path.read_text();return {n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
original=functions(REF/'charging-ui-audit-20261023/pm-worker-candidate/worker.py');current=functions(AUTHOR/'worker.py')
same={}
for name in ['healthy','services','configuration_preserved','audit_trace']:
 assert original[name]==current[name];same[name]=hashlib.sha256(current[name].encode()).hexdigest()
aggregate=json.loads((AUTHOR/'test-result.json').read_bytes())
new=json.loads((AUTHOR/'returned-fact-test-result.json').read_bytes())
assert aggregate['passed'] and new['passed'] and new['new_test_methods']==1 and len(new['cases'])==3
for name,digest in new['tested_files'].items():assert sha(AUTHOR/name)==digest
assert aggregate['prior_actual10_reused_not_rerun']['sha256']==sha(old/'test-result.json')
assert aggregate['new_receipt']['sha256']==sha(AUTHOR/'returned-fact-test-result.json')
assert aggregate['patch_sha256']==sha(AUTHOR/'revision-1-to-2.patch')
checks=json.loads((AUTHOR/'local-check-result.json').read_bytes())
assert checks['passed'] and all(x['returncode']==0 for x in checks['commands'])
for name,digest in checks['tested_source_sha256'].items():assert sha(AUTHOR/name)==digest
assert delivery['default_checks_sha256']==sha(AUTHOR/'local-check-result.json')
test_text=(AUTHOR/'test-returned-fact.py').read_text()
assert "'outcome': 'failed', 'mem_returned': True" in test_text
assert "self.assertFalse(result['functional_checks']['primitive_returned'])" in test_text
readme=(AUTHOR/'README.md').read_text()
for token in ['detached owned supervisor','stdin=subprocess.DEVNULL','start_new_session=True','PID/startticks','10..20','whole_system_accepted']:
 assert token in readme,token
report={'status':'accepted_for_limited_offline_scope','author_delivery_sha256':sha(AUTHOR/'delivery.json'),
 'author_history_r1_delivery_sha256':sha(old/'delivery.json'),'author_files_verified':checked,
 'primitive_whole_bytes_unchanged':True,'four_original_worker_functions_equal':same,
 'r2_single_worker_expression_delta_verified':True,'returned_fact_issue_closed':True,
 'new_counterexample_methods_receipt':{'methods':1,'terminal_vectors':3,'sha256':sha(AUTHOR/'returned-fact-test-result.json'),'reviewer_reran':False},
 'old10_27_29_126_rerun':False,'author_entry_imported_or_executed':False,
 'reviewer_device_trace_PM_build_SDK_Git':False,
 'checks':['actual502 adoption and current pointer before request binding','newguard/version/rootfs/board/notes before hardware reads',
  'missing pm_wakeup_irq stays null with errno','actual unique RTC IRQ and runtime fields; PID-scoped RTC/sched/lock filters',
  'filters and bounded128 stack trigger installed/read back before enable and arm','only fresh owned trace instance cleanup, including attempted writes',
  '10..20 second gate separate from raw mem return fact','strict functional success separate from unique reason and whole-system acceptance',
  'detached original owned Popen required by root operation contract; no automatic USB/DWC/desktop recovery'],
 'limits':['source and receipt review, not execution of test fixtures or Linux tracefs','no actual runtime request/bind/RTC/mem/host capture or data recovery verified',
  'root still owns detached dispatch/current window/host NCM and strict-key restoration integration','trace timing/first IRQ cannot establish unique wake cause'],
 'review_script_sha256':sha(Path(__file__))}
(HERE/'review-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'accepted_limited_scope':True,'review_result_sha256':sha(HERE/'review-result.json'),'author_files_verified':len(checked)}))
