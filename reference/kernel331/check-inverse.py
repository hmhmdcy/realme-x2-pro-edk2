from pathlib import Path
import hashlib,json,random,shutil,struct,subprocess
import host
from stock_inverse import StockInverse,OBJECT
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
binary=P.parent/'kernel328/stats-source/com.qti.stats.awb.so'
pin=next(r for r in json.loads((P.parent/'kernel328/oem-stats-source.json').read_text())['files'] if r['file']==binary.name)
assert hashlib.sha256(binary.read_bytes()).hexdigest()==pin['sha256']
engine=StockInverse(binary)
# Constructor 0x81b8 stores derived vptr 0x5eca8+16 after its base constructor.
assert engine.read(0x8218,'<I')[0]==0x9132a14a and engine.read(0x8228,'<I')[0]==0xf900026b
assert engine.read(0x5ecb8+32,'<Q')[0]==0x8380
assert engine.read(0x5ecb8+160,'<Q')[0]==0x9d70
# Factory 0x25fa0 constructs the object installed by caller0x360b8..360f8.
assert engine.read(0x25fd8,'<I')[0]==0x911d0108
assert engine.read(0x5f750+24,'<Q')[0]==0x264c0
f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
rng=random.Random(331);inputs=bytearray();expected=bytearray();cases=[];roots=0;calibration_values=0
bundle=json.loads((P.parent/'kernel328/wb-reference-bundle-private.json').read_text())
calibrations=json.loads((P.parent/'kernel329/calibrated-ratios-private.json').read_text())
for name,source in bundle.items():
 for root in [r for r in source['factory_roots'] if r['tag']=='refPtV1']:
  raw=root['data']['points'][:10];assert len(raw)==10;roots+=1
  for variant,factors in [('factory',[[1.,1.]]*10),('unit',calibrations[name]['factors'])]:
   points=engine.calibrated_points(raw,factors);calibration_values+=20
   assert points==[[f32(raw[i][c]*factors[i][c]) for c in range(2)] for i in range(10)]
   engine.configure(points)
   inputs.extend(struct.pack('<I60f',1,*[v for table in [raw,factors,points] for row in table for v in row]))
   queries=[list(p) for p in points]
   for a,b in [(0,1),(1,2),(2,3),(3,5),(5,7),(7,8),(8,9)]:
    for t in [.125,.5,.875]:
     p=[f32(points[a][i]*(1-t)+points[b][i]*t) for i in range(2)]
     queries.extend([[f32(p[0]+d),f32(p[1]+e)] for d,e in [(0,0),(.02,0),(-.02,0),(0,.02),(0,-.02)]])
   queries.extend([[f32(rng.uniform(.05,2.5)),f32(rng.uniform(.05,2.5))] for _ in range(160)])
   for ratio in queries:
    distance,cct,illuminant=engine.estimate(ratio)
    inputs.extend(struct.pack('<I2f',2,*ratio));expected.extend(struct.pack('<2fI',cct,distance,illuminant))
    cases.append(dict(source=name,uid=root['uid'],variant=variant,ratio=ratio,cct=cct,distance=distance,illuminant=illuminant))
(P/'inverse-input-private.bin').write_bytes(inputs);(P/'stock-expected-private.bin').write_bytes(expected)
(P/'inverse-cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');relative=Path('/private/camss331-inverse');stage=sdk/str(relative).lstrip('/')
stage.mkdir(mode=0o700,exist_ok=True);(stage/'libipa').mkdir(exist_ok=True)
shutil.copyfile(HERE.parent/'kernel329/libipa/awb_calibration.h',HERE/'libipa/awb_calibration.h')
for name in ['inverse-runner.cpp','libipa/awb_colour_temperature.h','libipa/awb_colour_temperature.cpp','libipa/awb_calibration.h']:
 shutil.copyfile(HERE/name,stage/name)
shutil.copyfile(P/'inverse-input-private.bin',stage/'inverse-input-private.bin')
flags=['-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror'];rows=[]
for arch in ['host','aarch64']:
 exe=P/('inverse-'+arch)
 args=['g++',*flags,str(HERE/'inverse-runner.cpp'),str(HERE/'libipa/awb_colour_temperature.cpp'),'-o',str(exe)] if arch=='host' else ['chroot',str(sdk),'g++',*flags,str(relative/'inverse-runner.cpp'),str(relative/'libipa/awb_colour_temperature.cpp'),'-o',str(relative/'inverse-aarch64')]
 q=subprocess.run(args,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(arch+'-output-private.bin')
 args=[str(exe),str(P/'inverse-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(sdk),str(relative/'inverse-aarch64'),str(relative/'inverse-input-private.bin'),str(relative/'aarch64-output-private.bin')]
 q=subprocess.run(args,capture_output=True);assert not q.returncode,(arch,q.returncode,q.stderr.decode())
 if arch=='aarch64':shutil.copyfile(stage/'aarch64-output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected)
 differences=[];cct_errors=[];distance_errors=[];class_errors=0
 for i,case in enumerate(cases):
  a=struct.unpack_from('<2fI',actual,i*12);b=struct.unpack_from('<2fI',expected,i*12)
  cct_errors.append(abs(a[0]-b[0]));distance_errors.append(abs(a[1]-b[1]));class_errors+=a[2]!=b[2]
  if a!=b:differences.append(dict(index=i,actual=a,stock=b,case=case))
 (P/(arch+'-differences-private.json')).write_text(json.dumps(differences,indent=2)+'\n')
 rows.append(dict(architecture=arch,queries=len(cases),different_queries=len(differences),maximum_cct_error=max(cct_errors),maximum_distance_error=max(distance_errors),illuminant_differences=class_errors))
 print(json.dumps(rows[-1]),flush=True)
 assert not differences,dict(architecture=arch,first_differences=differences[:2])
report=dict(stage=331,source=pin,reference_point_roots=roots,queries_per_architecture=len(cases),architectures=rows,
 vptr_proved=True,vptr='0x5ecb8, constructor0x81b8/0x8228; +32 ->0x8380; +160 ->0x9d70',
 solver_vptr='0x5f750, factory0x25fa0; +24 ->0x264c0; installed by0x360b8..360f8',
 factory_reference_points_distinct_from_mwb=True,calibrated_reference_point_transform_verified=True,
 calibrated_reference_point_values_per_architecture=calibration_values,
 reference_point_transform_instruction_block=['0x25da0','0x25ef0'],
 automatic_scene_cct_implemented=False,ipa_integration=False,phone_changed=False,
 instructions=engine.instructions,logging_stub_calls=engine.stub_calls,memcpy_emulated_calls=engine.copy_calls,sqrt_stub_calls=engine.sqrt_calls,
 native_oem_library_loaded=False,passed=True)
(HERE/'inverse-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
