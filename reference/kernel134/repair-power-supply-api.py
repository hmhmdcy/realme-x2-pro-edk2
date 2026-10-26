from pathlib import Path
import hashlib
import json
import runpy
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
runpy.run_path(str(ref / 'ensure-build-volume.py'))
k = Path('/home/cy122/pmos-samurai-build134/usb134/kernel')
driver = k / 'drivers/power/supply/samurai-usb-input.c'
assert hashlib.sha256(driver.read_bytes()).hexdigest() == 'e1c1cb82da089a639673553fd9a3c810439a190249ce69eae3978871da8d9422'
header = (k / 'include/linux/power_supply.h').read_text()
fragment = header[header.index('struct power_supply_config {'):header.index('struct power_supply_desc {')]
assert 'struct fwnode_handle *fwnode;' in fragment and '*of_node;' not in fragment
before = driver.read_text()
after = (ref / driver.name).read_text()
assert after == (before.replace('#include <linux/power_supply.h>', '#include <linux/power_supply.h>\n#include <linux/property.h>')
    .replace('config.of_node = dev->of_node;', 'config.fwnode = dev_fwnode(dev);'))
driver.write_text(after)
report = json.loads((ref / 'source-integration-validation.json').read_text())
report['source_driver_sha256'] = hashlib.sha256(driver.read_bytes()).hexdigest()
report['power_supply_firmware_node_api_checked_against_actual_header'] = True
report['initial_compile_failure_preserved'] = 'power_supply_config.of_node replaced by current fwnode API'
(ref / 'source-integration-validation.json').write_text(json.dumps(report, indent=2) + '\n')
source = (ref / 'validate-usb-source.py').read_text()
source = source[:source.index("runpy.run_path(str(r / 'reference/kernel122/ensure-rootfs-volume.py'))")]
source = source.replace("/usb134'", "/usb134-r4'").replace('host-test-private.txt', 'host-test-r4-private.txt')
exec(compile(source, 'final-power-supply-api-source-read-and-decoder-tests', 'exec'))
print('K134_CURRENT_FWNODE_API_REPAIRED_AND_HOST_TESTS_REVALIDATED', flush=True)
