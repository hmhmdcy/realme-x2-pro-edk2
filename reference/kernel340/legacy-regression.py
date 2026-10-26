"""Check changed transaction scheduling with retained reference CCM/LSC cases."""
from pathlib import Path
import json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2';relative=Path('/private/camss340-contract');stage=storage.SDK/str(relative).lstrip('/');rows=[]
with storage.sdk_candidate():
 shutil.copyfile(HERE.parent/'kernel335/ccm-contract.cpp',stage/'reference.cpp')
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include'];links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
 q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'reference.cpp'),*links,'-o',str(relative/'reference')],capture_output=True);(P/'reference-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 base=P.parent/'kernel335';name='sunny_imx319-unit';item=json.loads((base/'cases-private.json').read_text())[name];m=item['match']
 for path,target in [(base/'profiles'/(name+'.yaml'),stage/'reference.yaml'),(base/'profiles'/(name+'-oracle-private.bin'),stage/'reference-private.bin'),(base/'manual-oracle-private.bin',stage/'manual-private.bin'),(storage.SDK/'private/camss335-contract/combined.yaml',stage/'combined.yaml')]:shutil.copyfile(path,target)
 for profile,mode in [('reference',1),('combined',2)]:
  args=[str(relative/(profile+'.yaml')),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(relative/'reference-private.bin'),str(relative/'manual-private.bin'),str(mode)]
  q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',str(relative/'reference'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',*args],capture_output=True)
  (P/(profile+'-regression.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode and b'CCM_CONTRACT_PASS' in q.stdout,(profile,q.stderr.decode()[-2000:]);rows.append(dict(case=profile,passed=True))
(HERE/'reference-regression-validation.json').write_text(json.dumps(dict(stage=340,unchanged335_contract_reused=True,reference_ccm_manual_cct_priority_and_optional_lsc=True,cases=rows,passed=True),indent=2)+'\n');print(json.dumps(rows))
