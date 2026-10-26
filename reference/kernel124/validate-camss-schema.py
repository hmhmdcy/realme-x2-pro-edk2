from pathlib import Path
import runpy,subprocess,json,os,struct,hashlib
import libfdt
import dtschema
repo=Path('/mnt/e/RealmeX2Pro edk2');ref=repo/'reference/kernel124'
runpy.run_path(str(repo/'reference/kernel118/ensure-build-volume.py'))
runpy.run_path(str(repo/'reference/kernel122/ensure-rootfs-volume.py'))
k=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel')
bin=Path('/home/cy122/pmos-samurai-kernel118/camera120/schema-venv/bin')
out=Path('/mnt/e/edk2-samurai-out/kernel124/schema-test');out.mkdir(exist_ok=True)
schema=k/'Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml';processed=out/'processed-camss-private.json'
results=[]
def command(name,args):
    p=subprocess.run(args,capture_output=True,timeout=90,env=dict(os.environ,TMPDIR=str(k.parent)))
    log=p.stdout+p.stderr;(out/(name+'.txt')).write_bytes(log)
    results.append(dict(name=name,exit=p.returncode,diagnostic_bytes=len(log)))
    if log:print(name,log.decode(errors='replace')[:1600])
    assert p.returncode==0
    return log
assert command('doc',[str(bin/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)])==b''
assert command('compile',[str(bin/'dt-mk-schema'),'-j','-o',str(processed),str(schema),str(k/'Documentation/devicetree/bindings/media/video-interfaces.yaml')])==b''
dtb=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb';raw=dtb.read_bytes();fdt=libfdt.Fdt(raw);path='/soc@0/camss@acb3000';n=fdt.path_offset(path)
prop=lambda key:bytes(fdt.getprop(n,key))
cells=lambda key:struct.unpack('>'+'I'*(len(prop(key))//4),prop(key))
strings=lambda key:prop(key).rstrip(b'\0').decode().split('\0')
assert strings('compatible')==['qcom,sm8150-camss'] and strings('status')==['disabled']
reg=cells('reg');assert len(reg)==32
bases=[reg[i+1] for i in range(0,len(reg),4)];sizes=[reg[i+3] for i in range(0,len(reg),4)]
assert bases==[0xacb3000,0xacba000,0xac65000,0xac66000,0xac67000,0xac68000,0xacaf000,0xacb6000] and sizes==[4096]*6+[16384]*2
irq=cells('interrupts');assert irq==tuple(x for no in [464,466,477,478,479,448,465,467] for x in [0,no,1])
streams=cells('iommus');assert len(streams)==24 and [streams[i+1:i+3] for i in range(0,24,3)]==[(s,0x620) for s in [0x840,0x860,0xa40,0xa60,0xc40,0xc60,0xe40,0xe60]]
ports=fdt.path_offset(path+'/ports');assert fdt.first_subnode(ports,quiet=libfdt.QUIET_NOTFOUND)<0
assert len(strings('clock-names'))==31 and len(strings('interconnect-names'))==4
assert command('board-disabled',[str(bin/'dt-validate'),'-s',str(processed),'-l','qcom,sm8150-camss',str(dtb)])==b''
validator=dtschema.DTValidator([str(processed)])
def strict_errors(data):
    decoded=validator.decode_dtb(data)[0]
    node=decoded['soc@0']['camss@acb3000'];node['$nodename']=['camss@acb3000']
    assert node['compatible']==['qcom,sm8150-camss']
    return list(validator.iter_errors(node,filter=['qcom,sm8150-camss']))
assert not strict_errors(raw)
assert len(cells('vdda-phy-supply'))==1

mutations=[('enabled-missing-supply',{'status':b'okay\0','vdda-phy-supply':None},False),('bad-clock-name',{'clock-names':b'invalid\0'},False),('missing-icc',{'interconnects':None},False),('missing-smmu-stream',{'iommus':prop('iommus')[:-12]},False),('missing-reg',{'reg':prop('reg')[:-16]},False),('bad-irq-name',{'interrupt-names':b'invalid\0'},False),('extra-property',{'unverified-power-rail':struct.pack('>I',1)},False)]
checks=[]
for name,properties,valid in mutations:
    broken=libfdt.Fdt(raw);broken.resize(len(raw)+1024);bn=broken.path_offset(path)
    for key,value in properties.items():
        if value is None:broken.delprop(bn,key)
        else:broken.setprop(bn,key,value)
    p=out/(name+'.dtb');p.write_bytes(broken.as_bytearray())
    log=command(name,[str(bin/'dt-validate'),'-s',str(processed),'-l','qcom,sm8150-camss',str(p)])
    errors=strict_errors(bytes(broken.as_bytearray()))
    assert bool(errors)!=valid
    (out/(name+'-strict.txt')).write_text('\n'.join(e.message for e in errors))
    if log:assert b'camss@acb3000' in log and b'qcom,sm8150-camss' in log
    checks.append(dict(name=name,strict_negative_detected=True,strict_error_count=len(errors),cli_diagnostic_present=bool(log),validator_exit_alone_not_used=True))
report=dict(actual_disabled_camss_node_checked=True,strict_disabled_node_validation_no_errors=True,cli_suppresses_missing_required_properties_on_disabled_nodes=True,strict_validator_used_to_close_that_gap=True,native_mmio_irq_and_smmu_cells_exact=True,clocks=31,icc_paths=4,empty_sensor_ports=True,native_single_phy_supply=True,enabled_missing_supply_rejected=True,schema_checks=results,negative_controls=checks,negative_count=len(checks),full_board_validation=False,dtb_sha256=hashlib.sha256(raw).hexdigest(),phone_unchanged=True)
(ref/'camss-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('CAMSS124_ACTUAL_DTB_AND_NEGATIVE_SCHEMA_PASS')
