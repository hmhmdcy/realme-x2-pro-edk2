"""Pure current-readiness checks, never messages the user."""
import math
import protocol
import common

def ready(data,c,for_arm=False,roundtrip=0):
    reasons=[];rows=data.get('observations',[]);receipt=data.get('observer_receipt',{})
    if not data.get('identity_unchanged') or not data.get('environment_unchanged'):reasons.append('fresh identity/environment differs')
    if data.get('uncertain'):reasons.append('transaction outcome unknown; fetch only')
    if len(rows)!=2:return {'ready_to_arm':False,'may_prompt_user':False,'reasons':reasons+['two current observations required']}
    if not math.isfinite(roundtrip) or not 0<=roundtrip<=8:reasons.append('roundtrip over 8s')
    previous=None
    for i,row in enumerate(rows):
        status=row.get('status',{});proc=row.get('process',{});h=row.get('helper',{})
        if proc.get('state')!='alive' or any(proc.get(k)!=receipt.get(k) for k in ['pid','start_ticks','argv']):reasons.append('exact observer not live')
        if any(status.get(k)!=receipt.get(k) for k in ['pid','start_ticks']):reasons.append('status process differs')
        if status.get('transaction')!=c['transaction'] or status.get('token')!=c['token']:reasons.append('status owner differs')
        if not(status.get('active') is True and status.get('terminal') is False and status.get('phase')=='ready'):reasons.append('observer not currently ready')
        try:
            age=row['remote_realtime']-status['realtime']
            if not 0<=age<=3 or status['remaining_boottime_seconds']-roundtrip<(90 if for_arm else 35):reasons.append('stale observer or insufficient capture time')
            if not h.get('fresh'):raise ValueError('helper read stale')
            state=protocol.parse(h['state'],c['instance'])
            if for_arm:
                if not(status.get('ready_to_arm') is True and protocol.observed(state)):reasons.append('instance already armed or not observe-only')
            elif not protocol.waiting(state,row['remote_boottime_ms'],45000+int(roundtrip*1000)):
                reasons.append('arm not live with at least 45s remaining')
            if not common.healthy(status['latest_sample']):reasons.append('latest telemetry/source unsafe')
            if protocol.off(status['latest_sample']['raw_pmic']):reasons.append('physical input already off; no new unplug prompt')
            tick=status['tick']
            if type(tick) is not int or tick<3:reasons.append('too few baseline ticks')
            if previous is not None and (tick<=previous['status']['tick'] or not 1000<=row['remote_boottime_ms']-previous['remote_boottime_ms']<=5000):reasons.append('ticks/clocks did not advance')
        except (KeyError,ValueError,TypeError):reasons.append('incomplete helper/timing evidence')
        previous=row
    return {'ready_to_arm':for_arm and not reasons,'may_prompt_user':not for_arm and not reasons,
            'reasons':reasons,'recheck_if_not_prompted_within_seconds':3}
