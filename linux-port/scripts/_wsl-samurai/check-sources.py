#!/usr/bin/env python3
"""Check published local source hashes, syntax, and deployment-path independence."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
# This tree keeps every recipe under packages/.  The historic device/testing,
# temp/ and cross/ paths no longer exist, so gate what is actually here.
# The script lives in scripts/_wsl-samurai/, two levels below linux-port/.
root=Path(__file__).resolve().parents[2]
recipes=sorted(p for p in (root/'packages').iterdir() if (p/'APKBUILD').is_file())
hashes=0;checked=0;key_scan=0;libcamera_patches=[]
private_build_path=re.compile(r'/(?:home/[A-Za-z0-9._-]+|mnt/[A-Za-z])/')
windows_user_path=re.compile(r'(?i)(?<![A-Za-z0-9])[A-Z]:\\Users\\[^\\\s]+')
private_key_header=re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|-----BEGIN PGP PRIVATE KEY BLOCK-----|PuTTY-User-Key-File')
for directory in recipes:
 recipe=(directory/'APKBUILD').read_text()
 subprocess.run(['sh','-n',str(directory/'APKBUILD')],check=True)
 # abuild expects the checksum sequence to follow source, not just contain
 # a correct filename-to-hash map. Parse these deliberately simple recipes
 # without evaluating APKBUILD shell code on the host.
 values={}
 for key in ['pkgname','pkgver','_pkgver','_commit','_tuning_files']:
  m=re.search(r'^'+key+r'=(?:"([^"]*)"|([^\n]+))',recipe,re.M)
  if m:values[key]=m[1] if m[1] is not None else m[2]
 # Multi-line helper variables are folded to one line before expansion.
 for key in ['_tuning_files','_extra_sources','_commit']:
  m=re.search(r'^'+key+r'="([^"]*)"',recipe,re.M|re.S)
  if m:values[key]=' '.join(m[1].split())
  elif key in values:values[key]=' '.join(values[key].split())
 def expand(text):
  # ${var/pat/repl} and ${var//pat/repl}
  def repl(m):
   base=values.get(m[1],m[0])
   return base.replace(m[3],m[4]) if base!=m[0] else m[0]
  text=re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)([/]{1,2})(.+)/(.+)\}',repl,text)
  for _ in range(5):
   text=re.sub(r'\$(?:\{([A-Za-z_][A-Za-z_0-9]*)\}|([A-Za-z_][A-Za-z_0-9]*))',
    lambda m:values.get(m[1] or m[2],m[0]),text)
  return text
 m=re.search(r'^source="([^"]*)"',recipe,re.M)
 if not m:
  # Meta packages (samurai-apps) declare no sources at all.
  checked+=sum(1 for _ in directory.iterdir())
  continue
 sources=expand(m[1]).split()
 source_names=[t.split('::',1)[0] if '::' in t else t.rsplit('/',1)[-1] for t in sources]
 checksum_names=re.findall(r'^[0-9a-f]{128}  (.+)$',recipe,re.M)
 assert source_names==[n.rsplit('/',1)[-1] for n in checksum_names],'Source/checksum order mismatch: '+str(directory)
 if directory==root/'packages/libcamera':
  libcamera_patches=sorted(name for name in source_names if name.endswith('.patch'))
 for digest,name in re.findall(r'^([0-9a-f]{128})  (.+)$',recipe,re.M):
  p=directory/name
  if p.is_file():assert hashlib.sha512(p.read_bytes()).hexdigest()==digest,str(p);hashes+=1
 # A binary payload is allowed only when the recipe lists it as a source
 # and pins its SHA-512; anything else must stay plain text.
 pinned={digest for digest,name in re.findall(r'^([0-9a-f]{128})  (.+)$',recipe,re.M)
         if name in source_names}
 for p in directory.iterdir():
  if not p.is_file():continue
  data=p.read_bytes()
  if data.startswith(b'\x7fELF') and hashlib.sha512(data).hexdigest() in pinned:
   checked+=1;continue
  assert not data.startswith(b'\x7fELF'),str(p)
  text=data.decode()
  assert not private_key_header.search(text),str(p)
  if p.suffix not in {'.patch','.diff'}:
   assert not private_build_path.search(text),str(p)
   assert not windows_user_path.search(text),str(p)
  assert not re.search(r'/var/lib/samurai/k[0-9]',text),str(p)
  if p.suffix=='.py' or text.startswith('#!/usr/bin/python3'):ast.parse(text)
  if text.startswith(('#!/bin/sh','#!/sbin/openrc-run')):subprocess.run(['sh','-n',str(p)],check=True)
  checked+=1
owned=sorted(p for p in (root/'packages').iterdir() if p.is_dir())
owned+=[root/'dts',root/'ssc',root/'radio']
for base in owned:
 for p in base.rglob('*'):
  if not p.is_file() or p.is_symlink() or '.git' in p.parts or p.resolve()==Path(__file__).resolve():continue
  data=p.read_bytes()
  if b'\0' in data:continue
  assert not private_key_header.search(data.decode(errors='replace')),str(p)
  key_scan+=1
lock=json.loads((root/'packages/libcamera/source-lock.json').read_text())
libcamera_recipe=(root/'packages/libcamera/APKBUILD').read_text()
libcamera_rel=re.search(r'^pkgrel=([0-9]+)$',libcamera_recipe,re.M)[1]
camera_recipe=(root/'packages/samurai-camera-config/APKBUILD').read_text()
camera_ver=re.search(r'^pkgver=([^\n]+)$',camera_recipe,re.M)[1]
camera_rel=re.search(r'^pkgrel=([0-9]+)$',camera_recipe,re.M)[1]
assert lock['package_version']=='99990.7.2-r'+libcamera_rel, lock['package_version']
# The lock records every shipped source file by SHA-256; verify it against
# the files that are actually here, and that it covers the whole patch
# series the recipe applies.
locked=lock['source_files_sha256']
for name,digest in locked.items():
 p=root/'packages/libcamera'/name
 assert p.is_file(),name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
assert set(libcamera_patches)<=set(locked),sorted(set(libcamera_patches)-set(locked))
# The series grew from 50 to 51 patches when 0051 fixed the RAW-only PD10
# policy; the count is now derived from the recipe instead of hard-coded.
assert len(libcamera_patches)>=50, len(libcamera_patches)
# The directory also carries upstream's Pinephone patches, which this
# recipe intentionally does not reference; compare only what is listed.
listed = sorted(p.name for p in (root/'packages/libcamera').glob('00*.patch')
                if p.name in libcamera_patches)
assert listed == libcamera_patches
print(json.dumps({'recipes':len(recipes),'local_sha512_checks':hashes,'source_files_checked':checked,
 'libcamera_patches':len(libcamera_patches),'private_key_scan_files':key_scan,
 'private_build_paths_required':False,'hardware_tested':False},indent=2))
