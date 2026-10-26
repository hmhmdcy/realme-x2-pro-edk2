from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='95caf30a629bbaf454ebfc9ed25ce16ea3a952b5' and not git('status','--porcelain')
for relative in ['','drivers','drivers/media','drivers/media/platform','drivers/media/platform/qcom','drivers/media/platform/qcom/camss','arch','arch/arm64','arch/arm64/boot','arch/arm64/boot/dts','arch/arm64/boot/dts/qcom','Documentation','Documentation/devicetree','Documentation/devicetree/bindings','Documentation/devicetree/bindings/media']:
 p=source/relative/'AGENTS.md'
 if p.exists():print('AGENTS '+str(p)+'\n'+p.read_text())
names=['drivers/media/platform/qcom/camss/'+n for n in ['camss-icp-a5-boot-test.c','camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-m2m.c','camss-icp-a5-m2m.h','camss-icp-a5-ipe.h','Kconfig','Makefile']]
names+=['arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-realme-samurai.dts']
for name in names:
 p=source/name
 if p.exists():
  target=host.PRIVATE/'baseline'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
print(json.dumps(dict(source=str(source),commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),snapshots=names),indent=2))
print((host.PRIVATE/'baseline/drivers/media/platform/qcom/camss/camss-icp-a5-boot-test.c').read_text())
