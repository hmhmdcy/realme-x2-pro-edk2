"""Bounded read-only raw/source/UI capture; never controls or unloads a module."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import signal
import time
import common
import protocol

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
icon=load('usbin_frozen_icon',HERE/'icon-observation.py')
icon_audit=load('usbin_frozen_icon_audit',HERE/'icon-audit.py')

def helper(instance=None):
    start=common.boot_ms()
    try:state=protocol.parse(Path(protocol.SYSFS,'state').read_text(),instance);error=None
    except (OSError,ValueError,KeyError,TypeError) as e:state=None;error=str(e)
    end=common.boot_ms()
    fresh=state is not None and end-start<=2000 and start-1000<=state['now_boottime_ms']<=end and end-state['now_boottime_ms']<=1000
    return {'state':state,'error':error,'read_started_ms':start,'read_ended_ms':end,'fresh':fresh}

def audit(raw):
    ui=icon_audit.audit(raw);states=[r['helper']['state'] for r in raw['samples'] if r.get('helper',{}).get('state')]
    last=states[-1] if states else None
    verified=last is not None and protocol.verified(last)
    rows=[r for r in raw['samples'] if r.get('source_online')==r.get('acok_online')==1]
    before_source=rows[0].get('source') if rows else None;after_source=rows[-1].get('source') if rows else None
    before_cv=before_source['charger'].get('constant_charge_voltage') if before_source else None
    after_cv=after_source['charger'].get('constant_charge_voltage') if after_source else None
    return {'scope':'one-bit initialization, physical cycle, source and UI evidence are separate',
        'initialization_verified':verified,'configuration_changed':last.get('changed') if last else None,
        'physical_cycle_passed':ui['physical_cycle_passed'],
        'environment_unchanged':raw.get('environment_unchanged',False),
        'source_before':before_source,'source_after':after_source,
        'cv_per_cell_before_uv':before_cv//2 if type(before_cv) is int else None,
        'cv_per_cell_after_uv':after_cv//2 if type(after_cv) is int else None,
        'cv_cap_preserved':type(before_cv) is int and type(after_cv) is int and after_cv<=before_cv<=8725000,
        'post_online_telemetry_healthy':bool(rows and common.healthy(rows[-1])),
        'helper_terminal':last,'ui_observation':ui,'screen_latency_verified':False,
        'observer_terminal_reason':raw['terminal_reason'],
        'source_upgrade_caused_by_bit_clear_proven':False,'net_charging_proven':False}

def run(c):
    if not c.get('execute') or not c.get('window_confirmed') or not 90<=c['max_seconds']<=300:raise ValueError('explicit bounded coordinated capture required')
    os.umask(0o077);io=icon.RealIO();io.out=Path(c['capture']);io.out.mkdir(mode=0o700)
    common.save(io.out/'config-private.json',c)
    start=io.clock_pair();base=(start['m0']+start['m1'])/2;common.save(io.out/'clock-start.json',start)
    rows=[];cycle=icon.Cycle();reason='deadline';error=None;fd=None;monitor={'started':False,'errors':['not started']};same=False;env_same=False
    instance=None;healthy_count=0;before=None
    try:
        common.identity(c);before=common.environment();common.save(io.out/'environment-before-private.json',before)
        io.discover_battery();fd=common.open_pmic();io.start_events(base)
        while io.boottime()-start['boot']<c['max_seconds']:
            if not io.events_alive():raise RuntimeError('UI event monitor stopped')
            row=io.sample(base);row['battery']['temp_decic']=io.read(io.battery/'temp',True)
            row['raw_pmic']=common.pmic(fd);row['source']=common.source();row['helper']=helper(instance)
            hs=row['helper']['state']
            if hs is not None and instance is None:instance=hs['instance']
            row['t_end']=time.monotonic()-base;rows.append(row);io.append_sample(row)
            phase=cycle.feed(row);healthy_count=healthy_count+1 if common.healthy(row) else 0
            remaining=max(0,c['max_seconds']-(io.boottime()-start['boot']))
            io.status({'phase':phase,'active':True,'terminal':False,'tick':len(rows),'t':row['t_end'],
                'transaction':c['transaction'],'token':c['token'],'remaining_boottime_seconds':remaining,
                'ready_to_arm':healthy_count>=3 and phase=='ready' and remaining>=90 and row['helper']['fresh'] and hs is not None and protocol.observed(hs),
                'helper':row['helper'],'latest_sample':row,'ready_for_user_action':False})
            # Keep sampling a full minute after the real online edge for late State events.
            # This extends only this new collector; the frozen physical/UI parser is unchanged.
            if cycle.complete and cycle.on_begin is not None and row['t_end']-cycle.on_begin>=60 and hs is not None and not hs['running'] and hs['armed']:
                reason='cycle_complete';break
            io.sleep(1)
    except BaseException as e:error={'type':type(e).__name__,'message':str(e)};reason='exception'
    finally:
        try:monitor=io.stop_events()
        except Exception as e:monitor={'started':False,'errors':[str(e)]}
        if fd is not None:os.close(fd)
        end=io.clock_pair();common.save(io.out/'clock-end.json',end)
        errors=[]
        try:common.identity(c);same=True
        except Exception as e:errors.append('final identity: '+str(e))
        try:
            after=common.environment();env_same=before==after;common.save(io.out/'environment-after-private.json',after)
            if not env_same:errors.append('camera/session changed')
        except Exception as e:errors.append('final environment: '+str(e))
        try:events=io.event_data()
        except Exception as e:events={};errors.append('event read: '+str(e))
        raw={'schema':'charging-icon-capture-v1','transaction':c['transaction'],'samples':rows,
            'clock_start':start,'clock_end':end,'cycle':cycle.evidence(),'monitor':monitor,
            'terminal_reason':reason,'exception':error,'identity_unchanged':same,
            'environment_unchanged':env_same,'capture_errors':errors,
            'duration_seconds':(end['m0']+end['m1'])/2-base,**events}
        common.save(io.out/'capture-private.json',raw);result=audit(raw);common.save(io.out/'result.json',result)
        io.status({'phase':'terminal','active':False,'terminal':True,'tick':len(rows),'transaction':c['transaction'],'token':c['token'],
            'ready_to_arm':False,'ready_for_user_action':False,'reason':reason,'result':result})
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);args=p.parse_args()
    c=json.loads(Path(args.config).read_text())
    def stop(signum,frame):raise InterruptedError('observer signal '+str(signum))
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    result=run(c);print(json.dumps(result));return 0

if __name__=='__main__':raise SystemExit(main())
