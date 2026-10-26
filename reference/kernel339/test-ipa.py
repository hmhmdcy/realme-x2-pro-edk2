from pathlib import Path
import copy,ctypes,json,math,shutil,struct,subprocess,sys
import yaml
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
sys.path.insert(0,str(HERE.parent/'kernel337'));from stock_bg import StockBayer
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
engine=StockBayer(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');manual=StockBayer(P.parent/'kernel328/stats-source/com.qti.stats.aec.so')
f32=lambda x:ctypes.c_float(x).value
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());cases=json.loads((P.parent/'kernel335/cases-private.json').read_text())
TREE='/work/libcamera/src/libcamera-v0.7.2';relative=Path('/private/camss339-contract');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(mode=0o700,exist_ok=True)
(P/'profiles').mkdir(exist_ok=True);rows=[]
with storage.sdk_candidate():
 shutil.copyfile(HERE/'lux-contract.cpp',stage/'contract.cpp')
 flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include']
 links=['-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-ldl']
 q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'contract.cpp'),*links,'-o',str(relative/'contract')],capture_output=True)
 (P/'contract-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 env=['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',str(relative/'contract'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so']
 configs={}
 for name,item in cases.items():
  if item['kind']!='unit' or item.get('experimental_enable_override'):continue
  root=factory[item['variant']]['roots'];meter=next(r['data'] for r in root['Metering'] if r['uid']==106)
  table=next(r['data']['expTables'][0] for r in root['Arbitration'] if r['uid']==110);anchor=table['expKneeEntries'][0]
  config=dict(enabled=True,exposure_anchor=dict(analogue_gain=anchor['gain'],exposure_time_ns=anchor['expTime'],index=anchor['expIndex']),weights=meter['lumaWeight']['weight'],reference_gains=meter['lumaWeight']['refGain'],compensate_colour=meter['lumaWeight']['enableColorAndSensorComp'],normalization=1.,
   lux=dict(compensate_sensitivity=meter['indexCalc']['enableLuxIndexComp'],reference_zero_sensitivity=meter['indexCalc']['refSensitivityForExpIndexZero'],table_zero_sensitivity=f32(f32(table['sensitivityCorrectionFactor']*anchor['gain'])*f32(anchor['expTime'])),filter_factor=meter['indexCalc']['luxIndexFilterFactor']))
  configs[name]=dict(item=item,config=config)
 # Explicit diagnostic variations cover colour compensation, including >255 luma,
 # zero filter factor, and absent configuration without asserting mode binding.
 base=copy.deepcopy(configs['sunny_imx319-unit']);base['config']['compensate_colour']=True;configs['colour-compensation']=base
 base=copy.deepcopy(base);base['config']['lux']['filter_factor']=0.;configs['direct-unfiltered']=base
 base=copy.deepcopy(base);base['config']['enabled']=False;configs['disabled']=base
 for label,row in configs.items():
  item=row['item'];config=row['config'];model=item['model'];profile=yaml.safe_load((P.parent/'kernel335/profiles'/(item['profile']+'.yaml')).read_text())
  for mode in profile['modes']:mode['aec_lux']=copy.deepcopy(config)
  (P/'profiles'/(label+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False));shutil.copyfile(P/'profiles'/(label+'.yaml'),stage/(label+'.yaml'))
  packet=(P.parent/'kernel338/samples-r1'/('sample-'+model+'-private.stats')).read_bytes();(stage/(label+'.yaml.stats')).write_bytes(packet)
  m=item['match'];args=[str(relative/(label+'.yaml')),model,*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(int(config['enabled']))]
  q=subprocess.run([*env,*args],capture_output=True,timeout=90);(P/(label+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(label,q.stderr.decode()[-3000:]);assert b'LUX_CONTRACT_PASS' in q.stdout
  observations=[json.loads(line.split(' ',1)[1]) for line in q.stdout.decode().splitlines() if line.startswith('LUX_OBSERVATION ')]
  expected=bytearray();actual=bytearray();lastEpoch=None
  lux=config['lux'];a=config['exposure_anchor'];anchor=(a['analogue_gain'],a['exposure_time_ns'],a['index'])
  gridOffset=4112;values=struct.unpack_from('<8H',packet,gridOffset+8);left,top,rw,rh,cols,nrows,high,bits=values
  raw=[struct.unpack_from('<4I4H',packet,gridOffset+24+i*24) for i in range(cols*nrows)]
  maxLuma=0
  for obs in observations:
   if not obs['valid']:continue
   if obs['epoch']!=lastEpoch:engine.configure(lux['compensate_sensitivity'],lux['reference_zero_sensitivity'],lux['table_zero_sensitivity'],lux['filter_factor']);lastEpoch=obs['epoch']
   ns=math.floor(obs['lines']*(float(m['line_length'])*1000000/m['pixel_rate'])*1000+.5)
   exposure=manual.manual(anchor,obs['gain'],ns)
   weights=engine.weights(config['weights'],config['reference_gains'],[obs['red'],1.,obs['blue']],config['compensate_colour'])
   engine.region_setup(rw*rh//4,bits,[high]*4,weights,config['normalization'])
   for index,region in enumerate(raw):
    sums,counts=region[:4],region[4:]
    if obs['kind'] in [3,4]:sums=[0]*4
    if obs['kind']==4:counts=[0]*4
    engine.region(sums,counts,index)
   cells=engine.pool(cols,nrows);index,luma=engine.cells(exposure,[c[0] for c in cells]);maxLuma=max(maxLuma,luma)
   expected.extend(struct.pack('<3f',exposure,luma,index));actual.extend(struct.pack('<3f',obs['exposure_index'],obs['luma'],obs['index']))
  assert actual==expected,(label,[(i,struct.unpack_from('<f',actual,i)[0],struct.unpack_from('<f',expected,i)[0]) for i in range(0,len(expected),4) if actual[i:i+4]!=expected[i:i+4]])
  assert observations[1]['red']==observations[9]['red'] and observations[11]['red']!=observations[9]['red']
  (P/(label+'-actual-private.bin')).write_bytes(actual);(P/(label+'-expected-private.bin')).write_bytes(expected)
  rows.append(dict(case=label,observations=len(observations),valid_lux_records=len(actual)//12,compared_bytes=len(actual),differing_bytes=0,maximum_luma=maxLuma,passed=True))
 # Configuration errors local to the new parser only; retained CCM algorithms
 # and legacy parser are covered by their existing component evidence.
 base=yaml.safe_load((P/'profiles/sunny_imx319-unit.yaml').read_text());item=configs['sunny_imx319-unit']['item'];m=item['match']
 for label,modify,code in [('missing-anchor',lambda c:c.pop('exposure_anchor'),-22),('zero-anchor',lambda c:c['exposure_anchor'].update(exposure_time_ns=0),-34),('bad-filter',lambda c:c['lux'].update(filter_factor=1.1),-34)]:
  profile=copy.deepcopy(base)
  for mode in profile['modes']:modify(mode['aec_lux'])
  (stage/(label+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
  q=subprocess.run([*env,str(relative/(label+'.yaml')),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],str(code)],capture_output=True)
  (P/(label+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode and b'LUX_REJECT_PASS' in q.stdout
  rows.append(dict(case=label,expected_error=code,passed=True))
(P/'profiles-private.json').write_text(json.dumps(configs,indent=2)+'\n')
report=dict(stage=339,actual_aarch64_ipa_dso=True,cases=rows,real_four_sensor_statistics_replayed=True,original_oem_region_pooling_exposure_lux_instruction_oracle=True,delayed_sof_white_balance=True,stream_filter_reset=True,missing_invalid_stale_statistics_not_advanced=True,supplier_mode_binding_verified=False,installed=False,passed=True)
(HERE/'ipa-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
