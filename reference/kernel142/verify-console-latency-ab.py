from pathlib import Path
import hashlib
import json
import re
import struct
import tarfile
import zlib

out = Path('/mnt/e/edk2-samurai-out/kernel142')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel142')
boot = out.joinpath('embedded-boot-id-private.txt').read_bytes()

def load(name):
    with tarfile.open(out/name) as archive:
        data = {m.name.removeprefix('./'):archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, filename = line.split('  ',1)
        assert hashlib.sha256(data[filename.removeprefix('./')]).hexdigest() == digest
    assert data['boot-id-private.txt'] == boot
    return data

data = load('console-latency-ab-private.tar.gz')
after = load('console-latency-after-ab-private.tar.gz')
report = json.loads(data['ab-validation.json'])
assert report['error'] is None and report['same_boot'] and report['taint'] == 0
assert all(report[key] for key in ['original_ignore_loglevel_restored','printk_level_unchanged',
    'affinity_restored','both_info_messages_retained_in_dmesg','own_trace_removed'])
assert report['counts_before'] == report['counts_after'] and after['ignore-loglevel.txt'].strip() == b'Y'
stats = json.loads(data['trace-stats-private.json'])
loss = {cpu:{key:int(re.search(r'^'+key+r': (\d+)$',value,re.M)[1])
    for key in ['overrun','commit overrun','dropped events']} for cpu,value in stats.items()}
assert len(loss) == 8 and not any(number for row in loss.values() for number in row.values())
pattern = re.compile(r'\[(\d+)\].*?\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$')
events = []
for line in data['trace-private.txt'].decode().splitlines():
    match = pattern.search(line)
    if match:
        events.append(dict(cpu=int(match[1]),seconds=float(match[2]),name=match[3],body=match[4]))
events.sort(key=lambda event:event['seconds'])
for sample in report['tests']:
    label = sample['label']
    begin = next(event for event in events if event['name']=='tracing_mark_write' and event['body']=='K142_CONSOLE_'+label+'_BEGIN')
    end = next(event for event in events if event['name']=='tracing_mark_write' and event['body']=='K142_CONSOLE_'+label+'_END')
    assert begin['cpu'] == end['cpu'] == 0
    items = [begin]+[e for e in events if begin['seconds'] < e['seconds'] < end['seconds'] and e['cpu']==0]+[end]
    sample['trace_marker_interval_ms'] = round((end['seconds']-begin['seconds'])*1000,6)
    sample['cpu0_largest_event_gap_ms'] = round(max(right['seconds']-left['seconds'] for left,right in zip(items,items[1:]))*1000,6)
    sample['cpu0_irq_entries_during_call'] = sum(e['name']=='irq_handler_entry' for e in items)
    sample['cpu0_sched_switch_during_call'] = sum(e['name']=='sched_switch' for e in items)

journal = after['tx-journal-private.bin']
magic,version,size,count,record_size,first,last,crc,reserved = struct.unpack_from('<8sIIIIQQII',journal)
assert magic==b'EUDTXJ48' and version==1 and size==len(journal) and record_size==6 and reserved==0
assert size==48+count*6 and last-first+1==count
crc_data = bytearray(journal)
struct.pack_into('<I',crc_data,40,0)
assert zlib.crc32(crc_data)==crc
console = b''
for index in range(count):
    length,source,content = struct.unpack_from('<BB4s',journal,48+index*6)
    assert 1<=length<=4 and source in [1,2]
    if source==2:
        console+=content[:length]
assert ('K142 console latency A '+('x'*50)).encode() in console
assert b'K142 console latency B ' not in console
out.joinpath('post-ab-console-journal-private.txt').write_bytes(console)
assert report['tests'][0]['syscall_elapsed_ms'] > 50 and report['tests'][1]['syscall_elapsed_ms'] < 5
report.update(archive_manifests_verified=True, trace_loss_free=True, trace_loss=loss,
    post_ab_journal_crc_verified=True, A_bytes_issued_as_console_frames=True,
    B_info_retained_without_console_frames=True, host_delivery_ack_not_proven=True,
    long_synchronous_eud_console_latency_confirmed=True,
    original_boot_timeout_console_entry_exit_not_directly_traced=True,
    display_root_cause_fully_proven=False, functional_driver_fix_applied=False,
    all_three_acceptance_pending=True, goal_complete=False)
ref.joinpath('console-latency-ab-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
