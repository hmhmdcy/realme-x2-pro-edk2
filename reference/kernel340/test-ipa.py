from pathlib import Path
import copy,json,shutil,struct,subprocess
import yaml
import host,storage
from oracle import Oracle,Data
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2'
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
configs=json.loads((P.parent/'kernel339/profiles-private.json').read_text());profiles={};(P/'profiles').mkdir(exist_ok=True)
for name,row in configs.items():
 if name in ['colour-compensation','direct-unfiltered','disabled']:continue
 profile=yaml.safe_load((P.parent/'kernel339/profiles'/(name+'.yaml')).read_text())
 for mode in profile['modes']:
  mode['colour_correction']['aec_source']='runtime';mode['colour_correction']['reference_triggers'].pop('aec_value')
 profiles[name]=dict(item=row['item'],profile=profile)
experiment=copy.deepcopy(profiles['sunny_imx471-unit'])
for mode in experiment['profile']['modes']:mode['colour_correction']['enabled']=True
profiles['front-explicit-ccm-experiment']=experiment
gain=copy.deepcopy(profiles['sunny_imx319-unit'])
def gainAxis(nodes,level=0):
 if level==3:
  values=[copy.deepcopy(nodes[0]),copy.deepcopy(nodes[-1])]
  for node,limits in zip(values,[(1.,2.),(4.,8.)]):node['trigger']=[0.,0.,*limits]
  return values
 for node in nodes:node['children']=gainAxis(node['children'],level+1)
 return nodes
for mode in gain['profile']['modes']:
 c=mode['colour_correction'];c['aec_control']='analogue_gain';c['core']=gainAxis(c['core'])
profiles['gain-axis-diagnostic']=gain
oracle=Oracle(P);relative=Path('/private/camss340-contract');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True);rows=[]
with storage.sdk_candidate():
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include']
 links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
 shutil.copyfile(HERE/'ccm-runtime-contract.cpp',stage/'contract.cpp');q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'contract.cpp'),*links,'-o',str(relative/'contract')],capture_output=True)
 (P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 env=['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',str(relative/'contract'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so']
 for name,row in profiles.items():
  item=row['item'];profile=row['profile'];path=P/'profiles'/(name+'.yaml');path.write_text(yaml.safe_dump(profile,sort_keys=False));shutil.copyfile(path,stage/path.name)
  (stage/(path.name+'.stats')).write_bytes((P.parent/'kernel338/samples-r1'/('sample-'+item['model']+'-private.stats')).read_bytes())
  c=profile['modes'][0]['colour_correction'];mode=0 if not c['enabled'] else 2 if c['aec_control']=='analogue_gain' else 1;m=item['match']
  args=[str(relative/path.name),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(mode)]
  q=subprocess.run([*env,*args],capture_output=True,timeout=90);(P/(name+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(name,q.stderr.decode()[-4000:]);assert b'RUNTIME_CCM_CONTRACT_PASS' in q.stdout
  packets=[json.loads(line.split(' ',1)[1]) for line in q.stdout.decode().splitlines() if line.startswith('CCM_PACKET ')];states={};data=bytearray();expected=bytearray()
  for packet in packets:
   payload=bytes.fromhex(packet['packet']);assert len(payload)==(96 if mode else 56)
   if not mode:assert packet['matrix']==[0]*9;continue
   key=packet['epoch'],packet['revision']
   if packet['kind']=='fallback':wanted=states[(packet['epoch'],packet['parent'])]
   elif packet['kind'] in ['unity','manual']:
    matrix=[1,0,0,0,1,0,0,0,1] if packet['kind']=='unity' else [0,0,1,0,.75,0,1,0,0]
    import ctypes
    wanted=oracle.encode(Data((ctypes.c_float*9)(*matrix),(ctypes.c_int32*3)(0,0,0)),c['qfactor'])
   else:wanted=oracle.evaluate(c,packet['kelvin'],struct.unpack('<f',struct.pack('<I',packet['bits']))[0])
   assert payload[56:]==wanted[0],(name,packet['revision'],packet['kind'],'packet');assert struct.pack('<9f',*packet['matrix'])==struct.pack('<9f',*wanted[1]),(name,packet['revision'],'metadata')
   states[key]=wanted;data.extend(payload[56:]+struct.pack('<9f',*packet['matrix']));expected.extend(wanted[0]+struct.pack('<9f',*wanted[1]))
  (P/(name+'-actual-private.bin')).write_bytes(data);(P/(name+'-expected-private.bin')).write_bytes(expected)
  rows.append(dict(case=name,actual_ipa_packets=len(packets),compared_bytes=len(data),differing_bytes=0,ccm_enabled=bool(c['enabled']),factory_ccm_enabled=item['factory_ccm_enabled'],gain_axis_diagnostic=name=='gain-axis-diagnostic',passed=True))
 # New configuration prerequisites only; do not rerun unrelated old matrices.
 base=profiles['sunny_imx319-unit'];item=base['item'];m=item['match']
 for name,mutate in [('missing-lux',lambda mode:mode.pop('aec_lux')),('invalid-source',lambda mode:mode['colour_correction'].update(aec_source='exposure_ev'))]:
  profile=copy.deepcopy(base['profile'])
  for mode in profile['modes']:mutate(mode)
  (stage/(name+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False));args=[str(relative/(name+'.yaml')),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],'-22']
  q=subprocess.run([*env,*args],capture_output=True);(P/(name+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode and b'RUNTIME_CCM_REJECT_PASS' in q.stdout
  rows.append(dict(case=name,expected_error=-22,passed=True))
(P/'profiles-private.json').write_text(json.dumps({name:dict(item=row['item'],profile=name) for name,row in profiles.items()},indent=2)+'\n')
report=dict(stage=340,actual_aarch64_ipa=True,pinned_source_oracle_reused_from335=True,cases=rows,per_revision_frozen_ccm=True,delayed_sof_metadata=True,historical_sof_not_used_for_proposal=True,manual_matrix_priority=True,zero_gain_fallback=True,quantized_noops=True,source_reset_between_streams=True,front_factory_disabled_preserved=True,installed=False,passed=True)
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
