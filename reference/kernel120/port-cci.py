from pathlib import Path
import runpy,re,json,difflib,subprocess,hashlib
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
k=Path('/home/cy122/pmos-samurai-kernel118/camera120/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120')
own=json.loads((ref/'own-camera-resource-validation.json').read_text())
assert len(own['cci_pinctrl'])==8 and len(own['active_source_slots'])==5
for n,node in enumerate(own['downstream_cci']):
    assert node['properties']['reg']==f'<0xac4{["a","b"][n]}000 0x1000>'
    assert node['properties']['interrupts']==f'<0 {[460,271][n]} 0>'
for n,pair in enumerate(['17,18','19,20','31,32','33,34']):
    values=[x for x in own['cci_pinctrl'] if x['node'].startswith(f'cci{n}_active:')]
    assert len(values)==1 and re.findall(r'gpio(\d+)',values[0]['properties']['pins'])==pair.split(',')
patch=Path('/mnt/e/edk2-samurai-out/kernel117/camera-dt-reference/0057-arm64-dts-sm8150-add-the-camera-control-interfaces.patch').read_text()
added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))+'\n'
pin=added[:added.index('\t\tcci0: cci@')]
nodes=added[added.index('\t\tcci0: cci@'):]
nodes=nodes.replace('"qcom,sdm845-cci"','"qcom,msm8996-cci"')
# Source tables match generic v2 at 100kHz; faster vendor stretch settings
# differ by controller and are pending. Do not inherit an unverified 1MHz default.
assert nodes.count('clock-frequency = <1000000>;')==4
nodes=nodes.replace('clock-frequency = <1000000>;','clock-frequency = <100000>;')
p=k/'arch/arm64/boot/dts/qcom/sm8150.dtsi';before=p.read_text()
assert 'cci0: cci@' not in before
anchor='\t\t\tqup_i2c8_default: qup-i2c8-default-state {'
assert before.count(anchor)==1
after=before.replace(anchor,pin+anchor)
anchor='\t\tcamcc: clock-controller@ad00000 {'
assert after.count(anchor)==1
after=after.replace(anchor,nodes+anchor)
p.write_text(after)
changes=[('arch/arm64/boot/dts/qcom/sm8150.dtsi',before,after)]
p=k/'Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml';before=p.read_text()
anchor='              - qcom,sm8250-cci\n'
assert before.count(anchor)==2
after=before.replace(anchor,'              - qcom,sm8150-cci\n'+anchor,1)
anchor='              - qcom,sdm845-cci\n              - qcom,sm6350-cci'
assert after.count(anchor)==1
after=after.replace(anchor,'              - qcom,sdm845-cci\n              - qcom,sm8150-cci\n              - qcom,sm6350-cci')
p.write_text(after);changes.append(('Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml',before,after))
diff=''.join(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name,a,b in changes)
(ref/'sm8150-cci-7.3.patch').write_text(diff)
subprocess.run(['git','diff','--check','--',*(x[0] for x in changes)],cwd=k,check=True)
report=dict(cci_blocks=2,i2c_buses=4,native_mmio_irq_and_pin_pairs_matched=True,cci_v2_fallback_current_binding=True,six_clock_schema_added=True,default_bus_hz=100000,faster_mode_vendor_stretch_pending=True,all_cci_nodes_disabled=True,no_sensor_nodes_created=True,no_driver_timing_change=True,no_phone_changes=True,patch_sha256=hashlib.sha256(diff.encode()).hexdigest())
(ref/'cci-port-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
