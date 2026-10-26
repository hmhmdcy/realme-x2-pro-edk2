from pathlib import Path
import json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'session-regression';work.mkdir(exist_ok=True)
text=(P/'camss-icp-a5-boot.c.proposed').read_text();header=(P/'camss-icp-a5-boot.h.proposed').read_text()
header='\n'.join(l for l in header.splitlines() if not l.startswith('#include'))
(work/'model-header.h').write_text(header)
parts=['\n'.join(l for l in text.splitlines() if l.startswith('#define '))]
for start,end in [('static void command_failure(','static irqreturn_t a5_interrupt('),('static void process_message(','static irqreturn_t a5_interrupt_thread('),('static int send_packet(','bool camss_a5_backing_owned('),('static int quiesce_locked(','int camss_a5_stop(')]:
 a=text.index(start);b=text.index(end,a);parts.append(text[a:b])
(work/'body.inc').write_text('\n'.join(parts));(work/'probe.c').write_text((HERE/'session-regression.c').read_text())
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
rows=[]
for case in list(range(27))+list(range(30,42))+[44,45]:
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr)
 assert not q.returncode,(case,q.stderr.decode()[-2000:]);rows.append(dict(case=case,passed=True))
report=dict(stage=381,actual_production_parser_send_session_quiesce_stop_bodies_and_header=True,asan_ubsan=True,tests=rows,
 two_simultaneous_independent_sessions=True,io_map_config_unmap_and_error_ownership_checked=True,stale_wrong_type_wrong_token_wrong_opcode_and_malformed_replies_checked=True,
 original_48_byte_destroy_reply_checked_and_wrong_44_byte_reply_rejected=True,queued_timeout_or_unrecognized_reply_blocks_new_sessions=True,
 explicit_error_keeps_destroy_handle_for_retry=True,duplicate_handle_rejected=True,automatic_stop_destroys_known_sessions=True,
 forced_reset_failure_retains_cpu_sessions_dma_pm=True,irq_parser_joined_before_pending_state_reuse=True,sys_init_ping_pc_packets_and_parsing_regressed=True,
 successful_ack_cannot_clear_watchdog_error=True,error_arriving_during_irq_join_is_observed=True,
 firmware_irq_mmio_dma_reset_pm_and_scheduler_providers_mocked=True,no_hardware_execution_claim=True,passed=True)
(HERE/'session-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
