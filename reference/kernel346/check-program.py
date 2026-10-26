from pathlib import Path
import copy,json,struct,subprocess,shutil
import host
from stock_active import StockActive

HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((HERE/'hdr3-policy-binding-validation.json').read_text())['passed']
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());programs={};table_count=0
priority={'AECExpIncGain':0,'AECExpIncExpTime':1,'AECExpIncPrioMax':2}
def encode(knees):return b''.join(struct.pack('<fQIf',k['gain'],k['time'],k['priority'],k['index']) for k in knees)
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]
for variant,bundle in factory.items():
 for root in bundle['roots']['Arbitration']:
  data=root['data']
  for tableid,table in enumerate(data['expTables']):
   table_count+=1
   knees=[dict(gain=k['gain'],time=k['expTime'],priority=priority[k['incrementPriority']],index=k['expIndex']) for k in table['expKneeEntries']]
   cap=data['enableEVGainCapping'];gain=data['maxEVCappingGain'];key=encode(knees)+struct.pack('<IfQ',cap,gain if cap else 0.,data['minPreviewVertBlankTime'])
   row=programs.setdefault(key,dict(knees=knees,cap=cap,maximum_gain=gain,blanking_ns=data['minPreviewVertBlankTime'],sources=[]))
   row['sources'].append(dict(variant=variant,arbitration_uid=root['uid'],table_index=tableid,ev_table_adjustment_enabled=data['enableEVExpTableAdj']))
engine=StockActive(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');inputs=bytearray();expected=bytearray();cases=[];unique=set()
def add(knees,maximum,ev,cap,gain,hdr,label,valid=True):
 ev=f32(ev);gain=f32(gain);record=struct.pack('<QfIfII',maximum,ev,cap,gain,hdr,len(knees))+encode(knees)
 if record in unique:return
 unique.add(record);inputs.extend(record)
 start=len(expected)
 if valid:
  result=engine.program(knees,maximum,ev,cap,gain,hdr)
  expected.extend(struct.pack('<I',1)+struct.pack('<fQIf',*result['frame'])+struct.pack('<fQIf',*result['ev'])+struct.pack('<fI',result['offset'],len(result['knees'])))
  for knee in result['knees']:expected.extend(struct.pack('<fQIf',*knee))
 else:expected.extend(struct.pack('<I',0))
 cases.append(dict(label=label,maximum_ns=maximum,ev=ev,cap=bool(cap),hdr3=bool(hdr),expected_offset=start,expected_bytes=len(expected)-start,valid=valid))
for number,program in enumerate(programs.values()):
 knees=program['knees'];limits={knees[-1]['time']}
 for fps in [15.,30.,60.]:
  duration=int(f32(f32(1000000000.)/f32(fps)));blanking=program['blanking_ns'];limits.add(duration-blanking if blanking<duration else duration)
 for maximum in sorted(limits):
  for ev in [-3.,-1.,0.,1.,3.]:
   for hdr in [False,True]:add(knees,maximum,ev,program['cap'],program['maximum_gain'],hdr,'factory-'+str(number))
 # Insertion exactly on original knee indices at zero EV.
 for knee in knees:add(knees,knee['time'],0.,program['cap'],program['maximum_gain'],False,'factory-knee-'+str(number))
synthetic=[dict(gain=1.,time=100003,priority=0,index=-20.),dict(gain=2.,time=2000011,priority=1,index=0.),dict(gain=16.,time=80000003,priority=0,index=200.)]
for maximum in [100003,1000000,33333333,100000000]:
 for ev in [-4.,-.25,0.,.25,4.]:
  for cap,gain in [(False,0.),(True,.5),(True,2.),(True,32.)]:
   for hdr in [False,True]:add(synthetic,maximum,ev,cap,gain,hdr,'synthetic-policy')
# Duplicated indices and a declared Maximum priority preserve the OEM decisions.
duplicates=copy.deepcopy(synthetic);duplicates.insert(2,dict(gain=3.,time=3000011,priority=2,index=0.))
for ev in [-2.,0.,2.]:
 for hdr in [False,True]:add(duplicates,2000011,ev,False,0.,hdr,'synthetic-duplicate')
for label,maximum,ev,cap,gain in [('zero-duration',0,0.,False,0.),('nan-ev',1000000,float('nan'),False,0.),('invalid-cap',1000000,0.,True,0.)]:add(synthetic,maximum,ev,cap,gain,False,label,False)
(P/'program-input-private.bin').write_bytes(struct.pack('<I',len(cases))+inputs);(P/'program-expected-private.bin').write_bytes(expected)
(P/'program-cases-private.json').write_text(json.dumps(cases,allow_nan=True)+'\n');(P/'source-programs-private.json').write_text(json.dumps(list(programs.values()))+'\n')
work=SDK/'private/camss346-math';work.mkdir(exist_ok=True)
for source in [HERE/'program-runner.cpp',*sorted((HERE/'libipa').glob('*'))]:shutil.copyfile(source,work/source.name)
shutil.copyfile(P/'program-input-private.bin',work/'input-private.bin');rows=[]
for arch in ['host','aarch64']:
 command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),str(HERE/'program-runner.cpp'),str(HERE/'libipa/aec_exposure_table.cpp'),'-o',str(P/'program-host')] if arch=='host' else ['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss346-math/program-runner.cpp','/private/camss346-math/aec_exposure_table.cpp','-o','/private/camss346-math/program-aarch64']
 q=subprocess.run(command,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(arch+'-output-private.bin')
 command=[str(P/'program-host'),str(P/'program-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(SDK),'/private/camss346-math/program-aarch64','/private/camss346-math/input-private.bin','/private/camss346-math/output-private.bin']
 q=subprocess.run(command,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
 if arch=='aarch64':shutil.copyfile(work/'output-private.bin',output)
 actual=output.read_bytes();different=[];position=0
 for i,case in enumerate(cases):
  start=position;ok=struct.unpack_from('<I',actual,position)[0];position+=4
  if ok:
   size=struct.unpack_from('<I',actual,position+44)[0];position+=48+size*20
  wanted=expected[case['expected_offset']:case['expected_offset']+case['expected_bytes']]
  if actual[start:position]!=wanted:different.append(dict(case=i,**case,actual_bytes=position-start,actual_hex=actual[start:position].hex(),expected_hex=wanted.hex()))
 assert position==len(actual)
 (P/(arch+'-differences-private.json')).write_text(json.dumps(different,allow_nan=True)+'\n')
 rows.append(dict(architecture=arch,cases=len(cases),compared_bytes=len(expected),differing_records=len(different),passed=not different));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=346,source_tables=table_count,unique_table_policy_contexts=len(programs),identical_inputs_tested_once=True,architectures=rows,
 original_fps_ev_and_active_table_functions_executed=True,full_knee_arrays_compared=True,hdr3_flag_semantics_bound_to_actual_virtual_method=True,
 powf_log10_exp2_are_host_math_stubs=True,memcpy_and_logging_stubbed=True,android_algorithm_not_started=True,
 table_ev_adjustment_enable_is_caller_policy=True,anti_banding_and_sensor_limits_not_integrated=True,ipa_integrated=False,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'active-program-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
