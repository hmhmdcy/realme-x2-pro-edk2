from pathlib import Path
import ast,json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
profile=json.loads((HERE/'firmware-context-validation.json').read_text())
tree=ast.parse((HERE/'m2m-worker.py').read_text())
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='run' and n.args and isinstance(n.args[0],ast.List) and 'snapshot_offsets' in ast.unparse(n)]
assert len(calls)==1
args=eval(compile(ast.Expression(calls[0].args[0]),'actual-insmod-args','eval'),dict(ROOT=Path('/fixture'),meta=dict(snapshot_profile=profile)))
assert args[:3]==['insmod','/fixture/test.ko','hold_start_failure=1'] and args[5:]==['enable_m2m=1']
code="""from pathlib import Path
import json
root=Path(ROOT)
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),release=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 transaction_absent=not root.exists(),
 candidates_absent=not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem']),
 vb2_dependencies_present=all(Path('/sys/module',n).exists() for n in ['videobuf2_common','videobuf2_v4l2','videobuf2_memops','videobuf2_vmalloc']),
 m2m_video_absent=not any((p/'name').read_text().strip()=='qcom-ipe-a5' for p in Path('/sys/class/video4linux').glob('video*')),
 firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip(),
 battery={p.name:{n:(p/n).read_text().strip() for n in ['capacity','temp','status'] if (p/n).exists()} for p in Path('/sys/class/power_supply').iterdir() if (p/'type').read_text().strip()=='Battery'})))
""".replace('ROOT',repr('/var/lib/samurai/k386-m2m-'+run))
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=20).stdout)
assert d['taint']==0 and all(d[k] for k in ['transaction_absent','candidates_absent','vb2_dependencies_present','m2m_video_absent','firmware_absent']) and d['camss']=='suspended'
report=dict(stage=386,run=run,guard378_verified=True,actual_m2m_only_worker_parameters_checked=True,**d,passed=True)
(HERE/'runtime-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
