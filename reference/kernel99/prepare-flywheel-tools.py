from pathlib import Path
import json, subprocess

ref = Path('/mnt/e/RealmeX2Pro edk2/reference')
out = Path('/mnt/e/edk2-samurai-out/kernel99')
target = ref/'kernel99'
assert not (target/'collect-preflash.sh').exists()
for name in ('reboot-f1.ps1','read-eud.ps1','stop-connectivity.sh','scp-private.ps1'):
    source = (ref/'kernel98'/name).read_text().replace('kernel98','kernel99').replace('K98','K99').replace('k98','k99')
    (target/name).write_text(source)
source = (ref/'kernel98/collect-preflash.sh').read_text().replace('k98','k99').replace('#96 SMP PREEMPT','#97 SMP PREEMPT')
source = source.replace('grep -qx INDEPENDENT_QUERY_FAILURE_ISOLATION_PASS /tmp/k99-independent-addresses/result.txt\n','')
source = source.replace('grep -qx KEY_REMOVAL_BASELINE_CAPTURE_PASS /tmp/k99-key-removal/result.txt\n','')
source = source.replace('cp -a /tmp/k99-independent-addresses /tmp/k99-key-removal "$dir/"', 'cp -a /tmp/k98-final-readonly-status "$dir/"\ncp /tmp/k99-gpio-before.txt "$dir/"\ncat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux-before.txt"')
source = source.replace('935141253c61f2b9bb4ab92103217adaa45800a00894215326e1dac0d955718a','0ebd3ec3ab41a70b86f03b09cff2dd0d9e39d0bcdf739b2fdf2c96d0694e0fc2')
(target/'collect-preflash.sh').write_text(source)
subprocess.run(['sh','-n',str(target/'collect-preflash.sh')],check=True)
assert not (out/'fastboot-identity.json').exists()
(out/'fastboot-identity.json').write_bytes((out.parent/'kernel98/fastboot-identity.json').read_bytes())
print('HAPTICS_FLYWHEEL_TOOLS_PREPARED')
