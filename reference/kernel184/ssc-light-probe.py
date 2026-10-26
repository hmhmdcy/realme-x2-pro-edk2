#!/usr/bin/env python3
"""Bounded SSC light probe with standard/vendor lookup and explicit stream cleanup.

Wire definitions: libssc 0.4.4 SscLightResponse and SscClientRequest. All frames,
including unknown event IDs, are retained privately. Calibration events are
never counted as light measurements.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import struct
import time


def load_wire(path):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != '7618fe7e4f54b6ce8e9b9437961afc245d7c35b856b0d09e785a391958ad2656':
        raise ValueError('unexpected SSC wire helper')
    spec = importlib.util.spec_from_file_location('ssc_wire', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sensor_request(wire, transaction, uid, message, payload=b''):
    body = (wire.bytes_field(1, wire.uid_bytes(uid)) + wire.fixed32(2, message) +
            wire.bytes_field(3, wire.uint(1, 1) + wire.uint(2, 0)) +
            wire.bytes_field(4, wire.bytes_field(2, payload)))
    value = struct.pack('<H', len(body)) + body
    tlvs = b'\x10\x01\x00\x01' + b'\x01' + struct.pack('<H', len(value)) + value
    return struct.pack('<BHHH', 0, transaction, 32, len(tlvs)) + tlvs


def light_sample(wire, payload):
    fields = wire.protobuf(payload)
    status = wire.unique(fields, 2, int, 0)
    if not 0 <= status <= 3:
        raise ValueError('invalid light accuracy')
    values = []
    for value, kind in zip(fields.get(1, []), fields.wires.get(1, [])):
        if kind == 5:
            values.append(struct.unpack('<f', struct.pack('<I', value))[0])
        elif kind == 2 and len(value) % 4 == 0:
            values.extend(struct.unpack('<' + 'f' * (len(value) // 4), value))
        else:
            raise ValueError('invalid light float encoding')
    if not 1 <= len(values) <= 16 or any(not math.isfinite(v) for v in values) or values[0] < 0:
        raise ValueError('invalid light measurement')
    return {'lux': values[0], 'values': values, 'accuracy': status}


def attribute_scalar(wire, payload, wanted):
    fields = wire.protobuf(payload)
    for raw in fields.get(1, []):
        item = wire.protobuf(raw)
        if wire.unique(item, 1, int, 0) != wanted:
            continue
        values = wire.protobuf(wire.unique(item, 2, bytes, 2)).get(1, [])
        if len(values) != 1:
            raise ValueError('expected scalar sensor attribute')
        return wire.protobuf(values[0])
    raise ValueError('missing sensor attribute')


def run(args):
    wire = load_wire(args.wire)
    os.umask(0o077)
    out = Path(args.output)
    out.mkdir(mode=0o700)
    endpoint, listing = wire.locate_service()
    (out / 'qrtr-private.txt').write_text(listing)
    start = time.monotonic()
    events = collections.Counter()
    catalog = {}
    operations = {}
    attributes = {}
    samples = []
    malformed = []
    selected = None
    enable_sent = False
    disabled = False
    summary = {}
    with socket.socket(socket.AF_QIPCRTR, socket.SOCK_DGRAM) as sock, (out / 'frames-private.jsonl').open('x') as trace:
        sock.bind((sock.getsockname()[0], 0))
        sock.connect(endpoint)
        sock.settimeout(.2)

        def send(raw):
            sock.send(raw)
            trace.write(json.dumps({'direction': 'tx', 'elapsed': time.monotonic() - start, 'hex': raw.hex()}) + '\n')
            trace.flush()

        def receive(seconds):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    raw, _, flags, _ = sock.recvmsg(65536)
                except socket.timeout:
                    continue
                if flags & socket.MSG_TRUNC:
                    raise ValueError('truncated QRTR datagram')
                row = {'direction': 'rx', 'elapsed': time.monotonic() - start, 'hex': raw.hex()}
                try:
                    decoded = wire.decode_frame(raw)
                    row['decoded'] = decoded
                    if 'operation_result' in decoded:
                        transaction = decoded['transaction']
                        if transaction in operations:
                            raise ValueError('duplicate QMI operation acknowledgement')
                        operations[transaction] = (decoded['operation_result'], decoded['operation_error'])
                    for event in decoded['events']:
                        events[str(event['message_id'])] += 1
                        if 'suids' in event:
                            catalog[event['data_type']] = [tuple(u) for u in event['suids']]
                        elif selected and tuple(decoded['sensor_uid']) == selected:
                            if event['message_id'] == 128:
                                attributes.update({'raw': event['payload_hex']})
                            elif event['message_id'] == 1025:
                                sample = light_sample(wire, bytes.fromhex(event['payload_hex']))
                                sample.update(timestamp=event['timestamp'], elapsed=time.monotonic() - start)
                                samples.append(sample)
                except (ValueError, UnicodeDecodeError, struct.error) as error:
                    row['decode_error'] = str(error)
                    malformed.append(str(error))
                trace.write(json.dumps(row) + '\n')
                trace.flush()

        try:
            for txn, name in enumerate(['ambient_light', 'wise_light'], 1):
                send(wire.request(txn, name, False, updates=False))
            receive(4)
            kind = 'ambient_light' if catalog.get('ambient_light') else 'wise_light'
            candidates = catalog.get(kind, [])
            if len(candidates) != 1 or operations.get(1) != (0, 0) or operations.get(2) != (0, 0):
                raise ValueError('light lookup did not identify one unambiguous sensor')
            selected = candidates[0]
            send(sensor_request(wire, 3, selected, 1, wire.uint(2, 0)))
            receive(3)
            payload = bytes.fromhex(attributes['raw'])
            available = wire.unique(attribute_scalar(wire, payload, 3), 5, int, 0)
            physical = wire.unique(attribute_scalar(wire, payload, 21), 5, int, 0)
            stream_type = wire.unique(attribute_scalar(wire, payload, 16), 4, int, 1)
            if available != 1 or physical != 1 or stream_type not in (0, 1):
                raise ValueError('light sensor is unavailable or has unsupported attributes')
            if operations.get(3) != (0, 0):
                raise ValueError('attribute request failed')
            payload = b'\x0d' + struct.pack('<f', 5.0) if stream_type == 0 else b''
            send(sensor_request(wire, 4, selected, 513 if stream_type == 0 else 514, payload))
            enable_sent = True
            receive(args.duration)
            summary.update(selected_type=kind, stream_type=stream_type, sensor_available=True, physical_sensor=True)
        finally:
            if selected and enable_sent:
                send(sensor_request(wire, 5, selected, 10))
                receive(3)
                disabled = operations.get(5) == (0, 0)
            (out / 'samples-private.json').write_text(json.dumps(samples, indent=2) + '\n')
            (out / 'catalog-private.json').write_text(json.dumps(catalog, indent=2) + '\n')
            summary.update(
                lookup_counts={name: len(values) for name, values in catalog.items()},
                operations=operations, events=dict(events), malformed_frames=len(malformed),
                samples=len(samples), reliable_samples=sum(s['accuracy'] > 0 for s in samples),
                unique_lux_values=len(set(s['lux'] for s in samples)),
                minimum_lux=min((s['lux'] for s in samples), default=None),
                maximum_lux=max((s['lux'] for s in samples), default=None),
                disable_ack=disabled, duration_seconds=round(time.monotonic() - start, 3),
                success=bool(samples) and disabled and not malformed and operations.get(4) == (0, 0))
            (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
            print(json.dumps(summary))
    return 0 if summary['success'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--wire', default='/var/lib/samurai/k113-tools/ssc-suid-census.py')
    parser.add_argument('--duration', type=float, default=20)
    args = parser.parse_args()
    if not 5 <= args.duration <= 40:
        parser.error('duration must be 5..40 seconds')
    raise SystemExit(run(args))
