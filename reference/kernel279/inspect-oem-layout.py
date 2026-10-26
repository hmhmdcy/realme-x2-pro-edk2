"""Pin the handset's VFE170/CSID170 register and DMA descriptors for comparison."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
repo=Path('/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git');commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',commit,'drivers/media/platform/msm/camera'],text=True).splitlines()
selected=[p for p in paths if p.endswith(('cam_vfe170.h','cam_ife_csid170.h','cam_vfe_camif_ver2.c','cam_vfe_top_ver2.h','cam_vfe_bus_ver2.c','cam_vfe_camif_ver2.h'))]
proof={}
for path in selected:
 data=subprocess.check_output(['git','-C',str(repo),'show',commit+':'+path]);name=Path(path).name;(P/('oem-'+name)).write_bytes(data)
 proof[path]=dict(commit=commit,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
 text=data.decode();terms=['module_cfg','demux','demosaic','lens','camif_cfg','vfe_out_type','num_wm','wm_idx','client_cfg','format_measure','camif_cmd','pixel_pattern','pix_path']
 hits=[str(i+1)+': '+l for i,l in enumerate(text.splitlines()) if any(t in l for t in terms)]
 print(name);print('\n'.join(hits[:55]))
(R/'oem-source-layout.json').write_text(json.dumps(dict(stage=279,sources=proof,no_hardware_changes=True),indent=2)+'\n')
