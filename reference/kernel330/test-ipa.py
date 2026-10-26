from pathlib import Path
import copy,json,shutil,subprocess,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera330-wb-built/src/libcamera-v0.7.2';stage=SDK/'private/camss330-contract';stage.mkdir(mode=0o700,exist_ok=True)
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
shutil.copyfile(HERE/'cct-contract.cpp',stage/'contract.cpp')
flags=['-std=c++20','-O0','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+TREE+'/include','-I'+TREE+'/output/include']
links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
q=subprocess.run(['chroot',str(SDK),'g++',*flags,'/private/camss330-contract/contract.cpp',*links,'-o','/private/camss330-contract/contract'],capture_output=True)
(P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
env=['chroot',str(SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base']
rows=[]
for name,item in json.loads((P/'cases-private.json').read_text()).items():
 shutil.copyfile(P/'profiles'/(name+'.yaml'),stage/(name+'.yaml'));m=item['match']
 args=['/private/camss330-contract/contract',TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss330-contract/'+name+'.yaml',item['model'],
  *[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],*[str(v) for pair in item['expected_gains'] for v in pair]]
 q=subprocess.run([*env,*args],capture_output=True,timeout=45)
 (P/('contract-'+name+'.log')).write_bytes(q.stdout+q.stderr)
 rows.append(dict(case=name,exit_code=q.returncode,passed=not q.returncode and b'CCT_CONTRACT_PASS' in q.stdout))
 if not rows[-1]['passed']:print(q.stderr.decode()[-2200:]);break
assert all(r['passed'] for r in rows) and len(rows)==10
# One existing AWB contract covers unchanged legacy operation plus parser rejection.
s=(HERE.parent/'kernel321/ipa-contract.cpp').read_text()
needle='assert(!ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration));'
s=s.replace(needle,'''if(argc==4 && std::string(argv[3])=="reject-wb") {
 assert(ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration)==-EINVAL);
 std::cout<<"WB_REJECT_PASS"<<std::endl;return 0;
 }
 '''+needle)
s=s.replace('assert(controlsInfo.at(&controls::AwbEnable).max().get<bool>());','assert(controlsInfo.at(&controls::AwbEnable).max().get<bool>());\n assert(controlsInfo.find(&controls::ColourTemperature)==controlsInfo.end());')
(stage/'legacy.cpp').write_text(s)
q=subprocess.run(['chroot',str(SDK),'g++',*flags,'/private/camss330-contract/legacy.cpp',*links,'-o','/private/camss330-contract/legacy'],capture_output=True)
(P/'legacy-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
base=yaml.safe_load((HERE.parent/'kernel313/imx319.yaml').read_text())
(stage/'legacy.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
invalid=yaml.safe_load((P/'profiles/sunny_imx319-unit.yaml').read_text());invalid['modes'][0]['white_balance_reference']['calibration']['unit'][0][1]=0.
(stage/'invalid.yaml').write_text(yaml.safe_dump(invalid,sort_keys=False))
disabled=copy.deepcopy(invalid);disabled['modes'][0]['white_balance_reference']['enabled']=False
(stage/'disabled.yaml').write_text(yaml.safe_dump(disabled,sort_keys=False))
for name,extra,marker in [('legacy',[],'AWB_CONTRACT_PASS'),('invalid',['reject-wb'],'WB_REJECT_PASS'),('disabled',[],'AWB_CONTRACT_PASS')]:
 q=subprocess.run([*env,'/private/camss330-contract/legacy',TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so','/private/camss330-contract/'+name+'.yaml',*extra],capture_output=True,timeout=60)
 (P/('contract-'+name+'.log')).write_bytes(q.stdout+q.stderr)
 rows.append(dict(case=name,exit_code=q.returncode,passed=not q.returncode and marker.encode() in q.stdout))
 if not rows[-1]['passed']:print(q.stderr.decode()[-2200:]);break
report=dict(stage=330,actual_aarch64_ipa_dso=True,cases=rows,initial_and_runtime_packets_verified=True,
 applied_sof_metadata_verified=True,arbitrary_manual_gains_clear_cct_metadata=True,automatic_awb_does_not_report_fake_cct=True,
 inverse_cct_and_ccm_pending=True,installed=False,passed=all(r['passed'] for r in rows) and len(rows)==13)
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
