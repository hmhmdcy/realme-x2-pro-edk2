"""Check integrated production serialization, not a separate copy of the body."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;v=storage.mount.mounted_build().parent;k=v/'source354/drivers/media/platform/qcom/camss'
ipe=(k/'camss-icp-a5-ipe.c').read_text();prototype=(HERE/'pd10-striping.c').read_text();assert ipe.endswith(prototype)
model=(P/'geometry-model.c').read_text();start=model.index('int main(void){');code=model[:start]+(HERE/'geometry-contract.c').read_text()
assert prototype in code
(P/'geometry-contract-model.c').write_text(code);outputs=[]
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 binary=P/('geometry-contract-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'geometry-contract-model.c'),'-o',str(binary)],capture_output=True);(P/(arch+'-contract-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(binary)],capture_output=True);(P/(arch+'-contract-run.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode();outputs.append(q.stdout)
assert outputs[0]==outputs[1]==b'GEOMETRY_CONTRACT invalid=26 dc-off=6 result=0\n'
report=dict(stage=441,integrated_production_geometry_body_byte_identical_to_tested_prototype=True,production_file_sha256=hashlib.sha256(ipe.encode()).hexdigest(),invalid_geometry_null_and_capacity_preserve_output_and_used_per_architecture=26,dc_disabled_single_pass_byte_identical_cases_per_architecture=6,host_asan_ubsan=True,aarch64_static_qemu=True,phone_accessed=False,passed=True)
(HERE/'geometry-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
