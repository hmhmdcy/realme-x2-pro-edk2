from pathlib import Path
import hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193')
target=k/'drivers/of/samurai-front-identify.c';assert not target.exists();target.write_bytes((ref/target.name).read_bytes())
for name,extra in [('drivers/of/Makefile','\nobj-$(CONFIG_OF_SAMURAI_FRONT_IDENTIFY) += samurai-front-identify.o\n'),('drivers/of/Kconfig','\nconfig OF_SAMURAI_FRONT_IDENTIFY\n\ttristate "Temporary realme X2 Pro front camera identification"\n\tdepends on OF_DYNAMIC && ARCH_QCOM && MODULES && I2C && REGULATOR && GPIOLIB\n\tdepends on PINCTRL && COMMON_CLK\n\tselect REGMAP_I2C\n\thelp\n\t  Run one bounded camera power/ID/read/power-off sequence on\n\t  realme samurai. Development only; leave disabled for normal builds.\n\t  Read the ID without programming sensor stream registers.\n\t  Restore GPIOs, clocks and PMIC values before returning.\n')]:
 p=k/name;p.write_text(p.read_text()+extra)
old=ref/'cci-helper-build-validation.json';script=(ref/'build-cci-helper.py').read_text()
script=script.replace('samurai-cci-bringup','samurai-front-identify').replace('cci-helper-build','front-helper-build').replace('cci-helper-source','front-helper-source').replace('CONFIG_OF_SAMURAI_CCI_BRINGUP','CONFIG_OF_SAMURAI_FRONT_IDENTIFY')
(ref/'build-front-helper.py').write_text(script)
base=json.loads((ref/'cci-helper-source-validation.json').read_text())
base['helper_source_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();base['checkpatch_exit']=None
(ref/'front-helper-source-validation.json').write_text(json.dumps(base,indent=2)+'\n')
print('Front ID helper prepared; existing source hashes retained')
