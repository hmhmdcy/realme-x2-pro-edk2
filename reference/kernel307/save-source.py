"""Save the reviewed source change and selected native metadata samples."""
from pathlib import Path
import base64,json,shlex,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera307-rgb-kernel')
names=[
 'drivers/media/platform/qcom/camss/camss-vfe-175-stats.c',
 'drivers/media/platform/qcom/camss/camss-vfe-175-stats.h',
 'drivers/media/platform/qcom/camss/camss-vfe-17x.c',
 'drivers/media/platform/qcom/camss/camss-vfe.c',
 'drivers/media/platform/qcom/camss/camss-vfe.h',
 'include/uapi/linux/qcom-camss-config.h',
]
proof=json.loads((HERE/'rgb-capture-validation.json').read_text())
if not proof['passed']:raise RuntimeError('Native RGB run is not verified')
base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()
patch=subprocess.check_output(['git','diff','--',*names],cwd=TREE)
if not patch:raise RuntimeError('Source is already committed; inspect instead of replaying')
(HERE/'vfe175-rgb.patch').write_bytes(patch)
subprocess.run(['git','add','--',*names],cwd=TREE,check=True)
subprocess.run(['git','commit','-m','media: qcom: camss: add VFE175 RGB grid statistics alongside BHIST'],
               cwd=TREE,check=True,capture_output=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=TREE,text=True).strip()
source={'stage':307,'tree':str(TREE),'branch':'samurai-rgb307','base_commit':base,
        'commit':commit,'changed_files':names,'deployed':False,'pushed':False,
        'source_clean':not subprocess.check_output(['git','status','--porcelain'],cwd=TREE)}
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n')
shutil.copyfile(host.PRIVATE/'register-evidence-private.json',HERE/'oem-register-analysis.json')
code=r'''
from pathlib import Path
import base64,json
samples={}
for n in [1,2]:
    root=Path('/var/lib/samurai/k307-rgb-r'+str(n))
    for p in root.glob('frame-*.qcst'):
        samples[str(n)+'-'+p.name]=base64.b64encode(p.read_bytes()).decode()
print(json.dumps(samples))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
samples=host.PRIVATE/'stats-samples'
samples.mkdir(exist_ok=True)
for name,raw in json.loads(q.stdout).items():(samples/name).write_bytes(base64.b64decode(raw))
print(json.dumps(source,indent=2))
print('Private RGB/BHIST sample packets:',len(json.loads(q.stdout)))
