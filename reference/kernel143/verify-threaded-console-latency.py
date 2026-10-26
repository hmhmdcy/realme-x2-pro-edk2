from pathlib import Path
import hashlib
import json
import re
import struct
import tarfile
import zlib

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
with tarfile.open(out/'threaded-console-latency-private.tar.gz') as archive:
    data={m.name.removeprefix('./'):archive.extractfile(m).read() for m in archive if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
assert data['boot-id-private.txt']==out.joinpath('rejected-boot-id-private.txt').read_bytes()
report=json.loads(data['ab-validation.json']);assert report['error'] is None and report['taint']==0
assert report['counts_before']==report['counts_after']
assert all(report[key] for key in ['same_boot','actual_printer_thread_verified','printer_and_emitter_fixed_cpu0_during_probe',
    'printer_affinity_restored','affinity_restored','original_ignore_loglevel_restored','printk_level_unchanged',
    'both_info_messages_retained_in_dmesg','async_A_frame_issue_wait_completed','own_trace_removed'])
stats=json.loads(data['trace-stats-private.json'])
loss={cpu:{key:int(re.search(r'^'+key+r': (\d+)$',value,re.M)[1]) for key in ['overrun','commit overrun','dropped events']} for cpu,value in stats.items()}
assert len(loss)==8 and not any(n for row in loss.values() for n in row.values())
def issued(name):
    raw=data[name];magic,version,size,count,record_size,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',raw)
    assert magic==b'EUDTXJ48' and version==1 and size==len(raw)==48+6*count and record_size==6 and reserved==0
    assert last-first+1==count
    check=bytearray(raw);struct.pack_into('<I',check,40,0);assert zlib.crc32(check)==crc
    text=b''
    for i in range(count):
        length,source,content=struct.unpack_from('<BB4s',raw,48+6*i)
        assert 1<=length<=4 and source in [1,2]
        if source==2:text+=content[:length]
    return text
A=('K143 console latency A '+('x'*50)).encode()
assert A in issued('a-issued-journal-private.bin') and A in issued('final-journal-private.bin')
assert b'K143 console latency B ' not in issued('final-journal-private.bin')
pattern=re.compile(r'\[(\d+)\].*?\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$')
events=[]
for line in data['trace-private.txt'].decode().splitlines():
    match=pattern.search(line)
    if match:events.append(dict(cpu=int(match[1]),seconds=float(match[2]),name=match[3],body=match[4]))
events.sort(key=lambda event:event['seconds'])
def marker(name):return next(e for e in events if e['name']=='tracing_mark_write' and e['body']==name)
for sample in report['tests']:
    label=sample['label'];begin=marker('K143_CONSOLE_'+label+'_BEGIN');end=marker('K143_CONSOLE_'+label+'_CALL_RETURN')
    assert begin['cpu']==end['cpu']==0
    sample['cpu0_call_marker_interval_ms']=round((end['seconds']-begin['seconds'])*1000,6)
start=marker('K143_CONSOLE_A_BEGIN');end=marker('K143_CONSOLE_A_TX_ISSUED')
items=[start]+[e for e in events if e['cpu']==0 and start['seconds']<e['seconds']<end['seconds']]+[end]
max_gap=round(max(b['seconds']-a['seconds'] for a,b in zip(items,items[1:]))*1000,6)
irqs=sum(e['name']=='irq_handler_entry' for e in items)
printer_switches=sum(e['name']=='sched_switch' and 'pr/eud0' in e['body'] for e in items)
assert irqs>0 and printer_switches>0
previous=json.loads(ref.parent.joinpath('kernel142/console-latency-ab-validation.json').read_text())
assert previous['tests'][0]['payload_bytes']==report['tests'][0]['payload_bytes']==77
assert report['tests'][0]['syscall_elapsed_ms']<5 and max_gap<10
report.update(archive_manifest_verified=True,trace_loss_free=True,trace_loss=loss,
    both_journal_crc_verified=True,A_console_frames_issued=True,B_filtered_but_in_dmesg=True,
    prior140_same_payload_syscall_ms=previous['tests'][0]['syscall_elapsed_ms'],
    new143_async_issue_window_ms=round((end['seconds']-start['seconds'])*1000,6),
    cpu0_largest_event_gap_during_async_issue_ms=max_gap,cpu0_irq_entries_during_async_issue=irqs,
    actual_printer_sched_switch_events_cpu0=printer_switches,
    long_caller_stall_removed_for_this_record=True,irq_off_max_not_directly_measured=True,
    cross_boot_single_record_comparison=True,candidate_rejected_for_display_fifo_underflow=True,
    all_three_acceptance_pending=True,goal_complete=False)
ref.joinpath('threaded-console-latency-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='trace_loss'},indent=2))
