from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name in ['drivers/pmdomain/core.c','drivers/base/power/common.c']:
 p=k/name;s=p.read_text();rows=s.splitlines();print(name)
 for i,l in enumerate(rows):
  if 'attach_by_id(' in l or 'attach_by_name(' in l:
   print('\n'.join(rows[max(0,i-9):i+65]))
print('rpmh_binding_names',[p.name for p in (k/'include/dt-bindings/power').glob('*rpm*')])
p=k/'drivers/pmdomain/qcom/rpmhpd.c';s=p.read_text();print(s[:1800]);rows=s.splitlines()
for i,l in enumerate(rows):
 if 'rpmhpd_set_performance_state(' in l:print('\n'.join(rows[max(0,i-5):i+90]))
