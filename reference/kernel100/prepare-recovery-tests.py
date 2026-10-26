from pathlib import Path

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel100')
target=ref/'test-recovered-network.sh'
assert not target.exists()
source=(ref/'test-network.sh').read_text().replace(
    'grep -qx AUTOMATIC_ALL_SOURCE_READINESS_AND_HAPTICS_STANDBY_PASS /tmp/k100-automatic-start/result.txt',
    'grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k100-radio-recovery-first/result.txt')
source=source.replace('initial-network','recovered-network').replace('AFTER_AUTO_START_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS',
    'MANUAL_AFTER_CRASH_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS')
target.write_text(source)
target=ref/'collect-recovered-checkpoint.sh'
assert not target.exists()
source=(ref/'collect-checkpoint.sh').read_text().replace(
    'grep -qx AUTOMATIC_ALL_SOURCE_READINESS_AND_HAPTICS_STANDBY_PASS /tmp/k100-automatic-start/result.txt',
    'grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k100-radio-recovery-first/result.txt')
source=source.replace('AFTER_AUTO_START_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS','MANUAL_AFTER_CRASH_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS')
source=source.replace('/tmp/k100-initial-network','/tmp/k100-recovered-network')
source=source.replace('cp -a /tmp/k100-automatic-start /tmp/k100-recovered-network "$dir/tests/"',
    'cp -a /tmp/k100-automatic-start /tmp/k100-first-boot-failure /tmp/k100-radio-recovery-first /tmp/k100-recovered-network "$dir/tests/"')
target.write_text(source)
print('RECOVERY_EVIDENCE_BRANCH_PREPARED')
