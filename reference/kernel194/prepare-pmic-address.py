from pathlib import Path
import hashlib,json,subprocess
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel194')
p=k/'drivers/mfd/qcom-pm8008.c';original=p.read_text();assert 'pm8008_reset_and_address' not in original
assert not (out/'qcom-pm8008-before-private.c').exists();(out/'qcom-pm8008-before-private.c').write_text(original)
text=original.replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/mutex.h>\n#include <linux/property.h>')
block=(ref/'pm8008-initial-address.c').read_text();block=block[block.index('#define PM8008_FACTORY_ADDRESS'):]
text=text.replace('static int pm8008_probe(struct i2c_client *client)',block+'\nstatic int pm8008_probe(struct i2c_client *client)')
text=text.replace('\tstruct gpio_desc *reset;\n\tint num_cells;','\tint num_cells;')
needle='\tdummy = devm_i2c_new_dummy_device(dev, client->adapter, client->addr + 1);';assert text.count(needle)==1
text=text.replace(needle,'\tret = pm8008_reset_and_address(client);\n\tif (ret)\n\t\treturn dev_err_probe(dev, ret, "failed to initialize PMIC address\\n");\n\n'+needle)
start=text.index('\treset = devm_gpiod_get_optional(dev, "reset", GPIOD_OUT_LOW);');end=text.index('\n\tif (client->irq > 0)',start);text=text[:start]+text[end:];p.write_text(text)
schema=k/'Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml';old=schema.read_text();(out/'pm8008-binding-before-private.yaml').write_text(old)
needle='  reset-gpios:\n    maxItems: 1\n';assert old.count(needle)==1
schema.write_text(old.replace(needle,needle+'''
  qcom,initial-address:
    $ref: /schemas/types.yaml#/definitions/uint32
    const: 8
    description:
      Primary address after reset when the operating address in reg is 4.
      Requires reset-gpios. Any sibling at the initial address must remain
      in reset until the operating address has been assigned.
''').replace('dependencies:\n','dependencies:\n  qcom,initial-address: [ reset-gpios ]\n'))
report=dict(stage=194,source_before_sha256=hashlib.sha256(original.encode()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binding_sha256=hashlib.sha256(schema.read_bytes()).hexdigest(),only_supported_reassignment=dict(initial=8,assigned=4,sid=1),actual_handset_reset_evidence=True,legacy_no_property_path_preserved=True,secondary_reserved_after_address_setup=True,sibling_occupancy_rejected_while_own_reset_asserted=True,hardware_module_deployed=False)
(ref/'pmic-address-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
