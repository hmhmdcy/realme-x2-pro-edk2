"""Read the current OF/SMMU prerequisites; no device state transition."""
from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();config=(build/'.config').read_text()
features={key:next((l.split('=',1)[1] for l in config.splitlines() if l.startswith(key+'=')),None) for key in ['CONFIG_OF_OVERLAY','CONFIG_OF_DYNAMIC','CONFIG_ARM_SMMU','CONFIG_IOMMU_DMA']}
code=r'''
from pathlib import Path
import json,struct
root=Path('/sys/firmware/devicetree/base');soc=root/'soc@0';smmu=soc/'iommu@15000000'
result=dict(boot_matches=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes(),smmu_exists=smmu.is_dir(),soc_exists=soc.is_dir(),core_already_loaded=Path('/sys/module/qcom_camss_icp_a5_core').exists())
if smmu.is_dir():
 result.update(smmu_path='/soc@0/iommu@15000000',phandle=struct.unpack('>I',(smmu/'phandle').read_bytes())[0],iommu_cells=struct.unpack('>I',(smmu/'#iommu-cells').read_bytes())[0],compatible=(smmu/'compatible').read_bytes().replace(b'\0',b',').decode())
result['reserved_memory_exists']=(root/'reserved-memory').is_dir()
result['kernel_release']=Path('/proc/sys/kernel/osrelease').read_text().strip()
print(json.dumps(result))
'''
q=host.raw_ssh('python3 -',input=code.encode(),timeout=20);device=json.loads(q.stdout);(P/'runtime-prerequisites-private.json').write_text(json.dumps(device,indent=2)+'\n')
report=dict(stage=354,features=features,**device,read_only=True,passed=device['boot_matches'] and device['smmu_exists'] and device['soc_exists'])
(HERE/'runtime-prerequisites.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
