"""Refine the actual 452 tail using callback times, without asserting DMA state."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
storage=load(HERE.parent/'kernel449/storage.py','guard449');storage.mount.mounted_build()
auditor=load(HERE.parent/'kernel452/check-diagnostic.py','audit452')
p=Path('/mnt/e/edk2-samurai-out/kernel452')
hardware=json.loads((p/'diagnostic-hardware-validation.json').read_text());assert hardware['passed']
files=list((p/'runtime-collected-r1/trace-window/captures').glob('*.csv'));assert len(files)==1
summary,records=auditor.parse_trace(files[0].read_text())
assert summary['overwritten']==0
full={r['sof']:r for r in records if r['type']==7 and r['status']==0 and r['flags']&8}
assert 167 in full and 169 in full and 168 not in full
before,after=full[167],full[169]
begin=next(r for r in records if r['number']>before['number'] and r['type']==5)
result=next(r for r in records if r['number']>begin['number'] and r['type']==6)
assert result['status']==0 and result['buffer']==begin['buffer'] and result['request']==begin['request']
assert after['buffer']==result['buffer'] and after['request']==result['request']
zero=[r for r in records if before['number']<=r['number']<=begin['number']]
assert before['outstanding_full']==0 and all(r['outstanding_full']==0 for r in zero)
assert not any(r['type']==6 and r['status']==0 for r in zero)
pix166=next(r for r in records if r['type']==8 and r['sof']==166)
pix168=next(r for r in zero if r['type']==8 and r['sof']==168)
assert before['mono_ns']<pix168['mono_ns']<begin['mono_ns']<result['mono_ns']<after['mono_ns']
events=[pix166,before,pix168,begin,result,after]
report=dict(stage=457,csv_sha256=hashlib.sha256(files[0].read_bytes()).hexdigest(),source_auditor_sha256=hashlib.sha256((HERE.parent/'kernel452/check-diagnostic.py').read_bytes()).hexdigest(),actual_cached_csv_reaudited=True,missing_sof=168,all_events_retained=True,callback_events=[dict(number=r['number'],event=auditor.TYPES[r['type']],sof=r['sof'],milliseconds_from_pix166_callback=round((r['mono_ns']-pix166['mono_ns'])/1e6,3),outstanding_full=r['outstanding_full']) for r in events],zero_outstanding_until_next_qbuf_begin_ms=round((begin['mono_ns']-before['mono_ns'])/1e6,3),next_qbuf_call_ms=round((result['mono_ns']-begin['mono_ns'])/1e6,3),all_retained_callback_snapshots_zero_in_interval=True,no_new_successful_qbuf_before_next_begin=True,requeued_buffer_later_delivered_as_sof169=True,not_a_hardware_sof_or_fifo_measurement=True,hardware_ns_not_subtracted_from_mono_ns=True,physical_supply_or_dma_root_cause_proven=False,phone_accessed=False,compiled=False,passed=True)
(HERE/'gap-callback-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
