from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((here/'build-root-validation.json').read_text())['emulated_arm_compiler_runs']
with (private/'busybox-applet-links-private.log').open('xb') as log:subprocess.run(['chroot',str(root),'/bin/busybox','--install','-s'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=30)
for name,minor in [('null',3),('zero',5),('random',8),('urandom',9)]:
    path=root/'dev'/name;path.parent.mkdir(exist_ok=True)
    if not path.exists():os.mknod(path,stat.S_IFCHR|0o666,os.makedev(1,minor));path.chmod(0o666)
for name in ['tmp','var/tmp']:
    path=root/name;path.mkdir(parents=True,exist_ok=True);path.chmod(0o1777)
key_dir=Path('/home/cy122/x2pro-linux/libcamera214-signing-private');key_dir.mkdir(mode=0o700);ipa_key=key_dir/'ipa.rsa.pem'
with (private/'ipa-key-generation-private.log').open('xb') as log:subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(ipa_key)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=30)
ipa_key.chmod(0o600)
apk_dir=Path('/home/cy122/x2pro-linux/samurai-packages203/signing-private');apk_key=apk_dir/'samurai-linux-203.rsa';apk_pub=apk_dir/'samurai-linux-203.rsa.pub';assert apk_key.is_file() and apk_pub.is_file()
secret=root/'private';secret.mkdir(mode=0o700)
for src,name in [(ipa_key,'ipa214.rsa.pem'),(apk_key,'samurai-linux-203.rsa'),(apk_pub,'samurai-linux-203.rsa.pub')]:
    dst=secret/name;shutil.copyfile(src,dst);dst.chmod(0o600 if not name.endswith('.pub') else 0o644)
work=root/'work';work.mkdir(mode=0o755)
for name in ['libcamera','samurai-camera-config']:
    shutil.copytree(repo/'linux-port/packages'/name,work/name)
    for p in [work/name,*(work/name).rglob('*')]:
        if p.is_dir():p.chmod(0o755)
        elif p.is_file():p.chmod(0o644)
dist=root/'var/cache/distfiles';dist.mkdir(parents=True,exist_ok=True);archive=private.parent/'kernel211/libcamera-v0.7.2.tar.gz';expected=json.loads((repo/'linux-port/camera/libcamera/source-lock.json').read_text())['upstream_sha512'];assert hashlib.sha512(archive.read_bytes()).hexdigest()==expected;shutil.copyfile(archive,dist/archive.name)
config=root/'etc/abuild.conf';before=config.read_bytes();(private/'abuild-config-before-private.txt').write_bytes(before)
config.write_bytes(before+b'\nREPODEST=/packages\nSRCDEST=/var/cache/distfiles\nPACKAGER="Realme X2 Pro Linux port"\nPACKAGER_PRIVKEY=/private/samurai-linux-203.rsa\nJOBS=4\nMAKEFLAGS="-j4"\nNINJAFLAGS="-j4"\n')
commands=[['/bin/ash','-c','umask 022; uname -m; command -v abuild; command -v abuild-meson; command -v scanelf; command -v strip'],['/usr/bin/abuild','-h']]
outputs=[]
for index,args in enumerate(commands):
    p=subprocess.run(['chroot',str(root),*args],capture_output=True,text=True,timeout=30);(private/('build-environment-check-'+str(index)+'-private.log')).write_text(p.stdout+p.stderr);assert p.returncode==0;outputs.append(p.stdout)
assert 'aarch64' in outputs[0] and '-d' in outputs[1] and '-F' in outputs[1]
manifest={}
for entry in (root/'lib/apk/db/installed').read_text().split('\n\n'):
    fields={line[0]:line[2:] for line in entry.splitlines() if len(line)>1 and line[1]==':' and line[0] in ['P','V','A']}
    if 'P' in fields:manifest[fields['P']]={k:v for k,v in fields.items() if k!='P'}
(private/'build-dependencies-lock-private.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
report=dict(stage=214,host_arm_build_environment_ready=True,busybox_shell_applet_links_initialized=True,no_phone_access_required=True,original_project_apk_signing_key_reused_not_regenerated=True,retained_external_ipa_key_created_in_host_private_directory=True,private_keys_outside_source_and_package_trees=True,original_source_archive_sha512_verified=True,full_recipe_and_config_staged=True,arm_compiler='Alpine15.2.0',build_jobs=4,installed_build_dependency_count=len(manifest),no_device_mutation=True)
(here/'build-environment-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
