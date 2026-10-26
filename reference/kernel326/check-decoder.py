from pathlib import Path
import json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
decoded=json.loads((P/'decoded-unit-private.json').read_text());layouts=json.loads((P/'descriptor-layouts-private.json').read_text());cases={}
for name,item in decoded.items():
 for i,row in enumerate(layouts[name]['lights']['lsc']['rows']):
  base=row[3];low=[row[3+4*c]-base for c in range(4)];key=(item['model'],base,tuple(low))
  expected=[v for channel in item['lsc'][i]['channels'] for v in channel]
  if key in cases:assert cases[key]==expected
  else:cases[key]=expected
runs=[]
for arch,compiler,runner in [('host','gcc',[]),('aarch64','aarch64-linux-gnu-gcc',['qemu-aarch64'])]:
 binary=P/('decode-unit-'+arch);q=subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-Werror','-static',str(HERE/'decode-unit.c'),'-o',str(binary)],capture_output=True)
 (P/('decoder-build-'+arch+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 values=0
 for (model,base,low),expected in cases.items():
  for sample in [1,2]:
   q=subprocess.run([*runner,str(binary),str(P/'reads-r2'/(model+f'-read{sample}-private.bin')),str(base),*[str(v) for v in low]],capture_output=True,check=True)
   assert list(struct.unpack('<884H',q.stdout))==expected;values+=884
 runs.append(dict(architecture=arch,source_cases=len(cases),retained_samples_per_case=2,channel_values_compared=values,all_equal=True))
report=dict(stage=326,independent_sequential_c_vs_random_address_python=True,actual_descriptor_alias_preserved=True,runs=runs,passed=True)
(HERE/'decoder-crosscheck-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
