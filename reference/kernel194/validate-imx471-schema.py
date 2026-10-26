from pathlib import Path
import json,subprocess,os
import libfdt,dtschema
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel194';out=Path('/mnt/e/edk2-samurai-out/kernel194');k=Path('/home/cy122/pmos-samurai-kernel136/kernel');bin=Path('/home/cy122/x2pro-linux/schema-k194/venv/bin')
schema=k/'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml';processed=out/'processed-imx471-private.json'
commands=[('doc',[str(bin/'dt-doc-validate'),'-u',str(k/'Documentation/devicetree/bindings'),str(schema)]),('compile',[str(bin/'dt-mk-schema'),'-j','-o',str(processed),str(schema),str(k/'Documentation/devicetree/bindings/media/video-interface-devices.yaml'),str(k/'Documentation/devicetree/bindings/media/video-interfaces.yaml'),str(k/'Documentation/devicetree/bindings/leds/leds-consumer.yaml')])]
for name,args in commands:
 p=subprocess.run(args,capture_output=True,timeout=90);(out/('schema-'+name+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0 and not p.stdout and not p.stderr,(name,(p.stdout+p.stderr).decode()[-2200:])
raw=(out/'sm8150-samurai-camera-warm-private.dtb').read_bytes();path='/soc@0/cci@ac4b000/i2c-bus@1/camera@10';validator=dtschema.DTValidator([str(processed)])
def errors(data):
 node=validator.decode_dtb(data)[0]
 for part in path.strip('/').split('/'):node=node[part]
 node['$nodename']=['camera@10'];return list(validator.iter_errors(node,filter=['sony,imx471']))
assert not errors(raw),[e.message for e in errors(raw)]
tests=[]
for name,change,valid in [('missing-vdig',{'vdig-supply':None},False),('missing-vif',{'vif-supply':None},False),('missing-clock',{'clocks':None},False),('missing-endpoint',{},False),('bad-one-lane',{},False),('hardware-two-lane',{},True),('extra-property',{'invented-input':bytes(4)},False)]:
 f=libfdt.Fdt(raw);f.resize(len(raw)+2048);node=f.path_offset(path)
 for key,value in change.items():
  if value is None:f.delprop(node,key)
  else:f.setprop(node,key,value)
 ep=f.path_offset(path+'/port/endpoint')
 if name=='missing-endpoint':f.del_node(ep)
 if name=='bad-one-lane':f.setprop(ep,'data-lanes',(1).to_bytes(4,'big'))
 if name=='hardware-two-lane':f.setprop(ep,'data-lanes',(1).to_bytes(4,'big')+(2).to_bytes(4,'big'))
 found=errors(bytes(f.as_bytearray()));assert bool(found)!=valid,(name,[e.message for e in found]);tests.append(dict(name=name,expected_valid=valid,error_count=len(found)))
record=dict(stage=194,dtschema_version=dtschema.__version__,doc_and_schema_compile_clean=True,candidate_sensor_node_valid=True,strict_node_validation_used=True,negative_and_hardware_positive_controls=tests,driver_still_requires_four_lanes_and_200mhz=True,full_board_schema_validated=False,pmic_input_binding_gaps_not_hidden=True,hardware_deployed=False)
(ref/'imx471-schema-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
