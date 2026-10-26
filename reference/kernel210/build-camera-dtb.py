from pathlib import Path
import hashlib,json,os,shlex,struct,subprocess,sys
from fdt_compare import parser,compare
os.umask(0o077)
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel210')/('camera-dtb-r2' if '--fixed-bus-label' in sys.argv else 'camera-dtb');out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'];before={n:sha(k/n) for n in names}
recipe=(k/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=',1)[1]
commands=[];current=[]
for token in shlex.split(recipe):
    if token==';':commands.append(current);current=[]
    else:current.append(token)
commands.append(current);assert len(commands)==3
base='arch/arm64/boot/dts/qcom/'
mapping={base+'.sm8150-samurai.dtb.d.pre.tmp':str(out/'source-pre.d'),base+'.sm8150-samurai.dtb.d.dtc.tmp':str(out/'dtc.d'),base+'.sm8150-samurai.dtb.dts.tmp':str(out/'camera.pp.dts'),base+'sm8150-samurai.dtb':str(out/'camera.dtb')}
def rewrite(value):
    for original,target in sorted(mapping.items(),key=lambda item:-len(item[0])):value=value.replace(original,target)
    return value
for i,args in enumerate(commands[:2]):
    command=[rewrite(v) for v in args];assert Path(command[command.index('-o')+1]).parent==out
    p=subprocess.run(command,cwd=k,capture_output=True);(out/(str(i)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
yaml=out/'camera.yaml';p=subprocess.run(['dtc','-O','yaml','-o',str(yaml),str(out/'camera.pp.dts')],capture_output=True)
(out/'source-yaml-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
parse=parser();old=parse((out.parent.parent/'kernel204/sm8150-samurai-bt-wake-static-private.dtb').read_bytes());new=parse((out/'camera.dtb').read_bytes());result=compare(old,new,yaml)
assert result['only_old_nodes']==[]
cci='/soc@0/cci@ac4b000';sensor=cci+'/i2c-bus@1/camera@10';camss='/soc@0/camss@acb3000';pmic='/soc@0/geniqup@8c0000/i2c@890000/pmic@4';vio='/soc@0/rsc@18200000/regulators-1/ldo1';gpio='/soc@0/spmi@c440000/pmic@4/gpio@c000';tlmm='/soc@0/pinctrl@3100000'
expected_new={gpio+'/camera-rear-reset-hog',pmic,pmic+'/regulators',pmic+'/regulators/ldo2',pmic+'/regulators/ldo5',sensor,sensor+'/port',sensor+'/port/endpoint',camss+'/ports/port@2',camss+'/ports/port@2/endpoint'}
expected_new|={tlmm+'/camera-front-'+n+'-state' for n in ['mclk-active','mclk-sleep','select-active','select-sleep','reset']}
assert set(result['only_new_nodes'])==expected_new,result['only_new_nodes']
assert {(p['path'],p['property']) for p in result['remaining_changed_properties']}=={(cci,'status'),(vio,'phandle')},result['remaining_changed_properties']
handles={int.from_bytes(props['phandle'],'big'):path for path,props in new.items() if 'phandle' in props}
def cells(path,name):
    data=new[path][name];assert len(data)%4==0;return struct.unpack('>'+str(len(data)//4)+'I',data)
def target(path,name):return handles[cells(path,name)[0]]
assert target(sensor,'vif-supply')==vio
assert target(sensor,'vana-supply')==pmic+'/regulators/ldo5'
assert target(sensor,'vdig-supply')==pmic+'/regulators/ldo2'
assert target(pmic,'reset-gpios')==gpio and cells(pmic,'reset-gpios')[1:]==(4,1)
assert cells(gpio+'/camera-rear-reset-hog','gpios')==(1,0) and 'output-low' in new[gpio+'/camera-rear-reset-hog']
assert target(sensor+'/port/endpoint','remote-endpoint')==camss+'/ports/port@2/endpoint'
assert target(camss+'/ports/port@2/endpoint','remote-endpoint')==sensor+'/port/endpoint'
assert cells(sensor,'assigned-clock-rates')==(19200000,)
assert int.from_bytes(new[sensor+'/port/endpoint']['link-frequencies'],'big')==200000000
assert cells(sensor+'/port/endpoint','data-lanes')==(1,2,3,4)
assert 'bias-pull-down' in new[tlmm+'/camera-front-mclk-sleep-state']
assert {n:sha(k/n) for n in names}==before
report=dict(stage=210,candidate_dtb_sha256=sha(out/'camera.dtb'),only_intended_camera_nodes_and_cci_enable_vio_phandle_changed=True,existing_artifacts_unchanged=True,graph_links_and_supplies_checked=True,source_yaml_reference_markers_used=True,scalar_cells_not_remapped=True,**result)
(here/'camera-dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='only_new_nodes'}))
