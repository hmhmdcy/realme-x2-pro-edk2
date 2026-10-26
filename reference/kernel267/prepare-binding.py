"""Describe the common PMIC address dependency and optional external inputs."""
from pathlib import Path

R=Path(__file__).resolve().parent
K=Path('/home/cy122/pmos-samurai-kernel136/kernel')
s=(K/'Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml').read_text()
needle='  vdd-l1-l2-supply: true\n'
assert s.count(needle)==1
s=s.replace(needle,'''  qcom,address-setup-supplier:
    $ref: /schemas/types.yaml#/definitions/phandle
    description: |
      PM8008 on the same I2C bus which must finish moving from factory
      address 8 to operating address 4 before this device may leave reset.
      The supplier temporarily holds this device's reset GPIO while setting
      its address. A persistent device link orders probe and removal.

'''+needle)
for name in ['vdd-l3-l4-supply','vdd-l5-supply','vdd-l6-supply','vdd-l7-supply']:
    needle='  - '+name+'\n';assert s.count(needle)==1;s=s.replace(needle,'')
s=s.replace('  qcom,initial-address: [ reset-gpios ]','''  qcom,initial-address: [ reset-gpios ]
  qcom,address-setup-supplier: [ reset-gpios ]''')
s=s.replace('functions into a single IC.','''functions into a single IC.
  LDO output constraints are described under regulators. Omitted PLDO input
  supplies are externally managed; the driver does not create dummy input
  regulators for them. Describe controllable input supplies where known.''')
(R/'qcom,pm8008.yaml').write_text(s)
