from pathlib import Path
import subprocess,shutil,os,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel117')
work=Path('/home/cy122/x2pro-linux/parser-k117')
assert not work.exists();work.mkdir(mode=0o700)
owner=1000
os.chown(work,owner,owner)
source=out/'CamxChi/chi-cdk/tools/buildbins/linux64/ParameterParser'
p=work/'ParameterParser';shutil.copyfile(source,p);p.chmod(0o700);os.chown(p,owner,owner)
assert hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(source.read_bytes()).hexdigest()
result=subprocess.run(['runuser','-u','cy122','--',str(p)],cwd=work,capture_output=True,text=True,timeout=10)
(out/'parameter-parser-help.txt').write_text(result.stdout+result.stderr)
print((result.stdout+result.stderr)[:13500])
print('HELP_EXIT',result.returncode)
