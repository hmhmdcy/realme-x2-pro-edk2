from pathlib import Path
import hashlib
import host

ref=Path(__file__).resolve().parent
host.ssh('test ! -e /var/lib/samurai/k190-tools && mkdir -m700 /var/lib/samurai/k190-tools')
path=ref/'test-mm-location-stream.py';dest='/var/lib/samurai/k190-tools/'+path.name
host.upload(path,dest);host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
marker=host.PRIVATE/'mm-stream-worker-pid-private.txt';assert not marker.exists()
p=host.ssh("test ! -e /var/lib/samurai/k190-mm-stream || exit 1; nohup sh -c 'python3 /var/lib/samurai/k190-tools/test-mm-location-stream.py; result=$?; echo \"$result\" > /var/lib/samurai/k190-tools/mm-stream-worker-exit.txt' > /var/lib/samurai/k190-tools/mm-stream-worker-private.log 2>&1 < /dev/null & task_pid=$!; kill -0 \"$task_pid\" && echo \"$task_pid\"")
marker.write_bytes(p.stdout);print('One bounded standard ModemManager GPS stream worker started and live at submission.')
