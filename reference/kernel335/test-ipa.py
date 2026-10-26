from pathlib import Path
import copy,json,shutil,subprocess,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera335-ccm-built/src/libcamera-v0.7.2';relative=Path('/private/camss335-contract');stage=SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True)
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
flags=['-std=c++20','-O0','-ffp-contract=off','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+TREE+'/include','-I'+TREE+'/output/include']
links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
def build(name,source,extra=[]):
 shutil.copyfile(source,stage/(name+'.cpp'));q=subprocess.run(['chroot',str(SDK),'g++',*flags,str(relative/(name+'.cpp')),*extra,*links,'-o',str(relative/name)],capture_output=True)
 (P/(name+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
env=['chroot',str(SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base'];rows=[]
def run(name,exe,args,marker):
 q=subprocess.run([*env,str(relative/exe),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',*args],capture_output=True,timeout=90)
 (P/('contract-'+name+'.log')).write_bytes(q.stdout+q.stderr);row=dict(case=name,exit_code=q.returncode,passed=not q.returncode and marker.encode() in q.stdout);rows.append(row)
 assert row['passed'],(name,q.stderr.decode()[-3000:])
build('contract',HERE/'ccm-contract.cpp');cases=json.loads((P/'cases-private.json').read_text())
shutil.copyfile(P/'manual-oracle-private.bin',stage/'manual-private.bin')
def arguments(name,item,profile=None,mode=None):
 m=item['match'];return [str(relative/(profile or name+'.yaml')),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(relative/(name+'-oracle-private.bin')),str(relative/'manual-private.bin'),str(int(item['ccm_enabled']) if mode is None else mode)]
for name,item in cases.items():
 for suffix in ['.yaml','-oracle-private.bin']:shutil.copyfile(P/'profiles'/(name+suffix),stage/(name+suffix))
 run(name,'contract',arguments(name,item),'CCM_CONTRACT_PASS')
name='sunny_imx319-unit';item=cases[name];base=yaml.safe_load((P/'profiles'/(name+'.yaml')).read_text())
# Preserve the combined startup packet, without substituting a real lens calibration.
lsc=yaml.safe_load((SDK/'private/camss321-contract/lsc.yaml').read_text())
combined=copy.deepcopy(base);combined['modes'][0]['lens_shading']=copy.deepcopy(lsc['modes'][0]['lens_shading']);(stage/'combined.yaml').write_text(yaml.safe_dump(combined,sort_keys=False));run('combined-lsc','contract',arguments(name,item,'combined.yaml',2),'CCM_CONTRACT_PASS')
for label,mutate,code in [
 ('invalid-q',lambda t:t.update(qfactor=4),-22),
 ('invalid-axis',lambda t:t.update(aec_control='exposure_ev'),-22),
 ('missing-coordinate',lambda t:t['reference_triggers'].pop('aec_value'),-22),
 ('missing-led',lambda t:t['reference_triggers'].update(led_index=999),-2),
 ('empty-tree',lambda t:t.update(core=[]),-22)]:
 profile=copy.deepcopy(base);mutate(profile['modes'][0]['colour_correction']);(stage/(label+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False));run(label,'contract',arguments(name,item,label+'.yaml',code),'CCM_REJECT_PASS')
# Actual synthetic RGB feedback with delayed SOF acknowledgement, matrix versus independent per-K oracle.
s=(HERE.parent/'kernel332/dynamic-contract.cpp').read_text().replace('assert(argc==4);','assert(argc==5);')
s=s.replace('unsigned int checkedTemperatures=0;', '''std::ifstream matrixFile(argv[4],std::ios::binary);
 unsigned int checkedMatrices=0;
 unsigned int checkedTemperatures=0;''')
s=s.replace('++checkedTemperatures;', '''std::array<char,40> packet;std::array<float,9> matrix;
 matrixFile.seekg((*cct-1500)*76);assert(matrixFile.read(packet.data(),40));assert(matrixFile.read(reinterpret_cast<char*>(matrix.data()),36));
 auto actual=metadata.get(controls::ColourCorrectionMatrix);assert(actual&&!std::memcmp(actual->data(),matrix.data(),36));++checkedMatrices;
 ++checkedTemperatures;''')
s=s.replace('bytes==(lsc?1848:56)','bytes==(lsc?1888:96)').replace('bytes==56','bytes==96')
s=s.replace('assert(checkedTemperatures>0&&changedTemperature);','assert(checkedTemperatures>0&&changedTemperature&&checkedMatrices==checkedTemperatures);')
s=s.replace('assert(argc==5);','assert(argc==5);',1)
(HERE/'dynamic-contract.cpp').write_text(s);(stage/'libipa').mkdir(exist_ok=True)
for n in ['awb_colour_temperature.cpp','awb_colour_temperature.h','awb_calibration.h']:shutil.copyfile(HERE.parent/'kernel331/libipa'/n,stage/'libipa'/n)
build('dynamic',HERE/'dynamic-contract.cpp',[str(relative/'libipa/awb_colour_temperature.cpp')]);shutil.copyfile(P/(name+'-points-private.bin'),stage/'points-private.bin')
run('dynamic-awb-ccm','dynamic',[str(relative/(name+'.yaml')),str(relative/'points-private.bin'),str(relative/(name+'-oracle-private.bin'))],'AWB_INVERSE_CONTRACT_PASS')
# No-profile legacy behaviour is tested with the retained unchanged contract.
build('legacy',HERE.parent/'kernel332/legacy-contract.cpp');shutil.copyfile(HERE.parent/'kernel313/imx319.yaml',stage/'legacy.yaml')
run('legacy-no-reference','legacy',[str(relative/'legacy.yaml')],'AWB_CONTRACT_PASS')
report=dict(stage=335,actual_aarch64_ipa_dso=True,cases=rows,applied_sof_matrix_metadata_verified=True,synthetic_awb_feedback_matrix_verified=True,
 independent_pinned_source_selection_interpolation_encoding_oracle=True,front_factory_disable_preserved=True,installed=False,passed=all(r['passed'] for r in rows))
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
