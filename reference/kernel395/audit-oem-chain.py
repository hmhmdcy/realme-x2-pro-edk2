from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;out=P/'oem';out.mkdir(exist_ok=True)
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6';path='drivers/media/platform/msm/camera/cam_utils/cam_soc_util.c'
file=out/'cam_soc_util.c'
if not file.exists():file.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=35))
s=file.read_text();rows=[]
for name in ['cam_soc_util_disable_platform_resource','cam_soc_util_clk_disable_default','cam_soc_util_regulator_disable_default','cam_soc_util_clk_disable','cam_soc_util_regulator_disable','cam_soc_util_irq_disable']:
 m=re.search(r'(?:static )?(?:int|void)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert m,name
 body=m.group();rows.append(dict(name=name,line=s[:m.start()].count('\n')+1,lines=body.count('\n'),body_sha256=hashlib.sha256(body.encode()).hexdigest(),direct_reset_control='reset_control_' in body))
 print(body)
(HERE/'oem-resource-audit.json').write_text(json.dumps(dict(stage=395,commit=commit,path=path,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),functions=rows,primary_oem_code_private=True),indent=2)+'\n')
