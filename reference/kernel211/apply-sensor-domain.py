from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=Path('/mnt/e/edk2-samurai-out/kernel211');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
board=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';binding=k/'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml'
assert sha(board)=='68738cb98b06b935ce7c6b1ed3d65e0a1c50e54766d29155c148d9893c12f7d5'
(private/'source-before/sony-imx471-binding-before.yaml').write_bytes(binding.read_bytes())
changes=[]
for p in [board,binding]:
    old=p.read_text()
    if p==board:
        target='\t\tcompatible = "sony,imx471";\n\t\treg = <0x10>;'
        new=target+'\n\t\tpower-domains = <&camcc TITAN_TOP_GDSC>;'
    else:
        target='  clocks:\n    maxItems: 1'
        new=target+'\n\n  power-domains:\n    maxItems: 1\n    description: Power domain required by the sensor master-clock gate.'
    assert old.count(target)==1;data=old.replace(target,new);p.write_text(data)
    changes.append(''.join(difflib.unified_diff(old.splitlines(True),data.splitlines(True),fromfile='a/'+str(p.relative_to(k)),tofile='b/'+str(p.relative_to(k)))))
(here/'imx471-clock-domain.patch').write_text(''.join(changes))
report=dict(stage=211,board_dts_sha256=sha(board),sensor_binding_sha256=sha(binding),sensor_owns_titan_top_power_domain=True,master_clock_register_programming_unchanged=True,external_regulator_and_gpio_settings_unchanged=True,only_existing_domain_reference_added_to_board=True,hardware_deployment_pending=True)
(here/'sensor-domain-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
