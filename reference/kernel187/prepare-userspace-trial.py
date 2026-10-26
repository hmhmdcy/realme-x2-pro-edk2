from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent
source=(ref/'test-a11-trial.sh').read_text()
source=source.replace('k186-reboot-runtime-r2/boot-id-private.txt','k187-reboot-runtime/boot-id-private.txt')
source=source.replace('ram-k187-a11','ram-k187-a11-userspace')
source=source.replace('k187-a11-trial','k187-a11-userspace')
source=source.replace('instances/k187-slpi','instances/k187-userspace')
source=source.replace('timeout -s TERM -k 3 180 ','timeout -s TERM -k 3 280 ')
start=source.index('set +e\ntimeout -s TERM -k 2 40 python3')
source=source[:start]+'''set +e
timeout -s TERM -k 2 185 python3 -B /var/lib/samurai/k187-tools/test-a11-userspace.py --output "$dest/userspace" > "$dest/userspace-run-private.txt" 2>&1
query=$?
set -e
printf '%s\\n' "$query" > "$dest/userspace-exit.txt"
test "$(cat "$node/state")" = running
kill -0 "$owner"
exit "$query"
'''
script=ref/'test-a11-userspace-trial.sh'
assert not script.exists();script.write_text(source)
subprocess.run(['sh','-n',str(script)],check=True)
for path in [script,ref/'test-a11-userspace.py',ref/'ssc-vector-probe.py']:
    host.upload(path,'/var/lib/samurai/k187-tools/'+path.name)
    host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  /var/lib/samurai/k187-tools/'+path.name+'\n').encode())
host.ssh('test -f /var/lib/samurai/k187-reboot-runtime/summary.json && test ! -e /var/lib/samurai/k187-a11-userspace')
p=host.ssh('nohup sh /var/lib/samurai/k187-tools/test-a11-userspace-trial.sh > /var/lib/samurai/k187-a11-userspace-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE/'userspace-worker-pid-private.txt').write_bytes(p.stdout)
print(json.dumps({'fresh_boot_a11_vector_and_standard_userspace_trial_started':True,
    'vectors':['accel','gyro','mag'],'cli':['accelerometer','gyroscope','magnetometer','compass','light'],
    'standard_sensor_proxy_claims_planned':['Accelerometer','Light','Proximity'],
    'system_library_replaced':False,'no_flash':True}))
