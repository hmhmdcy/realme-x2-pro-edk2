from pathlib import Path
import hashlib,json,shlex,subprocess
from fdt_compare import parser,compare
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel211/sensor-domain-dtb');out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();names=['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'];before={n:sha(k/n) for n in names}
recipe=(k/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=',1)[1];commands=[];current=[]
for token in shlex.split(recipe):
    if token==';':commands.append(current);current=[]
    else:current.append(token)
commands.append(current);assert len(commands)==3
base='arch/arm64/boot/dts/qcom/';mapping={base+'.sm8150-samurai.dtb.d.pre.tmp':str(out/'source-pre.d'),base+'.sm8150-samurai.dtb.d.dtc.tmp':str(out/'dtc.d'),base+'.sm8150-samurai.dtb.dts.tmp':str(out/'sensor-domain.pp.dts'),base+'sm8150-samurai.dtb':str(out/'sensor-domain.dtb')}
def rewrite(v):
    for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):v=v.replace(a,b)
    return v
for i,args in enumerate(commands[:2]):
    p=subprocess.run([rewrite(v) for v in args],cwd=k,capture_output=True);(out/(str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
yaml=out/'sensor-domain.yaml';p=subprocess.run(['dtc','-O','yaml','-o',str(yaml),str(out/'sensor-domain.pp.dts')],capture_output=True);(out/'yaml-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
parse=parser();old=parse((out.parent.parent/'kernel210/camera-dtb-r2/camera.dtb').read_bytes());new=parse((out/'sensor-domain.dtb').read_bytes());result=compare(old,new,yaml)
assert result['only_old_nodes']==result['only_new_nodes']==[]
assert result['remaining_changed_properties']==[dict(path='/soc@0/cci@ac4b000/i2c-bus@1/camera@10',property='power-domains')]
sensor=new['/soc@0/cci@ac4b000/i2c-bus@1/camera@10'];cci=new['/soc@0/cci@ac4b000'];assert sensor['power-domains']==cci['power-domains']
assert before=={n:sha(k/n) for n in names}
report=dict(stage=211,candidate_dtb_sha256=sha(out/'sensor-domain.dtb'),only_sensor_power_domain_added=True,existing_build_artifacts_preserved=True,same_titan_top_as_cci_provider=True,**result)
(here/'sensor-domain-dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
