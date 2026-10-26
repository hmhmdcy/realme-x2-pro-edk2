from pathlib import Path
import ast
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel135'
prev = r / 'reference/kernel134'
t = (prev / 'collect-recovered-runtime.sh').read_text().replace('k134-recovered-runtime', 'k135-first-runtime').replace('/var/lib/samurai/k134-preflash/boot-id-private.txt', '/var/lib/samurai/k135-preflash/boot-id-private.txt').replace('/tmp/k134-recovered-runtime', '/tmp/k135-first-runtime').replace('KERNEL134_RECOVERED_NATIVE', 'K135_FIRST_AUTOMATIC_NATIVE')
t = t.replace('dmesg > "$dest/dmesg.txt"', 'sha256sum -c /var/lib/samurai/k135-preflash/gui-config.sha256 > "$dest/gui-config-check.txt"\ncat /sys/class/power_supply/samurai-usb-input/uevent > "$dest/usb-input-uevent-final.txt"\niw dev wlan0 link > "$dest/wifi-link-private.txt"\ndmesg > "$dest/dmesg.txt"')
assert not (ref / 'collect-runtime.sh').exists()
(ref / 'collect-runtime.sh').write_text(t)
t = (prev / 'inspect-recovered-runtime.py').read_text().replace("out=Path('/mnt/e/edk2-samurai-out/kernel134')", "out=Path('/mnt/e/edk2-samurai-out/kernel135')").replace("out/'recovered-runtime-private.tar.gz'", "out/'first-runtime-private.tar.gz'").replace("out/'modules-k134-private.tar.gz'", "out.parent/'kernel134/modules-k134-private.tar.gz'").replace('DTB-k134-private', 'DTB-k135-private').replace("r/'reference/kernel134/embedded-runtime-validation.json'", "r/'reference/kernel135/embedded-runtime-validation.json'")
t = t.replace('report=dict(initial_display_boot_failed=True,single_native_panel_reprobe_required=True,permanent_display_fix=False,', '''mdss='/soc@0/display-subsystem@ae00000'
dispcc='/soc@0/clock-controller@af00000'
assert live[mdss]['resets']==live[dispcc]['phandle']+bytes(4)
assert data['gui-config-check.txt'].count(b': OK')==3 and b'FAILED' not in data['gui-config-check.txt']
bad=[b'CTL shutdown failed',b'kms hw init failed',b'failed to acquire mdss reset',b'boot INTF1 frame stalled',b'adev bind failed']
assert not any(token in data['dmesg.txt'] for token in bad)
assert data['connector.txt'].strip()==b'connected'
assert b'active=1' in data['drm-state.txt']
report=dict(dt_variant=135,software_generation=134,initial_display_boot_pass=True,panel_reprobe_or_greetd_marker_recovery_used=False,permanent_display_fix=False,mdss_reset_live_property_verified=True,original_gui_configuration_unchanged=True,''')
ast.parse(t)
assert not (ref / 'inspect-runtime.py').exists()
(ref / 'inspect-runtime.py').write_text(t)
print('K135_NATIVE_FIRST_BOOT_COLLECTOR_AND_FULL_RUNTIME_VERIFIER_READY', flush=True)
