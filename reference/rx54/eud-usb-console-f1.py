#!/usr/bin/env python3
"""Manual bounded EUD session: one USB owner, native frames, target-only IN evidence.

No reset, setup opcode, automatic driver detach, reconfiguration or data retry.
u submits one Ctrl-U; send COMMAND submits native ASCII input; drain waits for
quiet; x closes. A missing data receipt stops the unsent remainder and exits.
Capture the immutable TX journal with dd/base64 through this same owner.
overlap manually triggers one unchanged RX51 kmsg record and one F1 header.
A single F1 [90 02] is submitted during that record, never as tty LEN2.
Only an overlap-probe timeout keeps capture open with sending disabled; a new
manual u receipt is required before any later command. No probe/data retries.
"""
import argparse
from contextlib import ExitStack
import datetime
from hashlib import sha256
import json
import os
import re
import queue
from pathlib import Path
import select
import sys
import threading
import time

import usb
import usb.backend.libusb1
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
    reader_stop, monitor_stop, sink_stop = threading.Event(), threading.Event(), threading.Event()
    incoming = queue.Queue()
    errors, workers = [], []
    state = dict(text='', last=time.monotonic(), frames=0, stray=0, pending=0, steps=0,
                 data_frames=0, data_bytes=0, acked=0, synchronized=False,
                 overlap_used=False, overlap_armed=False, overlap_boundary=0,
                 overlap_marker_at=None, overlap_end_at=None, overlap_receipt=None,
                 f1_submitted=False, f1_disconnect=None, f1_console_receipt=False,
                 io_reads=0, io_bytes=0, max_sink_queue=0, sink_drained=False)
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
                    helper_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
                    libusb_backend_sha256=sha256(Path(usb.backend.libusb1.__file__).read_bytes()).hexdigest(),
                    data_gap_ms=250, pyusb_version=usb.__version__, max_manual_steps=12,
                    seconds_limit=args.seconds, automatic_data_retries=False,
                    overlap_delay_ms=152, overlap_f1_hex='90 02',
                    hold_overlap_timeout_for_manual_sync=True, continuous_in_separate_sink=True,
                    transport='PyUSB/libusb -> WSL vhci -> usbipd -> Windows USB; qcusbser bypassed')
        paths['.json'].write_text(json.dumps(meta, indent=2) + '\n')
        print(json.dumps(meta), flush=True)
        with ExitStack() as stack:
            mon = stack.enter_context(open(f'/sys/kernel/debug/usb/usbmon/{dev.bus}u', 'rb', buffering=0))
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

            def sink():
                pending = bytearray()
                display_pending = ''

                def display(part):
                    nonlocal display_pending
                    display_pending += part
                    query = '\x1b[6n'
                    while display_pending:
                        escape = display_pending.find('\x1b')
                        if escape < 0:
                            print(display_pending, end='', flush=True)
                            display_pending = ''
                            return
                        if escape:
                            print(display_pending[:escape], end='', flush=True)
                            display_pending = display_pending[escape:]
                        if display_pending.startswith(query):
                            display_pending = display_pending[len(query):]
                        elif query.startswith(display_pending):
                            return  # Hold a query split across EUD frames.
                        else:
                            print(display_pending[0], end='', flush=True)
                            display_pending = display_pending[1:]

                try:
                    while not sink_stop.is_set() or not incoming.empty():
                        try:
                            received_at, data = incoming.get(timeout=.05)
                        except queue.Empty:
                            continue
                        raw.write(data)
                        raw.flush()
                        event('in', length=len(data), hex=data.hex(' '),
                              received_ms=round((received_at-started)*1000,3))
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
                                if state['overlap_armed']:
                                    segment = state['text'][state['overlap_boundary']:]
                                    if state['overlap_marker_at'] is None and re.search(r'(?m)^\[\s*\d+\.\d+\]\s*R51LOCK:', segment):
                                        state['overlap_marker_at'] = time.monotonic()
                                        event('overlap_marker', frames=state['frames'], decoded_chars=len(state['text']))
                                    if state['overlap_marker_at'] is not None and state['overlap_end_at'] is None and ':R51END\n' in segment:
                                        state['overlap_end_at'] = time.monotonic()
                                        event('overlap_end', frames=state['frames'], decoded_chars=len(state['text']))
                                changed.notify_all()
                            # Filter only display-side cursor requests. Raw/text
                            # retain them; never turn local terminal replies into
                            # unexpected diagnostic stdin input.
                            display(part)
                        state['pending'] = len(pending)
                except Exception as error:
                    failed('reader', error)

            def read():
                try:
                    while not reader_stop.is_set():
                        try:
                            data = bytes(dev.read(epin, 16, timeout=20))
                        except usb.core.USBTimeoutError:
                            continue
                        if data:
                            state['io_reads'] += 1
                            state['io_bytes'] += len(data)
                            incoming.put((time.monotonic(), data))
                            state['max_sink_queue'] = max(state['max_sink_queue'], incoming.qsize())
                except usb.core.USBError as error:
                    if state['f1_submitted'] and error.errno in (5,19):
                        with changed:
                            state['f1_disconnect'] = repr(error)
                            changed.notify_all()
                        event('disconnect_after_f1', error=repr(error), errno=error.errno)
                    else:
                        failed('io-reader', error)
                except Exception as error:
                    failed('io-reader', error)
            def close_owner():
                reader_stop.set()
                if len(workers) > 1 and workers[1].ident is not None:
                    workers[1].join(timeout=1)
                sink_stop.set()
                if len(workers) > 2 and workers[2].ident is not None:
                    workers[2].join(timeout=2)
                state['sink_drained'] = incoming.empty()
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
            workers.append(threading.Thread(target=sink, name='raw-decode-display-sink'))
            workers[2].start()

            def send(payload, sync=False, gap=True):
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
                if gap:
                    time.sleep(.25)
                return True

            print('\nCOMMAND> u | send COMMAND | overlap | drain | x; one owner, no automatic retries', flush=True)
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
                elif line == 'overlap':
                    if not state['synchronized'] or state['overlap_used']:
                        raise RuntimeError('Overlap needs fresh sync and can run only once')
                    state['steps'] += 1
                    with changed:
                        state['overlap_used'] = state['overlap_armed'] = True
                        state['overlap_boundary'] = len(state['text'])
                    command = "printf '<6>R51LOCK:%0990d:R51END\\n' 0 >/dev/kmsg"
                    payload = (command + '\n').encode('ascii')
                    event('overlap_armed', command=command, bytes=len(payload), delay_ms=152)
                    while payload:
                        n = min(14, len(payload))
                        if n == 2:
                            n = 1
                        if not send(payload[:n], gap=len(payload) > n):
                            raise RuntimeError('Trigger command has no receipt; no probe was submitted')
                        payload = payload[n:]
                    deadline = time.monotonic() + 4
                    with changed:
                        while state['overlap_marker_at'] is None:
                            if errors:
                                raise RuntimeError(errors)
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                raise RuntimeError('No complete kernel marker; overlap not measured')
                            changed.wait(timeout=min(remaining, .02))
                        marker_at = state['overlap_marker_at']
                    remaining = marker_at + .152 - time.monotonic()
                    if remaining > 0:
                        time.sleep(remaining)
                    with changed:
                        if state['overlap_end_at'] is not None:
                            raise RuntimeError('Record ended before probe; invalid overlap')
                    event('overlap_injection', marker_delta_ms=round((time.monotonic()-marker_at)*1000,3))
                    state['f1_submitted'] = True
                    event('f1_out_submit', hex='90 02', attempt=1, payload_bytes=0)
                    actual = dev.write(epout, bytes([0x90,2]), timeout=500)
                    event('f1_out_complete', length=actual)
                    if actual != 2:
                        raise RuntimeError('Short F1 OUT; do not retry')
                    deadline = time.monotonic()+12
                    with changed:
                        while not state['f1_disconnect']:
                            if errors:
                                raise RuntimeError(errors)
                            remaining = deadline-time.monotonic()
                            if remaining <= 0:
                                break
                            changed.wait(timeout=min(remaining,.1))
                        state['f1_console_receipt'] = 'eud: RX46 F1 via=console ' in state['text'][state['overlap_boundary']:]
                    event('f1_observation', console_receipt=state['f1_console_receipt'], disconnect=state['f1_disconnect'], physical_fastboot_check_required=True)
                    state['overlap_armed'] = False
                    break
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
                    print('Use u, send COMMAND, overlap, drain, or x.', flush=True)
                print('\nCOMMAND>', flush=True)
    finally:
        reader_stop.set()
        monitor_stop.set()
        sink_stop.set()
        try:
            for worker in workers:
                if worker.ident is not None:
                    worker.join(timeout=1)
        finally:
            usb.util.dispose_resources(dev)
            print('\nUSB resources disposed.', flush=True)

if __name__ == '__main__':
    main()
