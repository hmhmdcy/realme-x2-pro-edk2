"""Summarize stock initialization probes and matching successful sends.

No server strings, coordinates, satellite IDs, complete wire payloads or
process identities are exported. This observes a HAL restart, not modem boot
or the physical RF bus. Other processes and unverified TIDs are excluded.
"""
from pathlib import Path
import collections
import importlib.util
import json
import re
import struct

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel254')
spec=importlib.util.spec_from_file_location('u',ROOT/'kernel254/decode-sendto-uprobe.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
header=Path('/mnt/e/edk2-samurai-out/kernel221/loc-upstream/location_service_v02.h').read_text()
names={int(v,16):n for n,v in re.findall(r'#define\s+(QMI_LOC_\w+_REQ_V02)\s+0x([0-9A-Fa-f]+)\b',header)}


def capture(directory, trace, hal_trace, tasks, pidfile):
    events=u.decode(directory/trace)
    packets,parsing=u.wire.parse_trace(directory/hal_trace)
    tids={int(x) for p in tasks for x in p.read_text().split()}
    tids.add(int((directory/pidfile).read_text()))
    tids.update(p['tid'] for p in packets)
    verified=[e for e in events if e['tid'] in tids]
    selected=[e for e in verified if e['packet'] and e['packet']['flags']==0]
    request_counts=collections.Counter(e['packet']['message_id'] for e in selected)
    stats=(directory/trace.replace('.trace','-stats.txt')).read_text()
    overruns=[int(x) for x in re.findall(r'^overrun: (\d+)',stats,re.M)]
    drops=[int(x) for x in re.findall(r'^dropped events: (\d+)',stats,re.M)]
    assert len(overruns)==len(drops)==8
    sequences=[]
    protocol_names={16:'supl_security',17:'vx_version',18:'supl_version_enum',19:'lpp_config',
                    20:'assisted_glonass_mask',21:'supl_hash',24:'wifi_scan_inject_timeout',
                    25:'lppe_up_mask',26:'lppe_cp_mask'}
    protocols=[]
    for event in selected:
        p=event['packet'];ident=p['message_id']
        sequences.append(dict(message_id=hex(ident),name=names.get(ident),
                              complete_bytes=event['size'],send_success=event.get('result')==event['size'],
                              tlv_lengths={tag:len(bytes.fromhex(v)) for tag,v in p['tlvs'].items()}))
        if ident==0x54:
            values={protocol_names[int(k)]:int.from_bytes(bytes.fromhex(v),'little')
                    for k,v in p['tlvs'].items() if int(k) in protocol_names}
            protocols.append(values)
    modes={hex(ident):[int.from_bytes(bytes.fromhex(e['packet']['tlvs']['1']),'little') for e in selected
                     if e['packet']['message_id']==ident and '1' in e['packet']['tlvs']]
           for ident in [0x3a,0xca,0xcb,0x4a]}
    strace_sends=[p for p in packets if p['direction']=='send']
    matches=[sum(e['tid']==p['tid'] and e['size']==len(bytes.fromhex(p['wire_hex'])) and
                 p['wire_hex'].startswith(e['prefix_hex']) and e.get('result')==e['size']
                 for e in verified) for p in strace_sends]
    register_fds={e['fd'] for e in selected if e['packet']['message_id']==0x21}
    if not register_fds:
        raise ValueError('No verified probe register-events request; refuse socket guess')
    if any(p['direction']=='send' and p['message_id']==0x21 for p in packets):
        quality=u.wire.summarize(packets,parsing)
    else:
        known=register_fds & {p['fd'] for p in packets}
        for fd in known:
            peers={(e['peer_node'],e['peer_port']) for e in verified if e['fd']==fd}
            if len(peers)!=1:
                raise ValueError('FD peer changed; cannot inherit LOC identity')
        quality=u.wire.summarize(packets,parsing,explicit_fds=known) if known else None
    return dict(verified_qmi_requests=len(selected),
                successful_qmi_send_returns=sum(e.get('result')==e['size'] for e in selected),
                truncated_entries=sum(not e['complete_snapshot'] for e in verified),
                request_counts={hex(k):v for k,v in sorted(request_counts.items())},
                protocol_config_requests=protocols,first_tlv_values_for_named_controls=modes,
                sequence=sequences,
                trace_overruns_per_cpu=overruns,trace_drops_per_cpu=drops,
                strace_successful_sends=len(strace_sends),
                unique_probe_matches_to_successful_strace_sends=matches,
                all_observed_strace_sends_matched_once=all(m==1 for m in matches) if matches else None,
                socket_identified_for_late_strace=quality is not None,
                explicit_physical_rf_gain_setter_identified=False,
                absence_of_identified_setter_does_not_prove_no_modem_internal_rf_initialization=True,
                quality=quality),selected


def main():
    long,selected=capture(PRIVATE/'init-export','power-init.trace','hal-after-init.trace',
        [PRIVATE/'hal-after-task-list-private.txt'],'hal-pid-after-private.txt')
    short,selected_short=capture(PRIVATE/'short-export','short-init.trace','hal-short.trace',
        [PRIVATE/'short-export/hal-short-tasks-before-private.txt',PRIVATE/'short-export/hal-short-tasks-after-private.txt'],
        'hal-pid-after-short-private.txt')
    assert not any(short['trace_overruns_per_cpu']+short['trace_drops_per_cpu'])
    assert short['all_observed_strace_sends_matched_once'] is not False
    assert short['verified_qmi_requests']==short['successful_qmi_send_returns']
    logs=json.loads((PRIVATE/'diag-init-enable-decoded/logs-private.json').read_text())
    prx=[bytes.fromhex(r['payload_hex'])[16:] for r in logs if r['code']==0x147e]
    assert all(len(b)==722 and b[0]==5 for b in prx)
    gain=dict(collections.Counter(struct.unpack_from('<i',b,76)[0] for b in prx))
    result=dict(long_capture=long,short_capture=short,
        prx_offset76_candidate_counts=gain,prx_reports=len(prx),
        long_capture_has_overrun_and_is_not_complete=True,
        short_capture_no_overrun_but_limited_to_successful_sendto_and_verified_live_hal_tids=True,
        success_at_socket_does_not_prove_async_command_completion=True,
        os_boot_unchanged_and_no_modem_restart_requested=True,no_rf_nv_calibration_register_writes=True)
    (PRIVATE/'init-short-uprobe-events-private.json').write_text(json.dumps(selected_short))
    (ROOT/'kernel254/initialization-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(long_requests=long['verified_qmi_requests'],short_requests=short['verified_qmi_requests'],
        short_return_success=short['successful_qmi_send_returns'],short_overrun=short['trace_overruns_per_cpu'],
        short_ids=short['request_counts'],protocols=short['protocol_config_requests'],controls=short['first_tlv_values_for_named_controls'],
        pga_candidate_counts=gain,short_pga=(short['quality'] or {}).get('pqwm1'),
        short_strace_match=short['all_observed_strace_sends_matched_once']),indent=2))


if __name__=='__main__': main()
