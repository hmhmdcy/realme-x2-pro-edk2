#!/usr/bin/env python3
"""Preserve this build's signed APK index and packages in a fresh offline root."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,tarfile,subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--root',type=Path,required=True)
p.add_argument('--packages',type=Path,required=True,help='This build packages/edge directory')
a=p.parse_args();root=a.root.resolve();source=a.packages.resolve()/'aarch64'
if root==Path('/') or not (root/'etc/alpine-release').is_file():p.error('Offline Alpine root required')
assert not os.statvfs(root).f_flag & os.ST_RDONLY
index=source/'APKINDEX.tar.gz'
with tarfile.open(index) as archive:
 names=archive.getnames()
 signatures=[n for n in names if n.startswith('.SIGN.RSA.')]
 assert len(signatures)==1,'Expected one RSA-signed APK index'
 key=signatures[0].removeprefix('.SIGN.RSA.')
 assert re.fullmatch(r'[A-Za-z0-9@_.+-]+\.rsa\.pub',key),key
 assert (root/'etc/apk/keys'/key).is_file(),'Install this build public key first'
 rows=archive.extractfile('APKINDEX').read().decode()
# The build workspace index keeps every pkgrel produced in this tree, so one
# package name can appear several times. The runtime repository must expose
# exactly the version recorded in the installed database; exporting more than
# one version makes the repository ambiguous.
installed={}
for block in (root/'lib/apk/db/installed').read_text().split('\n\n'):
 if not block.startswith('C:'):continue
 lines=block.split('\n')
 name=None;version=None
 for line in lines:
  if line.startswith('P:'):name=line[2:]
  elif line.startswith('V:'):version=line[2:]
 if name and version:installed[name]=version
files=[];seen=set()
for block in rows.split('\n\n'):
 row=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if 'P' not in row:continue
 if installed.get(row['P'])!=row['V']:continue
 assert row['P'] not in seen,'Duplicate installed version in index: '+row['P']
 seen.add(row['P'])
 assert row['A'] in ['aarch64','noarch']
 name=row['P']+'-'+row['V']+'.apk'
 assert re.fullmatch(r'[A-Za-z0-9_.+~:-]+\.apk',name),name
 assert (source/name).is_file(),name
 files.append(name)
assert files,'Empty package index'
target=root/'var/lib/samurai/apk/aarch64';target.mkdir(parents=True,exist_ok=True)
# Only clean files recorded by our own previous export; preserve unknown files.
previous=root/'var/lib/samurai/apk/manifest.json'
if previous.exists():
 for name in json.loads(previous.read_text()):
  assert name=='APKINDEX.tar.gz' or re.fullmatch(r'[A-Za-z0-9_.+~:-]+\.apk',name)
  if name not in ['APKINDEX.tar.gz',*files]:
   old=target/name
   assert not old.is_symlink()
   if old.exists():old.unlink()
manifest={}
for name in ['APKINDEX.tar.gz',*files]:
 src=source/name;dest=target/name
 assert not dest.is_symlink(),str(dest)
 shutil.copyfile(src,dest)
 manifest[name]=hashlib.sha256(dest.read_bytes()).hexdigest()
repo=root/'etc/apk/repositories'
lines=repo.read_text().splitlines()
entry='@samurai /var/lib/samurai/apk'
if entry not in lines:repo.write_text('\n'.join(lines+[entry])+'\n')
# Verify signature through apk, without downloading, installing or running services.
result=subprocess.run(['chroot',str(root),'/sbin/apk','--no-network',
 '--repositories-file','/dev/null','--repository','/var/lib/samurai/apk','update'],
 capture_output=True,text=True)
assert result.returncode==0,result.stdout+result.stderr
(root/'var/lib/samurai/apk/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'signed_repository_preserved':True,'apk_files':len(files),
 'private_key_copied':False,'world_changed':False,'hardware_tested':False}))
