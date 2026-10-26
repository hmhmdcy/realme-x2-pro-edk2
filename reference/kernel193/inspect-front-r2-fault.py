from pathlib import Path
import host,json
for name in ['dmesg-before-private.txt','dmesg-after-private.txt','summary.json','insmod-private.log']:
 host.download('/var/lib/samurai/k193-front-identify-r2/'+name,host.PRIVATE/('front-r2-'+name))
before=(host.PRIVATE/'front-r2-dmesg-before-private.txt').read_text();after=(host.PRIVATE/'front-r2-dmesg-after-private.txt').read_text();assert after.startswith(before)
delta=after[len(before):];(host.PRIVATE/'front-r2-dmesg-delta-private.txt').write_text(delta)
print(delta[-14000:])
