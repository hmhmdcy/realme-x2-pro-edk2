"""Static AST/source/hash binder only; never import or run author tools."""
from pathlib import Path
import ast
import hashlib
import json
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
AUTHOR=REF/'charging-session-20261023/usb-irq-protection-activation-host-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def functions(p):
 text=p.read_text()
 return text,{node.name:ast.get_source_segment(text,node) for node in ast.parse(text).body if isinstance(node,ast.FunctionDef)}


def main():
 assert not sys.flags.optimize
 assert not (HERE/'review-result.json').exists(),'Frozen review exists'
 assert sha(AUTHOR/'delivery.json')=='210eff4787aaccafd16692d98f79ce395f032b66f1aa7b76ffc4ad9a341bf12b'
 delivery=read(AUTHOR/'delivery.json');assert delivery['passed'] is True and delivery['frozen'] is True and delivery['revision']==2
 for name,entry in delivery['files'].items():
  assert sha(AUTHOR/name)==entry['sha256'] and (AUTHOR/name).stat().st_size==entry['bytes'],name
 assert sha(AUTHOR/'controller.py')=='98fb6dfd750cd1d273b4d59e4157b64c4481830265f1f95103ffd77c3edffdb8'
 old=AUTHOR/'history/revision-1'
 assert sha(old/'delivery.json')=='93b0bc012d8f65321779863258b900b2820fa10818054cc3b53954f009ab6f86'
 before,oldfn=functions(old/'controller.py');after,newfn=functions(AUTHOR/'controller.py')
 assert set(oldfn)==set(newfn)
 changed=[name for name in oldfn if oldfn[name]!=newfn[name]]
 assert changed==['ssh_worker','terminal_job']
 for name in changed:
  assert before.count(oldfn[name])==after.count(newfn[name])==1
  before=before.replace(oldfn[name],'REVIEW_SAME_FUNCTION_'+name)
  after=after.replace(newfn[name],'REVIEW_SAME_FUNCTION_'+name)
 assert before==after,'Source outside the two functions changed'
 for name in ['remote.py','supervisor.py','source-pins.json','test-host.py','test-result.json','host-contract.json']:
  assert (AUTHOR/name).read_bytes()==(old/name).read_bytes(),name
 test=read(AUTHOR/'close-r2-result.json')
 assert sha(AUTHOR/'close-r2-result.json')=='b1db8b737373b6c0dabc99d8b28eda93ad725cf515627ca78fb6b4af97edd3a5'
 assert test['passed'] is True and test['methods']==3 and test['failures']==test['errors']==0
 assert test['old_R1_12_device_13_31_suites_rerun'] is False
 for name,digest in test['tested_files'].items():assert sha(AUTHOR/name)==digest
 default=test['default_controller'];assert default['terminal'] is True and default['returncode']==0
 prior=read(AUTHOR/'test-result.json');assert prior['passed'] is True and prior['methods']==12
 for name,digest in prior['tested_files'].items():assert sha(old/name)==digest
 assert len(prior['default_checks'])==3 and all(x['terminal'] is True and x['returncode']==0 for x in prior['default_checks'])
 pins=read(AUTHOR/'source-pins.json')
 for entry in pins.values():assert sha(Path(entry['path']))==entry['sha256']
 expected={'device_delivery':'6187ea66cedfb7eaf747f0894ec17d54da2cd278e3ef0460cf002ee7a3579ad2',
  'device_contract':'13bc81d89bfe34e573b4a23287c7841c67cd82c563cfc3266004b9ab3eba0914',
  'quiesce':'43c5bd1952949504e918c660b208ca6bb45cfa103be9c9be575268b64ef9036e',
  'restart':'56a58c08bd3f79813d95955279f3ad07f7338d522239d32a7cfec4ea8d3b05be',
  'stage_proof':'85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093',
  'operator_delivery':'ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41',
  'postboot_host_delivery':'8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'}
 assert all(pins[name]['sha256']==digest for name,digest in expected.items())
 for name in ['controller.py','remote.py','supervisor.py','test-close-r2.py']:
  ast.parse((AUTHOR/name).read_bytes())
 result=dict(schema=1,passed=True,reviewed_revision=2,new_blockers=[],
  author_delivery_sha256=sha(AUTHOR/'delivery.json'),controller_sha256=sha(AUTHOR/'controller.py'),
  R1_not_accepted=True,R1_finding_sha256=sha(HERE/'r1-stdin-eof-finding.json'),
  changed_functions=changed,unchanged_controller_functions=len(oldfn)-len(changed),
  outer_controller_source_unchanged=True,remote_supervisor_pins_and_export_context_unchanged=True,
  actual_new_cleanup_methods=3,inherited_R1_methods=12,old_suites_rerun=False,
  source_dependencies={name:entry['sha256'] for name,entry in pins.items()},
  accepted_boundaries=['owned stdin close attempted before the same child wait, with no kill or retry',
   'close/wait/log/hash/publication failures retained and finalization cleanliness required for terminal qualification',
   'unchanged service flock handoff and both supervisor/worker terminal-zero quiesce qualification',
   'unchanged source-authenticated bind, once mutation and seven-original operator-compatible context export'],
  limitations=['receipt capture failure can still transmit input; receipt_error blocks promotion but does not prove no action occurred',
   'a failed pipe close or wait does not prove the original child ended; unknown intent remains consumed',
   'original request/input intent is durable before Popen; no automatic replay or reconstructed identity',
   'author fake process/material boundaries and unchanged prior context compatibility are not real activation evidence'],
  author_import_entry_or_test_executed=False,device_SSH_USB_build_SDK_Git_used=False,
  actual_activation_or_physical_acceptance=False,
  own_files={name:sha(HERE/name) for name in ['review.py','README.md','r1-stdin-eof-finding.json']})
 (HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=True,review_sha256=sha(HERE/'review-result.json'),controller_sha256=sha(AUTHOR/'controller.py'))))


if __name__=='__main__':main()
