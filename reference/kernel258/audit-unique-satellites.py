#!/usr/bin/env python3
"""Count unique (constellation, SV ID) privately; export aggregate counts only."""
from pathlib import Path
import argparse,collections,hashlib,importlib.util,json,struct
ROOT=Path(__file__).resolve().parents[1]
def summarize(rows):
    result=collections.defaultdict(list)
    for r in rows:
        if r.get('message_id')!=0x25 or '16' not in r.get('tlvs',{}):continue
        b=bytes.fromhex(r['tlvs']['16']);assert len(b)==1+28*b[0]
        entries=[struct.unpack_from('<IIHBIBfff',b,1+28*i) for i in range(b[0])]
        for system in {v[1] for v in entries if v[0]&1}:
            track=[v for v in entries if v[0]&1 and v[1]==system and v[0]&8 and v[4]==3]
            result[system].append((len(track),len({v[2] for v in track})))
    return {str(s):dict(reports=len(values),track_entries_min=min(v[0] for v in values),track_entries_max=max(v[0] for v in values),
        unique_track_min=min(v[1] for v in values),unique_track_max=max(v[1] for v in values),unique_track_last=values[-1][1],
        duplicate_track_entries=sum(v[0]-v[1] for v in values)) for s,values in sorted(result.items())}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('private_root',type=Path)
    args=parser.parse_args();p=args.private_root
    native=[json.loads(v) for v in (p/'kernel258/events-private.jsonl').read_text().splitlines()]
    native=[v for v in native if v.get('kind')=='indication']
    spec=importlib.util.spec_from_file_location('wire250',ROOT/'kernel250/decode-android-hal.py')
    wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
    packets,parsing=wire.parse_trace(p/'kernel256/hal-outdoor.trace');quality=wire.summarize(packets,parsing)
    fds=set(quality['loc_socket_fds'])
    stock=[v for v in packets if v['fd'] in fds and v['direction']=='recv' and v['flags']==4]
    result=dict(stage=258,deduplication_key='constellation_and_sv_id_within_each_ordinary_report',
        expanded_and_ordinary_arrays_not_combined=True,track_entry_count_is_not_unique_satellite_count=True,
        stock256=summarize(stock),linux258=summarize(native),
        private_input_sha256={str(path.relative_to(p)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [p/'kernel256/hal-outdoor.trace',p/'kernel258/events-private.jsonl']})
    (ROOT/'kernel258/sv-uniqueness-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    # Keep the original entry-count values; explicitly identify their scope.
    out=ROOT/'kernel256/summary-validation.json';summary=json.loads(out.read_text())
    summary['gps_track_per_report_is_entry_count_not_unique_satellites']=True
    summary['gps_unique_track_per_report']=result['stock256']['1']
    summary['unique_satellite_count_audited_at_stage']=258
    out.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({name:result[name]['1'] for name in ['stock256','linux258']},indent=2))
if __name__=='__main__':main()
