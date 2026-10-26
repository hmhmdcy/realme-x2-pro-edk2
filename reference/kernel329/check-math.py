"""Compare portable C++ to instruction-emulated OEM math, host and AArch64."""
from pathlib import Path
import hashlib, json, shutil, struct, subprocess
import host
from stock_emulator import StockMath, calibration_oracle, OBJECT, OUT
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
binary=P.parent/'kernel328/stats-source/com.qti.stats.awb.so'
manifest=json.loads((P.parent/'kernel328/oem-stats-source.json').read_text())
pin=next(r for r in manifest['files'] if r['file']==binary.name)
assert hashlib.sha256(binary.read_bytes()).hexdigest()==pin['sha256']
f32=lambda value:struct.unpack('<f',struct.pack('<f',value))[0]
cal_engine=StockMath(binary,0x9e30,0xa8fc)
cct_engine=StockMath(binary,0x9bc0,0x9d70)
mwb_engine=StockMath(binary,0x8f24,0x9114)
assert cct_engine.read(0x463ac,'<16I')==(0,12000,1,7500,2,6500,3,5000,5,4000,7,2850,8,2300,9,1500)
rows=[];input_data=bytearray();expected=bytearray();cal_cases=[]

def calibration(name,ccts,golden,unit,unit_ccts=None):
 result,_=calibration_oracle(binary,ccts,golden,unit,unit_ccts,engine=cal_engine)
 n=len(ccts);zeros=[[0.,0.]]*(6-n)
 input_data.extend(struct.pack('<II30f',1,n,*(ccts+[0.]*(6-n)),
  *[v for row in golden+zeros for v in row],*[v for row in unit+zeros for v in row]))
 expected.extend(struct.pack('<20f',*[v for row in result for v in row]))
 cal_cases.append(dict(case=name,cct_slots=ccts,output_values=20))
 return result

# Cover every nonempty subset of the six actual OEM illuminant buckets.
temperatures=[6500.,5000.,4100.,3800.,2850.,2300.]
for mask in range(1,64):
 indices=[i for i in range(6) if mask&(1<<i)]
 calibration('bucket-subset-'+str(mask),[temperatures[i] for i in indices],
  [[f32(.7+i*.13),f32(.8+i*.09)] for i in indices],
  [[f32(1.1+i*.17),f32(.9+i*.11)] for i in indices])
# All equality boundaries plus duplicate-bucket, last-record-wins behaviour.
for kelvin in [2574.,2575.,3424.,3425.,3999.,4000.,4499.,4500.,5999.,6000.]:
 calibration('bucket-boundary-'+str(kelvin),[6500.,kelvin,2300.],
  [[1.,1.],[.7,.8],[.9,1.1]],[[1.1,1.2],[1.3,1.4],[1.5,1.6]])

bundle=json.loads((P.parent/'kernel328/wb-reference-bundle-private.json').read_text())
calibrated={};cct_cases=[]
queries=sorted({100.,1500.,12000.,20000.,*[float(k) for k in [7500,6500,5000,4000,2850,2300]],
 *[(a+b)*.5 for a,b in zip([12000,7500,6500,5000,4000,2850,2300],[7500,6500,5000,4000,2850,2300,1500])],
 *[k+d for k in [7500.,6500.,5000.,4000.,2850.,2300.,1500.] for d in [-.125,.125]]})
payload_independent=[]
for name,source in bundle.items():
 cal=next(r['data'] for r in source['factory_roots'] if r['tag']=='sensorCalV1')
 ccts=cal['cct'][:cal['num_of_cal_factors']]
 golden=cal['points'][:len(ccts)];unit=[[r['ratio_rg'],r['ratio_bg']] for r in source['unit_payload']]
 factors=calibration(name,ccts,golden,unit,[r['cct'] for r in source['unit_payload']])
 altered,_=calibration_oracle(binary,ccts,golden,unit,[999]*len(ccts),engine=cal_engine)
 assert factors==altered
 payload_independent.append(name)
 calibrated[name]=dict(factors=factors,reference_ratios=[])
 for root in [r for r in source['factory_roots'] if r['tag']=='MWBGainV1']:
  ratios=[[f32(f32(g/r)*factors[i][0]),f32(f32(g/b)*factors[i][1])]
   for i,(r,g,b) in enumerate(root['data']['gains'])]
  mwb_engine.write(OUT,'<Q',OUT+0x100)
  mwb_engine.write(OUT+0x120,'<30f',*[v for row in root['data']['gains'] for v in row])
  mwb_engine.write(OBJECT+0x47cb0,'<20f',*[v for row in factors for v in row])
  mwb_engine.fragment()
  stock=list(mwb_engine.read(OBJECT+0x96e,'<20f'))
  assert stock==[v for row in ratios for v in row]
  input_data.extend(struct.pack('<I50f',3,*[v for row in root['data']['gains'] for v in row],*[v for row in factors for v in row]))
  expected.extend(struct.pack('<20f',*stock))
  calibrated[name]['reference_ratios'].append(dict(uid=root['uid'],ratios=ratios))
  cct_engine.write(OBJECT+0x96e,'<20f',*[v for row in ratios for v in row])
  for kelvin in queries:
   cct_engine.call(s0=kelvin);values=cct_engine.read(OUT,'<2f')
   input_data.extend(struct.pack('<I21f',2,*[v for row in ratios for v in row],kelvin))
   expected.extend(struct.pack('<2f',*values))
   cct_cases.append(dict(module=name,root_uid=root['uid'],kelvin=kelvin))
(P/'calibrated-ratios-private.json').write_text(json.dumps(calibrated,indent=2)+'\n')
(P/'math-input-private.bin').write_bytes(input_data);(P/'stock-expected-private.bin').write_bytes(expected)
flags=['-std=c++17','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror']
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');relative=Path('/private/camss329-math');stage=sdk/str(relative).lstrip('/')
stage.mkdir(mode=0o700,exist_ok=True);(stage/'libipa').mkdir(exist_ok=True)
for name in ['math-runner.cpp','libipa/awb_calibration.cpp','libipa/awb_calibration.h']:shutil.copyfile(HERE/name,stage/name)
shutil.copyfile(P/'math-input-private.bin',stage/'math-input-private.bin')
for label in ['host','aarch64']:
 executable=P/('math-'+label)
 if label=='host':
  args=['g++',*flags,str(HERE/'math-runner.cpp'),str(HERE/'libipa/awb_calibration.cpp'),'-o',str(executable)]
 else:args=['chroot',str(sdk),'g++',*flags,str(relative/'math-runner.cpp'),str(relative/'libipa/awb_calibration.cpp'),'-o',str(relative/'math-aarch64')]
 q=subprocess.run(args,capture_output=True)
 (P/(label+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(label+'-output-private.bin')
 args=[str(executable),str(P/'math-input-private.bin'),str(output)] if label=='host' else ['chroot',str(sdk),str(relative/'math-aarch64'),str(relative/'math-input-private.bin'),str(relative/'aarch64-output-private.bin')]
 q=subprocess.run(args,capture_output=True,timeout=30)
 assert not q.returncode,(label,q.returncode,q.stderr.decode())
 if label=='aarch64':shutil.copyfile(stage/'aarch64-output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected)
 pairs=list(zip(struct.unpack('<'+'f'*(len(actual)//4),actual),struct.unpack('<'+'f'*(len(expected)//4),expected)))
 differences=[(i,a,b) for i,(a,b) in enumerate(pairs) if a!=b]
 (P/(label+'-differences-private.json')).write_text(json.dumps(differences,indent=2)+'\n')
 rows.append(dict(architecture=label,values=len(pairs),differing_values=len(differences),
  maximum_absolute_error=max((abs(a-b) for _,a,b in differences),default=0.)))
 assert not differences,dict(architecture=label,first_differences=differences[:5])
report=dict(stage=329,stock_instruction_oracle='Unicorn ARM64 2.1.4, selected functions only; all log calls stubbed; exceptions/syscalls rejected',
 source=pin,calibration_cases=len(cal_cases),illuminant_subsets=63,cct_lookup_cases=len(cct_cases),
 actual_factory_mwb_roots=19,calibration_unit_payload_cct_independence=payload_independent,
 mwb_conversion_instruction_block=['0x8f24','0x9114'],mwb_conversion_stock_instructions=mwb_engine.instructions,
 host_and_aarch64=rows,stock_calibration_instructions=cal_engine.instructions,stock_lookup_instructions=cct_engine.instructions,
 native_oem_library_loaded=False,phone_changed=False,dynamic_ipa_integration=False,passed=True)
(P/'math-cases-private.json').write_text(json.dumps(dict(calibration=cal_cases,cct_lookup=cct_cases),indent=2)+'\n')
(HERE/'math-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
