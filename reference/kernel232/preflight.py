"""Fresh accepted-state check and PMIC inventory, before any staging."""
from pathlib import Path
import ast,hashlib,json
import host
R=Path(__file__).resolve().parent
tree=ast.parse((R.parent/'kernel230/final-health.py').read_text())
code=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='code' for v in n.targets)))
assert code.count("out=root/'k230-final-health'")==1
code=code.replace("out=root/'k230-final-health'","out=root/'k232-preflight'").replace('report=dict(stage=230,','report=dict(stage=232,')
anchor="(out/'summary.json').write_text"
assert code.count(anchor)==1
extra=r'''
module_root=Path('/usr/lib/modules')/os.uname().release
pmic=module_root/'kernel/drivers/mfd/qcom-pm8008.ko'
assert pmic.is_file()
assert not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
assert not Path('/sys/bus/i2c/devices/4-0008').exists()
pmic_nodes=[]
for node in Path('/sys/bus/i2c/devices').glob('*-0004'):
 if (node/'driver').exists() and (node/'driver').resolve().name=='pm8008':pmic_nodes.append(node)
assert len(pmic_nodes)==1
q=pmic_nodes[0]
gpio=subprocess.run(['cat','/sys/kernel/debug/gpio'],capture_output=True,timeout=10)
(out/'gpio-before-private.txt').write_bytes(gpio.stdout+gpio.stderr)
if Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').is_file():
 (out/'pm8008-loaded-note-private.bin').write_bytes(Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes())
identity=dict(default_mfd_sha256=hashlib.sha256(pmic.read_bytes()).hexdigest(),
 default_mfd_bytes=pmic.stat().st_size,default_mfd_intree=subprocess.check_output(['modinfo','-F','intree',str(pmic)],text=True).strip(),
 q_device=q.name,q_children=sorted(p.name for p in q.iterdir() if p.is_dir() and p.name.startswith('pm8008-')))
(out/'pmic-baseline-private.json').write_text(json.dumps(identity,indent=2)+'\n')
report.update(pmic_q_bound=True,new_reset_provider_absent=True,no_staging_performed=True,
 current_default_mfd_sha256=identity['default_mfd_sha256'],current_default_mfd_bytes=identity['default_mfd_bytes'])
assert not any('/run/k231-rfs-vendor-ro ' in l or '/run/k231-rfs-persist-ro ' in l for l in Path('/proc/mounts').read_text().splitlines())
'''
code=code.replace(anchor,extra+'\n'+anchor)
result=host.ssh('python3 -',input=code.encode(),timeout=110)
(host.PRIVATE/'preflight-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout)
(R/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
