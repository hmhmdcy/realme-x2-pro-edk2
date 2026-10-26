"""Compare downloaded public Android configurations, without deploying them."""
from pathlib import Path
import difflib, hashlib, json, re

here = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel205/gnss-related-sources')
def active(path):
    result = {}
    # These Android source files contain a legacy smart-quote byte in comments.
    for line in path.read_text(encoding='cp1252').splitlines():
        match = re.match(r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*([^#]*?)\s*(?:#.*)?$', line)
        if match:
            assert match[1] not in result
            result[match[1]] = match[2]
    return result

a = private / 'HyperTeam-configs__gps.conf'
b = private / 'LineageOS-configs__gps.conf'
aa, bb = active(a), active(b)
differences = {key: dict(samurai=aa.get(key), oneplus=bb.get(key)) for key in sorted(aa.keys() | bb.keys()) if aa.get(key) != bb.get(key)}
assert differences == {'LPP_PROFILE': {'samurai': '2', 'oneplus': '3'}}
(private / 'samurai-oneplus-gps-conf.diff').write_text(''.join(difflib.unified_diff(a.read_text(encoding='cp1252').splitlines(True), b.read_text(encoding='cp1252').splitlines(True), fromfile='samurai-gps.conf', tofile='oneplus-gps.conf')))
patcher = (private / 'rapperskull-src__gnss_patcher.c').read_text()
assert 'gnss_old_data[GNSS_ENTRY_DATA_LEN] = {0x07, 0x00, 0x00, 0x00, 0x00}' in patcher
assert 'gnss_new_data[GNSS_ENTRY_DATA_LEN] = {0x07, 0x27, 0x00, 0x00, 0x00}' in patcher
result = dict(stage=205, public_sources_only=True, handset_modified=False, active_key_count=len(aa), active_key_differences=differences, samurai_sha256=hashlib.sha256(a.read_bytes()).hexdigest(), oneplus_sha256=hashlib.sha256(b.read_bytes()).hexdigest(), l5_patcher_changes_second_multiband_byte=True, l5_patcher_executed=False, lpp_difference_not_established_as_handset_root_cause=True, github_api_403_receipts_retained=True, source_snapshots_obtained_using_public_git=True)
(here / 'gnss-config-comparison-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
