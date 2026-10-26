from pathlib import Path
import copy,json,shutil,subprocess,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera332-cct-built/src/libcamera-v0.7.2';relative=Path('/private/camss332-contract');stage=SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True)
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
flags=['-std=c++20','-O0','-ffp-contract=off','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+TREE+'/include','-I'+TREE+'/output/include']
links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
def build(name,source,extra=[]):
 shutil.copyfile(source,stage/(name+'.cpp'))
 q=subprocess.run(['chroot',str(SDK),'g++',*flags,str(relative/(name+'.cpp')),*extra,*links,'-o',str(relative/name)],capture_output=True)
 (P/(name+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
env=['chroot',str(SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base'];rows=[]
def run(name,exe,args,marker):
 q=subprocess.run([*env,str(relative/exe),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',*args],capture_output=True,timeout=60)
 (P/('contract-'+name+'.log')).write_bytes(q.stdout+q.stderr)
 row=dict(case=name,exit_code=q.returncode,passed=not q.returncode and marker.encode() in q.stdout);rows.append(row)
 assert row['passed'],(name,q.stderr.decode()[-2500:])
build('contract',HERE/'cct-contract.cpp')
cases=json.loads((P/'cases-private.json').read_text())
for name,item in cases.items():
 shutil.copyfile(P/'profiles'/(name+'.yaml'),stage/(name+'.yaml'));m=item['match']
 args=[str(relative/(name+'.yaml')),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],*[str(v) for pair in item['expected_gains'] for v in pair],str(item['expected_manual_gain_cct'])]
 run(name,'contract',args,'CCT_CONTRACT_PASS')
# Preserve compatibility of the330 profile without inverse reference points.
name='sunny_imx319-unit';item=cases[name];m=item['match']
shutil.copyfile(P.parent/'kernel330/profiles'/(name+'.yaml'),stage/'forward-only.yaml')
build('forward',HERE.parent/'kernel330/cct-contract.cpp')
run('forward-only','forward',[str(relative/'forward-only.yaml'),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],*[str(v) for pair in item['expected_gains'] for v in pair]],'CCT_CONTRACT_PASS')
# New parser rejection and disabled/no-reference legacy behaviour.
s=(HERE.parent/'kernel321/ipa-contract.cpp').read_text();needle='assert(!ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration));'
s=s.replace(needle,'''if(argc==4 && std::string(argv[3])=="reject-wb") {
 assert(ipa->configure(info,info.outputSize,sensor,argv[2],&controlsInfo,&configuration)==-EINVAL);
 std::cout<<"WB_REJECT_PASS"<<std::endl;return 0;
 }
 '''+needle)
s=s.replace('assert(controlsInfo.at(&controls::AwbEnable).max().get<bool>());','assert(controlsInfo.at(&controls::AwbEnable).max().get<bool>());\n assert(controlsInfo.find(&controls::ColourTemperature)==controlsInfo.end());')
(HERE/'legacy-contract.cpp').write_text(s);build('legacy',HERE/'legacy-contract.cpp')
base=yaml.safe_load((HERE.parent/'kernel313/imx319.yaml').read_text());(stage/'legacy.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
invalid=yaml.safe_load((P/'profiles/sunny_imx319-unit.yaml').read_text());invalid['modes'][0]['white_balance_reference']['reference_points'][0][0]=0.
(stage/'invalid.yaml').write_text(yaml.safe_dump(invalid,sort_keys=False));disabled=copy.deepcopy(invalid);disabled['modes'][0]['white_balance_reference']['enabled']=False
(stage/'disabled.yaml').write_text(yaml.safe_dump(disabled,sort_keys=False))
for name,extra,marker in [('legacy',[],'AWB_CONTRACT_PASS'),('invalid',['reject-wb'],'WB_REJECT_PASS'),('disabled',[],'AWB_CONTRACT_PASS')]:run(name,'legacy',[str(relative/(name+'.yaml')),*extra],marker)
# Actual synthetic RGB feedback updates with delayed acknowledgements.
(stage/'libipa').mkdir(exist_ok=True)
for n in ['awb_colour_temperature.cpp','awb_colour_temperature.h','awb_calibration.h']:shutil.copyfile(HERE.parent/'kernel331/libipa'/n,stage/'libipa'/n)
build('dynamic',HERE/'dynamic-contract.cpp',[str(relative/'libipa/awb_colour_temperature.cpp')])
shutil.copyfile(P/'sunny_imx319-unit-points-private.bin',stage/'points-private.bin')
run('dynamic-awb','dynamic',[str(relative/'sunny_imx319-unit.yaml'),str(relative/'points-private.bin')],'AWB_INVERSE_CONTRACT_PASS')
report=dict(stage=332,actual_aarch64_ipa_dso=True,cases=rows,applied_sof_estimated_cct_verified=True,manual_gains_estimated_cct_verified=True,
 synthetic_awb_feedback_estimated_cct_verified=True,legacy_without_reference_points_preserved=True,ccm_pending=True,installed=False,passed=len(rows)==15 and all(r['passed'] for r in rows))
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
