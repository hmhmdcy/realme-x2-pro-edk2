from pathlib import Path
import hashlib,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2';K=T.parents[2]/'source354'
assert subprocess.check_output(['git','-C',str(K),'rev-parse','HEAD'],text=True).strip()=='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3' and not subprocess.check_output(['git','-C',str(K),'status','--porcelain'])
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='efd01b4cf0bbbbf966730c53cf381908408c7a27'
state=json.loads((HERE/'source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
code='''from pathlib import Path
import hashlib,json
d=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),status=json.loads((d/'m2m_status').read_text()),notes={n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();d=json.loads(q.stdout)
assert d['taint']==0 and d['notes']==json.loads((P.parent/'kernel434/runtime-collected-r2/state.json').read_text())['before_notes']
assert not any(d['status'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert d['status']['jobs']==d['status']['completed']==d['status']['direct_completed']
(P/'preflight-stdout-private.json').write_bytes(q.stdout)
r=dict(stage=435,phone_connected=True,boot_guard_matches=True,formal_notes_match=True,taint=0,maintained_sources_match=True,idle_m2m=True,previous_turn_classification='progress:434 physical GTM/banks/SOF and driver reopen fix verified',passed=True)
(HERE/'preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
