#!/usr/bin/env python3
"""Validate saved read-only PGA EFS probes; never contacts a device.

The input directory contains private DIAG captures. Only file-existence metadata,
source hashes and decoder quality are emitted. No file contents are requested.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_directory', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    private = args.private_directory
    spec = importlib.util.spec_from_file_location(
        'diag', Path(__file__).resolve().parents[1] / 'kernel252/decode-diag-trace.py')
    diag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diag)
    original = (private.parent / 'kernel252/diag-mask-original-private.bin').read_bytes()
    assert len(original) == 413 and not any(original)
    results = []
    for filename in ['efs-stat-export-private.json', 'efs-stat-cgps-export-private.json']:
        captures = json.loads((private / filename).read_text())
        assert len(captures) == 4
        for capture in captures:
            requests = [bytes.fromhex(s) for s in capture['request_payloads_hex']]
            assert len(requests) == 3
            assert requests[0] == struct.pack('<III', 0x73, 4, 1)
            assert requests[1] == struct.pack(
                '<BBH10I', 0x4b, 19, 0, *([0x100000] * 6 + [1, 1, 1, 0xffffffff]))
            assert requests[2] == b'\x4b\x13\x0f\x00' + capture['path'].encode() + b'\x00'
            trace = None
            for file in capture['files']:
                source = private / file['name']
                raw = source.read_bytes()
                assert len(raw) == file['bytes']
                assert hashlib.sha256(raw).hexdigest() == file['sha256']
                if source.suffix == '.trace':
                    trace = source
            assert trace
            frames, logs, quality = diag.decode(trace)
            assert not quality['read_errors'] and not quality['invalid_crc_frames']
            assert not quality['trailing_partial_bytes']
            payloads = [bytes.fromhex(f['payload_hex']) for f in frames]
            masks = [b for b in payloads if b[:8] == struct.pack('<II', 0x73, 4)]
            assert len(masks) == 1
            assert struct.unpack_from('<III', masks[0], 8) == (0, 1, 3304)
            assert masks[0][20:] == original
            stat = [b for b in payloads if b[:4] == b'\x4b\x13\x0f\x00']
            assert len(stat) == 1 and len(stat[0]) == 32
            error, mode, size = struct.unpack_from('<III', stat[0], 4)
            hello = [b for b in payloads if b[:4] == b'\x4b\x13\x00\x00']
            assert len(hello) == 1 and len(hello[0]) == 44
            assert struct.unpack_from('<I', hello[0], 28)[0] == 1
            results.append(dict(path=capture['path'], errno=error,
                exists=error == 0, mode_octal=oct(mode) if error == 0 else None,
                size_or_directory_entries=size if error == 0 else None,
                trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
                source_export_hashes_verified=True, hello_version_1=True,
                diag_get_log_mask_matches_original=True, decode=quality))
    # A successful exact parent query prevents confusing a missing parent with
    # three absent files. ENOENT alone still says nothing about firmware defaults.
    parent = next(r for r in results if r['path'] == '/nv/item_files/gps/cgps/me')
    assert parent['exists'] and parent['mode_octal'] == '0o40777'
    names = ['gnss_apq_pga_cal', 'gnss_dynamic_pga_config', 'gnss_pga_backoff_config']
    targets = [r for r in results if r['path'].startswith('/nv/item_files/gps/cgps/me/')]
    assert len(targets) == 3
    assert {r['path'].rsplit('/', 1)[1] for r in targets} == set(names)
    scan = json.loads((private / 'modem-pga-string-scan-validation.json').read_text())
    out = dict(stage=255, firmware_scan=scan, pga_candidate_names=names,
        operations_only_log_mask_get_efs_hello_stat=True,
        no_nv_open_read_write_create_or_unlock=True,
        candidate_parent_directory_exists=True, queries=results,
        all_three_cgps_targets_enoent=all(r['errno'] == 2 for r in targets),
        absence_does_not_prove_missing_required_calibration_or_default_values=True,
        no_linux_live_efs_comparison_this_stage=True,
        no_mpss_execution_trace_of_pga_configuration_read=True)
    args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'queries'}, indent=2))


if __name__ == '__main__':
    main()
