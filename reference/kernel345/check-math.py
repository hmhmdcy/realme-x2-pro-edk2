from pathlib import Path
import copy,json,math,shutil,struct,subprocess,sys
import host
from stock_exposure import StockExposure

HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
engine=StockExposure(P.parent/'kernel328/stats-source/com.qti.stats.aec.so')
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());programs={};sources=[]
priority={'AECExpIncGain':0,'AECExpIncExpTime':1,'AECExpIncPrioMax':2}
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
def neighbor(value,up):
 if value==0:return struct.unpack('<f',struct.pack('<I',1 if up else 0x80000001))[0]
 bits=struct.unpack('<I',struct.pack('<f',value))[0];bits+=1 if (value>0)==up else -1
 return struct.unpack('<f',struct.pack('<I',bits))[0]
def encode_knees(knees):return b''.join(struct.pack('<fQIf',k['gain'],k['time'],k['priority'],k['index']) for k in knees)
for variant,bundle in factory.items():
 for root in bundle['roots']['Arbitration']:
  for tableid,table in enumerate(root['data']['expTables']):
   knees=[dict(gain=k['gain'],time=k['expTime'],priority=priority[k['incrementPriority']],index=k['expIndex']) for k in table['expKneeEntries']]
   key=encode_knees(knees);program=programs.setdefault(key,dict(knees=knees,sources=[]));program['sources'].append(dict(variant=variant,arbitration_uid=root['uid'],table_index=tableid))
   sources.append(program)
inputs=bytearray();expected=bytearray();metadata=[];active_checks=0
def add(knees,index,label,valid=True):
 global active_checks
 index=f32(index);inputs.extend(struct.pack('<fI',index,len(knees))+encode_knees(knees))
 if valid:
  result=engine.lookup(knees,index)
  if label.endswith('knee') or label.startswith('synthetic'):
   assert engine.lookup(knees,index,active=True)==result;active_checks+=1
  expected.extend(struct.pack('<IfQf',1,*result))
 else:expected.extend(struct.pack('<IfQf',0,0,0,0))
 metadata.append(dict(label=label,index=index,knees=len(knees),expected_valid=valid))
for number,program in enumerate(programs.values()):
 knees=program['knees'];points={}
 def point(value,label):points[struct.pack('<f',f32(value))]=(f32(value),label)
 for knee in knees:
  index=knee['index'];point(index,'knee');point(neighbor(index,False),'below');point(neighbor(index,True),'above')
 for a,b in zip(knees,knees[1:]):
  for fraction in [.25,.5,.75]:point(a['index']+(b['index']-a['index'])*fraction,'interior')
 point(knees[0]['index']-10,'lower-clamp');point(knees[-1]['index']+10,'upper-clamp');point(-0.,'negative-zero')
 for value,label in points.values():add(knees,value,'factory-'+str(number)+'-'+label)
synthetic=[
 [dict(gain=1.,time=100000003,priority=p,index=0.),dict(gain=4.,time=400000011,priority=0,index=100.)] for p in [0,1,2]]
synthetic.append([dict(gain=1.,time=123456789,priority=0,index=-10.),dict(gain=2.,time=987654321,priority=1,index=0.),dict(gain=4.,time=1987654321,priority=1,index=0.),dict(gain=8.,time=3987654321,priority=0,index=50.)])
synthetic.append([dict(gain=1.,time=100000003,priority=1,index=0.),dict(gain=2.,time=50000001,priority=0,index=50.)])
for i,knees in enumerate(synthetic):
 for value in [-20.,-0.,0.,.125,1.,10.,25.,49.999,50.,99.999,100.,110.]:add(knees,value,'synthetic-'+str(i))
base=copy.deepcopy(synthetic[0])
for label,knees,index in [('empty',[],1.),('single',base[:1],0.),('nan-request',base,float('nan')),('infinite-request',base,float('inf'))]:add(knees,index,label,False)
for key,value in [('gain',0.),('gain',-1.),('gain',float('inf')),('time',0),('priority',3),('index',float('nan'))]:
 knees=copy.deepcopy(base);knees[0][key]=value;add(knees,1.,'invalid-'+key,False)
knees=copy.deepcopy(base);knees[1]['index']=-1.;add(knees,0.,'unsorted',False)
knees=[dict(gain=1.,time=2**64-1,priority=0,index=0.),dict(gain=1.,time=2**64-1,priority=1,index=100.)];add(knees,50.,'uint64-add-overflow',False)
(P/'math-input-private.bin').write_bytes(struct.pack('<I',len(metadata))+inputs)
(P/'stock-expected-private.bin').write_bytes(expected);(P/'math-cases-private.json').write_text(json.dumps(metadata,allow_nan=True)+'\n')
work=SDK/'private/camss345-math';work.mkdir(exist_ok=True)
for source in [HERE/'math-runner.cpp',*sorted((HERE/'libipa').glob('*'))]:shutil.copyfile(source,work/source.name)
shutil.copyfile(P/'math-input-private.bin',work/'input-private.bin')
files=[HERE/'math-runner.cpp',HERE/'libipa/aec_exposure_table.cpp'];rows=[]
commands=[('host',['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),*[str(p) for p in files],'-o',str(P/'math-host')]),
 ('aarch64',['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss345-math/math-runner.cpp','/private/camss345-math/aec_exposure_table.cpp','-o','/private/camss345-math/math-aarch64'])]
for arch,command in commands:
 q=subprocess.run(command,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(arch+'-output-private.bin')
 args=[str(P/'math-host'),str(P/'math-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(SDK),'/private/camss345-math/math-aarch64','/private/camss345-math/input-private.bin','/private/camss345-math/output-private.bin']
 q=subprocess.run(args,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
 if arch=='aarch64':shutil.copyfile(work/'output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected)
 differences=[i for i in range(len(metadata)) if actual[i*20:(i+1)*20]!=expected[i*20:(i+1)*20]]
 (P/(arch+'-differences-private.json')).write_text(json.dumps([dict(metadata[i],actual=list(struct.unpack_from('<IfQf',actual,i*20)),expected=list(struct.unpack_from('<IfQf',expected,i*20))) for i in differences],allow_nan=True)+'\n')
 rows.append(dict(architecture=arch,cases=len(metadata),compared_bytes=len(expected),differing_records=len(differences),passed=not differences))
 print(json.dumps(rows[-1]),flush=True)
report=dict(stage=345,factory_tables=len(sources),unique_knee_programs=len(programs),identical_programs_tested_once=True,architectures=rows,
 original_oem_lookup_full_function=True,original_and_active_table_views_compared=active_checks,
 powf_is_host_libm_stub=True,logging_is_stubbed=True,android_algorithm_not_started=True,
 selected_mode_and_regular_streaming_table_binding_reused_from343=True,
 sensor_limits_fps_ev_knee_construction_and_antibanding_not_integrated=True,ipa_integrated=False,phone_changed=False,passed=all(r['passed'] for r in rows))
(HERE/'math-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
