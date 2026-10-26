from pathlib import Path
import subprocess,json,time,os
base=Path('/var/lib/samurai/k148-mesa');env=json.loads((base/'build-env-private.json').read_text())
start=time.monotonic()
with (base/'compile-private.log').open('ab') as f:
    p=subprocess.Popen(['nice','-n','10','/tmp/k148-sdk/usr/bin/ninja','-C',str(base/'build'),'-j','3','src/freedreno/vulkan/libvulkan_freedreno.so'],env=env,stdout=f,stderr=subprocess.STDOUT)
    (base/'compile-pid-private.txt').write_text(str(p.pid)+'\n');rc=p.wait()
print('MESA_COMPILE_EXIT='+str(rc)+' elapsed='+str(round(time.monotonic()-start,1)),flush=True)
raise SystemExit(rc)
