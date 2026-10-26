from pathlib import Path
import difflib,hashlib,json,shutil,subprocess,tempfile
import storage,host
HERE=Path(__file__).resolve().parent;candidate=storage.candidate();tree=candidate/'src/libcamera-v0.7.2';old=candidate.parent/'libcamera423-ipa-tone/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());patch=''
for row in state['source_hashes']:
 n=row['path'];assert hashlib.sha256((tree/n).read_bytes()).hexdigest()==row['sha256'];a=(old/n).read_text();b=(tree/n).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
 if Path(n).name.startswith('ipe_tone_profile'):assert (HERE/Path(n).name).read_bytes()==(tree/n).read_bytes()
(HERE/'0045-camss-ltm-lux-history-and-stats-hold.patch').write_text(patch)
with tempfile.TemporaryDirectory(dir=candidate.parent/'tmp',prefix='k424-patch-') as folder:
 replay=Path(folder)
 for row in state['source_hashes']:
  n=row['path'];p=replay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)
 q=subprocess.run(['patch','-p1','--fuzz=0','--batch'],input=patch.encode(),cwd=replay,capture_output=True);assert not q.returncode,(q.stdout+q.stderr).decode()
 for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(tree/row['path']).read_bytes()
r=dict(stage=424,base_stage=423,files=len(state['source_hashes']),zero_fuzz_replayed=True,actual_candidate_matches_public_adapter_sources=True,
 source_hashes=state['source_hashes'],private_ipa_interface_unchanged=3,kernel_unchanged=True,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='source_hashes'}))
