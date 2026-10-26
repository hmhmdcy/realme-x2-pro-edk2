"""Generate an optional internal PHY window from pinned original-Image bytes."""
from pathlib import Path
import difflib
import hashlib
import json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'apsd-integration/current-r7'
NAME='phy-qcom-snps-femto-v2.c'
source=BASE/'snapshots/drivers--phy--qualcomm--phy-qcom-snps-femto-v2.c'
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='019dd4759be4955dfae6d92192c2fceb085a4e6945607e4942fb746cf2ab65a9'
linkage=json.loads((BASE/'image-source-linkage.json').read_bytes())
assert linkage['source_baseline_commit']=='ba61a62293e0f6bc5838c06f2e85e033e3d702a8'
assert linkage['comparisons'][0]['byte_equal_to_original_image_source']
s=raw.decode().replace('\r\n','\n')
def replace(old,new):
 global s
 assert s.count(old)==1,old[:100]
 s=s.replace(old,new)
replace('#include <linux/slab.h>', '#include <linux/slab.h>\n#include <linux/pm_runtime.h>\n\n#include "phy-qcom-snps-femto-v2-window.h"')
replace(' * @phy_initialized: if PHY has been initialized correctly', ' * @phy_initialized: if PHY has been initialized correctly\n * @window: owned masked-state receipt, protected by generic PHY mutex\n * @window_generation: never-zero per-provider cookie generation\n * @window_pm_ref: active-only provider runtime reference retained by window')
replace('\tbool phy_initialized;','\tbool phy_initialized;\n\tstruct qcom_snps_hsphy_window_result window;\n\tu64 window_generation;\n\tbool window_pm_ref;')
replace('static int qcom_snps_hsphy_suspend(', (HERE/'window-functions.c.txt').read_text()+'\nstatic int qcom_snps_hsphy_suspend(')
for name in ['init','exit','set_mode']:
 start=s.index('static int qcom_snps_hsphy_'+name+'(')
 anchor='struct qcom_snps_hsphy *hsphy = phy_get_drvdata(phy);'
 i=s.index(anchor,start)+len(anchor)
 # init has local declarations after hsphy; insert after them to avoid
 # declaration-after-statement and preserve original idle branch bytes.
 if name=='init':
  i=s.index('\tint ret, i;',i)+len('\tint ret, i;')
 s=s[:i]+ '\n\n\tif (qcom_snps_hsphy_window_busy(hsphy))\n\t\treturn -EBUSY;' +s[i:]
for name in ['suspend','resume']:
 old='''static int __maybe_unused qcom_snps_hsphy_runtime_%s(struct device *dev)
{
	struct qcom_snps_hsphy *hsphy = dev_get_drvdata(dev);

	if (!hsphy->phy_initialized)
		return 0;

	return qcom_snps_hsphy_%s(hsphy);
}'''%(name,name)
 new='''static int __maybe_unused qcom_snps_hsphy_runtime_%s(struct device *dev)
{
	struct qcom_snps_hsphy *hsphy = dev_get_drvdata(dev);
	int ret = 0;

	mutex_lock(&hsphy->phy->mutex);
	if (qcom_snps_hsphy_window_busy(hsphy))
		ret = -EBUSY;
	else if (hsphy->phy_initialized)
		ret = qcom_snps_hsphy_%s(hsphy);
	mutex_unlock(&hsphy->phy->mutex);
	return ret;
}'''%(name,name)
 replace(old,new)
(HERE/NAME).write_text(s)
header='phy-qcom-snps-femto-v2-window.h'
patch=''.join(difflib.unified_diff(raw.decode().splitlines(True),s.splitlines(True),
 fromfile='a/drivers/phy/qualcomm/'+NAME,tofile='b/drivers/phy/qualcomm/'+NAME))
patch+=''.join(difflib.unified_diff([], (HERE/header).read_text().splitlines(True),
 fromfile='/dev/null',tofile='b/drivers/phy/qualcomm/'+header))
(HERE/'phy-window.patch').write_text(patch)
manifest=dict(source_commit=linkage['source_baseline_commit'],base_phy_sha256=hashlib.sha256(raw).hexdigest(),
 image_source_linkage_sha256=hashlib.sha256((BASE/'image-source-linkage.json').read_bytes()).hexdigest(),
 files={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in [NAME,header,'phy-window.patch']},
 automatic_consumer=False,exported_api=False,device_accessed=False)
(HERE/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
