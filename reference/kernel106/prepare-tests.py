from pathlib import Path
import hashlib,json,shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';old=root/'reference/kernel105'
out=Path('/mnt/e/edk2-samurai-out/kernel106');prev=out.parent/'kernel105'
for n in ['test-playback.sh','test-capture-dmic.sh']:
    assert not (ref/n).exists()
    s=(old/n).read_text().replace('kernel105','kernel106').replace('k105','k106').replace('#104 SMP PREEMPT','#105 SMP PREEMPT')
    (ref/n).write_text(s)
for n in ['tinymix','tinyplay','tinycap','tone-low-private.wav']:
    assert not (out/n).exists();shutil.copyfile(prev/n,out/n)
p=ref/'recover-after-mpss-crash.sh';s=p.read_text()
before='dmesg > "$dir/dmesg-before.txt"'
assert s.count(before)==1
s=s.replace(before,'''test -f /tmp/k106-first-radio-trace/SHA256SUMS
(cd /tmp/k106-first-radio-trace && sha256sum -c SHA256SUMS) > "$dir/first-trace-source-check.txt"
radio=/sys/kernel/tracing/instances/radio
test "$(cat "$radio/tracing_on")" = 0
# The first trace is preserved above. Clear only the independent radio ring.
echo > "$radio/trace"
echo 1 > "$radio/tracing_on"
'''+before)
after='dmesg > "$dir/dmesg-after.txt"'
assert s.count(after)==1
s=s.replace(after,'''echo 0 > "$radio/tracing_on"
cat "$radio/trace" > "$dir/trace.txt"
for cpu in "$radio"/per_cpu/cpu*; do
    cat "$cpu/stats" > "$dir/${cpu##*/}-stats.txt"
done
qrtr-lookup > "$dir/qrtr-after.txt"
cp /run/samurai-wifi/tftp.log /run/samurai-wifi/rmtfs.log "$dir/"
cat /run/samurai-wifi/tftp.pid /run/samurai-wifi/rmtfs.pid > "$dir/server-pids.txt"
'''+after)
p.write_text(s)
(out/'private-test-inputs.json').write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['tinymix','tinyplay','tinycap','tone-low-private.wav']},indent=2))
print('BOUNDED_TESTS_AND_SEPARATE_RECOVERY_TRACE_PREPARED')
