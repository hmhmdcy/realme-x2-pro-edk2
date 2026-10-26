"""Parse private RMTFS numeric results and bounded TFTP metadata; emit aggregates."""
from collections import Counter
import re

FIRMWARE='/readonly/firmware/image/modem_pr/mcfg/configs/mcfg_sw/mdtime.txt'
SHARED='/shared/configs/mcfg_sw/mdtime.txt'
OTA='/readwrite/ota_firewall/ruleset'
WORK='/readwrite/mcfg.tmp'
RRQ=re.compile(r'^read request for (.+) \(mode: ([^,]+), rsize: (\d+), seek: (\d+)\) from (\d+):(\d+)$')
WRQ=re.compile(r'^write request for (.+?) \(.*')
DATA=re.compile(r'^Sending (\d+) bytes of DATA to (\d+):(\d+)$')
OPENED=re.compile(r'^(.+) opened for reading from (\d+):(\d+)$')
OPEN_WRITE=re.compile(r'^(.+) opened for writing from (\d+):(\d+)$')
END=re.compile(r'^Reader received end of transfer from (\d+):(\d+)$')
REJECT=re.compile(r'^unable to open (.+) \((\d+)\), reject$')
REPLY=re.compile(r'^\[RMTFS\].*=>.*\((-?\d+):(-?\d+)\)$')

def audit(tftp,rmtfs,firmware_bytes):
    replies=Counter();unknown_reply=0
    for line in rmtfs.splitlines():
        if '[RMTFS]' not in line or '=>' not in line:continue
        m=REPLY.fullmatch(line)
        if m:replies[(int(m[1]),int(m[2]))]+=1
        else:unknown_reply+=1
    transactions=[];active={};last=None;rejects=Counter();unmatched_rejects=0
    write_attempts=Counter();write_opens=Counter();pending_write=False
    invalid_data_lengths=0;unmatched_data=0;rrq_count=0;shared_wrq_count=0
    for line in tftp.splitlines():
        m=RRQ.fullmatch(line)
        if m:
            rrq_count+=1;pending_write=False
            last=dict(path=m[1],rsize=int(m[3]),seek=int(m[4]),opened_for_reading=False,peer_end_of_transfer=False,data_packet_bytes=[],local_reject_errno=None)
            active[(m[5],m[6])]=last
            if m[1] in [FIRMWARE,SHARED,OTA,WORK]:transactions.append(last)
            continue
        m=OPENED.fullmatch(line)
        if m:
            target=active.get((m[2],m[3]))
            if target and target['path']==m[1]:target['opened_for_reading']=True
            continue
        m=END.fullmatch(line)
        if m:
            target=active.get((m[1],m[2]))
            if target:target['peer_end_of_transfer']=True
            continue
        m=WRQ.match(line)
        if m:
            if m[1]==SHARED:shared_wrq_count+=1
            continue
        if line.startswith('WRQ options:'):
            pending_write=True
            continue
        m=OPEN_WRITE.fullmatch(line)
        if m:
            write_attempts[m[1]]+=1;write_opens[m[1]]+=1;pending_write=False
            continue
        m=REJECT.fullmatch(line)
        if m:
            rejects[int(m[2])]+=1
            if pending_write:
                write_attempts[m[1]]+=1;pending_write=False
            elif last and last['path']==m[1]:last['local_reject_errno']=int(m[2])
            else:unmatched_rejects+=1
            continue
        m=DATA.fullmatch(line)
        if m:
            length=int(m[1])
            if length<4:invalid_data_lengths+=1;continue
            target=active.get((m[2],m[3]))
            if target:target['data_packet_bytes'].append(length)
            else:unmatched_data+=1
    known={}
    for path,label in [(FIRMWARE,'firmware_mdtime'),(SHARED,'shared_mdtime'),(OTA,'ota_firewall_ruleset'),(WORK,'mcfg_workfile')]:
        cases=[t for t in transactions if t['path']==path]
        known[label]=dict(requests=len(cases),write_attempts_with_known_path=write_attempts[path],successful_write_opens=write_opens[path],cases=[{k:v for k,v in t.items() if k!='path'} for t in cases])
    results=[dict(result=r,error=e,count=n) for (r,e),n in sorted(replies.items())]
    errors=sum(n for (r,e),n in replies.items() if r!=0 or e!=0)
    return dict(tftp_lines=len(tftp.splitlines()),rmtfs_lines=len(rmtfs.splitlines()),
        rmtfs_numeric_replies=sum(replies.values()),rmtfs_numeric_failure_replies=errors,
        rmtfs_numeric_results=results,rmtfs_unparsed_reply_lines=unknown_reply,
        rmtfs_ready_markers=rmtfs.count('RMTFS RAM COW ready'),
        rmtfs_cow_sources_loaded=sum(l.startswith('[COW] loaded ') for l in rmtfs.splitlines()),
        tftp_rrq_requests=rrq_count,tftp_local_reject_errnos=dict(sorted(rejects.items())),
        tftp_unmatched_rejects=unmatched_rejects,tftp_unmatched_data_packets=unmatched_data,
        tftp_invalid_data_packet_lengths=invalid_data_lengths,shared_exact_wrq_requests=max(shared_wrq_count,write_attempts[SHARED]),
        known_mdtime_requests=known,firmware_mdtime_bytes=firmware_bytes,
        tftp_ack_completion_not_observable=True,wire_error_packets_not_captured=True,
        paths_peers_payloads_and_fingerprints_not_emitted=True)
