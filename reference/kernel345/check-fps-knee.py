from pathlib import Path
import json,shutil,struct,subprocess
import host
from stock_exposure import StockExposure
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
factory=json.loads((P.parent/'kernel336/factory-aec-bundle-private.json').read_text());priority={'AECExpIncGain':0,'AECExpIncExpTime':1,'AECExpIncPrioMax':2};programs={}
def encode(knees):return b''.join(struct.pack('<fQIf',k['gain'],k['time'],k['priority'],k['index']) for k in knees)
for bundle in factory.values():
 for root in bundle['roots']['Arbitration']:
  for table in root['data']['expTables']:
   knees=[dict(gain=k['gain'],time=k['expTime'],priority=priority[k['incrementPriority']],index=k['expIndex']) for k in table['expKneeEntries']];programs[encode(knees)]=knees
engine=StockExposure(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');inputs=bytearray();expected=bytearray();cases=[]
def add(knees,maximum,label):
 inputs.extend(struct.pack('<QI',maximum,len(knees))+encode(knees));result=engine.frame_knee(knees,maximum)
 expected.extend(struct.pack('<IfQIf',1,*result));cases.append(dict(label=label,maximum_ns=maximum))
for i,knees in enumerate(programs.values()):
 limits={1,1000000000//15,1000000000//30,1000000000//60}
 for knee in knees:limits.update([max(1,knee['time']-1),knee['time'],knee['time']+1])
 for a,b in zip(knees,knees[1:]):limits.add(max(1,(a['time']+b['time'])//2))
 for maximum in sorted(limits):add(knees,maximum,'factory-'+str(i))
for priority_value in [0,1,2]:
 knees=[dict(gain=1.,time=100000003,priority=priority_value,index=-10.),dict(gain=4.,time=400000011,priority=1,index=100.)]
 for maximum in [1,99999999,100000003,200000007,400000011,500000000]:add(knees,maximum,'synthetic-'+str(priority_value))
# Invalid physical frame duration is rejected without running the OEM log path.
inputs.extend(struct.pack('<QI',0,len(knees))+encode(knees));expected.extend(struct.pack('<IfQIf',0,0,0,0,0));cases.append(dict(label='zero-duration',maximum_ns=0))
(P/'fps-input-private.bin').write_bytes(struct.pack('<I',len(cases))+inputs);(P/'fps-expected-private.bin').write_bytes(expected)
work=SDK/'private/camss345-math';work.mkdir(exist_ok=True)
for source in [HERE/'fps-runner.cpp',*sorted((HERE/'libipa').glob('*'))]:shutil.copyfile(source,work/source.name)
shutil.copyfile(P/'fps-input-private.bin',work/'fps-input-private.bin');rows=[]
for arch in ['host','aarch64']:
 command=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(HERE/'libipa'),str(HERE/'fps-runner.cpp'),str(HERE/'libipa/aec_exposure_table.cpp'),'-o',str(P/'fps-host')] if arch=='host' else ['chroot',str(SDK),'g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','/private/camss345-math/fps-runner.cpp','/private/camss345-math/aec_exposure_table.cpp','-o','/private/camss345-math/fps-aarch64']
 q=subprocess.run(command,capture_output=True);(P/(arch+'-fps-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(arch+'-fps-output-private.bin')
 command=[str(P/'fps-host'),str(P/'fps-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(SDK),'/private/camss345-math/fps-aarch64','/private/camss345-math/fps-input-private.bin','/private/camss345-math/fps-output-private.bin']
 q=subprocess.run(command,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
 if arch=='aarch64':shutil.copyfile(work/'fps-output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected)
 different=[i for i in range(len(cases)) if actual[i*24:(i+1)*24]!=expected[i*24:(i+1)*24]]
 (P/(arch+'-fps-differences-private.json')).write_text(json.dumps([dict(cases[i],actual=list(struct.unpack_from('<IfQIf',actual,i*24)),expected=list(struct.unpack_from('<IfQIf',expected,i*24))) for i in different])+'\n')
 rows.append(dict(architecture=arch,cases=len(cases),compared_bytes=len(expected),differing_records=len(different),passed=not different));print(json.dumps(rows[-1]),flush=True)
report=dict(stage=345,unique_factory_programs=len(programs),architectures=rows,original_update_fps_knee_and_nested_lookup_instructions=True,
 original_function=['0x2d178','0x2d350'],powf_and_log10_are_host_math_stubs=True,active_table_construction_not_yet_integrated=True,
 actual_sensor_frame_duration_quantization_not_applied=True,phone_changed=False,passed=all(row['passed'] for row in rows))
(HERE/'fps-knee-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
