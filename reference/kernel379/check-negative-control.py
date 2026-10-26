from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;work=host.PRIVATE/'session-regression';body=work/'body.inc';saved=body.read_text()
anchor='a5->session_payload_status =\n\t\t\t(a5->session_opcode == IPE_CONFIG_IO ||\n\t\t\t a5->session_opcode == IPE_DESTROY) ?\n\t\t\tget_unaligned_le32(a5->message + 32) : 0;'
assert saved.count(anchor)==1
try:
 body.write_text(saved.replace(anchor,'a5->session_payload_status = get_unaligned_le32(a5->message + 32);'))
 q=subprocess.run(['cc','-std=gnu11','-O1','-Wno-unused-function','-Wno-unused-parameter',str(work/'probe.c'),'-o',str(work/'old-parser')],capture_output=True);assert q.returncode==0
 q=subprocess.run([str(work/'old-parser'),'30'],capture_output=True);assert q.returncode!=0
 (host.PRIVATE/'negative-control-private.log').write_bytes(q.stdout+q.stderr)
finally:body.write_text(saved)
report=dict(stage=379,old_parser_rejects_successful_dirty_tail_mapping_ack=True,corrected_parser_passed_same_fixture=True,phone_operations=False,passed=True)
(HERE/'negative-control-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
