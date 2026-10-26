from pathlib import Path
p=Path('/home/cy122/pmos-samurai-kernel136/kernel/Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml')
s=p.read_text();needle='dependencies:\n'
addition='''allOf:
  - if:
      required:
        - qcom,initial-address
    then:
      properties:
        reg:
          items:
            - const: 4

'''
assert '  - if:\n' not in s
p.write_text(s.replace(needle,addition+needle))
