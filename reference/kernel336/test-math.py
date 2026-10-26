from pathlib import Path
import json,math,random,shutil,struct,subprocess
import host
from stock_lux import StockLux
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
engine=StockLux(P.parent/'kernel328/stats-source/com.qti.stats.aec.so');inputs=bytearray();expected=bytearray();counts={}
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
def add(mode,data,a=0,b=0):
 inputs.extend(struct.pack('<I',mode)+data);expected.extend(struct.pack('<I2f',1,a,b));counts[mode]=counts.get(mode,0)+1
bundle=json.loads((P/'factory-aec-bundle-private.json').read_text())
anchors=[];zero_correction_tables=0;undefined_sensitivity_cases=0
for source in bundle.values():
 for root in source['roots']['Arbitration']:
  for table in root['data']['expTables']:
   first=table['expKneeEntries'][0];anchor=(first['gain'],first['expTime'],first['expIndex']);anchors.append((anchor,table['sensitivityCorrectionFactor']))
   if table['sensitivityCorrectionFactor']==0:zero_correction_tables+=1
   for knee in table['expKneeEntries']:
    add(1,struct.pack('<fQffQ',*anchor,knee['gain'],knee['expTime']),engine.manual(anchor,knee['gain'],knee['expTime']))
    sensitivity=f32(f32(table['sensitivityCorrectionFactor']*knee['gain'])*f32(knee['expTime']))
    if table['sensitivityCorrectionFactor']>0:
     add(2,struct.pack('<fQfff',*anchor,table['sensitivityCorrectionFactor'],sensitivity),engine.sensitivity(anchor,table['sensitivityCorrectionFactor'],sensitivity))
    else:undefined_sensitivity_cases+=1
# Nonzero anchors, negative indices and nanosecond float conversion boundaries.
for anchor in [(1.,16708,0.),(1.5,33333,17.25),(3.125,16777217,-12.5)]:
 for gain in [.25,1.,2.75,64.]:
  for ns in [1,9999,16777215,16777217,100000000,60000000000]:
   add(1,struct.pack('<fQffQ',*anchor,gain,ns),engine.manual(anchor,gain,ns))
def configure(comp,reference,zero,factor):
 engine.configure(comp,reference,zero,factor);add(3,struct.pack('<I3f',int(comp),reference,zero,factor))
for comp,reference,zero in [(False,0.,0.),(True,10000.,16708.),(True,33333.,10000.),(True,1.,100000.)]:
 for factor in [0.,.125,.5,.99,1.]:
  configure(comp,reference,zero,factor)
  for i,(index,luma) in enumerate([(0.,255.),(120.,50.),(300.,.1),(200.,10.),(100.,100.),(-20.,50.),(450.,.2)]):
   reset=i==4;add(4,struct.pack('<ffI',index,luma,int(reset)),engine.lux(index,luma,reset))
# Full OEM calculateLuma wrapper, one supplied 256-cell processed grid callback.
randomizer=random.Random(336)
for cells in [[0.]*256,[50.]*256,[255.]*256,[i*255/255 for i in range(256)],*[ [randomizer.random()*255 for _ in range(256)] for _ in range(8)]]:
 cells=[f32(v) for v in cells];configure(True,10000.,16708.,.5)
 for index in [0.,100.,350.]:
  a,b=engine.cells(index,cells);add(5,struct.pack('<fI256f',index,0,*cells),a,b)
(P/'math-input-private.bin').write_bytes(inputs);(P/'math-expected-private.bin').write_bytes(expected)
relative=Path('/private/camss336-lux');stage=SDK/str(relative).lstrip('/');(stage/'libipa').mkdir(parents=True,exist_ok=True)
for n in ['lux-runner.cpp','libipa/aec_lux.cpp','libipa/aec_lux.h']:shutil.copyfile(HERE/n,stage/n)
shutil.copyfile(P/'math-input-private.bin',stage/'input-private.bin');rows=[]
for arch in ['host','aarch64']:
 flags=['-std=c++17','-O2','-Wall','-Wextra','-Werror']
 exe=P/('math-'+arch)
 cmd=['g++',*flags,str(HERE/'lux-runner.cpp'),str(HERE/'libipa/aec_lux.cpp'),'-o',str(exe)] if arch=='host' else ['chroot',str(SDK),'g++',*flags,str(relative/'lux-runner.cpp'),str(relative/'libipa/aec_lux.cpp'),'-o',str(relative/'math-aarch64')]
 q=subprocess.run(cmd,capture_output=True);(P/(arch+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 output=P/(arch+'-output-private.bin')
 cmd=[str(exe),str(P/'math-input-private.bin'),str(output)] if arch=='host' else ['chroot',str(SDK),str(relative/'math-aarch64'),str(relative/'input-private.bin'),str(relative/'output-private.bin')]
 q=subprocess.run(cmd,capture_output=True);assert not q.returncode,(arch,q.returncode,q.stderr.decode())
 if arch=='aarch64':shutil.copyfile(stage/'output-private.bin',output)
 actual=output.read_bytes();assert len(actual)==len(expected);different=sum(a!=b for a,b in zip(actual,expected))
 row=dict(architecture=arch,cases=sum(counts.values()),differing_bytes=different,compared_bytes=len(expected));rows.append(row)
 if different:
  mismatches=[(i//12,struct.unpack_from('<I2f',actual,i//12*12),struct.unpack_from('<I2f',expected,i//12*12)) for i,(a,b) in enumerate(zip(actual,expected)) if a!=b];(P/(arch+'-mismatches-private.json')).write_text(json.dumps(mismatches[:30],indent=2));raise AssertionError(row)
report=dict(stage=336,architectures=rows,case_modes={str(k):v for k,v in counts.items()},original_oem_instructions=True,log10_is_host_math_stub=True,
 exposure_index_manual_full_function=True,sensitivity_to_index_math_fragment=True,lux_index_full_function=True,processed_luma_full_wrapper=True,raw_bayer_preprocessing_not_recovered=True,
 default_compiler_fma_contraction_supported=True,zero_correction_factory_tables_preserved=zero_correction_tables,undefined_zero_division_sensitivity_cases_excluded=undefined_sensitivity_cases,
 invalid_inputs_rejected_by_generic_api=True,ipa_integrated=False,phone_changed=False,emulator_calls=engine.calls,emulator_instructions=engine.instructions,passed=True)
(HERE/'math-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
