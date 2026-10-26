"""Upload verified software and launch one recorded staging worker."""
from pathlib import Path
import base64
import hashlib
import io
import json
import tarfile
import host

R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'build-package-validation.json').read_text())['firmware_only_dtb_changed']
for n in ['address-test-validation.json','common-power-test-validation.json','imx319-fault-validation.json']:
    assert (R/n).is_file()
binding=json.loads((R/'binding-validation.json').read_text())['results']
for name in ['qcom,pm8008.yaml','sony,imx319.yaml','qcom,pm8008-dtb','sony,imx319-dtb']:
    assert binding[name]['exit']==0 and binding[name]['diagnostic_bytes']==0,(name,binding[name])
build=json.loads((R/'module-build-validation.json').read_text())
before=json.loads((P/'baseline-private.json').read_text())['modules']
rows=[]
for name,directory in [('qcom_pm8008','mfd'),('qcom_pm8008_regulator','regulator'),('imx319','media/i2c')]:
    file=name.replace('_','-')+'.ko' if name!='imx319' else 'imx319.ko'
    proof=build['modules'][file];p=P/'modules-build-r1'/file
    assert hashlib.sha256(p.read_bytes()).hexdigest()==proof['sha256']
    rows.append(dict(name=name,file=file,relative_path='kernel/drivers/'+directory+'/'+file,
                     before_sha256=before[name]['sha256'],sha256=proof['sha256'],vermagic=proof['vermagic']))
remove=[]
for name,directory in [('qcom_pm8008_imx319_lab','regulator'),('reset_realme_rmx1931_pm8008','reset')]:
    remove.append(dict(name=name,relative_path='kernel/drivers/'+directory+'/'+name.replace('_','-')+'.ko',before_sha256=before[name]['sha256']))
manifest=dict(stage=267,modules=rows,remove_modules=remove)
(P/'staging-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
contents={row['file']:(P/'modules-build-r1'/row['file']).read_bytes() for row in rows}
contents['manifest.json']=json.dumps(manifest).encode();contents['native-stage.py']=(R/'native-stage.py').read_bytes()
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode='w:gz') as tar:
    for name,data in contents.items():
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600;tar.addfile(info,io.BytesIO(data))
payload=base64.b64encode(stream.getvalue()).decode()
code=r'''
from pathlib import Path
import base64,hashlib,io,json,os,subprocess,tarfile
os.umask(0o077);r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes()
assert not (r/'k267-module-transaction').exists() and not (r/'k267-input').exists()
p=r/'k267-input';p.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(PAYLOAD)),mode='r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and '/' not in m.name and m.name in NAMES
  (p/m.name).write_bytes(tar.extractfile(m).read())
compile((p/'native-stage.py').read_bytes(),'native-stage.py','exec')
with (p/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(p/'native-stage.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
print(json.dumps(dict(stage=267,worker_started=True,pid=child.pid,source_sha256=hashlib.sha256((p/'native-stage.py').read_bytes()).hexdigest())))
'''.replace('PAYLOAD',repr(payload)).replace('NAMES',repr(set(contents)))
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(P/'module-stage-launch-private.json').write_bytes(q.stdout)
print(q.stdout.decode())
