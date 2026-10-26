"""Trace reported PGA/clock provenance using private QMI captures.

No satellite IDs, coordinates, epochs, NMEA sentences or payloads in output.
Clock drift units below apply to the documented QMI structure, not guessed
offsets in the opaque DIAG Clock v3 packet.
"""
from pathlib import Path
import collections
import importlib.util
import json
import math
import struct

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


wire=module('wire250',ROOT/'kernel250/decode-android-hal.py')
pqwm=module('pqwm208',ROOT/'kernel208/pqwm1.py')
loc=module('loc226',ROOT/'kernel226/loc_decode.py')


def range_of(values):
    values=list(values)
    if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite clock value')
    return dict(samples=len(values),minimum=min(values) if values else None,
                maximum=max(values) if values else None,distinct=len(set(values)))


def load(path):
    if path.suffix=='.trace':return wire.parse_trace(path)[0]
    if path.suffix=='.jsonl':
        rows=[json.loads(s) for s in path.read_text().splitlines()]
        if rows and 'hex' in rows[0]:
            return [dict(time=i,**p) for i,r in enumerate(rows) if 'hex' in r
                    for p in [wire.decode_wire(bytes.fromhex(r['hex']))] if p]
        return rows
    return json.loads(path.read_text())


def analyze(rows):
    rf=[];clock=[];ce=[];measurements=0;agc_status=[];metrics=[]
    for row in rows:
        if row.get('direction')=='send' or (row.get('flags') is not None and row['flags']!=4):continue
        if row.get('kind') not in (None,'indication'):continue
        ident=row.get('message_id');tlv=row.get('tlvs',{})
        time=row.get('time',row.get('elapsed_us',0)/1e6)
        if ident==0x26:
            raw=bytes.fromhex(tlv.get('16') or tlv.get('1') or '')
            if not raw:continue
            for sentence in loc.nmea_text(raw).replace('\r','').split('\n'):
                if sentence.startswith('$PQWM1,'):
                    rf.append(dict(time=time,**pqwm.decode(sentence)))
        if ident==0x86:
            measurements+=1
            if '31' in tlv:
                raw=bytes.fromhex(tlv['31'])
                if len(raw)!=8:raise ValueError('Unexpected AGC/BP metric width')
                agc,bp=struct.unpack('<ii',raw)
                metrics.append(dict(time=time,system=int.from_bytes(bytes.fromhex(tlv['3']),'little'),
                    signal_mask=int.from_bytes(bytes.fromhex(tlv.get('30','')),'little'),
                    agc_word=agc,bp_word=bp,agc_db=agc/100,bp_db=bp/100))
            if '16' in tlv:
                raw=bytes.fromhex(tlv['16'])
                if len(raw)!=12:raise ValueError('Clock frequency structure is not 12 bytes')
                drift,unc,source=struct.unpack('<ffI',raw)
                resets=bytes.fromhex(tlv.get('28',''))
                if resets and len(resets)!=4:raise ValueError('Unexpected reset counter width')
                clock.append(dict(time=time,drift_mps=drift,uncertainty_mps=unc,source=source,
                    num_clock_resets=struct.unpack('<I',resets)[0] if resets else None))
            # Official IDL agcStatus TLV is verified in source before using it.
            if '67' in tlv:
                raw=bytes.fromhex(tlv['67'])
                if len(raw)!=4:raise ValueError('Unexpected AGC status width')
                agc_status.append(struct.unpack('<I',raw)[0])
        if ident==0xce:
            tick=bytes.fromhex(tlv.get('1',''));gain=bytes.fromhex(tlv.get('2',''))
            if len(tick)!=8 or len(gain)!=4:raise ValueError('Short band metrics indication')
            ce.append(dict(time=time,band1_pga_db=struct.unpack('<i',gain)[0]))
    report=dict(pqwm1_reports=len(rf),pga_missing=sum(r['pga_gain'] is None for r in rf),
        pga_counts=dict(collections.Counter(r['pga_gain'] for r in rf if r['pga_gain'] is not None)),
        pqwm_ranges={k:range_of(r[k] for r in rf if r[k] is not None) for k in
                     ['pga_gain','clock_bias','clock_bias_unc','xo_state','adc_i','adc_q','agc_gps','jammer_gps','error_recovery']},
        measurement_events=measurements,clock_reports=len(clock),
        clock_source_counts=dict(collections.Counter(r['source'] for r in clock)),
        num_clock_resets_counts=dict(collections.Counter(r['num_clock_resets'] for r in clock)),
        clock_drift_mps=range_of(r['drift_mps'] for r in clock),
        clock_drift_uncertainty_mps=range_of(r['uncertainty_mps'] for r in clock),
        agc_status_reports=len(agc_status),agc_status_counts=dict(collections.Counter(agc_status)),
        rf_metric_groups={f'system{system}_signal{hex(signal)}':dict(reports=len(values),
            int32_max_agc_word_count=sum(v['agc_word']==0x7fffffff for v in values),
            minus100_bp_word_count=sum(v['bp_word']==-100 for v in values),
            raw_scaled_agc_db=range_of(v['agc_db'] for v in values),raw_scaled_bp_db=range_of(v['bp_db'] for v in values))
            for system,signal in sorted({(v['system'],v['signal_mask']) for v in metrics})
            for values in [[v for v in metrics if v['system']==system and v['signal_mask']==signal]]},
        band_metrics_reports=len(ce),band1_pga_db_counts=dict(collections.Counter(r['band1_pga_db'] for r in ce)))
    return report,dict(pqwm=rf,clock=clock,band_metrics=ce,rf_metrics=metrics)


def main():
    files={
      'linux241_ordered':'kernel241/evidence/ordered/events-private.jsonl',
      'linux242':'kernel242/clock-evidence/events-private.jsonl',
      'linux243_window':'kernel243/evidence/k243-window-clock/events-private.jsonl',
      'linux243_wlan_off':'kernel243/wlan-evidence/k243-wlan-off-clock/events-private.jsonl',
      'linux247_baseline':'kernel247/baseline-off-snapshot/baseline-off-loc-events-private.jsonl',
      'linux247_online':'kernel247/comparison-online-snapshot/comparison-online-loc-events-private.jsonl',
      'thirdparty250_window':'kernel250/android-gnss-r2-root-private/decoded-qmi-private.json',
      'thirdparty250_outdoor':'kernel250/android-gnss-r3-outdoor-private/decoded-qmi-private.json',
      'thirdparty250_outdoor_long':'kernel250/android-gnss-r4-outdoor-long-private/decoded-qmi-private.json',
      'stock253_abab':'kernel254/qmi-abab-private.json',
      'stock254_after_restart':'kernel254/qmi-after-init-private.json',
      'stock254_final':'kernel254/hal-final.trace',
    }
    if (PRIVATE/'kernel255/hal-rf-clock.trace').exists():files['stock255_live']='kernel255/hal-rf-clock.trace'
    if (PRIVATE/'kernel255/rf-clock-events-private.jsonl').exists():files['native255_observer']='kernel255/rf-clock-events-private.jsonl'
    reports={};decoded={}
    for name,relative in files.items():
        reports[name],decoded[name]=analyze(load(PRIVATE/relative))
    old=json.loads((PRIVATE/'kernel254/qmi-measurements-private.json').read_text())
    start=min(r['host_time'] for r in old);end=max(r['host_time'] for r in old)
    rf=decoded['stock253_abab']['pqwm'];cl=decoded['stock253_abab']['clock']
    episode={}
    for name,a,b in [('before',start-20,start),('positive_reports',start,end+.01),('after',end+.01,end+20)]:
        r=[v for v in rf if a<=v['time']<b];c=[v for v in cl if a<=v['time']<b]
        episode[name]=dict(pga_counts=dict(collections.Counter(v['pga_gain'] for v in r)),
           clock_source_counts=dict(collections.Counter(v['source'] for v in c)),
           num_clock_resets_counts=dict(collections.Counter(v['num_clock_resets'] for v in c)),
           drift_mps=range_of(v['drift_mps'] for v in c),
           uncertainty_mps=range_of(v['uncertainty_mps'] for v in c),
           gps_l1ca_agc_metric_db=range_of(v['agc_db'] for v in decoded['stock253_abab']['rf_metrics'] if v['system']==1 and v['signal_mask']==1 and a<=v['time']<b),
           gps_l1ca_bp_metric_db=range_of(v['bp_db'] for v in decoded['stock253_abab']['rf_metrics'] if v['system']==1 and v['signal_mask']==1 and a<=v['time']<b))
    result=dict(groups=reports,gps_single_fresh_episode_clock_comparison=episode,
        pga_is_already_in_received_modem_nmea=True,hal_uses_atoi_field9_not_a_gain_setter=True,
        linux_pga_not_a_fixed_minus10_initialization_constant=True,
        agc_missing_not_assumed_no_saturation=True,clock_qmi_units_from_official_idl=True)
    (PRIVATE/'kernel255/pga-clock-decoded-private.json').write_text(json.dumps(decoded,indent=2)+'\n')
    (ROOT/'kernel255/pga-clock-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{name:v[name] for name in ['pqwm1_reports','pga_counts','clock_reports','clock_source_counts','clock_drift_uncertainty_mps','band_metrics_reports','band1_pga_db_counts']} for k,v in reports.items()},indent=2))


if __name__=='__main__':main()
