"""Compile a matched board DTB and check the exact semantic delta from boot235."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel267')
K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=P/'board-build-r1';audit=sys.argv[1:]==['--audit-existing']
assert not sys.argv[1:] or audit
if audit:
    for n in ['sm8150-samurai.dts','imx319.dtsi']:assert (R/n).read_bytes()==(out/n).read_bytes()
else:
    out.mkdir(mode=0o700)
    for n in ['sm8150-samurai.dts','imx319.dtsi']:shutil.copyfile(R/n,out/n)
recipe=(K/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=',1)[1]
commands=[];current=[]
for token in shlex.split(recipe):
    if token==';':commands.append(current);current=[]
    else:current.append(token)
commands.append(current);assert len(commands)==3
base='arch/arm64/boot/dts/qcom/'
mapping={base+'sm8150-samurai.dts':str(out/'sm8150-samurai.dts'),
 base+'.sm8150-samurai.dtb.d.pre.tmp':str(out/'pre.d'),
 base+'.sm8150-samurai.dtb.d.dtc.tmp':str(out/'dtc.d'),
 base+'.sm8150-samurai.dtb.dts.tmp':str(out/'sm8150-samurai.pp.dts'),
 base+'sm8150-samurai.dtb':str(out/'sm8150-samurai.dtb')}
def rewrite(arg):
    for a,b in sorted(mapping.items(),key=lambda x:-len(x[0])):arg=arg.replace(a,b)
    return arg
for i,args in enumerate([] if audit else commands[:2]):
    args=[rewrite(x) for x in args]
    if i==0:args+=['-iquote',str(K/base)]
    q=subprocess.run(args,cwd=K,capture_output=True,timeout=60)
    (out/(str(i)+'-private.log')).write_bytes(q.stdout+q.stderr)
    assert q.returncode==0,q.stderr[-2000:]
if not audit:
    q=subprocess.run(['dtc','-O','yaml','-o',str(out/'sm8150-samurai.yaml'),str(out/'sm8150-samurai.pp.dts')],capture_output=True,timeout=60)
    (out/'yaml-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
spec=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
parse=f.parser()
old=parse((P.parent/'kernel235/board-build-r2/imx319-p-lab.dtb').read_bytes())
dtb=out/'sm8150-samurai.dtb';new=parse(dtb.read_bytes())
delta=f.compare(old,new,out/'sm8150-samurai.yaml')
(out/'semantic-private.json').write_text(json.dumps(delta,indent=2)+'\n')
cells=lambda b:[int.from_bytes(b[i:i+4],'big') for i in range(0,len(b),4)]
one=lambda pred:next(p for p in new if pred(p))
q=one(lambda p:p.endswith('/pmic@4') and 'qcom,initial-address' in new[p])
p=q.rsplit('/',1)[0]+'/pmic@8'
rear=one(lambda p:new[p].get('compatible')==b'sony,imx319\0')
front=one(lambda p:new[p].get('compatible')==b'sony,imx471\0')
handle=lambda path:cells(new[path]['phandle'])[0]
assert cells(new[p]['reset-gpios'])[1:]==[1,1]
assert cells(new[q]['reset-gpios'])[1:]==[4,1]
assert cells(new[p]['qcom,address-setup-supplier'])==[handle(q)]
assert new[p]['vdd-l1-l2-supply']==new[q]['vdd-l1-l2-supply']
assert cells(new[rear]['orientation'])==[1] and 'rotation' not in new[rear]
assert cells(new[rear]['vana-supply'])==[handle(p+'/regulators/ldo4')]
assert cells(new[rear]['vdig-supply'])==[handle(p+'/regulators/ldo1')]
assert {x.rsplit('/',1)[-1] for x in new if x.startswith(p+'/regulators/')}=={'ldo1','ldo4'}
assert {x.rsplit('/',1)[-1] for x in new if x.startswith(q+'/regulators/')}=={'ldo2','ldo5'}
assert not any('realme,imx319-power-lab' in props or props.get('compatible')==b'realme,rmx1931-pm8008-resets\0' for props in new.values())
assert not any(n in new[p] or n in new[q] for n in ['resets','vdd-l3-l4-supply','vdd-l5-supply'])
# The remaining tree may differ only in these documented properties.
allowed={(p,n) for n in ['resets','reset-gpios','vdd-l1-l2-supply','realme,imx319-power-lab']}
allowed|={(q,n) for n in ['resets','reset-gpios']}
allowed|={(rear,n) for n in ['compatible','orientation']}
removed=set(old)-set(new);assert removed=={'/camera-pmic-resets'},removed
assert set(new)-set(old)==set()
actual={(x['path'],x['property']) for x in delta['remaining_changed_properties']}
assert actual==allowed,(actual-allowed,allowed-actual)
report=dict(stage=267,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),
            pmic_gpio_reset_pins_verified=True,pmic_address_dependency_verified=True,
            known_nldo_parent_added=True,unknown_pldo_parent_not_invented=True,
            standard_sensor_compatible=True,rear_orientation_from_dt=True,
            only_removed_node='/camera-pmic-resets',new_nodes=[],semantic_delta=delta,
            unrelated_properties_unchanged=True,hardware_not_changed=True)
(R/'board-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
