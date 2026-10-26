from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='1f0038ccbdc2efb71d97fc85c1f64452f9ce41a6' and not git('status','--porcelain')
for path in ['drivers/media/platform/qcom/camss/camss-icp-a5-boot.c','drivers/media/platform/qcom/camss/camss-icp-a5-boot.h','drivers/media/platform/qcom/camss/camss-icp-a5-boot-test.c','drivers/media/platform/qcom/camss/camss-icp-a5-resources.c','drivers/media/platform/qcom/camss/camss-icp-a5-resources.h','drivers/clk/qcom/camcc-sm8150.c','include/dt-bindings/clock/qcom,sm8150-camcc.h']:
 (P/(Path(path).name+'.before')).write_bytes((source/path).read_bytes())
repo='/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git';commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6';directory=P/'oem';directory.mkdir(exist_ok=True);records=[]
paths=['drivers/media/platform/msm/camera/cam_icp/icp_hw/ipe_hw/ipe_core.h']
for path in paths:
 out=directory/Path(path).name
 if not out.exists():out.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=35))
 raw=out.read_bytes();records.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(HERE/'oem-sources.json').write_text(json.dumps(dict(stage=381,commit=commit,files=records),indent=2)+'\n')
(HERE/'source-before.json').write_text(json.dumps(dict(stage=381,source=str(source),commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),clean=True),indent=2)+'\n')
print('Verified source380 and retained current core/resources/clock reset definitions plus fixed original IPE reset header.')
