from pathlib import Path
import hashlib,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2'
for row in json.loads((HERE/'source-state.json').read_text())['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
code='''from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai/k439-front-colour-r1');manifest=json.loads((root/'manifest.json').read_text());state=json.loads((root/'state.json').read_text());assert state['passed'] and state['terminal']
names=['factory-imx471-private.yaml','lib/libcamera.so.0.7.2','ipa/ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign','proxy/camss_ipa_proxy','tone-replay']
actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names};assert all(actual[n]==manifest[n] for n in names)
notes={n:hashlib.sha256(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes()).hexdigest() for n in state['before_notes']};assert notes==state['before_notes']
status=json.loads(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status').read_text());assert not any(status[k] for k in ['users','running','failed','cancelled','first_error','fatal','pinned','orphans'])
assert int(Path('/proc/sys/kernel/tainted').read_text())==0
print(json.dumps(dict(actual=actual,formal_notes_match=True,taint=0,idle=True)))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);q.check_returncode();actual=json.loads(q.stdout)
for name in ['factory-imx471-private.yaml','tone-replay']:assert actual['actual'][name]==hashlib.sha256((P/name).read_bytes()).hexdigest()
build=json.loads((HERE/'build-validation.json').read_text())
for row in build['runtime_files']:
 key=('lib/' if row['name'].startswith('libcamera') else 'proxy/' if row['name']=='camss_ipa_proxy' else 'ipa/')+row['name'];assert actual['actual'][key]==row['sha256']
(P/'actual-runtime-manifest-private.json').write_text(json.dumps(actual,indent=2)+'\n')
result={'stage':439,'passed':True,'actual_runtime_profile_library_ipa_signature_proxy_and_replay_match':True,'source_cohort_matches':True,'formal_notes_restored_and_idle':True,'taint':0,'phone_worker_terminal':True,'installed':False,'full_goal_complete':False}
(HERE/'current-state-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
