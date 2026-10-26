"""Save and replay only the generic IPA/caller delta from422."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess,tempfile
import storage,host
HERE=Path(__file__).resolve().parent;candidate=storage.candidate();tree=candidate/'src/libcamera-v0.7.2';old=candidate.parent/'libcamera422-tmc-ltm/src/libcamera-v0.7.2'
names=['include/libcamera/ipa/camss.mojom','src/ipa/camss-vfe/meson.build','src/ipa/camss-vfe/camss.cpp',
 'src/ipa/camss-vfe/ipe_tone_profile.h','src/ipa/camss-vfe/ipe_tone_profile.cpp','src/ipa/libipa/gamma_segments.h','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
patch='';rows=[]
for n in names:
 before=(old/n).read_text() if (old/n).exists() else '';after=(tree/n).read_text()
 patch+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n if before else '/dev/null',tofile='b/'+n))
 rows.append(dict(path=n,sha256=hashlib.sha256((tree/n).read_bytes()).hexdigest()))
 if Path(n).name in ['ipe_tone_profile.cpp','ipe_tone_profile.h']:assert (HERE/Path(n).name).read_bytes()==(tree/n).read_bytes()
(HERE/'0044-camss-ipa-request-tone-history.patch').write_text(patch)
with tempfile.TemporaryDirectory(dir=candidate.parent/'tmp',prefix='k423-patch-') as folder:
 replay=Path(folder)
 for n in names:
  if (old/n).exists():p=replay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,p)
 q=subprocess.run(['patch','-p1','--fuzz=0','--batch'],cwd=replay,input=patch.encode(),capture_output=True)
 (host.PRIVATE/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.stdout+q.stderr).decode()
 for n in names:assert (replay/n).read_bytes()==(tree/n).read_bytes(),n
q=subprocess.run(['aarch64-linux-gnu-nm','-C',str(host.PRIVATE/'ipa_camss_vfe.so')],capture_output=True,check=True)
symbols=q.stdout.decode();required=['IpeToneProfile::calculate','generateTmc11Curve','prepareLtm13Frame','IPACamss::prepareIpeParameters']
assert all(n in symbols for n in required)
r=dict(stage=423,base_stage=422,files=len(names),zero_fuzz_replayed=True,source_hashes=rows,actual_numeric_symbols_linked_in_ipa=True,private_ipa_version=3,kernel_uapi_version=1,typed_frame_bytes=6008,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='source_hashes'},indent=2))
