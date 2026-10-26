from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');base=k/'drivers/media/platform/qcom/camss'
for f in [base/'camss-sm8150.c',base/'camss-cpas.c',base/'camss.c']:
 if not f.exists():continue
 s=f.read_text();rows=s.splitlines();print(f.name)
 if f.name=='camss.c':
  for i,line in enumerate(rows):
   if 'runtime_' in line and ('static' in line or 'SET_RUNTIME' in line):print('\n'.join(rows[max(0,i-2):i+40]))
 else:
  for start in (['static const struct camss_subdev_resources csid_res_sm8150','static const struct camss_subdev_resources vfe_res_sm8150'] if 'sm8150' in f.name else ['int camss_cpas_init','int camss_cpas_power_on','void camss_cpas_power_off']):
   i=s.find(start);print(s[i:i+6500] if i>=0 else start+' NOT FOUND')
