from pathlib import Path
import runpy,subprocess,json,os,hashlib
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118/camera120');k=root/'kernel';bin=root/'schema-venv/bin'
out=Path('/mnt/e/edk2-samurai-out/kernel120');schema=k/'Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml'
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
env=dict(os.environ,TMPDIR=str(root))
commands=[('doc',[str(bin/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)]),('compile-schema',[str(bin/'dt-mk-schema'),'-j','-o',str(out/'processed-cci-private.json'),str(schema),str(k/'Documentation/devicetree/bindings/i2c/i2c-controller.yaml')]),('dtb',[str(bin/'dt-validate'),'-s',str(out/'processed-cci-private.json'),'-l','qcom,i2c-cci',str(dtb)])]
results=[]
for name,args in commands:
    logfile=out/f'cci-schema-{name}-private.txt'
    with logfile.open('w') as log:p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=90)
    results.append(dict(step=name,exit=p.returncode,diagnostic_bytes=logfile.stat().st_size))
    print(name,p.returncode,logfile.stat().st_size)
    if p.returncode or logfile.stat().st_size:
        print('\n'.join(logfile.read_text().splitlines()[-15:]))
    assert p.returncode==0
assert (out/'cci-schema-dtb-private.txt').stat().st_size==0
report=dict(dtschema_version='2026.9',schema_checks=results,cci_dtb_validation_no_diagnostics=True,full_board_schema_validation=False,dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),phone_not_changed=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120/cci-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
