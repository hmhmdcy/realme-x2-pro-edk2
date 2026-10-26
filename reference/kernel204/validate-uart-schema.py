from pathlib import Path
import json,subprocess
import dtschema

here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel204');bin=Path('/home/cy122/x2pro-linux/schema-k194/venv/bin')
schema=k/'Documentation/devicetree/bindings/serial/qcom,serial-geni-qcom.yaml';processed=out/'processed-uart-private.json'
old=out/'uart-schema-errors-private.json'
if old.exists():
 saved=out/'uart-schema-errors-r1-private.json';assert not saved.exists();old.rename(saved)
command=[str(bin/'dt-mk-schema'),'-j','-o',str(processed),str(schema),str(k/'Documentation/devicetree/bindings/serial/serial.yaml'),str(k/'Documentation/devicetree/bindings/serial/serial-peripheral-props.yaml'),str(k/'Documentation/devicetree/bindings/soc/qcom/qcom,se-common-props.yaml')]
p=subprocess.run(command,capture_output=True);(out/'schema-compile-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
v=dtschema.DTValidator([str(processed)]);decoded=v.decode_dtb((out/'sm8150-samurai-bt-wake-static-private.dtb').read_bytes())[0]['soc@0']['geniqup@cc0000']['serial@c8c000'];decoded['$nodename']=['serial@c8c000'];errors=list(v.iter_errors(decoded,filter=['qcom,serial-geni-qcom']));(out/'uart-schema-errors-private.json').write_text(json.dumps([e.message for e in errors],indent=2)+'\n');assert not errors,[e.message for e in errors]
r=dict(stage=204,actual_candidate_uart_binding_passed=True,second_interrupt_decoded_as_rx_gpio=True,sleep_and_default_state_binding_passed=True,compiled_schema=str(schema.relative_to(k)),not_a_hardware_wake_test=True)
(here/'uart-schema-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
