"""Negative controls for the numeric-error and EOF evidence that keywords miss."""
from pathlib import Path
import importlib.util,json
ref=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('audit',ref/'audit-file-services.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
report=a.audit('', '[RMTFS] iovec 7, not forced => (1:16)\n[RMTFS] alloc 1, 4 => 0xabcd (0:0)\n[RMTFS] bad => malformed\n',12)
assert report['rmtfs_numeric_replies']==2 and report['rmtfs_numeric_failure_replies']==1 and report['rmtfs_unparsed_reply_lines']==1
empty=a.audit('','',12);assert empty['rmtfs_numeric_replies']==0 and empty['known_mdtime_requests']['firmware_mdtime']['requests']==0
fixture=(f'read request for {a.FIRMWARE} (mode: octet, rsize: 8, seek: 12) from 7:9\nSending 4 bytes of DATA to 7:9\n'+f'read request for {a.SHARED} (mode: octet, rsize: 0, seek: 0) from 8:9\nunable to open {a.SHARED} (13), reject\n')
r=a.audit(fixture,'',12)
assert r['known_mdtime_requests']['firmware_mdtime']['cases'][0]['data_packet_bytes']==[4]
assert r['known_mdtime_requests']['shared_mdtime']['cases'][0]['local_reject_errno']==13
assert r['wire_error_packets_not_captured'] and r['tftp_ack_completion_not_observable']
assert '7:9' not in json.dumps(r) and '8:9' not in json.dumps(r)
bad=a.audit(f'read request for {a.FIRMWARE} (mode: octet, rsize: 8, seek: 12) from 7:9\nSending 3 bytes of DATA to 7:9\n','',12)
assert bad['tftp_invalid_data_packet_lengths']==1
result=dict(stage=231,numeric_failure_without_error_keyword_detected=True,unparsed_reply_not_silently_success=True,empty_log_not_readiness_proof=True,header_only_data_retained_as_zero_payload=True,local_errno_not_invented_wire_error=True,invalid_data_length_detected=True,private_peer_tokens_not_emitted=True)
(ref/'parser-negative-controls-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
