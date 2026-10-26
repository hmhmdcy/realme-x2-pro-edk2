from pathlib import Path
import collections, hashlib, json, tarfile

private=Path('/mnt/e/edk2-samurai-out/kernel114')
archives=[('gnss-single-client-private.tar.gz','2967edad65369752a9240556ab65c7b83fbfcc0a1f21f7aaf24d8155f63dfe6b'),('gnss-single-client-v2-private.tar.gz','3936b601c7c21b1f8af1f1eaf9c4fab78296dbca63b795946f4a4a7ee5e6c5bf'),('gnss-single-client-v3-private.tar.gz','6c8e2e4dfa68623d8c9bde0e733b0a6bdf1a202ad2c6705f44023e229ec39298')]
states=[]
for name,digest in archives:
    path=private/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    with tarfile.open(path) as tar:
        files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
    for line in files['SHA256SUMS'].decode().splitlines():
        sha,name=line.split('  ',1)
        assert hashlib.sha256(files[name.removeprefix('./')]).hexdigest()==sha
    state=json.loads(files['state-private.json'])
    assert files['nv-check.txt'].decode().count(': OK')==6
    assert files['source-check.txt'].decode().count(': OK')==4
    states.append(state)
assert all(not s['start_ack'] for s in states[:2])
state=states[-1]
assert state['client_registered'] and state['start_ack'] and state['stop_ack'] and not state['errors']
rows=[json.loads(s) for s in files['events-private.jsonl'].decode().splitlines()]
counts=collections.Counter(row['signal'] for row in rows)
assert dict(counts)==state['events']
statuses=collections.Counter(row['values']['get_session_status'] for row in rows if row['signal']=='position-report')
assert dict(statuses)=={'<LocSessionStatus.IN_PROGRESS: 1>':55}
report=dict(three_archives_and_all_member_hashes_verified=True,
            first_two_failures_before_engine_start=['unimplemented_signal_name','wrong_recurrence_enum_name'],
            successful_trial=3,single_loc_client_registers_starts_monitors_and_stops=True,
            gi_none_on_success_handled_correctly=True,monitor_window_seconds=55,event_counts=dict(counts),
            position_report_statuses={'in_progress':55},valid_position_fix_received=False,
            gnss_real_time_indication_transport_verified=True,nmea_stream_received=True,
            engine_session_stop_acknowledged=True,nv6_source4_unchanged=True,
            desktop_location_integration=False,goal_complete=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel114/gnss-single-client-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
