from pathlib import Path
import subprocess,os,shutil,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel117')
work=Path('/home/cy122/x2pro-linux/parser-k117')
input_bin=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin')
source=work/input_bin.name;assert not source.exists();shutil.copyfile(input_bin,source);os.chown(source,1000,1000)
dest=work/'xml-imx471';dest.mkdir(mode=0o700);os.chown(dest,1000,1000)
env=dict(os.environ,LD_LIBRARY_PATH=str(work/'runtime/lib'))
args=[str(work/'ParameterParser'),str(dest),'x',str(work/'xsd'),'-b'+str(source),'-q']
result=subprocess.run(['runuser','-u','cy122','--',*args],cwd=work,env=env,capture_output=True,text=True,timeout=30)
(out/'imx471-decode-private.log').write_text(result.stdout+result.stderr)
files=[dict(name=str(p.relative_to(dest)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in dest.rglob('*') if p.is_file()]
report=dict(exit_code=result.returncode,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),xml_files=files,physical_hardware_not_touched=True,roundtrip_pending=True,goal_complete=False)
(out/'imx471-first-decode-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));print((result.stdout+result.stderr)[:5500])
