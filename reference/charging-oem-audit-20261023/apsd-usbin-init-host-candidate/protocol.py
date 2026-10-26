"""Exact schema-1 adapter for the helper's actual state_show/control_store."""
import json
import re

SYSFS = '/sys/bus/platform/devices/samurai-usbin-init'
MODULE = 'samurai_usbin_init'
PHASES = {'observed','waiting','clear_verified','restored','committed','timeout','error','cancelled'}
BOOLS = 'armed running held_ref can_unload pending_restore commit_allowed committed old_valid write_attempted unknown_write changed have_first'.split()
INTS = 'op old_bit before_cfg after_cfg write_return readback_error post_error error clear_error clear_write_return off_samples first_boottime_ms started_boottime_ms deadline_boottime_ms now_boottime_ms remaining_ms pre_started_boottime_ms prewrite_boottime_ms post_boottime_ms'.split()

def parse(raw, instance=None):
    s=json.loads(raw) if isinstance(raw,(str,bytes)) else dict(raw)
    if s.get('schema')!=1 or not re.fullmatch('[0-9a-f]{16}',s.get('instance','')) or int(s['instance'],16)==0:
        raise ValueError('unknown helper schema/instance')
    if instance is not None and s['instance']!=instance:raise ValueError('helper instance changed')
    if s.get('phase') not in PHASES or any(type(s.get(k)) is not bool for k in BOOLS) or any(type(s.get(k)) is not int for k in INTS):
        raise ValueError('helper state types differ')
    if s['op'] not in (0,1,2) or s['old_bit'] not in (0,128) or any(not 0<=s[k]<=255 for k in ['before_cfg','after_cfg']):
        raise ValueError('helper enum/config invalid')
    for key in ['first','pre','post','saved']:
        if not isinstance(s.get(key),list) or len(s[key])!=8 or any(type(v) is not int or not 0<=v<=255 for v in s[key]):raise ValueError('raw snapshot invalid')
    if s['can_unload'] != (not s['running'] and not s['pending_restore'] and not s['held_ref']):raise ValueError('unload summary inconsistent')
    return s

def off(raw):return len(raw)==8 and not(raw[2]&0x10 or raw[5]&0x21 or raw[4]&0x20)

def observed(s):
    return bool(s['phase']=='observed' and s['op']==0 and not any(s[k] for k in ['armed','running','held_ref','pending_restore','write_attempted','unknown_write','error']) and s['can_unload'])

def waiting(s,remote_ms,min_remaining=0):
    return bool(s['phase']=='waiting' and s['op']==1 and s['armed'] and s['running'] and s['held_ref']
        and not any(s[k] for k in ['committed','commit_allowed','unknown_write','error'])
        and s['deadline_boottime_ms']-s['started_boottime_ms']==60000
        and s['started_boottime_ms']<=s['now_boottime_ms']<=remote_ms+1000
        and 0<=remote_ms-s['now_boottime_ms']<=1000
        and s['remaining_ms']==max(0,s['deadline_boottime_ms']-s['now_boottime_ms'])
        and s['deadline_boottime_ms']-remote_ms>=min_remaining)

def verified(s):
    return bool(s['phase']=='clear_verified' and s['op']==1 and s['armed'] and not s['running']
        and s['old_valid'] and s['commit_allowed'] and not s['committed']
        and not any(s[k] for k in ['unknown_write','error','write_return','readback_error','post_error','clear_error','clear_write_return'])
        and s['saved']==s['pre'] and s['before_cfg']==s['pre'][7] and s['after_cfg']==s['post'][7]
        and s['pre'][:7]==s['post'][:7] and off(s['first']) and off(s['pre']) and off(s['post'])
        and s['off_samples']>=2 and not(s['after_cfg']&0x80) and not((s['before_cfg']^s['after_cfg'])&0x7f)
        and s['prewrite_boottime_ms']-s['first_boottime_ms']>=500
        and s['started_boottime_ms']<=s['pre_started_boottime_ms']<=s['prewrite_boottime_ms']<s['deadline_boottime_ms']
        and s['prewrite_boottime_ms']-s['pre_started_boottime_ms']<=250 and s['post_boottime_ms']>=s['prewrite_boottime_ms']
        and s['old_bit']==(s['before_cfg']&0x80)
        and (s['write_attempted'] and s['held_ref'] and s['pending_restore'] and s['changed'] if s['old_bit'] else
             not s['write_attempted'] and not s['held_ref'] and not s['pending_restore'] and not s['changed'] and s['can_unload']))

def committed(s):
    return bool(s['phase']=='committed' and s['committed'] and s['can_unload'] and not any(s[k] for k in ['running','held_ref','pending_restore','unknown_write','error']))

def expired_zero_write(s):
    return bool(s['phase']=='timeout' and s['op']==1 and s['armed'] and s['error']==-110 and s['can_unload']
        and not any(s[k] for k in ['running','held_ref','pending_restore','unknown_write','write_attempted','write_return','clear_write_return','readback_error','post_error']))

def close_zero_write(s):
    """Unarmed observe or positively expired clear, never an attempted config write."""
    return expired_zero_write(s) or (observed(s) and not any(s[k] for k in ['old_valid','committed','commit_allowed','write_return','clear_write_return','readback_error','post_error','clear_error']))
