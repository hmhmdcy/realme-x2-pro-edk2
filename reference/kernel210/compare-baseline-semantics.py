from pathlib import Path
import json,subprocess,sys
from fdt_compare import parser,compare
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel210/baseline-dtb')
system='--system-dtc' in sys.argv
yaml_path=out/('baseline-system.yaml' if system else 'baseline.yaml')
assert not yaml_path.exists()
p=subprocess.run(['dtc' if system else str(k/'scripts/dtc/dtc'),'-O','yaml','-o',str(yaml_path),'-b','0','-i'+str(k/'arch/arm64/boot/dts/qcom'),'-i'+str(k/'scripts/dtc/include-prefixes'),str(out/'baseline.pp.dts')],capture_output=True)
(out/('source-yaml-system-private.log' if system else 'source-yaml-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
parse=parser();old=parse((out.parent.parent/'kernel204/sm8150-samurai-bt-wake-static-private.dtb').read_bytes());new=parse((out/'baseline.dtb').read_bytes())
result=dict(stage=210,phandle_markers_from_source_yaml=True,scalar_cells_not_remapped=True,**compare(old,new,yaml_path))
(here/'baseline-semantic-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
