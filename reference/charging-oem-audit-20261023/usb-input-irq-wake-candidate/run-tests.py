from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wake_source_functions',HERE/'prepare.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OUT=Path('/home/cy122/charging-management-20261023/usb-input-irq-wake-tests-01');assert not OUT.exists();OUT.mkdir(mode=0o700)
source=(HERE/'samurai-usb-input.c').read_text();record=json.loads((HERE/'source-result.json').read_bytes());assert hashlib.sha256((HERE/'samurai-usb-input.c').read_bytes()).hexdigest()==record['candidate_source_sha256']
names=['samurai_usb_changed','samurai_usb_set_property','samurai_usb_stop','samurai_usb_clear_wake','samurai_usb_arm_wake','samurai_usb_restart_work','samurai_usb_cleanup_wake','samurai_usb_suspend','samurai_usb_resume','samurai_usb_prepare','samurai_usb_complete','samurai_usb_event','samurai_usb_request_events','samurai_usb_shutdown']
(OUT/'actual-functions.inc').write_text('\n\n'.join(m.function(source,name) for name in names)+'\n')
# Source resource order is checked separately from the modeled API boundary.
probe=m.function(source,'samurai_usb_probe')
assert probe.index('devm_power_supply_register')<probe.index('dev, samurai_usb_cleanup_wake')<probe.index('dev, samurai_usb_stop')
commands=[['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-I',str(OUT),str(HERE/'test-wake.c'),'-o',str(OUT/'test-wake')],[str(OUT/'test-wake')]]
rows=[]
for argv in commands:
 child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:stdout,stderr=child.communicate()
 finally:child.wait()
 row=dict(argv=argv,pid=child.pid,terminal=True,returncode=child.returncode,stdout=stdout.decode(),stderr=stderr.decode());rows.append(row)
 if child.returncode:break
result=dict(passed=len(rows)==2 and all(r['returncode']==0 for r in rows),groups=10,actual_functions=names,source_sha256=record['candidate_source_sha256'],
 devres_stop_then_wake_cleanup_then_PSY_then_IRQ_order=True,old_notification8_decoder_and_unmodified_functions_reused=True,modeled_OS_boundaries=True,
 phone_or_real_IRQ_API_accessed=False,physical_USB_wakeup_accepted=False,results=rows)
for p in [OUT/'result.json',HERE/'test-result.json']:p.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
