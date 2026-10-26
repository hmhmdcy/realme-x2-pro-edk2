"""Only read/hash/AST binding of an already statically reviewed frozen leaf."""
from pathlib import Path
import ast
import hashlib
import json
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
AUTHOR=REF/'charging-oem-audit-20261023/irq-cohort-adoption-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def main():
 assert not sys.flags.optimize
 assert not (HERE/'review-result.json').exists(),'Frozen review exists'
 assert sha(AUTHOR/'delivery.json')=='d5946973156dd800d1028ccb740828c87cd82c763ec6c48064f35c036bd40e14'
 delivery=read(AUTHOR/'delivery.json')
 assert delivery['passed'] is True and delivery['frozen'] is True and len(delivery['files'])==8
 for name,entry in delivery['files'].items():
  assert sha(AUTHOR/name)==entry['sha256'] and (AUTHOR/name).stat().st_size==entry['bytes'],name
  if name.endswith('.py') or name.endswith('.inc'):ast.parse((AUTHOR/name).read_bytes())
 pins=read(AUTHOR/'source-pins.json')
 assert pins==delivery['source_inputs']
 for name,entry in pins.items():assert sha(REF/entry['path'])==entry['sha256'],name
 assert pins['host_delivery']['sha256']=='8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'
 assert pins['host']['sha256']=='58d0cbf0dd4ec2db29725bdfd2b01467cbe04c4401b1ca411960438e66dca6e7'
 assert pins['device']['sha256']=='78337b7801b21e120f7814a2f8857e52dc1056ef80364821a6507d5faf2a444d'
 assert pins['operator_delivery']['sha256']=='ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41'
 tests=read(AUTHOR/'test-result.json')
 assert tests['passed'] is True and tests['new_cases']==20 and len(tests['cases'])==20
 assert all(row['passed'] is True for row in tests['cases'])
 assert tests['prior_host_device_operator_suites_rerun'] is False
 default=read(AUTHOR/'default-result.json')
 assert default['passed'] is True and len(default['results'])==2
 normal,optimized=default['results']
 assert normal['terminal'] is True and normal['returncode']==0 and '-O' not in normal['argv']
 assert optimized['terminal'] is True and optimized['returncode']==1 and '-O' in optimized['argv']
 assert 'optimized interpreter is unsupported' in optimized['stderr']
 tailtree=ast.parse((AUTHOR/'adopt-device-tail.inc').read_bytes())
 assert len([node for node in tailtree.body if isinstance(node,ast.FunctionDef)])==1
 assert len([node for node in tailtree.body if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call)])==1
 reused={'postboot_host_R2':HERE.parent/'irq-cohort-postboot-host-independent-review/review-result.json',
         'boot_operator_completion':HERE.parent/'usb-irq-protection-fastboot-independent-review/review-result.json'}
 assert all(read(path)['passed'] is True for path in reused.values())
 result=dict(schema=1,passed=True,new_blockers=[],
  author_delivery_sha256=sha(AUTHOR/'delivery.json'),adopt_source_sha256=sha(AUTHOR/'adopt.py'),
  remote_tail_sha256=sha(AUTHOR/'adopt-device-tail.inc'),new_author_cases=20,
  reused_independent_review_sha256={name:sha(path) for name,path in reused.items()},
  source_inputs=pins,
  accepted_boundaries=['actual host R2 completion/stage/input/whole raw audit before descriptor',
   'exact #502 new UUID and IRQ boot/logdump/manifest, original authenticated request object and output digest',
   'fresh collector audit before unique proof-then-guard fsync/readback; existing/partial directory refuses reuse',
   'owned original SSH child, requested and interop observed argv separately retained, input SHA and same-child EOF/wait',
   'known original #502 pointer plus retained byte comparisons before atomic replacement; old guards/pointer backup remain'],
  limitations=['canonical postboot request-object SHA is not a separate JSON original-format hash',
   'pointer publication requires exclusive owner window and is not a general atomic CAS',
   'unknown after remote guard or pointer write is retained, never automatically retried',
   'author host/device IO boundaries are fake; no actual future materials or device acceptance are established'],
  author_import_entry_or_test_executed=False,device_SSH_USB_build_SDK_Git_used=False,
  physical_delivery_or_latency_accepted=False,
  own_files={name:sha(HERE/name) for name in ['review.py','README.md']})
 (HERE/'review-result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(passed=True,review_sha256=sha(HERE/'review-result.json'),adopt_sha256=sha(AUTHOR/'adopt.py'))))


if __name__=='__main__':main()
