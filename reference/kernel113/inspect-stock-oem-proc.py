from pathlib import Path
import hashlib,json,re,subprocess
repo=Path('/home/cy122/x2pro-linux/refs/realme-x2pro-androidr-project-k112')
out=Path('/mnt/e/edk2-samurai-out/kernel113/stock-oem-reference')
out.mkdir(exist_ok=True)
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()=='23172a1571bd91156032cc9fef16284a82b63d2c'
name='drivers/soc/oplus/system/oplus_project/qcom/oplus_project.c'
data=subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+name])
(out/'oplus_project.c').write_bytes(data)
text=data.decode(); lines=text.splitlines(); found=[]
for i,line in enumerate(lines):
    if 'modemType' in line or 'MODEM_VERSION' in line or 'RF_VERSION' in line:
        found.extend(lines[max(0,i-3):i+4])
print(json.dumps(dict(source_sha256=hashlib.sha256(data).hexdigest(),source_excerpts=found[:50])))
