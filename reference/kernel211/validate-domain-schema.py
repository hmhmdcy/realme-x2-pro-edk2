from pathlib import Path
import copy,json,subprocess,dtschema
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel211');binary=Path('/home/cy122/x2pro-linux/schema-k194/venv/bin');schema=k/'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml';processed=out/'processed-sensor-domain-private.json'
commands=[('doc',[str(binary/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)]),('compile',[str(binary/'dt-mk-schema'),'-j','-o',str(processed),str(schema),str(k/'Documentation/devicetree/bindings/media/video-interface-devices.yaml'),str(k/'Documentation/devicetree/bindings/media/video-interfaces.yaml'),str(k/'Documentation/devicetree/bindings/leds/leds-consumer.yaml')])]
for name,args in commands:
    p=subprocess.run(args,capture_output=True,timeout=90);(out/('sensor-domain-schema-'+name+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0 and not p.stdout and not p.stderr
validator=dtschema.DTValidator([str(processed)]);node=validator.decode_dtb((out/'sensor-domain-dtb/sensor-domain.dtb').read_bytes())[0]
for part in ['soc@0','cci@ac4b000','i2c-bus@1','camera@10']:node=node[part]
node['$nodename']=['camera@10'];assert not list(validator.iter_errors(node,filter=['sony,imx471']))
bad=copy.deepcopy(node);bad['power-domains']*=2;errors=list(validator.iter_errors(bad,filter=['sony,imx471']));assert errors
report=dict(stage=211,dtschema_version=dtschema.__version__,doc_and_schema_compile_clean=True,candidate_sensor_node_valid=True,new_single_power_domain_property_valid=True,two_domain_negative_control_rejected=True,full_board_schema_validated=False,unknown_pmic_pldo_input_gaps_preserved=True)
(here/'sensor-domain-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
