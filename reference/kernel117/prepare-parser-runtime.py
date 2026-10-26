from pathlib import Path
import urllib.request,hashlib,tarfile,json,os,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel117')
work=Path('/home/cy122/x2pro-linux/parser-k117')
base='https://download.gnome.org/sources/libxml2/2.9/'
name='libxml2-2.9.14.tar.xz'
def fetch(url):
    with urllib.request.urlopen(url,timeout=45) as r:return r.read()
checks=fetch(base+'libxml2-2.9.14.sha256sum');data=fetch(base+name)
expected=next(l.decode().split()[0] for l in checks.splitlines() if name.encode() in l)
assert hashlib.sha256(data).hexdigest()==expected
(out/name).write_bytes(data);(out/'libxml2-2.9.14.sha256sum').write_bytes(checks)
source=work/'libxml2-2.9.14';assert not source.exists()
with tarfile.open(out/name) as tf:
    tf.extractall(work,filter='data')
for p in [source,*source.rglob('*')]:
    if not p.is_symlink():os.chown(p,1000,1000)
runtime=work/'runtime'
with (out/'parser-libxml2-build-private.log').open('wb') as log:
    for args in [['./configure','--prefix='+str(runtime),'--without-python','--without-icu','--without-lzma','--without-zlib'],['make','-j8'],['make','install']]:
        subprocess.run(['runuser','-u','cy122','--',*args],cwd=source,stdout=log,stderr=log,check=True,timeout=120)
env=dict(os.environ,LD_LIBRARY_PATH=str(runtime/'lib'))
result=subprocess.run(['runuser','-u','cy122','--',str(work/'ParameterParser')],cwd=work,capture_output=True,text=True,env=env,timeout=10)
(out/'parameter-parser-help.txt').write_text(result.stdout+result.stderr)
report=dict(private_runtime=True,no_global_library_install=True,libxml2_source_url=base+name,source_sha256=expected,help_exit=result.returncode)
(out/'parser-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print((result.stdout+result.stderr)[:15500])
