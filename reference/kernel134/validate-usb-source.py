from pathlib import Path
import hashlib
import json
import re
import runpy
import shutil
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
runpy.run_path(str(r / 'reference/kernel118/ensure-build-volume.py'))
stage = Path('/home/cy122/pmos-samurai-kernel118/usb134')
assert not stage.exists() and shutil.disk_usage(stage.parent).free > 256 * 1024**2
stage.mkdir(mode=0o700)
for name in ['samurai-usb-input-decode.h', 'samurai-usb-input.c', 'test-usb-input.c', 'usb-read-stubs.h', 'Makefile']:
    shutil.copy2(ref / name, stage / name)
source = (ref / 'samurai-usb-input.c').read_text()
assert not re.search(r'\b(?:regmap_(?:write|update_bits|bulk_write)|spmi_ext_register_write|regulator_enable|regulator_disable|tcpm_register_port)\b', source)
reader = source[source.index('static int samurai_usb_read_status'):source.index('static enum power_supply_usb_type')]
(stage / 'actual-usb-read-functions.c').write_text('#include "usb-read-stubs.h"\n' + reader)
cmd = ['gcc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
       '-fno-omit-frame-pointer', str(stage / 'test-usb-input.c'), '-o', str(stage / 'test-usb-input')]
subprocess.run(cmd, check=True, timeout=60)
test = subprocess.check_output([str(stage / 'test-usb-input')], text=True, timeout=30).strip()
assert test.startswith('K134_ACTUAL_C_DECODER_AND_IO_FAULT_SCENARIOS_PASS ')
(out / 'host-test-private.txt').write_text(test + '\n')
header = out / 'stock-smb5-reg.h'
assert hashlib.sha256(header.read_bytes()).hexdigest() == 'd8b7ac8b704f8c7be4399249296f0c7acc156e5b44db20c71f406142a179e508'
text = header.read_text()
for token in ['#define USBIN_BASE\t0x1300', '#define TYPEC_BASE\t0X1500', 'APSD_DTC_STATUS_DONE_BIT',
              'CDP_CHARGER_BIT', 'TYPE_C_SNK_STATUS_REG', 'TYPE_C_MISC_STATUS_REG']:
    assert token in text
report = dict(stage=134, decoder_sha256=hashlib.sha256((ref / 'samurai-usb-input-decode.h').read_bytes()).hexdigest(),
    driver_sha256=hashlib.sha256((ref / 'samurai-usb-input.c').read_bytes()).hexdigest(),
    original_oem_header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
    original_oem_commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6',
    original_oem_header_url='https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/supply/qcom/smb5-reg.h',
    host_scenarios=int(test.rsplit(' ', 1)[1]), actual_reader_and_decoder_executed=True,
    all_fourteen_register_read_failure_positions_propagated=True, changing_snapshot_rejected=True,
    sdp_current_budget_not_inferred=True, address_allowlist_only=True, charger_or_role_writes=0,
    gcc_warnings_errors_asan_ubsan_passed=True, kernel_module_build_pending=True,
    deployed=False, charging_control_accepted=False, goal_complete=False)
(ref / 'usb-source-static-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(test, flush=True)
runpy.run_path(str(r / 'reference/kernel122/ensure-rootfs-volume.py'))
mount = Path('/home/cy122/pmos-samurai-rootfs122')
print('K134_EXISTING_E122_INNER_FREE_BYTES', shutil.disk_usage(mount).free, flush=True)
with (out / 'e122-directory-space-private.txt').open('w') as log:
    subprocess.run(['du', '-h', '--max-depth=1', str(mount)], stdout=log, check=True, timeout=90)
print('K134_EXISTING_VOLUME_SPACE_INSPECTION_COMPLETE', flush=True)
