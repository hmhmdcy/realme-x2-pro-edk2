from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'include/linux/pm_domain.h';rows=p.read_text().splitlines()
for i,l in enumerate(rows):
 if 'performance_state' in l and ('dev_pm_genpd_' in l or 'dev_gpd_data' in l):print(i+1,'\n'.join(rows[max(0,i-2):i+5]))
p=k/'include/dt-bindings/power/qcom-rpmpd.h';print(p.read_text()[-2600:])
o=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/clk/qcom')
for p in o.glob('*sm8150*.h'):
 s=p.read_text()
 if 'VDD_HIGH' in s or 'RPMH_REGULATOR_LEVEL_TURBO' in s:print(p.name,s[:5000])
