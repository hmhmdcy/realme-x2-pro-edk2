from pathlib import Path
import hashlib,importlib.util,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('decode368',HERE.parent/'kernel368/decode-start-dump.py');decode=importlib.util.module_from_spec(spec);spec.loader.exec_module(decode)
raw=(P/'collected-r1/a5-devcd1-private.bin').read_bytes();d=decode.decode(raw)
logs=(P/'recovered-console-ramoops-0-private').read_text(errors='replace')
lines=[l for l in logs.splitlines() if any(w in l for w in ['A5 CPU release','A5 HFI response=','A5 stopped, block reset asserted'])]
assert len(lines)==3 and 'response=3' in lines[1] and 'expired=0' in lines[1]
times=[float(re.search(r'\[\s*(\d+\.\d+)\]',l)[1]) for l in lines]
report=dict(stage=369,run='r1',firmware_handshake_passed=False,original_transaction_normal_terminal=False,
    raw_standard_devcoredump_recovered=True,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),format_version=d['version'],
    init_response=d['init_response'],firmware_version_register=d['firmware_version'],queue_indices=d['queue_indices'],
    interrupts=d['interrupts'],watchdogs=d['watchdogs'],protocol_errors=d['protocol_errors'],
    sfr_text_recovered=bool(d['sfr']),sfr_text_bytes=len(d['sfr'].encode()),
    fatal_response_latency_ms=round((times[1]-times[0])*1000,3),deadline_expired=False,
    block_reset_asserted_logged=True,new_boot_after_attempt=True,collector_acknowledgement_not_observed=True,
    raw_data_durably_recovered_but_collector_did_not_finish=True,reset_cause_not_proven=True,
    bounded_kernel_evidence=lines,passed=False)
(HERE/'boot-runtime-r1-validation.json').write_text(json.dumps(report,indent=2)+'\n');(HERE/'boot-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
