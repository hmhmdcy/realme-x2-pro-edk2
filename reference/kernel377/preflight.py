from pathlib import Path
import ast,json,shlex
import host
HERE=Path(__file__).resolve().parent
profile=json.loads((HERE/'firmware-context-validation.json').read_text());assert profile['passed'] and 0<len(profile['windows'])<=4
tree=ast.parse((HERE/'boot-worker.py').read_text());calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='run' and node.args and isinstance(node.args[0],ast.List) and 'snapshot_offsets' in ast.unparse(node)]
assert len(calls)==1
args=eval(compile(ast.Expression(calls[0].args[0]),'actual-insmod-arguments','eval'),dict(ROOT=Path('/fixture'),meta=dict(snapshot_profile=profile)))
assert args[:3]==['insmod','/fixture/test.ko','hold_start_failure=1']
assert args[3]=='snapshot_offsets='+','.join(str(w['offset']) for w in profile['windows']) and args[4]=='snapshot_words='+','.join(str(w['words']) for w in profile['windows'])
code='''from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),release=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 transaction_absent=not Path('/var/lib/samurai/k377-boot-r1').exists(),core_absent=not Path('/sys/module/qcom_camss_icp_a5_core').exists(),
 test_absent=not Path('/sys/module/camss_icp_a5_boot_test').exists(),firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip())))
'''
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and d['transaction_absent'] and d['core_absent'] and d['test_absent'] and d['firmware_absent'] and d['camss']=='suspended'
report=dict(stage=377,current374_guard_verified=True,actual_worker_parameter_expression_checked=True,observer_ranges=4,observer_words=sum(w['words'] for w in profile['windows']),**d,passed=True)
(HERE/'runtime-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
