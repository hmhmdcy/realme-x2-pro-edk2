from pathlib import Path
import host,json
out=host.PRIVATE;remote='/var/lib/samurai/k197-front-capture-r4/'
for n in ['summary.json','clocks-before-capture-private.txt','clocks-after-capture-private.txt','genpd-before-capture-private.txt','genpd-after-capture-private.txt','interrupts-before-capture-private.txt','interrupts-after-capture-private.txt']:
 host.download(remote+n,out/('diagnostic-'+n))
r=json.loads((out/'diagnostic-summary.json').read_text());print('CAMSS PM',r.get('camss_power_before_capture'))
for name in ['clocks-before','clocks-after','genpd-before','genpd-after','interrupts-before','interrupts-after']:
 text=(out/('diagnostic-'+name+'-capture-private.txt')).read_text();print(name)
 print('\n'.join(s for s in text.splitlines() if any(x in s.lower() for x in ['titan','cam_cc_ife','ife0','ife1','csid','camss','camnoc','camera_ahb'])))
