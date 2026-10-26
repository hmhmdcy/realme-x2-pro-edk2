from pathlib import Path
import json
O=Path('/mnt/e/edk2-samurai-out/kernel91')
a=(O/'config-before').read_text().splitlines(); b=Path('/home/cy122/x2pro-linux/linux/.config').read_text().splitlines()
assert [x for x in a if x not in b]==['CONFIG_QCOM_RMTFS_MEM=m']
assert [x for x in b if x not in a]==['CONFIG_QCOM_RMTFS_MEM=y']
(O/'config-validation.json').write_text(json.dumps({'only_change':'CONFIG_QCOM_RMTFS_MEM=m -> y'},indent=2)+'\n')
