from pathlib import Path
import hashlib,json,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel102'
out=Path('/mnt/e/edk2-samurai-out/kernel102')
assert not (out/'postboot-tools-prepared.json').exists()
for name in ('collect-audio-runtime.sh','collect-boot-failure.sh'):
    p=ref/name;s=p.read_text()
    s=s.replace('cat /sys/bus/i2c/devices/1-005a/status', 'cat "$(/tmp/k102-haptics-device)/status"')
    p.write_text(s)
# This warm boot succeeded automatically; retain the original failed-boot
# recovery tools unused. The network test accepts only that observed success.
old=(ref/'test-recovered-network-retry1.sh').read_text()
assert not (ref/'test-auto-network.sh').exists()
s=old.replace('grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k102-radio-recovery-first/result.txt',
              'grep -qx 0 /run/samurai-wifi/boot-finished\n/usr/sbin/samurai-bluetooth stop')
s=s.replace('k102-recovered-network-retry1','k102-auto-network')
s=s.replace('MANUAL_AFTER_CRASH_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS','AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS')
(ref/'test-auto-network.sh').write_text(s)
profile=(out/'wpa-5g-private.conf').read_text()
assert re.search(r'^\s*freq_list=5180\s*$',profile,re.M)
assert (out/'bt-mgmt-probe-private').read_bytes()==(out.parent/'kernel98/bt-mgmt-probe-scan-window').read_bytes()
report=dict(private_profile_band_mhz=5180,bt_probe_sha256=hashlib.sha256((out/'bt-mgmt-probe-private').read_bytes()).hexdigest(),
 motor_resolved_by_exact_driver_and_dt=True,auto_boot_observed_success=True,manual_recovery_not_executed=True)
(out/'postboot-tools-prepared.json').write_text(json.dumps(report,indent=2)+'\n')
print('AUDIO_POSTBOOT_TOOLS_PREPARED')
