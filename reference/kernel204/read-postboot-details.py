from pathlib import Path
import re
import host

for name in ['ssc-init-private.txt','ssc-logs-private.txt','ssc-status-private.txt','services-private.txt']:
 path=host.PRIVATE/name;host.download('/var/lib/samurai/k204-postboot-inspection/'+name,path)
 text=path.read_text(errors='replace')
 if name in ['ssc-init-private.txt','ssc-logs-private.txt','ssc-status-private.txt']:print(name+'\n'+text[:7000])
