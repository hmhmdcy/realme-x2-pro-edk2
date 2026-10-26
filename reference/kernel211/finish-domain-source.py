from pathlib import Path
import difflib,hashlib,json
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=Path('/mnt/e/edk2-samurai-out/kernel211');sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
board=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';binding=k/'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml'
new_board=board.read_text();new_fragment='\t\tcompatible = "sony,imx471";\n\t\treg = <0x10>;\n\t\tpower-domains = <&camcc TITAN_TOP_GDSC>;';old_fragment=new_fragment.rsplit('\n',1)[0]
assert new_board.count(new_fragment)==1;old_board=new_board.replace(new_fragment,old_fragment);assert sha(old_board)=='68738cb98b06b935ce7c6b1ed3d65e0a1c50e54766d29155c148d9893c12f7d5'
(private/'source-before/board-before-domain-private.dts').write_text(old_board)
old_binding=(private/'source-before/sony-imx471-binding-before.yaml').read_text();assert binding.read_text()==old_binding
target='  clocks:\n    description: External input clock, 19.2 MHz\n    maxItems: 1'
assert old_binding.count(target)==1
new_binding=old_binding.replace(target,target+'\n\n  power-domains:\n    maxItems: 1\n    description: Power domain required by the sensor master-clock gate.')
binding.write_text(new_binding)
patch=''
for p,old,new in [(board,old_board,new_board),(binding,old_binding,new_binding)]:
    patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+str(p.relative_to(k)),tofile='b/'+str(p.relative_to(k))))
(here/'imx471-clock-domain.patch').write_text(patch)
report=dict(stage=211,board_dts_sha256=sha(new_board),sensor_binding_sha256=sha(new_binding),sensor_owns_titan_top_power_domain=True,master_clock_register_programming_unchanged=True,external_regulator_and_gpio_settings_unchanged=True,only_existing_domain_reference_added_to_board=True,first_binding_context_assertion_stopped_after_board_edit=True,original_board_recovered_and_hash_verified=True,hardware_deployment_pending=True)
(here/'sensor-domain-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
