"""One normal nbcon record and one filtered record, after desktop quiesce."""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import time
import zlib

out=Path('/var/lib/samurai/k143-threaded-console-latency')
trace=Path('/sys/kernel/tracing/instances/k143-console-ab')
parameter=Path('/sys/module/printk/parameters/ignore_loglevel')
boot_path=Path('/proc/sys/kernel/random/boot_id')
boot=Path('/var/lib/samurai/k143-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid()==0 and os.uname().version.startswith('#143 ')
assert boot_path.read_bytes()==boot and not out.exists() and not trace.exists()
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text()
assert int(Path('/proc/sys/kernel/tainted').read_text())==0
paths=[p/'tx_journal' for p in Path('/sys/bus/platform/drivers/qcom_eud_com').iterdir() if (p/'tx_journal').is_file()]
assert len(paths)==1
threads=[int(p.name) for p in Path('/proc').iterdir() if p.name.isdigit() and (p/'comm').is_file() and (p/'comm').read_text().strip()=='pr/eud0']
assert len(threads)==1, 'Exactly one real EUD printer thread required'
printer=threads[0]
original_printer_affinity=os.sched_getaffinity(printer)
original_affinity=os.sched_getaffinity(0)
original_ignore=parameter.read_text().strip()
original_printk=Path('/proc/sys/kernel/printk').read_text()
assert original_ignore=='Y' and int(original_printk.split()[0])==1
assert 0 in original_affinity and 0 in original_printer_affinity
out.mkdir(mode=0o700);out.joinpath('boot-id-private.txt').write_bytes(boot)
def journal():
    data=paths[0].read_bytes()
    magic,version,size,count,record_size,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',data)
    assert magic==b'EUDTXJ48' and version==1 and size==len(data) and record_size==6 and reserved==0
    assert size==48+count*6 and last-first+1==count
    check=bytearray(data);struct.pack_into('<I',check,40,0);assert zlib.crc32(check)==crc
    issued=b''
    for i in range(count):
        length,source,content=struct.unpack_from('<BB4s',data,48+i*6)
        assert 1<=length<=4 and source in [1,2]
        if source==2:issued+=content[:length]
    return data,issued
def dmesg():return subprocess.check_output(['dmesg'],text=True)
def counts(text):return {name:text.count(pattern) for name,pattern in [('dpu','frame done timeout'),('dsi','dsi_err_worker'),('gpu','gpu fault:'),('warn','WARNING:'),('dma','unable to prepare channel')]}
before=dmesg();out.joinpath('dmesg-before-private.txt').write_text(before)
samples=[];error=None;trace.mkdir()
try:
    trace.joinpath('tracing_on').write_text('0');trace.joinpath('buffer_size_kb').write_text('4096');trace.joinpath('trace_clock').write_text('mono')
    for event in ['irq_handler_entry','irq_handler_exit','cpu_idle','sched_switch']:
        matches=list(trace.joinpath('events').glob('*/'+event+'/enable'));assert len(matches)==1;matches[0].write_text('1')
    os.sched_setaffinity(0,{0});os.sched_setaffinity(printer,{0})
    assert Path('/proc').joinpath(str(printer),'comm').read_text().strip()=='pr/eud0'
    trace.joinpath('tracing_on').write_text('1')
    for label,ignore in [('A','Y'),('B','N')]:
        assert boot_path.read_bytes()==boot;parameter.write_text(ignore+'\n')
        payload='<6>K143 console latency '+label+' '+('x'*50)+'\n'
        trace.joinpath('trace_marker').write_text('K143_CONSOLE_'+label+'_BEGIN\n')
        start=time.monotonic_ns()
        with Path('/dev/kmsg').open('w') as f:f.write(payload)
        elapsed=(time.monotonic_ns()-start)/1e6
        trace.joinpath('trace_marker').write_text('K143_CONSOLE_'+label+'_CALL_RETURN\n')
        if label=='A':
            deadline=time.monotonic()+30
            while True:
                raw,issued=journal()
                if ('K143 console latency A '+('x'*50)).encode() in issued:break
                assert time.monotonic()<deadline, 'Wait for complete async output before changing filter'
                time.sleep(0.005)
            trace.joinpath('trace_marker').write_text('K143_CONSOLE_A_TX_ISSUED\n')
            out.joinpath('a-issued-journal-private.bin').write_bytes(raw)
        else:time.sleep(0.25)
        samples.append(dict(label=label,ignore_loglevel=ignore,syscall_elapsed_ms=round(elapsed,6),payload_bytes=len(payload.encode())))
    raw,issued=journal();out.joinpath('final-journal-private.bin').write_bytes(raw)
    assert b'K143 console latency B ' not in issued
    trace.joinpath('trace_marker').write_text('K143_CONSOLE_CAPTURE_END\n')
except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
finally:
    parameter.write_text(original_ignore+'\n');os.sched_setaffinity(0,original_affinity);os.sched_setaffinity(printer,original_printer_affinity)
    trace.joinpath('tracing_on').write_text('0');out.joinpath('trace-private.txt').write_text(trace.joinpath('trace').read_text())
    out.joinpath('trace-stats-private.json').write_text(json.dumps({p.parent.name:p.read_text() for p in trace.joinpath('per_cpu').glob('cpu*/stats')},indent=2)+'\n')
    trace.joinpath('events/enable').write_text('0');trace.rmdir()
after=dmesg();out.joinpath('dmesg-after-private.txt').write_text(after)
report=dict(stage=143,kernel_build=143,same_boot=boot_path.read_bytes()==boot,error=error,tests=samples,
    actual_printer_thread_verified=True,printer_and_emitter_fixed_cpu0_during_probe=True,
    printer_affinity_restored=os.sched_getaffinity(printer)==original_printer_affinity,
    affinity_restored=os.sched_getaffinity(0)==original_affinity,
    original_ignore_loglevel_restored=parameter.read_text().strip()==original_ignore,
    printk_level_unchanged=Path('/proc/sys/kernel/printk').read_text()==original_printk,
    both_info_messages_retained_in_dmesg=all(after.count('K143 console latency '+label+' '+('x'*50))==1 for label in ['A','B']),
    counts_before=counts(before),counts_after=counts(after),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    async_A_frame_issue_wait_completed=error is None,own_trace_removed=not trace.exists(),
    host_delivery_ack_not_proven=True,screen_already_quiesced=True,no_gpu_workload_requested=True,
    display_fix_accepted=False,gpu_charging_acceptance_pending=True,goal_complete=False)
out.joinpath('ab-validation.json').write_text(json.dumps(report,indent=2)+'\n')
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar','-C',str(out),'-czf','/tmp/k143-threaded-console-latency-private.tar.gz','.'],check=True,timeout=20)
print(json.dumps(report,indent=2))
