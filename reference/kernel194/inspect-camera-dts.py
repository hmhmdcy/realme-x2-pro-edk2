from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';text=p.read_text();print('\n'.join(text.splitlines()[:80]))
for term in ['regulators-1','ldo1 {','smps8 {','&camss','&cci','&i2c4','l3c']:
 lines=text.splitlines()
 for i,s in enumerate(lines):
  if term in s:print(i+1,'\n'.join(lines[max(0,i-4):i+18]))
root=k/'arch/arm64/boot/dts/qcom'
print('VIO labels')
for name in ['sm8150.dtsi','sm8150-samurai.dts','sm8150-pm8150.dtsi','sm8150-hdk.dts','sm8150-hdk.dtsi']:
 p=root/name
 if p.is_file():
  for i,s in enumerate(p.read_text().splitlines()):
   if 'vreg_l1c' in s or ('ldo1' in s and ':' in s):print(name,i+1,s)
