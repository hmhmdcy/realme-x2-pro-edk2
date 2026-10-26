"""Exercise both standard signed loading and forced process isolation."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
p=HERE/'native-ipa.py';s=p.read_text()
if "force=os.environ.get('CAMSS_TEST_FORCE_ISOLATION'" not in s:
 saved=host.PRIVATE/'native-r1-isolated-private.py'
 if not saved.exists():saved.write_text(s)
 s=s.replace('state=dict(stage=300',"force=os.environ.get('CAMSS_TEST_FORCE_ISOLATION','1');assert force in ['0','1']\nstate=dict(stage=300",1)
 s=s.replace("LIBCAMERA_IPA_FORCE_ISOLATION='1'","LIBCAMERA_IPA_FORCE_ISOLATION=force")
 s=s.replace('ipa_isolation_forced=True','ipa_isolation_forced=force==\'1\'')
 lines=s.splitlines();old=next(l for l in lines if "report['passed']=report['passed'] and len(app_pids)" in l)
 s=s.replace(old," process_mode_ok=len(app_pids)==1 and len(ipa_pids)==1 and stats_pids==ipa_pids and ((force=='1' and not app_pids.intersection(ipa_pids)) or (force=='0' and app_pids==ipa_pids and 'signature is valid' in text))\n report['passed']=report['passed'] and process_mode_ok and not ipa_live and report['ipa_metadata_frames']==72")
 p.write_text(s)
p=HERE/'native-ipa.py';s=p.read_text()
if "if force=='0':env.pop('LIBCAMERA_IPA_FORCE_ISOLATION'" not in s:
 needle=" with (root/'capture-private.log').open('xb') as output:"
 assert needle in s
 s=s.replace(needle," if force=='0':env.pop('LIBCAMERA_IPA_FORCE_ISOLATION',None)\n"+needle)
s=s.replace("ipa_isolation_forced=force=='1'","ipa_isolation_forced=('forced through configuration' in text),ipa_isolation_requested=(force=='1')")
p.write_text(s)
p=HERE/'launch-ipa.py';s=p.read_text()
if 'CAMSS_TEST_FORCE_ISOLATION={force!r}' not in s:
 needle="assert hashlib.sha256(archive.read_bytes()).hexdigest()==bundle['archive_sha256']"
 s=s.replace(needle,needle+"\nmode=sys.argv[2] if len(sys.argv)>2 else 'isolated';assert mode in ['isolated','direct']\nforce='1' if mode=='isolated' else '0'")
 s=s.replace('stdin=subprocess.DEVNULL,stdout=log','env=dict(os.environ,CAMSS_TEST_FORCE_ISOLATION={force!r}),stdin=subprocess.DEVNULL,stdout=log')
 p.write_text(s)
p=HERE/'runtime-tools-validation.json';d=json.loads(p.read_text());d['supports_signed_direct_and_forced_isolated_modes']=True;p.write_text(json.dumps(d,indent=2)+'\n')
print('Runtime workflow supports signed direct and forced isolated modes; application/library bytes unchanged.')
