"""Verify actual read-only ODM configuration against locked public sources."""
from pathlib import Path
import hashlib
import json

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out')
actual = (P / 'kernel239/odm-source-private/payload/etc/gps.conf').read_bytes()
community = (P / 'kernel205/gnss-related-sources/HyperTeam-configs__gps.conf').read_bytes()
aosp = (P / 'kernel206/hal-sources/etc__gps.conf').read_bytes()
locked = json.loads((R.parent / 'kernel205/gnss-related-source-validation.json').read_text())
expected = next(item for item in locked['repositories'] if item['repo'] == 'HyperTeam/android_device_realme_samurai')
assert hashlib.sha256(community).hexdigest() == expected['files']['configs/gps.conf']['sha256']
aosp_lock = json.loads((R.parent / 'kernel206/gnss-hal-source-validation.json').read_text())
assert hashlib.sha256(aosp).hexdigest() == aosp_lock['files']['etc/gps.conf']['sha256']
assert actual == community


def parse(data):
    result = {}
    for line in data.decode('cp1252').splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        assert '=' in line
        key, value = [part.strip() for part in line.split('=', 1)]
        assert key not in result
        result[key] = value
    return result


source, reference = parse(actual), parse(aosp)


def numeric(value):
    if value is None:
        return False
    try:
        int(value, 0)
        return True
    except ValueError:
        return False


differences = {key: {'actual_odm': source.get(key), 'aosp_reference': reference.get(key)}
               for key in sorted(set(source) | set(reference))
               if source.get(key) != reference.get(key)
               and (numeric(source.get(key)) or numeric(reference.get(key)))}
assert len(source) == 39 and sum(numeric(v) for v in source.values()) == 34
assert set(differences) == {'DEBUG_LEVEL', 'XTRA_VERSION_CHECK', 'NMEA_TAG_BLOCK_GROUPING_ENABLED'} | {
    key for key in reference if key.startswith('RF_LOSS_')}
assert sum(key.startswith('RF_LOSS_') for key in differences) == 10
report = dict(stage=239, actual_current_odm_gps_conf_equals_locked_community_bytes=True,
              enabled_keys=39, numeric_keys=34, numeric_differences_from_aosp= differences,
              source_file_presence_not_proof_of_hal_adoption=True,
              modem_runtime_configuration_not_measured=True,
              no_private_build_properties_or_fingerprints_published=True,
              no_phone_operation_or_gnss_set=True)
(R / 'odm-gps-comparison-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
