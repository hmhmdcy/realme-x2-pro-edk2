from pathlib import Path
import importlib.util,json,shutil,struct,subprocess,sys
import host,storage
from unicorn.arm64_const import UC_ARM64_REG_S0
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'build-validation.json').read_text())['passed']
T='/work/libcamera/src/libcamera-v0.7.2';W='/private/camss439-profile';work=storage.SDK/W.lstrip('/');work.mkdir(exist_ok=True)
shutil.copyfile(HERE/'front-profile-contract.cpp',work/'profile.cpp');shutil.copyfile(P/'factory-imx471-private.yaml',work/'factory.yaml')
with storage.sdk_candidate():
 objects=[T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/'+n+'.cpp.o' for n in ['ipe_tone_profile','gamma_profile','colour_correction_profile']]
 q=subprocess.run(['chroot',str(storage.SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+T+'/include','-I'+T+'/output/include','-I'+T+'/src/ipa/camss-vfe',W+'/profile.cpp',*objects,T+'/output/src/ipa/libipa/libipa.a','-L'+T+'/output/src/libcamera','-L'+T+'/output/src/libcamera/base','-Wl,-rpath-link,'+T+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o',W+'/profile'],capture_output=True)
 (P/'front-profile-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+T+'/output/src/libcamera:'+T+'/output/src/libcamera/base',W+'/profile',W+'/factory.yaml',W+'/output.bin'],capture_output=True,timeout=35)
 (P/'front-profile-run.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,(q.returncode,(q.stdout+q.stderr).decode()[-3500:])
actual=(work/'output.bin').read_bytes();shutil.copyfile(work/'output.bin',P/'front-profile-actual-private.bin')
spec=importlib.util.spec_from_file_location('colour396',HERE.parent/'kernel396/colour-model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);oracle=m.Colour()
root=next(x for x in json.loads((P.parent/'kernel351/mode-profiles-private.json').read_text())['sunny_imx471'] if x['sensor_mode_index']==1 and x['usecase']=='Preview')['modules']['cc13_ipe']
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
def blend(a,b,w):
 base=m.DATA+0x8000;oracle.u.mem_write(base,struct.pack('<12f',*a));oracle.u.mem_write(base+0x100,struct.pack('<12f',*b));oracle.u.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',w))[0]);assert oracle.call(0x47ebf0,base,base+0x100,base+0x200)==1;return struct.unpack('<12f',oracle.u.mem_read(base+0x200,48))
def evaluate(nodes,level,cct,lux):
 def child(n):return n['matrix']+n['offsets'] if level==4 else evaluate(n['children'],level+1,cct,lux)
 if level==2:return child(next(n for n in nodes if n['trigger']==[0]))
 value=[1.,1.,0.,lux,float(cct)][level];axis=2*root['control_method'][1] if level==1 else 2*root['control_method'][0] if level==3 else 0
 for i,n in enumerate(nodes):
  if value<=n['trigger'][axis+1] or i+1==len(nodes):return child(n)
  second=nodes[i+1]
  if value<second['trigger'][axis]:return blend(child(n),child(second),f32((value-n['trigger'][axis+1])/(second['trigger'][axis]-n['trigger'][axis+1])))
 raise AssertionError('no region')
expected=bytearray()
for cct,lux in [(3000,100),(5750,160),(8000,250)]:
 values=evaluate(root['core'],0,cct,lux);native=oracle.calculate(values[:9],values[9:],root['qfactor']);words=struct.unpack('<9I',native)
 # Invert the original GBR register layout to the public signed RGB fields.
 signed=lambda v,b:(v&((1<<b)-1))-(1<<b) if v&(1<<(b-1)) else v&((1<<b)-1)
 fields=[words[5],words[1],words[3],words[4],words[0],words[2],words[4]>>16,words[0]>>16,words[2]>>16]
 coeff=[signed(v,12) for v in fields];offset=[signed(words[7],13),signed(words[6],13),signed(words[6]>>16,13)];q=words[8];scale=1<<(7+q)
 expected.extend(struct.pack('<12f',*values)+struct.pack('<12hI',*coeff,*offset,q)+struct.pack('<9f',*(v/scale for v in coeff)))
assert actual==expected,(len(actual),len(expected),next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None))
(P/'front-profile-expected-private.bin').write_bytes(expected)
r={'stage':439,'passed':True,'actual_arm64_profile_objects':True,'compiler_werror':True,'original_selected_front_tree':True,'native_interpolation_and_complete_calculation_zero_differences':True,'cases':3,'disabled_tmc_gtm_preserved':True,'ipe_ccm_only':True,'frame_cct_snapshot_owned':True,'failed_history_discarded':True,'unknown_cct_held_or_unity_explicit':True,'manual_ipe_matrix_and_restart':True,'phone_changed':False}
(HERE/'front-math-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(q.stdout.decode() if hasattr(q,'stdout') else '');print(json.dumps(r,indent=2))
