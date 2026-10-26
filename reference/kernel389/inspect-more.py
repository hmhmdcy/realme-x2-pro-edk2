from pathlib import Path
import importlib.util
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=m.mounted_build().parent/'source354'
for name in ['drivers/media/platform/qcom/camss/camss.c','drivers/media/platform/qcom/camss/camss-icp-a5-resources.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts','Documentation/devicetree/bindings/media/qcom,sm8250-camss.yaml']:
 p=source/name;target=host.PRIVATE/'baseline'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
print((host.PRIVATE/'baseline/drivers/media/platform/qcom/camss/camss.c').read_text()[-3500:])
