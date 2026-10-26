from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';old=root/'reference/kernel105'
def base(n):return (old/n).read_text().replace('kernel105','kernel106').replace('k105','k106').replace('#104 SMP PREEMPT','#105 SMP PREEMPT').replace('stage=105','stage=106').replace('kernel_build=104','kernel_build=105')
s=base('verify-tests.py')
s=s.replace("'core-followup'","'first-radio-trace'").replace(";follow=allfiles['first-radio-trace']",";first=allfiles['first-radio-trace']")
s=s.replace("state.count('running')==2","state.count('running')==1 and state.count('crashed')==1")
a=s.index("assert core['api-after-exit.txt']");b=s.index("parts={n:h",a)
s=s[:a]+'''assert core['api-after.txt']==api and core['api-after-exit.txt']==b'0\\n' and core['api-after-error.txt']==b''
assert b'APR: service is not registered' not in core['dmesg-after.txt']
assert core['dmesg-after.txt'].count(b'samurai APR service registered id=3 domain=4')==2
diag={};exec((root/'reference/kernel106/analyse-trace.py').read_text().split("if __name__=='__main__':",1)[0],diag)
for name in ['first-radio-trace','core-rebind-once','radio-recovery-first']:
    trace=diag['read_archive'](name)
    for n,b in trace.items():
        if n.endswith('-stats.txt'):
            assert all(int(v)==0 for v in re.findall(rb'^(?:overrun|commit overrun|dropped events):\\s*(\\d+)',b,re.M))
initial=first['trace.txt'].decode();recovered=rec['trace.txt'].decode()
hello_time=float(re.search(r'(\\d+\\.\\d+): qrtr_endpoint_tx: node=0 wire_node=0 type=2 .*result=0',initial)[1])
blocked_time=float(re.search(r'(\\d+\\.\\d+): qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=-11',initial)[1])
assert blocked_time < hello_time and 'samurai_qrtr_rx_drop:' not in initial
assert len(re.findall(r'qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=0',initial))==0
assert len(re.findall(r'qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=0',recovered))==3
assert 'service=kernel/elf_loader offset=0 total=1 returned=1 result=0' in recovered
assert first['server-pids.txt']==rec['server-pids.txt']
assert 'phase=2 command=0x1292c token=0x1 opcode=0x0 bytes=0 status=0 result=0' in core['trace.txt'].decode()
assert 'result=-110' not in core['trace.txt'].decode()
''' + s[b:]
s=s.replace('initial_rebind_query_timeout_preserved=True,bounded_followup_with_eud_reader_pass=True','first_rebind_query_within_100ms_pass=True,eud_reader_active_during_rebind=False,first_hello_service_announcement_race_observed=True,trace_loss_count=0,original_services_reused=True')
assert 'follow[' not in s
assert not (ref/'verify-tests.py').exists();(ref/'verify-tests.py').write_text(s)
s=base('collect-checkpoint.sh').replace('core-followup','first-radio-trace');assert not (ref/'collect-checkpoint.sh').exists();(ref/'collect-checkpoint.sh').write_text(s)
s=base('verify-checkpoint.py')
s=s.replace('rebind_initial_timeout_preserved=True','first_rebind_query_within_100ms_pass=True,eud_reader_active_during_rebind=False,first_hello_service_announcement_race_observed=True,trace_loss_count=0')
assert not (ref/'verify-checkpoint.py').exists();(ref/'verify-checkpoint.py').write_text(s)
print('EIGHT_ORIGINAL_ARCHIVES_AND_TRACE_ORDER_VERIFIERS_PREPARED')
