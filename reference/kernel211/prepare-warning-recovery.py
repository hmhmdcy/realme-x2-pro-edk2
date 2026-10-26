from pathlib import Path
import ast,json,subprocess
here=Path(__file__).resolve().parent
text=(here/'check-quiesce.py').read_text()
text=text.replace("read_text().strip()=='0'","read_text().strip()=='512'")
old="assert current.count('WARNING:')==prior.count('WARNING:')==0";assert old in text
text=text.replace(old,"assert prior.count('WARNING:')==0 and current.count('WARNING:')==2\nassert all('clk-branch.c:87 at clk_branch_toggle' in line for line in current.splitlines() if 'WARNING:' in line)\nassert current.count(\"cam_cc_mclk2_clk status stuck at 'off'\")==2\nassert all(current.count(v)==0 for v in ['Oops:', 'gpu fault:', 'fatal error received', 'Frame reassembly failed'])")
text=text.replace('camera-quiesce-validation.json','camera-quiesce-recovery-validation.json').replace("camera['taint']==0","camera['taint']==512 and camera['known_mclk_warning_count']==2").replace('taint=0,current_kernel','taint=512,known_captured_mclk_warnings=2,current_kernel')
assert 'taint=0' not in text;ast.parse(text);(here/'check-quiesce-recovery.py').write_text(text)
text=(here/'quiesce-current183.sh').read_text();start=text.index('if rc-service elogind status')
tail=text[start:].replace('/tmp/k211-check-quiesce.py','/tmp/k211-check-quiesce-recovery.py')
prefix='''#!/bin/sh
set -eu
umask 077
before=/var/lib/samurai/k211-before-reboot
dest=/var/lib/samurai/k211-quiesce
test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat "$before/boot-id-private.txt")"
test "$(cat /proc/sys/kernel/tainted)" = 512
test ! -e "$dest/quiesce-validation.json"
for module in imx471 qcom_camss v4l2_cci qcom_pm8008_regulator qcom_pm8008 i2c_qcom_cci; do test ! -d "/sys/module/$module"; done
test -z "$(pgrep -u 10000 || true)"
'''
(here/'continue-quiesce-after-warning.sh').write_text(prefix+tail)
text=(here/'freeze-for-bootloader.sh').read_text().replace('"$(cat /proc/sys/kernel/tainted)" = 0','"$(cat /proc/sys/kernel/tainted)" = 512').replace('/tmp/k211-check-quiesce.py','/tmp/k211-check-quiesce-recovery.py')
(here/'freeze-after-warning.sh').write_text(text)
text=(here/'linux-restart2-bootloader.py').read_text().replace('import json\n','import json\nimport subprocess\n').replace("read_text().strip() == '0'","read_text().strip() == '512'").replace('taint=0,','taint=512, known_captured_mclk_warnings=2,')
target="assert Path('/proc/sys/kernel/tainted').read_text().strip() == '512'"
text=text.replace(target,target+"\nwarning_log = subprocess.check_output(['dmesg'], text=True)\nassert warning_log.count('WARNING:') == 2 and warning_log.count(\"cam_cc_mclk2_clk status stuck at 'off'\") == 2\nassert all('clk-branch.c:87 at clk_branch_toggle' in line for line in warning_log.splitlines() if 'WARNING:' in line)")
ast.parse(text);(here/'restart-after-warning.py').write_text(text)
text=(here/'reboot-current.py').read_text().replace("proof['taint'] == 0","proof['taint'] == 512 and proof['known_captured_mclk_warnings'] == 2").replace('freeze-for-bootloader.sh','freeze-after-warning.sh').replace('linux-restart2-bootloader.py','restart-after-warning.py')
ast.parse(text);(here/'reboot-after-warning.py').write_text(text)
for name in ['continue-quiesce-after-warning.sh','freeze-after-warning.sh']:subprocess.run(['sh','-n',str(here/name)],check=True)
print('Recovery tools preserve known WARN2/taint512 explicitly and reject any new/different warning; original scripts retained.')
