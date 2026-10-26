"""Read maintained and same-handset OEM ISP sources without touching the camera hardware."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;main=Path('/home/cy122/x2pro-linux/camera270-kernel');vendor=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git')
def git(path,*args):return subprocess.check_output(['git','-C',str(path),*args],text=True)
files={}
for source,repo,paths in [('maintained',main,['drivers/media/platform/qcom/camss/camss-vfe-17x.c','drivers/media/platform/qcom/camss/camss.c']),('oem',vendor,['drivers/media/platform/msm/camera/cam_isp/isp_hw_mgr/isp_hw/vfe_hw/vfe17x/cam_vfe170.h'])]:
 for path in paths:
  text=git(repo,'show','HEAD:'+path);name=source+'-'+Path(path).name;target=host.PRIVATE/name;target.write_text(text)
  files[name]=dict(source=source,path=path,commit=git(repo,'rev-parse','HEAD').strip(),sha256=hashlib.sha256(text.encode()).hexdigest(),lines=len(text.splitlines()))
(host.PRIVATE/'isp-source-inputs-private.json').write_text(json.dumps(files,indent=2)+'\n')
for name in files:
 lines=(host.PRIVATE/name).read_text().splitlines()
 if name.endswith('camss.c'):terms=['vfe_res_8150','vfe_170','vfe_ops_170','CAMSS_8150']
 elif name.startswith('oem'):terms=['VFE_OUT_FULL','VFE_OUT_DS4','VFE_OUT_DS16','VFE_OUT_RAW_DUMP','VFE_OUT_FD','VFE_OUT_RDI','output','num_client','num_out','cam_vfe_top','rdi_hw_info']
 else:terms=['vfe_ops_170','PIX','RDI','vfe_enable','wm_start','wm_stop','wm_set','vfe_get']
 hits=[(i+1,l) for i,l in enumerate(lines) if any(t in l for t in terms)]
 print(name,'lines',len(lines));print('\n'.join(str(i)+': '+l for i,l in hits[:65]))
