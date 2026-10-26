from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';out=Path('/mnt/e/edk2-samurai-out/kernel103')
s=(root/'reference/kernel102/test-auto-network.sh').read_text().replace('k102','k103').replace('#101 SMP PREEMPT','#102 SMP PREEMPT')
start=s.index('/tmp/k103-bt-mgmt-probe info');end=s.index('[ "$(cat /proc/sys/kernel/tainted)" = 0 ]',start)
s=s[:start]+'''ls /sys/class/bluetooth > "$dir/bt-class.txt"
test ! -s "$dir/bt-class.txt"
'''+s[end:]
assert not (ref/'test-auto-network.sh').exists()
(ref/'test-auto-network.sh').write_text(s)
profile=out/'wpa-5g-private.conf';assert not profile.exists()
profile.write_bytes((out.parent/'kernel102/wpa-5g-private.conf').read_bytes())
print('NETWORK_TEST_PREPARED; BLUETOOTH_STOP_ONLY')
