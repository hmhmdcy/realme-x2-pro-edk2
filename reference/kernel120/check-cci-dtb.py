from pathlib import Path
import subprocess,json,struct,hashlib,os
import libfdt
root=Path('/home/cy122/pmos-samurai-kernel118/camera120');k=root/'kernel';out=Path('/mnt/e/edk2-samurai-out/kernel120')
assert root.parent.is_mount()
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb';raw=dtb.read_bytes();fdt=libfdt.Fdt(raw)
records=[]
for suffix,irq in [('a',460),('b',271)]:
    path=f'/soc@0/cci@ac4{suffix}000'
    node=fdt.path_offset(path)
    prop=lambda key:bytes(fdt.getprop(node,key))
    assert prop('compatible').split(b'\0')[:-1]==[b'qcom,sm8150-cci',b'qcom,msm8996-cci']
    assert prop('status')==b'disabled\0'
    reg=struct.unpack('>4I',prop('reg'));assert reg==(0,int(f'ac4{suffix}000',16),0,4096)
    intr=struct.unpack('>3I',prop('interrupts'));assert intr==(0,irq,1)
    for master in [0,1]:
        child=fdt.path_offset(path+f'/i2c-bus@{master}')
        assert struct.unpack('>I',fdt.getprop(child,'clock-frequency'))==(100000,)
        assert fdt.first_subnode(child,quiet=libfdt.QUIET_NOTFOUND)<0
    records.append(dict(node=path,irq=irq,disabled=True,buses=2,default_hz=100000,no_sensor_children=True))
mutations=[]
for name,key,value in [('bad-fallback','compatible',b'qcom,sm8150-cci\0qcom,sdm845-cci\0'),('bad-clock-name','clock-names',b'invalid\0')]:
    broken=libfdt.Fdt(raw);broken.resize(len(raw)+256)
    broken.setprop(broken.path_offset('/soc@0/cci@ac4a000'),key,value)
    p=out/f'negative-{name}-private.dtb';p.write_bytes(broken.as_bytearray())
    cmd=[str(root/'schema-venv/bin/dt-validate'),'-s',str(out/'processed-cci-private.json'),'-l','qcom,i2c-cci',str(p)]
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
    log=out/f'negative-{name}-private.txt';log.write_bytes(proc.stdout)
    assert b'cci@ac4a000' in proc.stdout and b'qcom,i2c-cci' in proc.stdout
    mutations.append(dict(name=name,diagnostics_detected=True,exit=proc.returncode,diagnostic_bytes=len(proc.stdout)))
report=dict(actual_cci_nodes_verified=records,negative_controls=mutations,validator_exit_alone_not_used=True,no_phone_changes=True,dtb_sha256=hashlib.sha256(raw).hexdigest())
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120/cci-dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
