"""Build a separate signed Alpine recovery tool root; do not install on phone."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');target=Path('/home/cy122/x2pro-linux/gnss248-rescue-root-r2');assert not target.exists();target.mkdir(mode=0o700)
(target/'etc/apk').mkdir(parents=True);shutil.copytree(sdk/'etc/apk/keys',target/'etc/apk/keys');(target/'etc/apk/repositories').write_text('https://dl-cdn.alpinelinux.org/alpine/v3.23/main\nhttps://dl-cdn.alpinelinux.org/alpine/v3.23/community\n');(target/'etc/ssl/certs').mkdir(parents=True);shutil.copy2(sdk/'etc/ssl/certs/ca-certificates.crt',target/'etc/ssl/certs/ca-certificates.crt')
shutil.copyfile('/etc/resolv.conf',target/'etc/resolv.conf')
args=['/home/cy122/pmos-samurai-rootfs01/work/apk.static','--root',str(target),'--initdb','--arch','aarch64','--no-cache','--no-scripts','add','busybox','partclone','f2fs-tools','curl','python3','zstd','tar','dropbear']
with (P/'rescue-tool-build-r2-private.log').open('xb') as log:subprocess.run(args,stdout=log,stderr=log,check=True,timeout=600)
subprocess.run(['chroot',str(target),'/bin/busybox','--install','-s','/bin'],capture_output=True,check=True)
checks={}
for name,args in [('partclone',['partclone.f2fs','--version']),('restore',['partclone.restore','--version']),('f2fs',['fsck.f2fs','-V']),('tar',['tar','--version']),('python',['python3','--version']),('zstd',['zstd','--version']),('curl',['curl','--version'])]:
 x=subprocess.run(['chroot',str(target),*args],capture_output=True,timeout=20);checks[name]=dict(exit_code=x.returncode,text=(x.stdout+x.stderr).decode());assert x.returncode==0,(name,checks[name])
out=P/'rescue-tools-private.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz',compresslevel=1) as archive:
 for p in sorted(target.iterdir()):archive.add(p,arcname=p.name)
v=dict(stage=248,separate_recovery_root_built=True,signed_repositories_only=True,no_allow_untrusted=True,phone_package_database_unchanged=True,archive_bytes=out.stat().st_size,archive_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),checks=checks)
(P/'rescue-tool-build-private.json').write_text(json.dumps(v,indent=2)+'\n');(R/'rescue-tool-build-validation.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
