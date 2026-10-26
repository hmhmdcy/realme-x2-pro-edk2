from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';old=root/'reference/kernel101'
for name in ('collect-boot-failure.sh','recover-after-mpss-crash.sh'):
    s=(old/name).read_text().replace('k101','k104').replace('#100 SMP PREEMPT','#103 SMP PREEMPT')
    if name=='collect-boot-failure.sh':
        s=s.replace('cat /sys/bus/i2c/devices/1-005a/status','cat "$(/tmp/k104-haptics-device)/status"')
    else:
        # API failure is evidence to retain; prove ADSP identity/state directly.
        s=s.replace('grep -qx 0 /tmp/k104-audio-runtime/native-api-exit.txt\nadsp=$(cat /tmp/k104-audio-runtime/adsp-path.txt)', '''test -f /tmp/k104-audio-runtime/SHA256SUMS
count=0
for r in /sys/class/remoteproc/remoteproc*; do
    [ "$(cat "$r/name")" = adsp ] || continue
    count=$((count+1));adsp=$r
done
[ "$count" = 1 ]
[ "$(readlink -f "$adsp/device/of_node")" = /sys/firmware/devicetree/base/soc@0/remoteproc@17300000 ]
[ "$(cat "$adsp/firmware")" = qcom/sm8150/realme/samurai/adsp.mdt ]''')
        s=s.replace('''/usr/sbin/samurai-bluetooth start > "$dir/bt-start.txt" 2>&1
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
/tmp/k104-bt-mgmt-probe info > "$dir/bt-info.txt"''', '''ls /sys/class/bluetooth > "$dir/bt-class.txt"
test ! -s "$dir/bt-class.txt"''')
        s=s.replace('cat /sys/bus/aprbus/devices/*/samurai_api > "$dir/native-api-after.txt"', '''if cat /sys/bus/aprbus/devices/*/samurai_api > "$dir/native-api-after.txt" 2> "$dir/native-api-after-error.txt"; then
    echo 0 > "$dir/native-api-after-exit.txt"
else
    echo 1 > "$dir/native-api-after-exit.txt"
fi''')
    assert not (ref/name).exists()
    (ref/name).write_text(s)
s=(root/'reference/kernel103/test-core-rebind-once.sh').read_text().replace('k103','k104').replace('#102 SMP PREEMPT','#103 SMP PREEMPT')
(ref/'test-core-rebind-once.sh').write_text(s)
# Keep the original auto-start result. A later successful test is manual recovery.
p=ref/'test-auto-network.sh';s=p.read_text()
assert 'grep -qx 0 /run/samurai-wifi/boot-finished' in s
s=s.replace('grep -qx 0 /run/samurai-wifi/boot-finished', '''grep -qx 1 /run/samurai-wifi/boot-finished
test -f /tmp/k104-first-boot-failure/SHA256SUMS
grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k104-radio-recovery-first/result.txt''')
s=s.replace('AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS','MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS')
(ref/'test-auto-network.auto-only-before.sh').write_text(p.read_text())
p.write_text(s)
print('SINGLE_RECOVERY_TOOLS_PREPARED_WITH_AUTO_FAILURE_PRESERVED')
