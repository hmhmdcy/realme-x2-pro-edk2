"""Inspect the bounded DMS power cycle and contemporaneous GNSS reports."""
from pathlib import Path
import collections,json,struct
from importlib.util import spec_from_file_location,module_from_spec

ROOT=Path(__file__).resolve().parents[1]
P=Path('/mnt/e/edk2-samurai-out/kernel255')
s=spec_from_file_location('pgaclock',ROOT/'kernel255/analyze-pga-clock.py')
a=module_from_spec(s);s.loader.exec_module(a)


def main():
    rows=[json.loads(x) for x in (P/'dms-cycle-events-private.jsonl').read_text().splitlines()]
    assert rows[-1]==dict(kind='cleanup',initial_mode=0,final_mode=0,online_restore_ack=True,closed=True)
    packets,parsing=a.wire.parse_trace(P/'hal-dms-cycle.trace')
    quality=a.wire.summarize(packets,parsing)
    report,decoded=a.analyze(packets)
    clock=json.loads((P/'clock-after-cycle-private.json').read_text())
    epoch_offset=(clock['realtime_ms']-clock['monotonic_ms'])/1000
    phase_start=[r for r in rows if r['kind']=='phase']
    modes={};phases={}
    for index,r in enumerate(phase_start):
        name=r['phase'];samples=[x for x in rows if x.get('kind')=='mode_sample' and x['phase']==name]
        modes[name]=dict(collections.Counter(x['mode'] for x in samples))
        start=epoch_offset+r['monotonic']+3
        end=epoch_offset+(phase_start[index+1]['monotonic'] if index+1<len(phase_start) else max(x['monotonic'] for x in samples))-3
        selected=[x for x in packets if start<=x['time']<end]
        phases[name]=a.analyze(selected)[0]
    sets=[];acks=[]
    for r in rows:
        if 'hex' not in r:continue
        q=a.wire.decode_wire(bytes.fromhex(r['hex']))
        if not q:continue
        if r['kind']=='request':
            assert q['message_id'] in (0x2d,0x2e)
            if q['message_id']==0x2e:
                mode=bytes.fromhex(q['tlvs']['1']);assert len(mode)==1 and mode[0] in (0,1);sets.append(mode[0])
        elif q['flags']==2 and q['message_id']==0x2e:
            result,error=struct.unpack('<HH',bytes.fromhex(q['tlvs']['2']));acks.append(dict(result=result,error=error))
    assert sets==[1,0] and acks==[dict(result=0,error=0)]*2
    output=dict(dms_set_modes_in_order=sets,dms_set_acknowledgements=acks,mode_readback_counts=modes,
        original_online_restored_and_readback=True,gnss_whole_capture=report,
        phase_comparisons=phases,quality=quality,
        phase_alignment_uses_post_capture_realtime_monotonic_offset=True,
        three_seconds_excluded_at_phase_edges=True,clock_step_during_run_not_independently_ruled_out=True,
        no_modem_reset_offline_persistent_nv_mode=True)
    (ROOT/'kernel255/dms-cycle-validation.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(modes=modes,whole_pga=report['pga_counts'],
        phases={k:dict(pga=v['pga_counts'],clock_unc=v['clock_drift_uncertainty_mps'],source=v['clock_source_counts']) for k,v in phases.items()},
        gps=quality['constellations']['totals_by_constellation'].get('GPS'),
        successful_positions=quality['quality']['successful_qmi_positions_with_valid_coordinates']),indent=2))


if __name__=='__main__':main()
