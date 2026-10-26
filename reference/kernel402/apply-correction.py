"""Correct only the factory Gamma DMI opcode; retain failed r1 history."""
from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'dmi-correction-validation.json').read_text())['passed']
assert json.loads((HERE/'current-state-validation.json').read_text())['passed']
for name in ['runtime-validation.json','pixels-validation.json','current-state-validation.json','source-state.json','intree-build-validation.json','staging-validation.json']:
 target=HERE/(name.replace('.json','-r1.json'));assert not target.exists();target.write_bytes((HERE/name).read_bytes())
for name in ['runtime.py','stage-runtime.py']:(HERE/(name.replace('.py','-r1.py'))).write_bytes((HERE/name).read_bytes())
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';parent='b8ce3ce92745a11b039e1335e87bbb2dd783c2c7';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True)
assert git('rev-parse','HEAD').strip()==parent and not git('status','--porcelain')
relative='drivers/media/platform/qcom/camss/camss-icp-a5-colour.c';path=source/relative;old=path.read_text();assert old.count('0x0a0003ff')==1;new=old.replace('0x0a0003ff','0x010003ff')
git('checkout','-b','samurai-ipe-gamma-dmi402');path.write_text(new);git('diff','--check');git('add','--',relative);git('commit','-m','media: camss: use target Gamma CDMDMI command format','--',relative)
state=dict(stage=402,parent=parent,source=str(source),branch=git('branch','--show-current').strip(),commit=git('rev-parse','HEAD').strip(),changed=[relative],clean=not git('status','--porcelain'),installed=False,maintained_source_stage=402,source_unchanged_from401=False,temporary_adapter_source_restored=True,gamma_dmi_opcode=1,previous_failed_opcode=10)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');(HERE/'gamma-dmi-correction.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
base=source/'drivers/media/platform/qcom/camss'
for name in ['camss-icp-a5-colour.c','camss-icp-a5-colour.h','camss-icp-a5-ipe.h','camss-icp-a5-boot.c']:(P/(name+'.proposed')).write_bytes((base/name).read_bytes())
(P/'camss-icp-a5-ipe.c.before').write_bytes((base/'camss-icp-a5-ipe.c').read_bytes())
(P/'gamma-lut-oracle-private.bin').write_bytes((P.parent/'kernel401/gamma-lut-oracle-private.bin').read_bytes())
contract=json.loads((HERE.parent/'kernel401/contract-validation.json').read_text());contract.update(stage=402,indirect_dmi_opcode=1,source_cmd_type=1,source_cmd_type_verified_from_original_resource_init=True,previous401_opcode10_withdrawn=True)
(HERE/'contract-validation.json').write_text(json.dumps(contract,indent=2)+'\n')
for name in ['check-parcel.py','check-transfer.py','check-firmware-parcel.py','build-intree.py']:
 text=(HERE.parent/'kernel401'/name).read_text().replace('stage=401','stage=402').replace('0x0a0003ff','0x010003ff')
 (HERE/name).write_text(text)
for name in ['stage-runtime.py','runtime.py']:
 text=(HERE/(name.replace('.py','-r1.py'))).read_text().replace('k402-gamma-r1','k402-gamma-r2').replace('runtime-collected-r1','runtime-collected-r2')
 if name=='stage-runtime.py':text=text.replace("assert test['modules'][0]['sha256']==core['sha256']","assert adapter['sha256']=='4bfbb80fcfefc50aa770b0c39c49f4c016093dda95da82c11e43144030fefe5a' # adapter ABI and fixture unchanged")
 (HERE/name).write_text(text)
# A fresh payload filename for the distinct transaction; never restart r1.
p=HERE/'stage-runtime.py';p.write_text(p.read_text().replace("P/'payload-private.tar.gz'","P/'payload-r2-private.tar.gz'"))
print(json.dumps(state,indent=2))
