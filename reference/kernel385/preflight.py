from pathlib import Path
import ast,json,shlex,sys,re
import host
HERE=Path(__file__).resolve().parent
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
case=sys.argv[2] if len(sys.argv)>2 else 'small';image=json.loads((HERE/'image-cases.json').read_text())[case]
profile=json.loads((HERE/'firmware-context-validation.json').read_text());assert profile['passed'] and 0<len(profile['windows'])<=4
tree=ast.parse((HERE/'boot-worker.py').read_text());calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='run' and node.args and isinstance(node.args[0],ast.List) and 'snapshot_offsets' in ast.unparse(node)]
assert len(calls)==1
args=eval(compile(ast.Expression(calls[0].args[0]),'actual-insmod-arguments','eval'),dict(ROOT=Path('/fixture'),image_case=image,meta=dict(snapshot_profile=profile,image_test=image)))
assert args[:3]==['insmod','/fixture/test.ko','hold_start_failure=1']
assert args[5]=='enable_frame=1'
assert args[6:]==['test_'+k+'='+str(int(image[k]) if k=='uv_swap' else image[k]) for k in ['width','height','port','cores','frames','uv_swap']]
assert args[3]=='snapshot_offsets='+','.join(str(w['offset']) for w in profile['windows']) and args[4]=='snapshot_words='+','.join(str(w['words']) for w in profile['windows'])
code='''from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),release=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 transaction_absent=not Path('/var/lib/samurai/k385-boot-r1').exists(),core_absent=not Path('/sys/module/qcom_camss_icp_a5_core').exists(),
 test_absent=not Path('/sys/module/camss_icp_a5_boot_test').exists(),firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 extra_firmware_absent=not any(Path('/lib/firmware/qcom/sm8150',name).exists() for name in ['samurai-ipe382-stripe.bin']),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),
 battery={p.name:{n:(p/n).read_text().strip() for n in ['capacity','temp','status'] if (p/n).exists()} for p in Path('/sys/class/power_supply').iterdir() if (p/'type').read_text().strip()=='Battery'})))
'''
code=code.replace('/var/lib/samurai/k385-boot-r1','/var/lib/samurai/k385-boot-'+run)
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and d['transaction_absent'] and d['core_absent'] and d['test_absent'] and d['firmware_absent'] and d['extra_firmware_absent'] and d['camss']=='suspended'
report=dict(stage=385,run=run,image_case=image,current378_guard_verified=True,actual_worker_parameter_expression_checked=True,observer_ranges=4,observer_words=sum(w['words'] for w in profile['windows']),**d,passed=True)
(HERE/'runtime-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
