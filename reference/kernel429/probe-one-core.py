from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
n=module('native425',HERE.parent/'kernel425/native-model.py');fw=module('firmware429',HERE/'firmware-model.py')
config=(P.parent/'kernel425/width-640-dc-1-config-private.bin').read_bytes();iq=(P.parent/'kernel424/coarse-width-640-dc-1-iq-private.bin').read_bytes()
actual=(P/'actual-c-stripe-private.bin').read_bytes();rows=[]
for cores in [1,2]:
 native=n.Native();gold,bl,cap=native.striping(config,640,480,cores,iq)
 model,job,commands,scratch=fw.prepare(config,actual,iq,cores)
 _,gj,gc,_=fw.prepare(config,gold,iq,cores);assert job==gj and commands==gc
 (P/f'cores-{cores}-native-cdm-private.bin').write_bytes(commands)
 rows.append(dict(max_cores=cores,job_equal=True,whole_command_bytes_compared=len(commands),different_command_bytes=0,scratch_bytes=scratch))
r=dict(stage=429,original_hal_and_firmware_core_count_input_only=True,rows=rows,one_core_hardware_test_not_yet_run=True,passed=True)
(HERE/'one-core-oracle-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
