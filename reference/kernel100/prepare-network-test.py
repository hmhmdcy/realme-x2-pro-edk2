from pathlib import Path

root=Path('/mnt/e/RealmeX2Pro edk2/reference')
out=Path('/mnt/e/edk2-samurai-out/kernel100')
target=root/'kernel100/test-network.sh'
assert not target.exists()
source=(root/'kernel99/restore-network.sh').read_text()
source=source.replace("grep -qx RADIO_RAM_RECOVERY_PASS /tmp/k99-radio-ram-recovery/result.txt",
    "grep -qx AUTOMATIC_ALL_SOURCE_READINESS_AND_HAPTICS_STANDBY_PASS /tmp/k100-automatic-start/result.txt")
source=source.replace('#98 SMP PREEMPT','#99 SMP PREEMPT').replace('k99','k100').replace('restored-network-retry1','initial-network')
source=source.replace('MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS','AFTER_AUTO_START_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS')
target.write_text(source)
assert not (out/'wpa-private.conf').exists()
(out/'wpa-private.conf').write_bytes((out.parent/'kernel99/wpa-private.conf').read_bytes())
print('PRIVATE_NETWORK_TEST_PREPARED')
