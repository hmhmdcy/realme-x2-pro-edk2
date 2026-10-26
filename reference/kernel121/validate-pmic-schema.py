from pathlib import Path
import runpy,subprocess,json,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118');k=root/'camera121/kernel';bin=root/'camera120/schema-venv/bin'
out=Path('/mnt/e/edk2-samurai-out/kernel121/schema-test');out.mkdir(exist_ok=True)
schema=k/'Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml';processed=out/'processed-pm8008-private.json'
results=[]
def command(name,args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=90,env=dict(os.environ,TMPDIR=str(root/'camera121')))
    log=p.stdout+p.stderr;(out/(name+'.txt')).write_text(log)
    results.append(dict(name=name,exit=p.returncode,diagnostic_bytes=len(log.encode())))
    assert p.returncode==0
    return log
assert command('doc',[str(bin/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)])==''
assert command('compile',[str(bin/'dt-mk-schema'),'-j','-o',str(processed),str(schema)])==''
supplies='\n'.join(f'vdd-{group}-supply = <&synthetic_supply>;' for group in ['l1-l2','l3-l4','l5','l6','l7'])
irq='interrupt-parent = <&synthetic_irq>; interrupts = <32 1>; interrupt-controller; #interrupt-cells = <2>;'
gpio='gpio-controller; #gpio-cells = <2>; gpio-ranges = <&pmic 0 0 2>;'
base='compatible = "qcom,pm8008"; reg = <8>; '+supplies
cases=[('no-irq-regulators',base,True),('full-irq',base+irq+gpio+'#thermal-sensor-cells = <0>;',True),('missing-input',base.replace('vdd-l7-supply = <&synthetic_supply>;',''),False),('orphan-irq-cells',base+'#interrupt-cells = <2>;',False),('orphan-irq-controller',base+'interrupt-controller;',False),('no-irq-gpio',base+gpio,False),('no-irq-temperature',base+'#thermal-sensor-cells = <0>;',False),('orphan-gpio-cells',base+'#gpio-cells = <2>;',False),('unsupported-fallback',base.replace('"qcom,pm8008"','"qcom,pm8008", "qcom,pm8010-i2c"'),False)]
checks=[]
for name,properties,valid in cases:
    text='''/dts-v1/;
/ { #address-cells = <1>; #size-cells = <1>;
synthetic_supply: synthetic-supply { compatible = "regulator-fixed"; regulator-name = "OFFLINE-FIXTURE-ONLY"; #regulator-cells = <0>; };
synthetic_irq: synthetic-irq { interrupt-controller; #interrupt-cells = <2>; #address-cells = <0>; };
i2c@1000 { reg = <0x1000 0x100>; #address-cells = <1>; #size-cells = <0>;
pmic: pmic@8 { '''+properties+''' }; }; };
'''
    dts=out/(name+'.dts');dtb=out/(name+'.dtb');dts.write_text(text)
    p=subprocess.run([str(k/'scripts/dtc/dtc'),'-I','dts','-O','dtb','-o',str(dtb),str(dts)],capture_output=True,text=True,timeout=10)
    (out/(name+'-dtc.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0
    diagnostic=command(name,[str(bin/'dt-validate'),'-s',str(processed),'-l','qcom,pm8008',str(dtb)])
    assert (not diagnostic)==valid
    if not valid:assert 'pmic@8' in diagnostic
    checks.append(dict(name=name,expected_valid=valid,diagnostic_present=bool(diagnostic),accepted_as_expected=True))
# Board has no PM8008 nodes yet: checking it would be vacuous. Fixtures are
# deliberately synthetic and cannot be copied into a board DT or deployed.
report=dict(schema_checks=results,fixtures=checks,positive_cases=2,negative_cases=7,synthetic_supply_not_hardware_evidence=True,full_board_validation=False,no_pmic_board_nodes_yet=True,no_phone_changes=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel121/pmic-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(checks))
