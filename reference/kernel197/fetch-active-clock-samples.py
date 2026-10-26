from pathlib import Path
import host,json,re
out=host.PRIVATE;remote='/var/lib/samurai/k197-front-capture-r5/'
host.download(remote+'active-clock-sampler-private.json',out/'active-clock-sampler-private.json');r=json.loads((out/'active-clock-sampler-private.json').read_text());print(json.dumps(r))
for sample in r['samples']:
 i=sample['sample']
 for n in ['clocks','genpd','interrupts']:
  name='active-'+str(i)+'-'+n+'-private.txt';host.download(remote+name,out/name)
  if i>1:continue
  text=(out/name).read_text();print(n)
  if n=='clocks':print('\n'.join(l for l in text.splitlines() if re.match(r'\s*(cam_cc_(ife_0|core_ahb|cpas_ahb|camnoc_axi|cphy_rx)|gcc_camera)',l)))
  elif n=='genpd':
   rows=text.splitlines()
   for index,line in enumerate(rows):
    if any(x in line for x in ['ife_0','ife_1','titan_top']):print('\n'.join(rows[index:index+4]))
  else:print('\n'.join(l for l in text.splitlines() if 'camss_msm_' in l))
