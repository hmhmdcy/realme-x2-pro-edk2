"""Adapt the existing durable temporary-load/restore transaction to requests."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
body=(HERE.parent/'kernel406/runtime-worker-body.py').read_text()
# r2 exposed the missing mandatory callback before any image DMA. Preserve
# that WARN taint; compare against it rather than erasing it or rebooting.
body=body.replace("Path('/proc/sys/kernel/tainted').read_text().strip()=='0'", "int(Path('/proc/sys/kernel/tainted').read_text())==512")
body=body.replace("and not state['taint']", "and state['taint']==512")
body=body.replace("candidate_permanently_installed=False)", "candidate_permanently_installed=False,baseline_taint=512,known_warning_from_failed_runtime_r2=True)")
old="s=m2m();assert not s['jobs'] and not core()['cpu_release_attempted'];p=Path('/sys/module/camss_icp_a5_m2m/parameters/test_ltm_mode')\n if kind=='candidate':assert p.read_text().strip()=='0'\n else:assert not p.exists()"
new="s=m2m();assert not s['jobs'] and not core()['cpu_release_attempted']\n assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_ltm_mode').exists()"
assert old in body;body=body.replace(old,new)
old="launch([str(root/'colour-client'),'/dev/'+nodes[0].name,str(root)],'colour-pixels',timeout=150)"
new="""import fcntl
 media=[]
 for p in Path('/dev').glob('media[0-9]*'):
  fd=os.open(p,os.O_RDWR|os.O_CLOEXEC)
  try:
   info=bytearray(256);fcntl.ioctl(fd,0xc1007c00,info)
   if bytes(info[16:48]).split(b'\\0')[0]==b'SM8150 IPE':media.append(str(p))
  finally:os.close(fd)
 assert len(media)==1
 launch([str(root/'request-client'),'/dev/'+nodes[0].name,media[0],str(root)],'request-pixels',timeout=90)"""
assert old in body;body=body.replace(old,new).replace("'colour-pixels.out'","'request-pixels.out'")
old="assert len(rows)==53 and [(r['width'],r['format'],r['mode']) for r in rows[:52]]==[(w,f,m) for w in [640,650] for f in range(2) for m in range(13)] and rows[-1]['passed']"
new="assert len(rows)==17 and [(r['case'],r['sequence'],r['mode']) for r in rows[:16]]==[(c,s,m) for c in range(2) for s,m in enumerate([0,1,2,2,3,4,0,1])] and rows[-1]['passed']"
assert old in body;body=body.replace(old,new).replace("==52 and s['starts']==s['stops']==52","==16 and s['starts']==s['stops']==2").replace('native-ltm-completed-before-restore','native-request-iq-completed-before-restore')
ast.parse(body);(HERE/'runtime-worker-body.py').write_text(body)
stage=(HERE.parent/'kernel406/stage-runtime-r2.py').read_text()
begin=stage.index("spec=importlib.util.spec_from_file_location('prefix395'")
stage=stage[:stage.index("normal=json.loads")]+"build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and not build['diagnostics']\ncore,adapter=build['modules'][:2]\nassert json.loads((HERE/'params-validation.json').read_text())['passed']\nassert json.loads((HERE/'client-build-validation.json').read_text())['passed']\n"+stage[begin:]
stage=stage.replace('stage=406','stage=417').replace("'stage':406","'stage':417").replace("'test_adapter_only_loaded_privately'","'request_adapter_only_loaded_privately'").replace('test_adapter_only_loaded_privately=True','request_adapter_only_loaded_privately=True')
stage=stage.replace("replace(\"'stage':395\",\"'stage':406\")","replace(\"'stage':395\",\"'stage':417\")")
stage=stage.replace('colour-client','request-client').replace('k406-ltm-r2','k417-request-r4').replace('payload-r2-private','payload-r4-private').replace('staging-validation-r2.json','staging-validation.json')
ast.parse(stage);(HERE/'stage-runtime.py').write_text(stage)
runtime=(HERE.parent/'kernel406/runtime.py').read_text().replace('stage=406','stage=417').replace('k406-ltm-r1','k417-request-r4').replace('colour-client','request-client').replace('runtime-collected-r1','runtime-collected-r4')
runtime=runtime.replace("'collector-result.json']","'collector-result.json']")
ast.parse(runtime);(HERE/'runtime.py').write_text(runtime)
print('Prepared existing durable transaction for the request candidate and normal restoration.')
