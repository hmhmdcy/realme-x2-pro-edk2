from pathlib import Path
import ast

ref=Path(__file__).parent
s=(ref.parent/'kernel174/build-package.py').read_text()
s=s.replace('kernel174','kernel175').replace('k174','k175').replace('K174','K175').replace("KBUILD_BUILD_VERSION='174'","KBUILD_BUILD_VERSION='175'")
s=s.replace("'#174 SMP PREEMPT'","'#175 SMP PREEMPT'").replace('stage=174','stage=175').replace('kernel_build=174','kernel_build=175')
s=s.replace("baseline=json.loads((ref.parent/'kernel172/build-package-validation.json').read_text())","baseline=json.loads((ref.parent/'kernel174/build-package-validation.json').read_text())")
s=s.replace("['W=1','-j4','sound/soc/codecs/wcd934x.o']","['W=1','-j4','sound/soc/codecs/wcd934x.o','sound/soc/qcom/samurai-audio.o','drivers/mfd/wcd934x.o']")
s=s.replace("rollback=out.parent/'kernel172/logdump-k172-headset.img'","rollback=out.parent/'kernel174/logdump-k174-port-lifecycle.img'")
s=s.replace('rollback172_sha256','rollback174_sha256').replace('k175-port-lifecycle','k175-lifetime')
s=s.replace('config_unchanged=True,dtb172_unchanged=True','port_irq174_preserved=True,config_unchanged=True,dtb172_unchanged=True')
ast.parse(s);(ref/'build-package.py').write_text(s)
print('K175_BUILD_PREPARED',flush=True)
