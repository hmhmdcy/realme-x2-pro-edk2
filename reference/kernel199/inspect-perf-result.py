from pathlib import Path
import host,json,re
out=host.PRIVATE;remote='/var/lib/samurai/k199-mmcx-tpg/'
for name in ['before-genpd-private.txt','performance-active-genpd-private.txt','restored-genpd-private.txt','after-capture-clocks-private.txt']:
 host.download(remote+name,out/name);rows=(out/name).read_text().splitlines();print(name)
 if 'clocks' in name:
  print('\n'.join(l for l in rows if re.match(r'\s*cam_cc_ife_0_(?:clk|csid_clk)\s',l)))
 else:
  for i,l in enumerate(rows):
   if re.match(r'^mmcx\s',l):print('\n'.join(rows[i:i+8]))
