from pathlib import Path
import base64,hashlib,importlib.util,json,secrets,shutil
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248')
source=(R/'native-userdata-spool.py').read_bytes();compile(source,'native-userdata-spool.py','exec')
spec=importlib.util.spec_from_file_location('rescue',R/'rescue-host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
prior=P/'linux-userdata-partclone-r5-private.zst'
cfg=dict(boot_id=(P/'ram-rescue-boot-id-private.txt').read_text().strip(),token=secrets.token_urlsafe(32),bind_address='169.254.42.1',port=18751,state_dir='/run/k248-userdata-r6',spool_dir='/run/k248-spool-r6',output_filename='linux-userdata-partclone-r6-private.zst',prefix_bytes=prior.stat().st_size)
code=r'''
from pathlib import Path
import base64,json,os,subprocess
os.umask(0o077);cfg=CONFIG;assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==cfg['boot_id'];p=Path(cfg['state_dir']+'-worker.py');assert not p.exists();p.write_bytes(base64.b64decode(SOURCE));config=Path(cfg['state_dir']+'-config-private.json');config.write_text(json.dumps(cfg))
with Path(cfg['state_dir']+'-worker-private.log').open('xb') as log:child=subprocess.Popen(['python3',str(p),str(config)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=248,ram_spool_worker_started=True,pid=child.pid,source_read_only=True)))
'''.replace('CONFIG',repr(cfg)).replace('SOURCE',repr(base64.b64encode(source).decode()))
for name in ['userdata-server-config-private.json','userdata-worker-state-private.json']:
 p=P/name;shutil.copyfile(p,P/(p.stem+'-r5.json'))
x=host.ssh('chroot /run/rescue-tools /usr/bin/python3 -',input=code.encode(),timeout=20);(P/'userdata-spool-launch-private.log').write_bytes(x.stdout+x.stderr);(P/'userdata-server-config-private.json').write_text(json.dumps(cfg,indent=2)+'\n');print(x.stdout.decode())
