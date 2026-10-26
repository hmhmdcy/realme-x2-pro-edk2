"""Revalidate maintained source and the connected phone before module work."""
from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage434preflight',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354'
expected=json.loads((HERE/'source-state.json').read_text())['commit'] if (HERE/'source-state.json').exists() else '04f8c5a3c815e2fa4244564da108227561a0321b'
assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==expected and not subprocess.check_output(['git','-C',str(kernel),'status','--porcelain'])
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='b2f3b25a20c76f794bd7000434ef6b175bc7e6a4'
code='''from pathlib import Path
import hashlib,json,subprocess
d=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(release=subprocess.check_output(['uname','-r'],text=True).strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),status=json.loads((d/'m2m_status').read_text()),notes={n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in ['qcom_camss','camss_icp_a5_m2m','qcom_camss_icp_a5_core']})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);(P/'preflight-stdout-private.json').write_bytes(q.stdout);(P/'preflight-stderr-private.log').write_bytes(q.stderr);q.check_returncode();d=json.loads(q.stdout)
normal=json.loads((P.parent/'kernel429/runtime-collected-r3/state.json').read_text())['before_notes'];assert d['notes']==normal and d['taint']==0
assert not any(d['status'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert d['status']['jobs']==d['status']['completed']==d['status']['direct_completed']
r=dict(stage=434,phone_connected=True,guard_matches=True,formal_module_notes_match=True,taint=d['taint'],idle_m2m=True,maintained_kernel_clean=True,last_goal_turn_classification='progress:433 GTM typed upload, serialized PIX ACK and SOF snapshots implemented and built; hardware pending',passed=True)
(HERE/'preflight-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
