#!/usr/bin/env python3
"""Summarize private native Linux LOC output; never publish positions or IDs."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,json,math,struct

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ranges(values):
    values=list(values);assert all(math.isfinite(v) for v in values)
    return dict(samples=len(values),minimum=min(values) if values else None,maximum=max(values) if values else None)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_directory',type=Path)
    parser.add_argument('--output-directory',required=True,type=Path)
    args=parser.parse_args();private=args.private_directory;out=args.output_directory
    out.mkdir(exist_ok=True,parents=True)
    receipt=json.loads((private/'export-manifest-private.json').read_text())
    for e in receipt:
        b=(private/e['name']).read_bytes()
        assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256']
    native=[json.loads(v) for v in (private/'events-private.jsonl').read_text().splitlines()]
    state=json.loads((private/'status.json').read_text())
    assert state['phase']=='complete' and state['client_returncode']==0 and state['power_restored']
    decoder=module('quality246',ROOT/'kernel246/loc_decode.py')
    measurements=module('measurement254',ROOT/'kernel254/analyze-qmi-measurements.py')
    rf=module('rf255',ROOT/'kernel255/analyze-pga-clock.py')
    quality=decoder.summarize(native);radio,details=rf.analyze(native)
    indications=[dict(**r,flags=4,time=r['elapsed_us']/1e6) for r in native if r.get('kind')=='indication']
    raw,rows=measurements.analyze(indications)
    positions=[];statuses=collections.Counter();technology=collections.Counter();uncertainties=[];confidences=[];session_mismatch=0
    for r in indications:
        if r['message_id']!=0x24:continue
        t=r['tlvs'];status=decoder.uint(t,1,4);statuses[status]+=1
        if status:continue
        if decoder.uint(t,2,1)!=226:session_mismatch+=1;continue
        if not all(k in t and len(bytes.fromhex(t[k]))==8 for k in ('16','17')):continue
        lat,lon=(struct.unpack('<d',bytes.fromhex(t[k]))[0] for k in ('16','17'))
        if not (math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180):continue
        positions.append(r['time'])
        if '35' in t:technology[decoder.uint(t,35,4)]+=1
        if '18' in t:uncertainties.append(struct.unpack('<f',bytes.fromhex(t['18']))[0])
        if '22' in t:confidences.append(decoder.uint(t,22,1))
    ordinary=collections.defaultdict(list)
    for r in indications:
        if r['message_id']!=0x25 or '16' not in r['tlvs']:continue
        data=bytes.fromhex(r['tlvs']['16']);decoder.sv_list(data)
        records=[struct.unpack_from('<IIHBIBfff',data,1+28*i) for i in range(data[0])]
        for system in {v[1] for v in records if v[0]&1}:
            subset=[v for v in records if v[0]&1 and v[1]==system]
            cn0=[v[8] for v in subset if v[0]&128 and math.isfinite(v[8]) and v[8]>0]
            tracked=[v for v in subset if v[0]&8 and v[4]==3]
            ordinary[system].append(dict(time=r['time'],track=len(tracked),unique_track=len({v[2] for v in tracked}),positive=len(cn0),cn0=cn0))
    per_system={}
    for system in sorted({r['system'] for r in rows}):
        subset=[r for r in rows if r['system']==system];reports=collections.defaultdict(list)
        for r in subset:reports[r['host_time']].append(r)
        fresh=[t for t,values in reports.items() if any(v['valid_status']&0x08000000 and v['measurement_status']&0x08000000 for v in values)]
        per_system[str(system)]=dict(records=len(subset),measurement_reports=len(reports),reports_with_fresh=len(fresh),fresh_report_span_seconds=fresh[-1]-fresh[0] if fresh else 0,
            status_counts=dict(collections.Counter(v['status'] for v in subset)),
            validity={name:dict(valid=sum(bool(v['valid_status']&bit) for v in subset),true_when_valid=sum(bool(v['valid_status']&bit and v['measurement_status']&bit) for v in subset)) for name,bit in measurements.FLAGS.items()},
            cno_dbhz=ranges(v['cno'] for v in subset))
    ordinary_summary={str(system):dict(reports=len(values),track_entries_per_report=ranges(v['track'] for v in values),unique_track_satellites_per_report=ranges(v['unique_track'] for v in values),positive_cn0_entries_per_report=ranges(v['positive'] for v in values),cno_dbhz=ranges(c for v in values for c in v['cn0']),last_track_entries=values[-1]['track'],last_unique_track_satellites=values[-1]['unique_track']) for system,values in sorted(ordinary.items())}
    lifecycle=[r for r in native if r['kind']=='cleanup'];report_cleanup=[r for r in native if r['kind']=='report_cleanup']
    assert len(lifecycle)==1 and lifecycle[0]['success'] and lifecycle[0]['stop_ack'] and lifecycle[0]['client_released'] and lifecycle[0]['device_closed']
    assert len(report_cleanup)==1 and report_cleanup[0]['cleared']
    clock_after_fix=[v['uncertainty_mps'] for v in details['clock'] if positions and v['time']>=positions[0]]
    summary=dict(stage=258,user_confirmed_same_outdoor_location_as_stock_and_usb_disconnected=True,wireless_ssh_original_host_key_and_current_boot_verified=True,
        source_exports_sha_verified=len(receipt),native_same_cid_session_id=226,observation_seconds=300,
        valid_coordinate_position_reports=len(positions),position_session_mismatches=session_mismatch,position_status_counts=dict(statuses),
        position_technology_mask_counts={hex(k):v for k,v in technology.items()},satellite_used_reports=sum(v for k,v in technology.items() if k&1),propagated_position_reports=sum(v for k,v in technology.items() if k&0x800),
        first_valid_position_seconds_from_client_initialization=positions[0] if positions else None,
        continuous_position_span_seconds=positions[-1]-positions[0] if positions else 0,position_gap_seconds=ranges(b-a for a,b in zip(positions,positions[1:])),
        reported_horizontal_uncertainty_circular_m=ranges(uncertainties),reported_horizontal_confidence_counts=dict(collections.Counter(confidences)),
        ordinary_sv_by_system=ordinary_summary,raw_measurements_by_system=per_system,
        pga_counts=radio['pga_counts'],clock_source_counts=radio['clock_source_counts'],num_clock_resets_counts=radio['num_clock_resets_counts'],
        clock_drift_uncertainty_mps=radio['clock_drift_uncertainty_mps'],clock_drift_uncertainty_after_first_fix_mps=ranges(clock_after_fix),
        normal_modem_power_before=state['power_before'],normal_modem_power_during=state['power_during'],normal_modem_power_after=state['power_after'],dms_during_online=state['dms_during_online'],power_restored=state['power_restored'],taint_after=state['taint_after'],
        diagnostic_raw_measurement_report_configuration_enabled_and_cleared=True,no_gain_nv_rf_clock_or_memshare_provider_changes=True,
        native_loc_fix_verified=True,modemmanager_geoclue_desktop_integration_not_tested=True,
        cold_start_ttff_and_surveyed_accuracy_not_measured=True,indoor_failure_and_pga_root_cause_not_identified=True,
        old_memshare_provider_difference_not_fixed_by_this_test=True)
    stock=json.loads((ROOT/'kernel256/summary-validation.json').read_text())
    comparison=dict(stock_stage=256,linux_stage=258,same_phone_and_user_confirmed_outdoor_position=True,usb_disconnected_both=True,
        different_os_boot_and_assistance_state=True,not_a_cold_start_or_sensitivity_benchmark=True,
        stock=dict(valid_positions=stock['valid_coordinate_position_reports'],position_span_seconds=stock['continuous_position_span_seconds'],max_position_gap_seconds=stock['position_gap_seconds']['maximum'],gps_max_track_entries=stock['gps_track_per_report']['maximum'],gps_max_unique_track=stock['gps_unique_track_per_report']['unique_track_max'],gps_max_cno=stock['gps_cn0_dbhz']['maximum'],pga_counts=stock['pga_counts'],clock_uncertainty=stock['clock_drift_uncertainty_mps']),
        linux=dict(valid_positions=len(positions),position_span_seconds=summary['continuous_position_span_seconds'],max_position_gap_seconds=summary['position_gap_seconds']['maximum'],gps_max_track_entries=ordinary_summary['1']['track_entries_per_report']['maximum'],gps_max_unique_track=ordinary_summary['1']['unique_track_satellites_per_report']['maximum'],gps_max_cno=ordinary_summary['1']['cno_dbhz']['maximum'],pga_counts=radio['pga_counts'],clock_uncertainty=summary['clock_drift_uncertainty_mps'],clock_uncertainty_after_fix=summary['clock_drift_uncertainty_after_first_fix_mps']))
    for name,value in [('quality-validation.json',quality),('measurements-validation.json',raw),('pga-clock-validation.json',radio),('summary-validation.json',summary),('comparison-validation.json',comparison),('lifecycle-validation.json',dict(cleanup=lifecycle[0],report_cleanup=report_cleanup[0]))]:
        (out/name).write_text(json.dumps(value,indent=2)+'\n')
    (private/'decoded-measurements-private.json').write_text(json.dumps(rows)+'\n')
    (private/'decoded-clock-private.json').write_text(json.dumps(details)+'\n')
    print(json.dumps(comparison,indent=2))
if __name__=='__main__':main()
