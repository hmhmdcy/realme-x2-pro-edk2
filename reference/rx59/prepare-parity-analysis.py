"""Derive the same strict analyzer with an explicit one-frame boundary gap."""
from pathlib import Path
root=Path(__file__).resolve().parent
s=(root/'analyze-first-status.py').read_text()
def change(a,b):
    global s
    assert s.count(a)==1,a
    s=s.replace(a,b)
change("SRC=ROOT/'rx58'","SRC=ROOT/'rx59'")
s=s.replace('driver-logs-first-status-01','driver-logs-parity-01').replace('first-status-owner-','parity-owner-').replace('joint-first-status','parity').replace('first-status-01.etl','parity-01.etl').replace('first-status-01.all-local-lr.xml','parity-01.all-local-lr.xml')
s=s.replace('(1,2,3)','(1,2)').replace('parity-owner-3.raw','parity-owner-2.raw')
change("prior=decode((REF/'rx57/windows-log-02.raw').read_bytes())[0]\nassert prior[-k:]==wanted[:k] and frames[:512-k]==wanted[k:]", """prior=decode((ROOT/'rx58/first-status-owner-3.raw').read_bytes())[0]
one=decode((SRC/'parity-owner-1.raw').read_bytes())[0]
two=decode((SRC/'parity-owner-2.raw').read_bytes())[0]
assert len(one)==75 and len(owners[0]['sends'])==2
gap=k+len(one)
assert prior[-k:]==wanted[:k] and one==wanted[k:gap]
assert two[:512-gap-1]==wanted[gap+1:]
assert wanted[gap][:2]==b'\\x90\\x04' and blob[48+6*gap+1]==2
missing=dict(seq=first+gap,wire_hex=wanted[gap].hex(' '),source='console',first_frame_of_second_owner=True)
assert two[0][2:]+wanted[gap][2:]!=wanted[gap][2:]+two[0][2:]
initial_perf=[x for x in [json.loads(t) for t in (SRC/'parity-owner-2.rx-audit.jsonl').read_text().splitlines()] if x['event']=='perf' and x['reason']=='manual-idle'][0]
status_bytes=initial_perf['raw_position']
assert status_bytes==330
missing['first_status_host_and_counter_bytes']=status_bytes
missing['first_status_cpu_issued_wire_bytes']=status_bytes+len(wanted[gap])
missing['first_status_driver_log_bytes']=sum(x['length'] for x in reports[2]['records'][:len(decode((SRC/'parity-owner-2.raw').read_bytes()[:status_bytes])[0])])
assert missing['first_status_driver_log_bytes']==status_bytes
missing['observed_first_line']=owners[1]['first_line']
missing['issued_first_line']=(wanted[gap][2:]+owners[1]['first_line'].encode()).decode()
assert re.fullmatch(r'\\[\\s*\\d+\\.\\d+\\] eud: tty byte=15 .*',missing['issued_first_line'])""")
change('current_direct_matches=512-k,total_direct_matches=512','first_owner_direct_matches=len(one),second_owner_direct_matches=512-gap-1,total_direct_matches=511,missing=missing')
change("initial_rx_retry_owner=2,tx_gap_reproduced=False,limits=['Initial full PnP reload differs from serial reopen.','Owners 1 and 2 closed at the unchanged 20-second audit deadline, not manual Ctrl-].','CPU issue and ETW headers do not reveal physical ACK or DATA0/1.']", "initial_rx_retry_owner=None,tx_gap_reproduced=True,limits=['Initial full PnP reload differs from ordinary serial reopen.','Both owners manually closed before deadlines.','CPU issue and ETW headers do not reveal physical ACK or DATA0/1.']")
change('==13 and sum(int','==12 and sum(int')
s=s.replace(')==134',')==134') # 9+125 =134 wire bytes; twelve nonempty OUT requests.
change('successful_in_bytes=9086','successful_in_bytes=8894')
change("print(json.dumps(dict(owners=", "print(json.dumps(dict(missing=missing,owners=")
(root/'analyze-parity.py').write_text(s)
post=(root/'capture-post-state.ps1').read_text().replace('EUD-RX58-FIRST-STATUS','EUD-RX59-PARITY').replace('Independent state after authorized RX58 joint capture','Independent state after authorized RX59 parity capture').replace('joint-first-status-post-state.json','parity-post-state.json').replace('capture-windows-first-status\\.ps1','capture-windows-(?:first-status|parity)\\.ps1')
(root/'capture-parity-post-state.ps1').write_text(post)
