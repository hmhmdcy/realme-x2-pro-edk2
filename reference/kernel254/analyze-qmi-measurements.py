"""Decode QMI LOC 0x86/TLV0x1b from the pinned Qualcomm IDL.

Outputs aggregate evidence only. Full rows, satellite IDs and payloads belong
in the private output directory. Missing measurement arrays are not zero C/N0.
"""
from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import math
import struct

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path('/mnt/e/edk2-samurai-out')
FLAGS = dict(code_phase=1, sub_bit_time=2, millisecond_time=4, bit_edge=8,
             doppler=16, fine_doppler=32, lock_point=64,
             fresh_last_second=0x08000000)


def array(value):
    if not value or len(value) != 1+90*value[0]:
        raise ValueError('QMI measurement count/90-byte stride mismatch')
    result = []
    for index in range(value[0]):
        b = value[1+90*index:1+90*(index+1)]
        r = dict(sv=struct.unpack_from('<H',b)[0],
                 status=struct.unpack_from('<I',b,3)[0],
                 valid_mask=struct.unpack_from('<H',b,7)[0],
                 nav=b[10], valid_status=struct.unpack_from('<Q',b,11)[0],
                 measurement_status=struct.unpack_from('<Q',b,19)[0],
                 cno=struct.unpack_from('<H',b,27)[0]/10,
                 latency_ms=struct.unpack_from('<i',b,31)[0],
                 ms=struct.unpack_from('<I',b,35)[0],
                 sub_ms=struct.unpack_from('<f',b,39)[0],
                 time_unc_ms=struct.unpack_from('<f',b,43)[0],
                 doppler_mps=struct.unpack_from('<f',b,47)[0],
                 doppler_unc_mps=struct.unpack_from('<f',b,51)[0],
                 loss_of_lock=b[60])
        if not all(math.isfinite(r[k]) for k in
                   ['sub_ms','time_unc_ms','doppler_mps','doppler_unc_mps']):
            raise ValueError('Nonfinite QMI measurement')
        result.append(r)
    return result


def range_of(values):
    values=list(values)
    return dict(samples=len(values),min=min(values) if values else None,
                max=max(values) if values else None,
                distinct=len(set(values)))


def analyze(packets):
    events=[p for p in packets if p['message_id']==0x86 and p['flags']==4]
    rows=[]
    for p in events:
        if '27' not in p['tlvs']:
            continue
        system=struct.unpack('<I',bytes.fromhex(p['tlvs']['3']))[0]
        for r in array(bytes.fromhex(p['tlvs']['27'])):
            r.update(system=system,host_time=p['time'])
            rows.append(r)
    result=dict(events=len(events),events_with_sv_array=sum('27' in p['tlvs'] for p in events),
                events_without_sv_array=sum('27' not in p['tlvs'] for p in events),
                records=len(rows),systems=dict(collections.Counter(r['system'] for r in rows)),
                status_counts=dict(collections.Counter(r['status'] for r in rows)),
                nav_counts=dict(collections.Counter(r['nav'] for r in rows)),
                loss_of_lock_counts=dict(collections.Counter(r['loss_of_lock'] for r in rows)),
                valid_status_mask_counts=dict(collections.Counter(hex(r['valid_status']) for r in rows)),
                measurement_status_counts=dict(collections.Counter(hex(r['measurement_status']) for r in rows)),
                validity={name:dict(status_valid=sum(bool(r['valid_status']&bit) for r in rows),
                    status_true_when_valid=sum(bool(r['valid_status']&bit and r['measurement_status']&bit) for r in rows))
                    for name,bit in FLAGS.items()},
                ranges={k:range_of(r[k] for r in rows) for k in
                        ['cno','latency_ms','time_unc_ms','doppler_mps','doppler_unc_mps']})
    if rows:
        result['successive_latency_steps_ms']=dict(collections.Counter(b['latency_ms']-a['latency_ms'] for a,b in zip(rows,rows[1:])))
        result['successive_doppler_unc_steps_mps']=range_of(b['doppler_unc_mps']-a['doppler_unc_mps'] for a,b in zip(rows,rows[1:]))
        result['fresh_record_indices']=[i for i,r in enumerate(rows) if r['valid_status']&0x08000000 and r['measurement_status']&0x08000000]
    return result,rows


def selftest():
    good=bytes([0])
    assert array(good)==[]
    for bad in [b'', b'\x01', bytes([0])+bytes(90), bytes([2])+bytes(90)]:
        try: array(bad)
        except ValueError: pass
        else: raise AssertionError('Malformed array accepted')
    empty,rows=analyze([dict(message_id=0x86,flags=4,tlvs={})])
    assert empty['events_without_sv_array']==1 and empty['records']==0 and rows==[]
    return dict(count_stride_truncation_rejected=True,missing_not_zero=True)


def main():
    source=PRIVATE/'kernel221/loc-upstream'
    pins={'location_service_v02.h':'5ebe4ed7a33c8bb567eb67d6c7203671bfbf6bcb02666ecd3e5393242ff3d255',
          'location_service_v02.c':'b66db26326a17b15ec94750aa3ac6eea7ad2ed00e07c24e37e87eb0237aa3f47'}
    for name,digest in pins.items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
    packets=json.loads((PRIVATE/'kernel254/qmi-abab-private.json').read_text())
    result,rows=analyze(packets)
    private_raw=json.loads((PRIVATE/'kernel254/search-measurements-private.json').read_text())['stock253_abab']
    raw=[s for r in private_raw for s in r['satellites'] if s['cno']>0]
    assert len(raw)==len(rows)==19
    matches={key:sum(q[qkey]==r[rkey] for q,r in zip(rows,raw)) for key,qkey,rkey in
             [('same_sv','sv','sv'),('latency','latency_ms','latency'),('sv_time_ms','ms','ms'),
              ('sub_ms','sub_ms','sub_ms'),('time_unc','time_unc_ms','time_unc'),
              ('doppler','doppler_mps','speed'),('doppler_unc','doppler_unc_mps','speed_unc')]}
    matches['measurement_status_low32']=sum(q['measurement_status']&0xffffffff==int.from_bytes(bytes.fromhex(r['measurement_status']),'little') for q,r in zip(rows,raw))
    result.update(source_sha256=pins,selftest=selftest(),raw_qmi_field_matches=matches,
                  qmi_units_from_official_header=True,
                  raw_latency_and_time_uncertainty_not_identical_to_qmi=True,
                  raw_latency_units_not_inferred_from_qmi=True,
                  one_fresh_measurement_followed_by_aged_reports=len(result['fresh_record_indices'])==1)
    (PRIVATE/'kernel254/qmi-measurements-private.json').write_text(json.dumps(rows,indent=2)+'\n')
    (ROOT/'kernel254/qmi-measurements-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
