from pathlib import Path
import argparse,base64,importlib.util,json,secrets
parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,required=True);attempt=parser.parse_args().attempt;assert attempt>=4
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');source=(R/'native-userdata-backup.py').read_bytes();compile(source,'native-userdata-backup.py','exec');spec=importlib.util.spec_from_file_location('rescue',R/'rescue-host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host);cfg=dict(boot_id=(P/'ram-rescue-boot-id-private.txt').read_text().strip(),token=secrets.token_urlsafe(32),bind_address='169.254.42.1',port=18750,state_dir=f'/run/k248-userdata-r{attempt}',source_fsck_state='/run/k248-userdata-r2/state-private.json',partclone_binary='/usr/sbin/partclone.f2fs-ro248',output_filename=f'linux-userdata-partclone-r{attempt}-private.zst')
code=r'''
from pathlib import Path
import base64,json,os,subprocess
os.umask(0o077);cfg=CONFIG;assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==cfg['boot_id'] and Path('/sys/class/block/sda16/ro').read_text().strip()=='1';p=Path(cfg['state_dir']+'-worker.py');assert not p.exists();p.write_bytes(base64.b64decode(SOURCE));config=Path(cfg['state_dir']+'-config-private.json');config.write_text(json.dumps(cfg))
with Path(cfg['state_dir']+'-worker-private.log').open('xb') as log:child=subprocess.Popen(['python3',str(p),str(config)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=248,offline_userdata_backup_worker_started=True,pid=child.pid,source_read_only=True)))
'''.replace('CONFIG',repr(cfg)).replace('SOURCE',repr(base64.b64encode(source).decode()))
x=host.ssh('chroot /run/rescue-tools /usr/bin/python3 -',input=code.encode(),timeout=20);(P/'userdata-worker-launch-private.log').write_bytes(x.stdout+x.stderr);(P/'userdata-server-config-private.json').write_text(json.dumps(cfg,indent=2)+'\n');v=json.loads(x.stdout);(R/'userdata-worker-launch-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
