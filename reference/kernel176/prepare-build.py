from pathlib import Path
import ast

ref=Path(__file__).parent
s=(ref.parent/'kernel175/build-package-v4.py').read_text()
s=s.replace('kernel175','kernel176').replace('k175','k176').replace('K175','K176').replace("KBUILD_BUILD_VERSION='175'","KBUILD_BUILD_VERSION='176'")
s=s.replace("'#175 SMP PREEMPT'","'#176 SMP PREEMPT'").replace('stage=175','stage=176').replace('kernel_build=175','kernel_build=176')
s=s.replace("baseline=json.loads((ref.parent/'kernel174/build-package-validation.json').read_text())","baseline=json.loads((ref.parent/'kernel175/build-package-validation.json').read_text())")
s=s.replace("['W=1','-j4','sound/soc/codecs/wcd934x.o','sound/soc/qcom/samurai-audio.o','drivers/mfd/wcd934x.o']","['W=1','-j4','drivers/mfd/wcd934x.o','drivers/slimbus/core.o','drivers/slimbus/qcom-ngd-ctrl.o','sound/soc/codecs/wcd934x.o']")
s=s.replace('modules-root175-v4','modules-root176').replace('-v4-build-private.log','-build-private.log')
s=s.replace('Image-k176-lifetime-v4-private','Image-k176-reset-private').replace('logdump-k176-lifetime-v4.img','logdump-k176-reset.img')
s=s.replace("rollback=out.parent/'kernel174/logdump-k174-port-lifecycle.img'","rollback=out.parent/'kernel175/logdump-k175-lifetime-v4.img'").replace('rollback174_sha256','rollback175_sha256')
s=s.replace('already_up_bind_fix_included=True,card_probe_failure_cleanup_included=True,clock_lifetime_fix_included=True,first_candidate_not_deployed=True',
            'reset_address_refresh_and_managed_probe_cleanup_included=True,lifetimes175_preserved=True')
ast.parse(s);(ref/'build-package.py').write_text(s)
print('K176_BUILD_PREPARED',flush=True)
