#!/usr/bin/env python3
"""Manual bounded EUD session: one USB owner, native frames, target-only IN evidence.

No reset, setup opcode, automatic driver detach, reconfiguration or data retry.
u submits one Ctrl-U; send COMMAND submits native ASCII input; drain waits for
quiet; x closes. A missing data receipt stops the unsent remainder and exits.
Capture the immutable TX journal with dd/base64 through this same owner.
"""
import argparse
from contextlib import ExitStack
import datetime
import json
import os
from pathlib import Path
import select
import sys
import threading
import time

import usb
import usb.core
import usb.util

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=900, choices=range(30, 1201))
    args = parser.parse_args()
    paths = {ext: Path(str(args.out) + ext) for ext in ('.json', '.raw', '.txt', '.events.jsonl', '.usbmon')}
    if any(p.exists() for p in paths.values()):
        raise FileExistsError('Use a new capture prefix')
    devices = list(usb.core.find(find_all=True, idVendor=0x05c6, idProduct=0x9505))
    if len(devices) != 1:
        raise RuntimeError(f'Expected one 9505, found {len(devices)}')
    dev = devices[0]
    lock, changed = threading.RLock(), threading.Condition()
    reader_stop, monitor_stop = threading.Event(), threading.Event()
    errors, workers = [], []
    state = dict(text='', last=time.monotonic(), frames=0, stray=0, pending=0, steps=0,
                 data_frames=0, data_bytes=0, acked=0, synchronized=False)
    started = time.monotonic()
    try:
        cfg = dev.get_active_configuration()
        interfaces = list(cfg)
        if len(interfaces) != 1:
            raise RuntimeError('Expected one active interface/alternate setting')
        interface = interfaces[0].bInterfaceNumber
        if dev.is_kernel_driver_active(interface):
            raise RuntimeError('Kernel driver owns interface; no automatic detach')
        bulk = [e for e in interfaces[0] if usb.util.endpoint_type(e.bmAttributes) == 2]
        ins = [e for e in bulk if e.bEndpointAddress & 0x80]
        outs = [e for e in bulk if not e.bEndpointAddress & 0x80]
        if len(ins) != 1 or len(outs) != 1 or ins[0].wMaxPacketSize != 16 or outs[0].wMaxPacketSize != 16:
            raise RuntimeError('Inspect unexpected bulk endpoints before proceeding')
        epin, epout = ins[0].bEndpointAddress, outs[0].bEndpointAddress
        meta = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    bus=dev.bus, address=dev.address, vid=dev.idVendor, pid=dev.idProduct,
                    configuration=cfg.bConfigurationValue, interface=interface,
                    endpoints=[dict(address=e.bEndpointAddress, attributes=e.bmAttributes,
                                    max_packet=e.wMaxPacketSize) for e in interfaces[0]],
                    read_size=16, read_timeout_ms=20, data_ack_timeout_ms=4000,
                    data_gap_ms=250, pyusb_version=usb.__version__, max_manual_steps=12,
                    seconds_limit=args.seconds, automatic_data_retries=False,
                    transport='PyUSB/libusb -> WSL vhci -> usbipd -> Windows USB; qcusbser bypassed')
        paths['.json'].write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(meta), flush=True)
        with ExitStack() as stack:
            mon = stack.enter_context(open('/sys/kernel/debug/usb/usbmon/0u', 'rb', buffering=0))
            os.set_blocking(mon.fileno(), False)
            raw = stack.enter_context(paths['.raw'].open('xb'))
            text = stack.enter_context(paths['.txt'].open('x', encoding='utf-8'))
            events = stack.enter_context(paths['.events.jsonl'].open('x', encoding='utf-8'))
            trace = stack.enter_context(paths['.usbmon'].open('xb'))

            def event(kind, **fields):
                row = dict(ms=round((time.monotonic() - started) * 1000, 3), event=kind, **fields)
                with lock:
                    events.write(json.dumps(row) + '\n')
                    events.flush()
                if kind != 'in':
                    print('\n[host] ' + json.dumps(row), flush=True)

            def failed(where, error):
                with changed:
                    errors.append((where, repr(error)))
                    changed.notify_all()

            def capture():
                pending = b''
                try:
                    while not monitor_stop.is_set():
                        if not select.select([mon], [], [], 0.025)[0]:
                            continue
                        try:
                            block = os.read(mon.fileno(), 65536)
                        except BlockingIOError:
                            continue
                        if not block:
                            break
                        pending += block
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            fields = line.split()
                            address = fields[3].split(b':') if len(fields) >= 4 else []
                            if len(address) == 4 and (int(address[1]), int(address[2])) == (dev.bus, dev.address):
                                trace.write(line + b'\n')
                                trace.flush()
                    if pending:
                        event('monitor_partial_line', bytes=len(pending))
                except Exception as error:
                    failed('usbmon', error)

            def read():
                pending = bytearray()
                try:
                    while not reader_stop.is_set():
                        try:
                            data = bytes(dev.read(epin, 16, timeout=20))
                        except usb.core.USBTimeoutError:
                            continue  # Installed libusb1 backend returns timeout partial bytes.
                        if not data:
                            continue
                        raw.write(data)
                        raw.flush()
                        event('in', length=len(data), hex=data.hex(' '))
                        pending.extend(data)
                        while len(pending) >= 2:
                            n = pending[1]
                            if pending[0] != 0x90 or not 1 <= n <= 64:
                                del pending[0]
                                state['stray'] += 1
                                continue
                            if len(pending) < n + 2:
                                break
                            part = bytes(pending[2:n + 2]).decode('ascii', errors='replace')
                            del pending[:n + 2]
                            text.write(part)
                            text.flush()
                            with changed:
                                state['frames'] += 1
                                state['text'] += part
                                state['last'] = time.monotonic()
                                changed.notify_all()
                            print(part, end='', flush=True)
                        state['pending'] = len(pending)
                except Exception as error:
                    failed('reader', error)

            def close_owner():
                reader_stop.set()
                if len(workers) > 1 and workers[1].ident is not None:
                    workers[1].join(timeout=1)
                # Keep the monitor alive for disposal/cancel events, then drain.
                try:
                    usb.util.dispose_resources(dev)
                    time.sleep(0.1)
                finally:
                    monitor_stop.set()
                    for worker in workers:
                        if worker.ident is not None:
                            worker.join(timeout=1)
                event('closed', **{k: v for k, v in state.items() if k not in ('text', 'last')},
                      worker_alive=[w.name for w in workers if w.is_alive()], errors=errors)
                if any(w.is_alive() for w in workers):
                    raise RuntimeError('USB capture worker did not close')

            workers.append(threading.Thread(target=capture, name='target-usbmon'))
            workers[0].start()
            stack.callback(close_owner)
            usb.util.claim_interface(dev, interface)
            event('claimed')
            workers.append(threading.Thread(target=read, name='bulk-in-reader'))
            workers[1].start()

            def send(payload, sync=False):
                n = len(payload)
                if n not in (1, *range(3, 15)):
                    raise ValueError('LEN2 is reserved for F1; no two-byte tty frame')
                with changed:
                    boundary = len(state['text'])
                wire = bytes([0x90, n]) + payload
                event('out_submit', hex=wire.hex(' '), payload_hex=payload.hex(' '), length=n, sync=sync, attempt=1)
                actual = dev.write(epout, wire, timeout=500)
                event('out_complete', length=actual)
                if actual != len(wire):
                    raise RuntimeError('Short bulk OUT; do not retry')
                if not sync:
                    state['data_frames'] += 1
                    state['data_bytes'] += n
                ack = f'tty byte={payload[0]:02x}' if n == 1 else f'len={n} data={payload.hex(" ")} s1_after='
                deadline = time.monotonic() + 4
                with changed:
                    while ack not in state['text'][boundary:]:
                        if errors:
                            raise RuntimeError(errors)
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            event('receipt_timeout', length=n, payload_hex=payload.hex(' '), sync=sync)
                            return False
                        changed.wait(timeout=min(remaining, .1))
                event('receipt', length=n, payload_hex=payload.hex(' '), sync=sync)
                if not sync:
                    state['acked'] += 1
                time.sleep(.25)
                return True

            print('\nCOMMAND> u | send COMMAND | drain | x; one owner, no automatic retries', flush=True)
            while time.monotonic() - started < args.seconds and state['steps'] < 12:
                if errors:
                    raise RuntimeError(errors)
                if not select.select([sys.stdin], [], [], .1)[0]:
                    continue
                line = sys.stdin.readline()
                if not line or line.rstrip('\r\n') == 'x':
                    break
                line = line.rstrip('\r\n')
                if line == 'u':
                    state['steps'] += 1
                    state['synchronized'] = send(b'\x15', sync=True)
                elif line.startswith('send '):
                    if not state['synchronized']:
                        raise RuntimeError('Fresh Ctrl-U receipt required before command input')
                    payload = (line[5:] + '\n').encode('ascii')
                    if len(payload) > 512:
                        raise ValueError('Manual diagnostic command limit is 512 ASCII bytes')
                    state['steps'] += 1
                    event('command', text=line[5:], bytes=len(payload))
                    while payload:
                        n = min(14, len(payload))
                        if n == 2:
                            n = 1
                        if not send(payload[:n]):
                            raise RuntimeError('Missing data receipt; unsent remainder stopped, no retry')
                        payload = payload[n:]
                elif line == 'drain':
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        if errors:
                            raise RuntimeError(errors)
                        if time.monotonic() - state['last'] >= 2:
                            break
                        time.sleep(.05)
                    event('drained')
                else:
                    print('Use u, send COMMAND, drain, or x.', flush=True)
                print('\nCOMMAND>', flush=True)
    finally:
        reader_stop.set()
        monitor_stop.set()
        try:
            for worker in workers:
                if worker.ident is not None:
                    worker.join(timeout=1)
        finally:
            usb.util.dispose_resources(dev)
            print('\nUSB resources disposed.', flush=True)

if __name__ == '__main__':
    main()
