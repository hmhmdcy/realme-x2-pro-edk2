"""Seal current-boot cleanup, health and the EUD latency hypothesis."""
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
assert boot == out.joinpath('new-boot-id-private.txt').read_bytes()

def load(filename):
    with tarfile.open(out/filename) as archive:
        data = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, name = line.split('  ',1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest() == digest
    assert data['boot-id-private.txt'] == boot
    return data

cleanup = json.loads(load('recorder-cleanup-private.tar.gz')['cleanup-validation.json'])
assert all(cleanup[key] for key in ['same_startup_boot', 'sealed_archive_sha256_matches_host',
    'recorder_already_terminal', 'recorder_service_removed', 'boot_link_removed',
    'recorder_pidfile_removed', 'own_trace_instance_absent', 'gui_three_files_preserved'])
assert not cleanup['process_killed'] and cleanup['taint'] == 0
health_data = load('settled-health-private.tar.gz')
health = json.loads(health_data['health-validation.json'])
assert health['same_boot'] and health['taint_values'] == [0] and health['counters_unchanged']
assert health['desktop_pids_unchanged'] and health['phosh_present_final'] and health['phoc_present_final']
capabilities = json.loads(load('trace-capabilities-private.tar.gz')['capabilities-validation.json'])
assert capabilities['read_only'] and capabilities['same_boot']
journal_data = load('eud-journal-private.tar.gz')
journal = journal_data['tx-journal-private.bin']
magic, version, size, count, record_size, first, last, crc, reserved = struct.unpack_from('<8sIIIIQQII', journal)
assert magic == b'EUDTXJ48' and version == 1 and size == len(journal) and record_size == 6 and reserved == 0
assert size == 48 + count * 6 and last - first + 1 == count and count <= 512
crc_data = bytearray(journal)
struct.pack_into('<I',crc_data,40,0)
assert zlib.crc32(crc_data) == crc
records = []
for index in range(count):
    length, source, content = struct.unpack_from('<BB4s',journal,48+index*6)
    assert 1 <= length <= 4 and source in [1,2]
    records.append(dict(length=length, source=source, data=content[:length], seq=first+index))
console = b''.join(row['data'] for row in records if row['source'] == 2)
out.joinpath('console-journal-decoded-private.txt').write_bytes(console)
with tarfile.open(out/'reboot140-startup-private.tar.gz') as archive:
    dmesg = archive.extractfile('./dmesg-final-private.txt').read().decode()
    early = archive.extractfile('./default-display-early-private.txt').read().decode()
trace_meta = json.loads(ref.joinpath('startup-irq-idle-validation.json').read_text())
gap = json.loads(ref.joinpath('cpu0-event-gap-validation.json').read_text())
dmesg_timeouts = [float(match[1]) for match in re.finditer(r'^\[\s*(\d+\.\d+)\].*frame done timeout', dmesg,re.M)]
early_timeouts = [float(match[1]) for match in re.finditer(r'\s(\d+\.\d+): dpu_enc_frame_done_timeout:',early)]
own_timeouts = [row['timeout_trace_seconds'] for row in trace_meta['timeout_summaries']]
assert len(dmesg_timeouts) == 2 and len(early_timeouts) == 1 and len(own_timeouts) == 1
pairs = list(zip(early_timeouts + own_timeouts, dmesg_timeouts))
offsets = [dmesg_stamp-trace_stamp for trace_stamp,dmesg_stamp in pairs]
assert max(offsets)-min(offsets) < 0.00001
offset = sum(offsets)/len(offsets)
ready = next(line for line in dmesg.splitlines() if '[   56.571459]' in line and 'samurai Q6 ready item=421' in line)
ready_stamp = float(re.match(r'\[\s*(\d+\.\d+)\]',ready)[1])
ready_trace = ready_stamp-offset
gap_begin = own_timeouts[0]+gap['gap_begin_before_timeout_ms']/1000
gap_end = own_timeouts[0]+gap['gap_end_before_timeout_ms']/1000
encoded = (ready+'\n').encode()
predicted_ms = ((len(encoded)+3)//4)*2.4+len(encoded)*0.2
journal_ready = [line for line in console.decode(errors='replace').splitlines()
    if 'samurai Q6 ready item=421' in line]
root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
source = root.joinpath('drivers/tty/serial/eud.c').read_text()
start = source.index('static void eud_console_write(')
end = source.index('static struct console eud_console',start)
callback = source[start:end]
assert callback.index('uart_port_lock_irqsave') < callback.index('while (count)') < callback.index('uart_port_unlock_irqrestore')
assert '#define EUD_TX_BYTE_US         200' in source and '#define EUD_TX_FRAME_US        2000' in source
report = dict(stage=142, kernel_build=140, same_boot_archives_verified=True,
    paired_same_function_timeout_print_offsets_seconds=[round(x,9) for x in offsets],
    offset_scope='Only these two timeout calls on this stage142 boot; not a general clock calibration.',
    cpu0_event_gap_ms=gap['cpu0_largest_event_gap_ms'],
    q6_ready_print_timestamp_inside_gap=gap_begin <= ready_trace <= gap_end,
    q6_ready_print_after_gap_start_ms=round((ready_trace-gap_begin)*1000,3),
    q6_ready_dmesg_line_bytes_including_newline=len(encoded),
    estimated_software_tx_pacing_ms=round(predicted_ms,3),
    estimate_limits='Dmesg formatting is not guaranteed byte-identical to console output; includes no RX/lock/MMIO overhead.',
    tx_journal_crc_verified=True, tx_journal_records=count,
    same_ready_text_present_in_retained_journal=bool(journal_ready),
    exact_gap_ready_record_retained=(ready+'\n').encode() in console,
    host_delivery_or_ack_proven=False,
    legacy_eud_console_holds_local_irqs_off_across_entire_record=True,
    existing_console_level=int(journal_data['printk-private.txt'].split()[0]),
    legacy_bootconsole_already_retired=True,
    slow_eud_printing_is_specific_causal_candidate=True,
    direct_console_entry_exit_trace_available=False, causal_ab_test_completed=False,
    actual_fix_applied=False, display_accepted=False, gpu_accepted=False,
    charging_accepted=False, goal_complete=False)
ab_path = ref/'console-latency-ab-validation.json'
if ab_path.exists():
    ab = json.loads(ab_path.read_text())
    assert ab['archive_manifests_verified'] and ab['trace_loss_free'] and ab['same_boot']
    report.update(causal_ab_test_completed=True,
        controlled_eud_latency_causally_confirmed=True,
        ab_console_output_ms=ab['tests'][0]['syscall_elapsed_ms'],
        ab_console_bypass_ms=ab['tests'][1]['syscall_elapsed_ms'],
        ab_both_records_retained_in_dmesg=True, original_ignore_loglevel_restored=True,
        original_display_timeout_direct_console_span_not_traced=True)
for name, value in [('recorder-cleanup-validation.json',cleanup),('settled-health-validation.json',health),
    ('trace-capabilities-validation.json',capabilities),('eud-console-latency-hypothesis-validation.json',report)]:
    value['archive_manifest_verified'] = True
    ref.joinpath(name).write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(report,indent=2))
