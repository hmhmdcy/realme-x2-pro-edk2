"""Build and schema-check the extra rear camera without changing the phone DT."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270')
W=Path('/home/cy122/x2pro-linux/camera270-kernel');B=Path('/home/cy122/x2pro-linux/camera270-build-r1')
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup',KBUILD_BUILD_VERSION='270')
attempt=2 if (B/'board-private.log').exists() else 1
with (B/('board-r'+str(attempt)+'-private.log')).open('xb') as log:
 q=subprocess.run(['make','-C',str(W),'O='+str(B),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j3','qcom/sm8150-samurai.dtb'],env=env,stdout=log,stderr=subprocess.STDOUT)
assert q.returncode==0
pp=P/'telephoto.pp.dts';yaml=P/'telephoto.yaml';dtb=B/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
q=subprocess.run(['cpp','-nostdinc','-undef','-D__DTS__','-x','assembler-with-cpp','-I',str(W/'scripts/dtc/include-prefixes'),str(W/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'),'-o',str(pp)],capture_output=True);assert q.returncode==0
q=subprocess.run(['dtc','-I','dts','-O','yaml','-o',str(yaml),str(pp)],capture_output=True)
(P/'telephoto-dtc-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
spec=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
parse=f.parser();old=parse(Path('/home/cy122/x2pro-linux/camera269-full-build-r1/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes());new=parse(dtb.read_bytes())
delta=f.compare(old,new,yaml);(P/'telephoto-dtb-semantic-private.json').write_text(json.dumps(delta,indent=2)+'\n')
assert not delta['only_old_nodes']
tele=next(n for n,p in new.items() if p.get('compatible')==b'samsung,s5k3m5\0')
pmic=next(n for n,p in new.items() if n.endswith('/pmic@8') and p.get('qcom,address-setup-supplier'))
cci=tele.rsplit('/',1)[0]
allowed_new={tele,tele+'/port',tele+'/port/endpoint',pmic+'/regulators/ldo2',pmic+'/regulators/ldo6',
 '/soc@0/pinctrl@3100000/camera-tele-mclk-active-state','/soc@0/pinctrl@3100000/camera-tele-mclk-sleep-state',
 '/soc@0/pinctrl@3100000/camera-tele-reset-state','/soc@0/camss@acb3000/ports/port@3','/soc@0/camss@acb3000/ports/port@3/endpoint'}
assert set(delta['only_new_nodes'])==allowed_new,(set(delta['only_new_nodes'])-allowed_new,allowed_new-set(delta['only_new_nodes']))
changed={(row['path'],row['property']) for row in delta['remaining_changed_properties']}
assert changed<={(cci,'status')},changed
validations={}
for select in ['samsung,s5k3m5','qcom,sm8150-camss','qcom,pm8008','reserved-memory']:
 q=subprocess.run(['/home/cy122/x2pro-linux/.venv-dtschema/bin/dt-validate','-s',str(P/'schema270.json'),'-l',select,str(dtb)],capture_output=True)
 (P/('telephoto-schema-r'+str(attempt)+'-'+select.replace(',','-')+'-private.log')).write_bytes(q.stdout+q.stderr)
 validations[select]=dict(exit=q.returncode,diagnostic_bytes=len(q.stdout+q.stderr))
 assert q.returncode==0 and not q.stdout and not q.stderr,(select,'inspect private schema diagnostics')
report=dict(stage=270,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),new_nodes=len(allowed_new),
 no_existing_nodes_removed=True,existing_property_changes=[list(v) for v in sorted(changed)],schema_validations=validations,
 existing_imx319_imx471_and_pmic_properties_preserved=True,all_other_existing_peripheral_properties_preserved=True,
 static_sensor_and_standard_regulator_nodes=True,hardware_not_yet_probed=True,phone_unchanged=True)
(R/'telephoto-board-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
