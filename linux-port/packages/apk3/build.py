#!/usr/bin/env python3
"""Build signed APKv3 packages from verified source and upstream payloads.

No phone access, package installation, privileged scripts, or cleanup is performed.
Use a new Linux-filesystem build directory; DrvFS does not preserve APK file modes.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,stat,subprocess,tarfile

parser=argparse.ArgumentParser()
for name in ['inputs','candidate','apk','trusted-keys','sign-key','build-root','output']:
    parser.add_argument('--'+name,required=True,type=Path)
args=parser.parse_args()
repo=Path(__file__).resolve().parents[3]
source=repo/'linux-port/packages/samurai-gnss-assist'
lock=json.loads((repo/'linux-port/packages/modemmanager/source-lock.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(args.candidate)==lock['runtime_binary_sha256']
assert sha(source/'samurai-gnss-assist.py')=='42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97'
assert sha(source/'samurai-gnss-assist.initd')=='54b8174507e97badfafba6c373ebf937045c1c85034f094e7de910369af78af3'
assert args.build_root.is_absolute() and not args.build_root.exists()
assert not str(args.build_root).startswith('/mnt/'), 'Build on a Linux filesystem to retain ownership and modes'
assert args.sign_key.is_file() and args.trusted_keys.is_dir()
args.build_root.mkdir(mode=0o700,parents=True);args.output.mkdir(mode=0o700,parents=True,exist_ok=True)
epoch=1792022400
old=lock['base_package_version'];new=lock['local_package_version']
pins={
 'modemmanager':'93fc1bbdbd155d175a3a3896562f32bab64dde44801d332a57c90c54723dc730',
 'modemmanager-openrc':'a5aab37ce6ce7cff707883b283fa432b5db92935268557b9804bf31654f277e6',
 'modemmanager-udev':'029bfb9eb3adc2d7936db691586ce79bf64a9d120fae533f339a810a940f8dc4'}
records=[]

def run(command,label):
    result=subprocess.run([str(item) for item in command],capture_output=True)
    (args.build_root/(label+'.log')).write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(label+' failed; inspect its build log')
    return result

def normalize(root):
    for path in [*root.rglob('*'),root]:
        if not path.is_symlink():os.chown(path,0,0)
        os.utime(path,(epoch,epoch),follow_symlinks=False)

def manifest(root):
    result={}
    for path in sorted(root.rglob('*')):
        relative=str(path.relative_to(root))
        if path.is_symlink():result[relative]=dict(kind='symlink',target=str(path.readlink()))
        elif path.is_file():result[relative]=dict(kind='file',sha256=sha(path),mode=stat.S_IMODE(path.stat().st_mode))
    return result

def make_package(name,version,arch,root,info,scripts=None):
    normalize(root)
    target=args.output/(name+'-'+version+'.apk')
    assert not target.exists()
    metadata=dict(name=name,version=version,arch=arch,**info)
    metadata['build-time']=str(epoch)
    metadata['maintainer']='Realme X2 Pro Linux port'
    command=[args.apk,'mkpkg','--compat','3.0.0','--compression','deflate:9','--files',root,'--sign-key',args.sign_key,'--output',target]
    for key,value in sorted(metadata.items()):
        if value:command+=['--info',key+':'+value]
    for kind,path in (scripts or {}).items():command+=['--script',kind+':'+str(path)]
    run(command,name+'-mkpkg')
    result=dict(name=name,version=version,arch=arch,sha256=sha(target),bytes=target.stat().st_size,files=manifest(root),metadata=metadata)
    records.append(result)

for name,pinned_hash in pins.items():
    archive=args.inputs/(name+'-'+old+'.apk');assert sha(archive)==pinned_hash
    run([args.apk,'--keys-dir',args.trusted_keys,'verify',archive],name+'-upstream-verify')
    with tarfile.open(archive,'r:gz',ignore_zeros=True) as upstream:
        fields={}
        for line in upstream.extractfile('.PKGINFO').read().decode().splitlines():
            if ' = ' in line:
                key,value=line.split(' = ',1);fields.setdefault(key,[]).append(value)
        controls=[member.name for member in upstream.getmembers() if member.isfile() and member.name.startswith('.') and member.name!='.PKGINFO' and not member.name.startswith('.SIGN')]
        modes={member.name:member.mode for member in upstream.getmembers() if member.isfile() and not member.name.startswith('.')}
    assert fields['pkgname']==[name] and fields['pkgver']==[old] and not controls
    payload=args.build_root/name;payload.mkdir()
    run([args.apk,'--keys-dir',args.trusted_keys,'extract','--destination',payload,archive],name+'-extract')
    baseline=manifest(payload)
    assert all(item['mode']==modes[path] for path,item in baseline.items() if item['kind']=='file')
    if name=='modemmanager':
        binary=payload/'usr/sbin/ModemManager';assert binary.is_file()
        shutil.copyfile(args.candidate,binary);binary.chmod(0o755)
        after=manifest(payload)
        assert [path for path in baseline if baseline[path]!=after[path]]==['usr/sbin/ModemManager']
    else:assert manifest(payload)==baseline
    metadata=dict(description=fields['pkgdesc'][0],license=fields['license'][0],origin='modemmanager',url=fields['url'][0],depends=' '.join(fields.get('depend',[])))
    for field,key in [('provides','provides'),('install_if','install-if'),('replaces','replaces')]:
        if fields.get(field):metadata[key]=' '.join(fields[field]).replace(old,new)
    make_package(name,new,fields['arch'][0],payload,metadata)

helper=args.build_root/'samurai-gnss-assist';helper.mkdir()
for name,target,mode in [('samurai-gnss-assist.py','usr/sbin/samurai-gnss-assist',0o755),('samurai-gnss-assist.initd','etc/init.d/samurai-gnss-assist',0o755),('NOTICE','usr/share/doc/samurai-gnss-assist/NOTICE',0o644)]:
    path=helper/target;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,path);path.chmod(mode)
make_package('samurai-gnss-assist','0.1.0-r0','noarch',helper,dict(description='Realme X2 Pro GNSS synchronized time and assistance maintenance',license='LicenseRef-Local-Project',origin='samurai-gnss-assist',depends='python3 py3-dbus py3-gobject3 libqmi libqrtr-glib chrony chrony-openrc ca-certificates dbus dbus-openrc openrc modemmanager'),{'post-install':source/'post-install','pre-deinstall':source/'pre-deinstall'})
stack=args.build_root/'samurai-gnss-stack';stack.mkdir()
make_package('samurai-gnss-stack','0.1.0-r0','noarch',stack,dict(description='Pinned Realme X2 Pro GNSS assistance and validated ModemManager backend',license='LicenseRef-Local-Project',origin='samurai-gnss-assist',depends='samurai-gnss-assist=0.1.0-r0 '+' '.join(name+'='+new for name in pins)))
(args.output/'package-manifest.json').write_text(json.dumps(dict(schema=1,source_date_epoch=epoch,source_lock=lock,packages=records),indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(packages=len(records),signed=True,only_mm_payload_change='usr/sbin/ModemManager',candidate_sha256=sha(args.candidate))))
