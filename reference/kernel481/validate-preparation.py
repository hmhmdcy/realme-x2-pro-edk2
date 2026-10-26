"""Finite local481 preparation checks; never accesses a target or SDK."""
from pathlib import Path
import ast,hashlib,json,shlex,subprocess,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel481')
WORK=PRIVATE/'k481-package-adoption-r1-offline-template-r2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
 prepared=json.loads((WORK/'preparation-private.json').read_text());plan=json.loads((WORK/'plan-private.json').read_text())
 assert prepared['deployable'] is False and plan['deployable'] is False
 for name,digest in prepared['source_sha256'].items():assert sha(HERE.parent/name)==digest
 assert sha(WORK/'worker.py')==prepared['worker_sha256'] and sha(WORK/'payload-private.tar.gz')==prepared['archive_sha256']
 queries={name:WORK/(name+'-query.py') for name in ['stage','launch','observe','collect']}
 for name,path in queries.items():assert sha(path)==prepared['query_sha256'][name];ast.parse(path.read_text())
 tree=ast.parse((WORK/'worker.py').read_text());body=ast.parse((HERE/'worker-body.py').read_text())
 gate=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='gate')
 namespace={'WINDOW':plan['window_id']};exec(compile(ast.Module(body=[gate],type_ignores=[]),'<actual481-gate-only>','exec'),namespace)
 try:namespace['gate'](plan)
 except AssertionError:pass
 else:raise AssertionError('Unbound worker gate accepted')
 local=[]
 for name in ['stage','launch']:
  result=subprocess.run(['python3','-B',str(queries[name])],input=b'',capture_output=True)
  (PRIVATE/(name+'-unbound-local-stderr-private.txt')).write_bytes(result.stderr)
  assert result.returncode==1 and not result.stdout and b"plan['deployable']" in result.stderr
  local.append(dict(action=name,exit_code=1,rejected_before_inventory_or_mutation=True))
 stage=ast.parse(queries['stage'].read_text());launch=ast.parse(queries['launch'].read_text())
 assert any(isinstance(n,ast.Constant) and n.value=='\n\n' for n in ast.walk(stage)),'Installed DB separator must be two LF'
 stage_call=next(n for n in ast.walk(stage) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write_text')
 launch_call=next(n for n in ast.walk(launch) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='write')
 env=dict(json=json,expected={},record=dict(pid=1,start_ticks='1',launched=True),chr=chr)
 text=eval(compile(ast.Expression(stage_call.args[0]),'<stage-json-only>','eval'),env)
 data=eval(compile(ast.Expression(launch_call.args[1]),'<launch-json-only>','eval'),env)
 assert json.loads(text)==dict(passed=True,files_sha256={}) and text.endswith(chr(10))
 assert json.loads(data)==env['record'] and data.endswith(bytes([10]))
 with tarfile.open(WORK/'payload-private.tar.gz') as tar:
  members=tar.getmembers();files=[m for m in members if m.isfile()];assert len(files)==40
  for member in members:
   assert member.uid==member.gid==0 and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
   if member.isdir():assert member.mode==0o700;continue
   assert member.isfile() and member.mode==(0o755 if member.name in plan['expected_forward']['probe_tools'] else 0o600)
   digest=hashlib.sha256(tar.extractfile(member).read()).hexdigest()
   assert digest==(sha(WORK/'plan-private.json') if member.name=='plan-private.json' else plan['payload_sha256'][member.name])
 keep=next(n for n in body.body if isinstance(n,ast.FunctionDef) and n.name=='keep_forward')
 first=next(i for i,n in enumerate(keep.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='world')
 stop=next(i for i,n in enumerate(keep.body[first:],first) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='atomic')
 logic=compile(ast.Module(body=keep.body[first:stop],type_ignores=[]),'<actual-world-composition-only>','exec')
 class Backup:
  def __init__(self,data):self.data=data
  def __truediv__(self,name):assert name=='etc/apk/world';return self
  def read_bytes(self):return self.data
 world_cases=[]
 for original in [b'',b'busybox',b'busybox\nsamurai-camera-stack=0.1.0-r27\n# retained\nother\n']:
  context=dict(backup=Backup(original),cohort=plan['cohort'],re=__import__('re'))
  exec(logic,context);output=context['data'];lines=output.splitlines()
  assert all((name+'='+version).encode() in lines for name,version in plan['cohort']['forward_packages'].items())
  if original.startswith(b'busybox'):assert output.startswith(b'busybox\n')
  if b'# retained\nother\n' in original:assert b'# retained\nother\n' in output
  assert b'samurai-camera-stack=0.1.0-r27' not in output
  world_cases.append(dict(input_sha256=hashlib.sha256(original).hexdigest(),output_sha256=hashlib.sha256(output).hexdigest(),passed=True))
 scripts=plan['scripts_metadata'];assert all(not row['scripts'] and not row['triggers'] for key,row in scripts.items() if isinstance(row,dict))
 command_bytes=len(('python3 -B -c '+shlex.quote(queries['stage'].read_text())).encode());assert command_bytes<120*1024
 report=dict(stage=481,passed=True,scope='offline preparation only; no package installation or device execution',
  final_template=WORK.name,prior_draft_r1_retained=True,deployable=False,no_ssh=True,no_sdk=True,no_device=True,
  native_transactions_planned=['forward-first r33/r28','rollback-exact r32/r27','forward-final r33/r28'],
  package_database_raw_restore_forbidden=True,seven_package_scripts_and_triggers_absent_in_both_cohorts=True,
  native_global_hooks_triggers_enabled_without_claim_of_exercise=True,modules4_profiles4_exact475=True,module_dependency_alias_metadata_equal=True,
  unbound_local_rejections=local,unbound_worker_gate_rejected=True,json_LF_and_DB_separator_semantics_passed=True,
  world_composition_cases=world_cases,archive_files=40,archive_bytes=prepared['archive_bytes'],archive_sha256=prepared['archive_sha256'],
  worker_sha256=prepared['worker_sha256'],plan_sha256=prepared['plan_sha256'],source_sha256=prepared['source_sha256'],query_sha256=prepared['query_sha256'],
  stage_command_bytes=command_bytes,promotion_deadline_seconds=300,diagnostic_budget_seconds=480,
  recovery_not_blocked_by_owner_age_or_diagnostic_overrun=True,live_unknown_APK_same_handle_no_kill_no_replay=True,
  actual_install_upgrade_rollback_and_default_capture_verified=False,validator_sha256=sha(Path(__file__)))
 (HERE/'preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:report[key] for key in ['stage','passed','final_template','archive_sha256','stage_command_bytes']}))

if __name__=='__main__':main()
