"""One A.11 boot with SSC discovery and private SCM/GLINK trace."""
from pathlib import Path
import hashlib,json,subprocess
import host

ref=Path(__file__).resolve().parent
source=(ref.parent/'kernel186/test-original-cycle1.sh').read_text()
source=source.replace('k186-reboot-runtime/boot-id-private.txt','k186-reboot-runtime-r2/boot-id-private.txt')
source=source.replace('ram-k186-original-cycle1','ram-k187-a11')
source=source.replace('k186-original-cycle1','k187-a11-trial')
source=source.replace('timeout -s TERM -k 3 110 ','timeout -s TERM -k 3 180 ')
marker='cat "$node/firmware" > "$dest/firmware-selected.txt"'
source=source.replace(marker,'''selected_fw=qcom/sm8150/realme/samurai-a11-r187/slpi.mdt
echo "$selected_fw" > "$node/firmware"
cat "$node/firmware" > "$dest/firmware-selected.txt"
(cd /lib/firmware/qcom/sm8150/realme/samurai-a11-r187 && sha256sum -c SHA256SUMS) > "$dest/candidate-firmware-check.txt"''')
start=source.index('set +e\ntimeout -s TERM -k 2 55 python3')
source=source[:start]+'''set +e
timeout -s TERM -k 2 40 python3 -B /var/lib/samurai/k187-tools/ssc-attribute-census.py --output "$dest/attributes" --duration 25 > "$dest/attributes-host-private.txt" 2>&1
query=$?
set -e
printf '%s\\n' "$query" > "$dest/attributes-exit.txt"
test "$(cat "$node/state")" = running
kill -0 "$owner"
if [ "$query" != 0 ]; then exit "$query"; fi
set +e
timeout -s TERM -k 2 50 python3 -B /var/lib/samurai/k187-tools/ssc-light-probe.py --output "$dest/light" --duration 15 > "$dest/light-host-private.txt" 2>&1
light=$?
set -e
printf '%s\\n' "$light" > "$dest/light-exit.txt"
test "$(cat "$node/state")" = running
kill -0 "$owner"
exit "$light"
'''
# Isolated existing tracepoints record firmware calls, not invented owner state.
marker='trap finish EXIT\n'
trace='''trace=/sys/kernel/tracing/instances/k187-slpi
test ! -e "$trace"
mkdir "$trace"
echo 1024 > "$trace/buffer_size_kb"
for group in qcom_scm qcom_smp2p qcom_glink; do echo 1 > "$trace/events/$group/enable"; done
echo 1 > "$trace/tracing_on"
'''
source=source.replace(marker,marker+trace)
marker='    dmesg > "$dest/dmesg-final.txt"'
finishtrace='''    if [ -d "$trace" ]; then
        echo 0 > "$trace/tracing_on"
        cat "$trace/trace" > "$dest/scm-glink-trace-private.txt"
        for path in "$trace"/per_cpu/cpu*/stats; do
            test -f "$path" || continue
            printf '%s\\n' "$path" >> "$dest/trace-stats-private.txt"
            cat "$path" >> "$dest/trace-stats-private.txt"
        done
        for group in qcom_scm qcom_smp2p qcom_glink; do echo 0 > "$trace/events/$group/enable"; done
        rmdir "$trace"
    fi
'''
source=source.replace(marker,finishtrace+marker)
# Define before installing the trap so early cleanup still has a valid path.
source=source.replace('trap finish EXIT\ntrace=', 'trace=/sys/kernel/tracing/instances/k187-slpi\ntrap finish EXIT\ntrace=')
path=ref/'test-a11-trial.sh'
assert not path.exists()
path.write_text(source)
subprocess.run(['sh','-n',str(path)],check=True)
for p in [path,ref.parent/'kernel113/ssc-suid-census.py',ref.parent/'kernel113/ssc-attribute-census.py',ref.parent/'kernel184/ssc-light-probe.py']:
    dest='/var/lib/samurai/k187-tools/'+p.name
    host.upload(p,dest)
    host.ssh('sha256sum -c -',input=(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+dest+'\n').encode())
report=dict(stage=187,script_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    original_fastrpc_module_used=True,current_kernel_build=183,a11_first_trial_on_fresh_boot=True,
    stock_calibration_only_in_private_ram_copy=True,isolated_scm_smp2p_glink_trace=True,
    no_owner_mask_changes_by_host=True,no_crash_injection=True,no_reboot_or_flash=True)
(ref/'trial-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
p=host.ssh('nohup sh /var/lib/samurai/k187-tools/test-a11-trial.sh > /var/lib/samurai/k187-a11-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE/'a11-worker-pid-private.txt').write_bytes(p.stdout)
print(json.dumps(report))
