"""Summarise existing probe runs and read the final device state, without capture."""
from pathlib import Path
import hashlib,json,re,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent
runs={}
for name in ['r1','r2','r3','r4','r5']:
    observation=json.loads((host.PRIVATE/('probe-'+name+'-observation.json')).read_text())
    state=observation['state'];summary=state.get('summary',{})
    captures=summary.get('captures',{})
    runs[name]=dict(terminal=state['terminal'],phase=state['phase'],worker_live=observation['worker_live'],
        summary_passed=summary.get('passed',False),deployment_restored=summary.get('deployment_restored',False),
        captures=captures,taint=summary.get('taint'),fault_delta=summary.get('fault_delta'),health=summary.get('health'))
    if name in ['r4','r5']:
        log=observation['logs'].get('capture-main-isolated.log','')
        runs[name]['failure_kind']='event_dispatcher_notifier_assertion' if name=='r4' else 'camss_isp_controls_pop_front_reentrancy'
        runs[name]['failure_reproduced']=('iter != notifiers_.end()' in log if name=='r4' else "Assertion '!this->empty()' failed" in log)
threaded=[]
for run in ['r3','r4']:
    for name,item in runs[run]['captures'].items():
        if item['probe_passed'] and not item['isolation_requested']:
            threaded.append(dict(run=run,name=name,**item))
assert len(threaded)==10 and len({item['name'] for item in threaded})==10
assert all(runs[r]['terminal'] and not runs[r]['worker_live'] and runs[r]['deployment_restored'] for r in runs)
report=dict(stage=361,threaded_factory_contexts=threaded,threaded_factory_context_count=10,physical_sensors=4,
    threaded_frames=sum(item['frames'] for item in threaded),physical_modes=5,runs=runs,isolated_path_passed=False,patched_base_isolated_path_passed=False,
    optical_case_executed=False,absolute_optical_calibration_verified=False,installed=False,
    dispatcher_fix_aarch64_regression_passed=True,full_candidate_validation_passed=False,
    note='r4 contains nine completed threaded cases but its whole transaction failed. r5 uses fixed base and exposes a second CAMSS queue reentrancy error. No later cases were run.')
(HERE/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
code=r'''
from pathlib import Path
import hashlib,json,subprocess
services={}
workers=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':continue
  comm=(p/'comm').read_text().strip()
  if comm in ['pipewire','wireplumber']:services.setdefault(comm,[]).append(dict(pid=int(p.name),uid=p.stat().st_uid))
  cmd=(p/'cmdline').read_bytes()
  if any(a.startswith(b'/var/lib/samurai/k361-request-') and a.endswith(b'/worker.py') for a in cmd.split(b'\0')):workers.append(int(p.name))
 except OSError:pass
database={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if 'P' in fields and 'V' in fields:database[fields['P']]=fields['V']
packages={n:database[n] for n in ['libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']}
facts=dict(kernel=subprocess.check_output(['uname','-r'],text=True).strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 original_boot_guard_matches=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k360-recovered/boot-id-private.txt').read_bytes(),
 camss_build_note_sha256=hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
 services=services,workers=workers,installed_packages=packages,
 platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 icp_experiment_modules=[p.name for p in Path('/sys/module').glob('*icp*')],
 orphan_icp_firmware_present=Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists())
print(json.dumps(facts))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=30)
facts=json.loads(q.stdout)
facts.update(stage=361,ssh='strict_original_key_usb',capture_performed=False)
facts['passed']=(facts['original_boot_guard_matches'] and facts['taint']==0 and not facts['workers'] and
    facts['camss_build_note_sha256']=='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297' and
    all(v=='suspended' for v in facts['platforms'].values()) and
    all(len(facts['services'].get(n,[]))==1 and facts['services'][n][0]['uid']==10000 for n in ['pipewire','wireplumber']) and
    not facts['icp_experiment_modules'] and not facts['orphan_icp_firmware_present'] and
    all(v.endswith('-r27') if n.startswith('libcamera') else v.endswith('-r22') for n,v in facts['installed_packages'].items()))
(HERE/'closeout-device-validation.json').write_text(json.dumps(facts,indent=2)+'\n')
print(json.dumps(dict(threaded_contexts=10,isolated_passed=False,device=facts),indent=2));assert facts['passed']
