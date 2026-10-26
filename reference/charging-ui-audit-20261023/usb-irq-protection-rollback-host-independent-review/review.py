"""Read/AST/hash only. Never import author or run its entry/tests."""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
AUTHOR=REF/'charging-oem-audit-20261023/usb-irq-protection-rollback-host-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def body_map(path,cls=None):
 text=path.read_text();tree=ast.parse(text)
 nodes=tree.body if cls is None else next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls).body
 return {node.name:ast.get_source_segment(text,node) for node in nodes if isinstance(node,ast.FunctionDef)}


def main():
 assert not sys.flags.optimize and not (HERE/'review-result.json').exists()
 assert sha(AUTHOR/'delivery.json')=='c8f53b5704cd73e601c7653a2b56372566e2f186bc877f558e64e2b6b3653745'
 delivery=read(AUTHOR/'delivery.json');assert delivery['passed'] is True and delivery['frozen'] is True
 assert delivery['connected_owner_implemented'] is False
 for name,entry in delivery['files'].items():
  assert sha(AUTHOR/name)==entry['sha256'] and (AUTHOR/name).stat().st_size==entry['bytes'],name
  if name.endswith('.py'):ast.parse((AUTHOR/name).read_bytes())
 test=read(AUTHOR/'test-result.json');assert test['passed'] is True and test['count']==len(test['cases'])==12
 assert test['old_21_6_20_suites_rerun'] is False
 for name,digest in test['files'].items():assert sha(AUTHOR/name)==digest
 local=read(AUTHOR/'local-checks.json');assert local['passed'] is True and len(local['commands'])==2
 assert all(row['terminal'] is True and row['returncode']==0 for row in local['commands'])
 pins=read(AUTHOR/'source-pins.json')
 for entry in pins.values():assert sha(Path(entry['path']))==entry['sha256']
 assert pins['worker']['sha256']=='f0767ce2506f500b5893ddfdf28f7aa7d7a4d0930ccde092970170f1b7fa4142'
 assert pins['saved_proof']['sha256']=='3c16d34bbf6d1454d1a3dc09bc03815f3be9dceafd23c8720bb3ff32cc810092'
 assert pins['auth_host']['sha256']=='58d0cbf0dd4ec2db29725bdfd2b01467cbe04c4401b1ca411960438e66dca6e7'
 assert pins['payload']['sha256']=='5ecae1f5799a1c01d132553b1ad4fb5923d643d1e13fcde8007f5380253fa339'
 assert Path(pins['payload']['path']).stat().st_size==44194
 reuse=read(AUTHOR/'probe-reuse.json');worker=Path(pins['worker']['path'])
 assert sha(worker)==reuse['source_sha256'] and sha(AUTHOR/'current-probe.py')==reuse['probe_sha256']
 wf,pf=body_map(worker),body_map(AUTHOR/'current-probe.py')
 wm,pm=body_map(worker,'Device'),body_map(AUTHOR/'current-probe.py','Probe')
 assert len(reuse['actual_unchanged_functions'])==6
 for name,digest in reuse['actual_unchanged_functions'].items():
  if name.startswith('Probe.'):key=name.split('.',1)[1];original,current=wm[key],pm[key]
  else:original,current=wf[name],pf[name]
  assert original==current and hashlib.sha256(current.encode()).hexdigest()==digest,name
 contract=read(AUTHOR/'contract.json')
 assert contract['connected_launch_status_fetch_supervisor_implemented'] is False
 assert contract['runtime_request_guard_lease_or_endpoint_capture_created'] is False
 result=dict(schema=1,passed=True,new_blockers=[],author_delivery_sha256=sha(AUTHOR/'delivery.json'),
  binder_sha256=sha(AUTHOR/'bind.py'),current_probe_sha256=sha(AUTHOR/'current-probe.py'),
  actual_unchanged_readonly_bodies=6,author_new_cases=12,author_default_entries_terminal0=2,
  source_dependencies={name:entry['sha256'] for name,entry in pins.items()},
  accepted_boundaries=['frozen saved source/profile authentication before constructing probe input',
   'reused original-key R2 same-Popen/double-stdin/terminal/output proof',
   'before/current/after current identity around complete carriers and actual live module notes',
   'actual worker profile/unpack validation and all-evidence-before-mkdir binder',
   'current identity comes only from actual saved probe; old pointer is not a current identity source'],
  limitations=['probe/request adapter only; connected launch/status/fetch/supervisor and real lease are not implemented',
   'saved probe is not continuing freshness or stopping authorization; future worker must recheck all live gates',
   'author existing saved-source/action authentication boundaries are fake in synthetic positive fixtures',
   'no actual runtime request, guard, lease, endpoint, device recovery or physical acceptance'],
  old_suites_rerun=False,author_import_entry_or_tests_executed=False,
  device_SSH_USB_build_SDK_Git_used=False,
  own_files={name:sha(HERE/name) for name in ['review.py','README.md']})
 (HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=True,review_sha256=sha(HERE/'review-result.json'),binder_sha256=sha(AUTHOR/'bind.py'))))


if __name__=='__main__':main()
