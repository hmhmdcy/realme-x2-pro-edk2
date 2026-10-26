from pathlib import Path
import hashlib,json,shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';old=root/'reference/kernel104'
out=Path('/mnt/e/edk2-samurai-out/kernel105');prev=out.parent/'kernel104'
for n in ['test-playback.sh','test-capture-dmic.sh']:
    assert not (ref/n).exists()
    s=(old/n).read_text().replace('kernel104','kernel105').replace('k104','k105').replace('#103 SMP PREEMPT','#104 SMP PREEMPT')
    (ref/n).write_text(s)
for n in ['tinymix','tinyplay','tinycap','tone-low-private.wav']:
    assert not (out/n).exists();shutil.copyfile(prev/n,out/n)
p=ref/'test-auto-network.sh';s=p.read_text()
oldguard='''grep -qx 1 /run/samurai-wifi/boot-finished
test -f /tmp/k105-first-boot-failure/SHA256SUMS
grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k105-radio-recovery-first/result.txt'''
assert oldguard in s
s=s.replace(oldguard,'''if grep -qx 0 /run/samurai-wifi/boot-finished; then
    result=AUTOMATIC_FIRST_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS
else
    grep -qx 1 /run/samurai-wifi/boot-finished
    test -f /tmp/k105-first-boot-failure/SHA256SUMS
    grep -qx BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS /tmp/k105-radio-recovery-first/result.txt
    result=MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS
fi''')
s=s.replace('echo MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS > "$dir/result.txt"','echo "$result" > "$dir/result.txt"')
p.write_text(s)
(out/'private-test-inputs.json').write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['tinymix','tinyplay','tinycap','tone-low-private.wav']},indent=2))
print('BOUNDED_AUDIO_AND_FIRST_BOOT_NETWORK_TESTS_PREPARED')
