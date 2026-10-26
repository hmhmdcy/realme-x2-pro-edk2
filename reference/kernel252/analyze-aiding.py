#!/usr/bin/env python3
"""Reproduce sanitized before/after aiding summaries from a private export."""
import argparse
import importlib.util
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('private_export', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('decoder',
        Path(__file__).resolve().parents[1] / 'kernel250/decode-android-hal.py')
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    trace = args.private_export / 'hal.trace'
    packets, parsing = decoder.parse_trace(trace)
    full = decoder.summarize(packets, parsing)
    fds = full['loc_socket_fds']
    text = trace.read_text()
    if any(re.search(r'close\(' + str(fd) + r'(?:<[^\n]*>)?\)\s+=\s+0', text) for fd in fds):
        raise ValueError('LOC fd closed; re-identify each socket before phase splitting')
    cut = int((args.private_export / 'refresh-start-epoch.txt').read_text())
    phases = {}
    for name, subset in [('baseline', [p for p in packets if p['time'] < cut]),
                         ('after_refresh_request', [p for p in packets if p['time'] >= cut])]:
        result = decoder.summarize(subset, {}, fds)
        if result['quality']['decode_errors'] or result['measurements']['errors']:
            raise ValueError('Decoder rejected phase data')
        phases[name] = result
    args.output.write_text(json.dumps(dict(parsing=parsing, phases=phases), indent=2) + '\n')
    print(json.dumps({name: dict(sv_reports=r['quality']['sv']['ordinary_reports'],
        successful_positions=r['quality']['successful_qmi_positions_with_valid_coordinates'])
        for name, r in phases.items()}))


if __name__ == '__main__':
    main()
