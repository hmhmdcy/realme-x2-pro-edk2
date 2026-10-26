"""Saved once-capture addendum only. Never query/rearm, reinterpret runtime or classify bits."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, stat, subprocess, sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'protection-evidence-parser-candidate'
PARSER_SHA = '2ee04828775c330bfdafdca47e945645708f90e581c8939cd5932d6f8f1dc5b8'
OLD_DECODER_SHA = '58aa5dcc9c15c571310d531d0b530ea024855b18fbcf95af6bb391d6d97e10f2'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def need(ok, message):
    if not ok: raise ValueError(message)

def ordinary(path, limit):
    path = Path(path).resolve()
    need(not any(path.is_relative_to(Path(base)) for base in ('/sys', '/proc', '/dev')), 'saved ordinary files only')
    info = path.stat(); need(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'bounded saved file')
    raw = path.read_bytes(); need(len(raw) <= limit, 'saved file grew beyond bound'); return raw

def parser_module():
    path = OLD / 'parse-evidence.py'
    need(sha(path.read_bytes()) == PARSER_SHA, 'frozen R1 parser differs')
    spec = importlib.util.spec_from_file_location('r2_actual_saved_parser', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def analyze_saved(report, original_analysis, old_decoder, diagnostic_decoder, diagnostic_sha):
    need(sha(Path(diagnostic_decoder).read_bytes()) == diagnostic_sha, 'R2 diagnostic executable differs')
    parsed = parser_module().parse_saved(report, old_decoder, OLD_DECODER_SHA)
    original = json.loads(original_analysis)
    need(original['parsed'] == parsed and original['source_authenticated'] is True and original['batch_time_bound'] is True and
         original['compatibility_verified'] is False and original['TCA_classification'] == 'UNVERIFIED', 'original source-bound analysis differs')
    h, f = parsed['header'], parsed['frames'][7]
    need(parsed['frames'][0]['decoded']['value'] == 0x2719 and h['attempted'] == h['terminal'] == 1 and
         h['stage'] == 4 and h['error'] == -90 and h['frames_attempted'] == 8 and
         h['battery_before_valid'] == 1 and h['battery_after_valid'] == 0, 'original failed once-batch facts differ')
    need(f['cmd'] == 0x0056 and f['full_read'] == 1 and f['read_rc'] == 2 and f['expected_size'] == 4 and
         f['validate_rc'] == -90 and f['raw'] != 'unavailable', 'original full0056/size4 failure required')
    run = subprocess.run([str(diagnostic_decoder), f['raw']], capture_output=True, check=False)
    need(run.returncode == 0 and not run.stderr, 'R2 saved-frame decoder failed')
    decoded = json.loads(run.stdout)
    need(decoded['legacy_payload4_validate_rc'] == -90 and decoded['observed_2719_payload3_validate_rc'] == 0 and
         decoded['length_byte'] == 7, 'saved0056 is not the observed length7 profile')
    return {'schema': 'samurai-saved-2719-0056-length-addendum-v1',
        'report_sha256': sha(report), 'original_analysis_sha256': sha(original_analysis),
        'original_parser_sha256': PARSER_SHA, 'original_decoder_sha256': OLD_DECODER_SHA,
        'diagnostic_decoder_sha256': diagnostic_sha, 'frame_sha256': sha(bytes.fromhex(f['raw'])),
        'original_expected_payload_bytes': 4, 'original_validate_rc': -90,
        'original_batch_stage': 4, 'original_batch_error': -90, 'original_sequence_complete': parsed['sequence_complete'],
        'observed_payload_bytes': 3, 'observed_length_byte': 7, 'observed_frame_valid': True,
        'raw_payload_hex': bytes.fromhex(f['raw'])[2:5].hex(), 'raw_value_u24': decoded['raw_value_u24'],
        'fourth_payload_byte_present_in_logical_length': False,
        'official_standard_profile_conflict': 'SLUUA65E12.2.32 describes a reserved fourth byte; this saved2719 response length is7, hence3 payload bytes',
        'original_source_authentication_claim_retained': True, 'source_authentication_newly_verified': False,
        'battery_after_read': False, 'stability_verified': False, 'batch_sequence_complete': False,
        'compatibility_verified': False, 'TCA_classification': 'UNVERIFIED', 'charge_or_recharge_authorized': False,
        'runtime_report_modified': False, 'new_query_or_rearm_authorized': False, 'device_accessed': False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'original-analysis', 'old-decoder', 'diagnostic-decoder', 'diagnostic-sha256'):
        p.add_argument('--' + name)
    p.add_argument('--analyze-saved', action='store_true'); args = p.parse_args()
    if not args.analyze_saved:
        parser_module(); print(json.dumps({'source_only': True, 'device_accessed': False, 'query_or_runtime_report_created': False})); return
    result = analyze_saved(ordinary(args.input, 4095), ordinary(args.original_analysis, 200000),
                           Path(args.old_decoder), Path(args.diagnostic_decoder), args.diagnostic_sha256)
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
