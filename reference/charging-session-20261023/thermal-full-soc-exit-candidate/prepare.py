"""Exact private source delta only; no kernel build or device access."""
from pathlib import Path
import difflib, hashlib, json
HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'charger-reattach-observation-candidate'
R8 = HERE.parent / 'r8-source-integration/kernel-sources/drivers/power/supply'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def changed(text, old, new):
    if text.count(old) != 1: raise ValueError('source anchor not unique: ' + old[:80])
    return text.replace(old, new)


def main():
    original = {'samurai-mp2650.c': (BASE / 'samurai-mp2650.c').read_bytes(),
                **{name: (R8 / name).read_bytes() for name in ('mp2650-core.h', 'oem-full-cycle.h')}}
    if sha(original['samurai-mp2650.c']) != '1c088829ff827cb8015cccafc1a7fc1cad5b519d5a91ba08abdebd1adeb5b4b1':
        raise ValueError('frozen 97c source differs')
    text = {name: raw.decode().replace('\r\n', '\n') for name, raw in original.items()}
    text['mp2650-core.h'] = changed(text['mp2650-core.h'], '\tint gauge_current_ua;\n',
        '\tint gauge_current_ua;\n\t/* Optional fresh raw percent; never substitute cached/UI capacity. */\n\tint soc_valid, soc_percent;\n')
    text['samurai-mp2650.c'] = changed(text['samurai-mp2650.c'], '\tint temp, pack, flags, current_word, ret;\n',
        '\tint temp, pack, flags, current_word, soc_word, ret;\n\n\ts->soc_valid = 0;\n\ts->soc_percent = -1;\n')
    text['samurai-mp2650.c'] = changed(text['samurai-mp2650.c'],
        '\tret = sm_gauge_mac_locked(g, 0x0071, packet);\n\tif (ret) goto out;\n',
        '\tret = sm_gauge_mac_locked(g, 0x0071, packet);\n\tif (ret) goto out;\n'
        '\t/* OEM reg_soc and the installed bq28z610 map both use 0x2c, in\n'
        '\t * percent. Optional failure/out-of-range is unknown, not 0 or a\n'
        '\t * cached permit; the existing mandatory safety reads stay fatal.\n'
        '\t */\n\tsoc_word = sm_gauge_word_locked(g, 0x2c, false, 0);\n'
        '\tif (soc_word >= 0 && soc_word <= 100) {\n\t\ts->soc_valid = 1;\n\t\ts->soc_percent = soc_word;\n\t}\n')
    text['samurai-mp2650.c'] = changed(text['samurai-mp2650.c'],
        '\tint ret, validation, source, thermal_hold = 0;\n\tbool healthy_full;\n',
        '\tint ret, validation, source, thermal_hold = 0;\n'
        '\tint previous_band = c->thermal.initialized ? c->thermal.band : SM_POLICY_STATIC_BAND;\n'
        '\tbool healthy_full, was_full_holding = c->full_holding;\n')
    text['samurai-mp2650.c'] = changed(text['samurai-mp2650.c'],
        '\t\t.policy_band = c->thermal.initialized ? c->thermal.band : SM_POLICY_STATIC_BAND,\n',
        '\t\t.policy_band = c->thermal.initialized ? c->thermal.band : SM_POLICY_STATIC_BAND,\n'
        '\t\t.previous_policy_band = previous_band,\n'
        '\t\t.policy_band_changed = c->thermal.initialized && previous_band != c->thermal.band,\n'
        '\t\t.was_full_holding = was_full_holding,\n'
        '\t\t.soc_valid = c->sample.soc_valid,\n\t\t.soc_percent = c->sample.soc_percent,\n')
    text['samurai-mp2650.c'] = changed(text['samurai-mp2650.c'],
        '\tsm_reattach_source(&c->reattach, now, source);\n',
        '\tsm_reattach_source(&c->reattach, now, source);\n'
        '\t/* full_holding records the last successful transaction and may\n'
        '\t * survive a suspend stop. Confirm current converter hold only on\n'
        '\t * an otherwise eligible thermal/SOC edge; never infer it from UI.\n'
        '\t */\n'
        '\tif (c->auto_requested && was_full_holding && c->full_state.full &&\n'
        '\t    !c->latched && !validation && c->sample.soc_valid &&\n'
        '\t    c->sample.soc_percent >= 0 && c->sample.soc_percent < 100 &&\n'
        '\t    (previous_band == 0 || previous_band == 5) &&\n'
        '\t    c->thermal.initialized && previous_band != c->thermal.band) {\n'
        '\t\tint hold_status = sm_read(c, 0x08);\n'
        '\t\tif (hold_status < 0) {\n'
        '\t\t\tret = validation = hold_status;\n'
        '\t\t\treason = SM_POLICY_REASON_NONE;\n'
        '\t\t} else {\n'
        '\t\t\twas_full_holding = !(hold_status & 0x18);\n'
        '\t\t}\n\t}\n')
    text['oem-full-cycle.h'] = changed(text['oem-full-cycle.h'],
        '\tint policy_band_valid, policy_band;\n',
        '\tint policy_band_valid, policy_band;\n'
        '\t/* The actual current thermal edge, not a retained Full counter band. */\n'
        '\tint policy_band_changed, previous_policy_band, was_full_holding;\n'
        '\tint soc_valid, soc_percent;\n')
    text['oem-full-cycle.h'] = changed(text['oem-full-cycle.h'],
        '\t/* A fresh hardware termination is already an actual completion event,\n',
        '\t/* OEM check_tbatt_is_good clears only the FULL voter when leaving\n'
        '\t * COLD/WARM with soc != 100, batt_full and charging_state==FULL.\n'
        '\t * Require the actual current edge, previous successful Full hold\n'
        '\t * and fresh in-range SOC. All policy/fault/TCA/clock gates above\n'
        '\t * still win; INHIBIT/unknown observations cannot defer a permit.\n'
        '\t */\n'
        '\tif (s->full && in->was_full_holding && in->policy_band_valid &&\n'
        '\t    in->policy_band_changed && in->previous_policy_band != band &&\n'
        '\t    (in->previous_policy_band == 0 || in->previous_policy_band == 5) &&\n'
        '\t    in->soc_valid && in->soc_percent >= 0 && in->soc_percent < 100 &&\n'
        '\t    !in->recharge_forbidden) {\n'
        '\t\ts->full = 0; s->cause = SM_FULL_NONE;\n'
        '\t\tsm_oem_full_clear_streak(s);\n'
        '\t\ts->last_tick_ns = now; s->have_tick = 1;\n'
        '\t\tout.full = 0; out.hold_charge_only = 0;\n'
        '\t\tout.recharge = 1; out.cause = SM_FULL_NONE;\n'
        '\t\treturn out;\n\t}\n'
        '\t/* A fresh hardware termination is already an actual completion event,\n')
    patch = ''
    rows = {}
    for name, new in text.items():
        raw = new.encode(); path = HERE / name
        with path.open('xb') as stream: stream.write(raw)
        old = original[name].decode().replace('\r\n', '\n')
        patch += ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                         fromfile='a/' + name, tofile='b/' + name))
        rows[name] = {'base_sha256': sha(original[name]), 'candidate_sha256': sha(raw),
                      'base_path': str(BASE / name if name == 'samurai-mp2650.c' else R8 / name)}
    (HERE / 'thermal-full-soc-exit.patch').write_bytes(patch.encode())
    (HERE / 'source-reuse.json').write_text(json.dumps({'source_only': True, 'bases': rows,
        'kernel_built': False, 'device_accessed': False,
        'unchanged': ['all policy and hardware transaction functions', 'reattach 250ms/3s helper and poll wiring',
                      '5s Full/recharge cadence', '36000s timeout and existing latch priorities', 'thermal band algorithm',
                      'mandatory gauge/current/MAC failures', 'manual INHIBIT skip']}, indent=2) + '\n')
    print(json.dumps({'prepared': True, 'kernel_built': False, 'device_accessed': False}))


if __name__ == '__main__': main()
