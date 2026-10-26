from pathlib import Path
import base64,importlib.util,json,secrets
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');source=(R/'native-backup-server.py').read_bytes();compile(source,'native-backup-server.py','exec');spec=importlib.util.spec_from_file_location('host',R.parent/'kernel247/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
inventory=json.loads((P/'inspect-linux-private.json').read_text());parts={x['label']:x for x in inventory['report']['partitions']};labels=['boot','dtbo','vbmeta','recovery','metadata','misc','cache','system','vendor','odm','modem','modemst1','modemst2','fsc','fsg','persist','oppodycnvbk','oppostanvbk','uefivarstore','devinfo'];sources={name+'.img':dict(path='/dev/disk/by-partlabel/'+name,bytes=parts[name]['bytes']) for name in labels};cfg=dict(boot_id=inventory['private']['boot_id'],token=secrets.token_urlsafe(32),bind_address='169.254.42.1',port=18748,sources=sources)
code=r'''
from pathlib import Path
import base64,json,os,subprocess
os.umask(0o077);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k247-runtime/boot-id-private.txt').read_bytes();assert not Path('/run/k248-backup').exists();p=Path('/run/k248-backup-server.py');assert not p.exists();p.write_bytes(base64.b64decode(SOURCE));cfg=CONFIG;assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==cfg['boot_id'];Path('/run/k248-backup-config-private.json').write_text(json.dumps(cfg));
with Path('/run/k248-backup-worker-private.log').open('xb') as log:child=subprocess.Popen(['python3',str(p)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=248,read_only_partition_server_launched=True,pid=child.pid,source_count=len(cfg['sources']),token_required=True,usb_address_only=True)))
'''.replace('SOURCE',repr(base64.b64encode(source).decode())).replace('CONFIG',repr(cfg))
x=host.ssh('python3 -',input=code.encode(),timeout=20);(P/'partition-server-launch-private.log').write_bytes(x.stdout+x.stderr);(P/'partition-server-config-private.json').write_text(json.dumps(cfg,indent=2)+'\n');v=json.loads(x.stdout);(R/'partition-server-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
