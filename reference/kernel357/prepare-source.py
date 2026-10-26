"""Fix the OF node reference lifetime in the common IOMMU reservation parser."""
from pathlib import Path
import importlib.util, json, subprocess

HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel357');P.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
parent='3a485310daa7baed7d1f0d1798ded15cc85ad1ab'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==parent
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True)
subprocess.run(['git','-C',str(source),'switch','-c','samurai-iommu-node-lifetime357'],check=True,capture_output=True)
path=source/'drivers/iommu/of_iommu.c';old=path.read_text()
start=old.index('void of_iommu_get_resv_regions')
assert old[start:].count('struct device_node *np;')==1
new=old[:start]+old[start:].replace('struct device_node *np;','struct device_node *np __free(device_node) = NULL;',1)
path.write_text(new)
(P/'of_iommu-before-private.c').write_text(old)
(HERE/'of_iommu-after.c').write_text(new)
(HERE/'source-state.json').write_text(json.dumps(dict(stage=357,source=str(source),parent=parent,
    branch='samurai-iommu-node-lifetime357',installed=False),indent=2)+'\n')
print('Prepared one-line common IOMMU node-lifetime fix on a separate branch.')
