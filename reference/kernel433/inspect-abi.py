"""Read current parameter/ack contracts and pinned GPL DMI64 implementation."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage433abi',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);kernel=m.mounted_build().parent/'source354'
paths=['include/uapi/linux/qcom-camss-config.h','drivers/media/platform/qcom/camss/camss-vfe.c','drivers/media/platform/qcom/camss/camss-vfe.h','drivers/media/platform/qcom/camss/Makefile']
out=P/'kernel-before'
for path in paths:(out/Path(path).name).write_bytes((kernel/path).read_bytes())
q=subprocess.run(['git','-C',str(kernel),'grep','-n','-E','params_apply|params.*sequence|reg_update.*params|params.*reg_update','--','drivers/media/platform/qcom/camss'],text=True,capture_output=True);assert q.returncode in [0,1];(P/'ack-search-private.txt').write_text(q.stdout);print(q.stdout[:10000])
repo=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git');rev='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6';path='drivers/media/platform/msm/camera/cam_cdm/cam_cdm_util.c';raw=subprocess.check_output(['git','--git-dir='+str(repo),'show',rev+':'+path]);assert raw==(P.parent/'kernel286/reference-cam_cdm_util.c-private').read_bytes();(P/'official-cam-cdm-util-private.c').write_bytes(raw)
header=(P.parent/'kernel296/titan170-ife-source-0-private.h').read_bytes();assert hashlib.sha256(header).hexdigest()=='800a9dbbf2bdf16ec36a03bd670d733bee8f63d4d9ed0311de9b24e29413cf53';facts={}
for line in header.decode().splitlines():
 if re.search(r'GTM|regIFE_IFE_0_VFE_DMI_|DMI_CFG_AUTO_INC|DMI_CFG_AUTO_LOAD|regIFE_IFE_0_VFE_MODULE_COLOR_(CGC_OVERRIDE|EN)',line):
  match=re.match(r'#define\s+(\w+)\s+(0x[0-9a-fA-F]+|\d+)\b',line)
  if match:facts[match[1]]=int(match[2],0)
  match=re.match(r'\s*(IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_GTM_LUT_RAM_BANK[01])\s*=\s*(0x[0-9a-fA-F]+)',line)
  if match:facts[match[1]]=int(match[2],0)
r=dict(stage=433,official_kernel_commit=rev,official_cdm_path=path,official_cdm_sha256=hashlib.sha256(raw).hexdigest(),retained_generated_header_sha256=hashlib.sha256(header).hexdigest(),protocol=facts,source_reused_no_download=True,phone_accessed=False,passed=True)
(HERE/'protocol-sources.json').write_text(json.dumps(r,indent=2)+'\n')
