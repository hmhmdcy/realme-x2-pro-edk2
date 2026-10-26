from pathlib import Path
import json, os, re, subprocess, time
os.umask(0o077)
out=Path('/var/lib/samurai/k186-original-cycles')
out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/k186-reboot-runtime/boot-id-private.txt').read_bytes()
assert json.loads(Path('/var/lib/samurai/k186-load-fastrpc-r2/summary.json').read_text())['loaded_build_id_matches']
(out/'boot-id-private.txt').write_bytes(boot)
reports=[]
for i in range(1,4):
    code=subprocess.run(['sh','/var/lib/samurai/k186-tools/test-original-cycle'+str(i)+'.sh'],capture_output=True,timeout=130)
    (out/('cycle'+str(i)+'-worker-private.log')).write_bytes(code.stdout+code.stderr)
    trial=Path('/var/lib/samurai/k186-original-cycle'+str(i))
    log=(trial/'dmesg-final.txt').read_text()
    before=(trial/'dmesg-before.txt').read_text()
    assert log.startswith(before), 'Kernel ring coverage must be retained with candidate'
    extra=log[len(before):]
    faults={k:extra.count(v) for k,v in {
        'scm_assignment':'Assign memory protection call failed',
        'fastrpc_probe':'probe with driver qcom,fastrpc failed',
        'pool_reclaim':'failed to reclaim reserved pool',
        'slpi_start':'2400000.remoteproc: start timed out',
        'slpi_stop':'2400000.remoteproc: timed out on wait',
        'warning':'WARNING:', 'oops':'Oops:', 'gpu':'gpu fault:',
        'asoc':'ASoC error','bluetooth_reassembly':'Frame reassembly failed'}.items()}
    state=dict(cycle=i,worker_exit=code.returncode,fault_delta=faults,
        trial_exit=(trial/'trial-exit.txt').read_text().strip(),
        light_exit=(trial/'light-exit.txt').read_text().strip(),
        stop_exit=(trial/'stop-exit.txt').read_text().strip(),
        slpi_final=(trial/'slpi-final-state.txt').read_text().strip(),
        sensor_power_final=(trial/'power-final.txt').read_text().strip(),
        daemon_exit=(trial/'daemon-exit.txt').read_text().strip(),
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_bytes())
    reports.append(state)
    (out/'progress.json').write_text(json.dumps(reports,indent=2)+'\n')
    assert code.returncode==0 and state['trial_exit']=='0' and state['light_exit']=='0'
    assert state['stop_exit']=='0' and state['slpi_final']=='offline' and state['sensor_power_final']=='vdd=0 vddio=0'
    assert state['taint']==0 and state['same_boot'] and not any(faults.values())
    time.sleep(5)
(out/'summary.json').write_text(json.dumps(dict(stage=186,kernel_build=183,
    original_firmware_full_cycles=reports,all_three_full_cycles_passed=True),indent=2)+'\n')
print('THREE_ORIGINAL_FIRMWARE_CYCLES_PASSED')
