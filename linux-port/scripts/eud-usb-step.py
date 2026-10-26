#!/usr/bin/env python3
"""One bounded EUD 9505 libusb experiment on Linux, with target-only usbmon.

Requires python3-usb and usbmon. Does not bind, USB-reset or reconfigure a device.
An optional single COM setup command uses the public QUIC command table.
Detach from WSL separately after this process exits. The USB monitor records
URBs at the virtual host controller, not physical USB packets or bus ACKs.
"""
import argparse
from contextlib import ExitStack
import datetime
import json
import os
from pathlib import Path
import select
import threading
import time

import usb.core
import usb.util


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hex', default='', help='one complete frame, e.g. 90 03 41 42 43')
    parser.add_argument('--repeat', type=int, default=1, choices=range(1, 6))
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--ack', default='', help='stop retries on fresh decoded receipt')
    parser.add_argument('--out', required=True, type=Path, help='new output prefix (no overwrite)')
    parser.add_argument('--setup', choices=['port-reset', 'rx-timeout', 'tx-timeout'],
                        help='one public COM command before the probe; timeout bytes match QUIC test_function')
    parser.add_argument('--read-size', type=int, choices=[16, 4096], default=4096,
                        help='16 completes each full IN packet without waiting for a short packet')
    parser.add_argument('--zlp', action='store_true',
                        help='explicit empty OUT after a complete max-packet frame (len=14)')
    args = parser.parse_args()
    setup_frames = {'port-reset': bytes.fromhex('03'),
                    'rx-timeout': bytes.fromhex('02 ff ff 00 00'),
                    'tx-timeout': bytes.fromhex('01 ff ff 00 00')}
    setup = setup_frames.get(args.setup, b'')
    frame = bytes.fromhex(args.hex)
    if frame and not (len(frame) >= 2 and frame[0] == 0x90 and
                      ((frame[1] == 2 and len(frame) == 2) or
                       ((frame[1] == 1 or 3 <= frame[1] <= 14) and
                        len(frame) == frame[1] + 2))):
        parser.error('requires a complete 0x90 frame: len=1 tty, len=2 F1, len=3..14 probe')
    if not 1 <= args.seconds <= 60:
        parser.error('--seconds must be 1..60')
    if setup and (not frame or not args.ack or args.seconds < 8):
        parser.error('--setup requires a probe, a fresh receipt criterion and at least 8 seconds')
    devices = list(usb.core.find(find_all=True, idVendor=0x05c6, idProduct=0x9505))
    if len(devices) != 1:
        raise RuntimeError(f'expected exactly one EUD 9505, found {len(devices)}')
    dev = devices[0]
    stop = threading.Event()
    monitor = None
    start = time.monotonic()
    try:
        cfg = dev.get_active_configuration()
        interfaces = list(cfg)
        if len(interfaces) != 1:
            raise RuntimeError('expected one active interface/altsetting; inspect descriptors first')
        intf = interfaces[0]
        if dev.is_kernel_driver_active(intf.bInterfaceNumber):
            raise RuntimeError('kernel driver owns interface; refusing automatic detach')
        bulk = [ep for ep in intf if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK]
        ins = [ep for ep in bulk if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN]
        outs = [ep for ep in bulk if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT]
        if len(ins) != 1 or len(outs) != 1:
            raise RuntimeError('expected exactly one bulk IN and one bulk OUT')
        epin, epout = ins[0], outs[0]
        if frame and len(frame) > epout.wMaxPacketSize:
            raise RuntimeError('this probe must fit in one OUT packet')
        if args.zlp and len(frame) != epout.wMaxPacketSize:
            raise RuntimeError('--zlp requires a complete max-packet frame')
        metadata = {
            'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'bus': dev.bus, 'address': dev.address, 'vid': dev.idVendor, 'pid': dev.idProduct,
            'configuration': cfg.bConfigurationValue, 'interface': intf.bInterfaceNumber,
            'endpoints': [{'address': ep.bEndpointAddress, 'attributes': ep.bmAttributes,
                           'max_packet': ep.wMaxPacketSize} for ep in intf],
            'frame': frame.hex(' '), 'repeat_limit': args.repeat, 'ack': args.ack,
            'setup': args.setup, 'setup_hex': setup.hex(' '),
            'read_size': args.read_size,
            'explicit_out_zlp': args.zlp,
            'setup_source': 'https://github.com/quic/eud/blob/693741a3b0448690402539ed0e6af067510e386f/inc/com_eud.h',
            'transport': 'PyUSB/libusb -> WSL vhci -> usbipd -> Windows USB (bypasses qcusbser)',
        }
        paths = [Path(str(args.out) + ext) for ext in ('.json', '.raw', '.events.jsonl', '.usbmon', '.txt')]
        if any(path.exists() for path in paths):
            raise FileExistsError('output prefix already exists')
        with paths[0].open('x', encoding='utf-8') as meta:
            meta.write(json.dumps(metadata, indent=2) + '\n')
        print(json.dumps(metadata), flush=True)
        with open('/sys/kernel/debug/usb/usbmon/0u', 'rb', buffering=0) as mon, \
             paths[1].open('xb') as raw, paths[2].open('x', encoding='utf-8') as events, \
             paths[3].open('xb') as trace, paths[4].open('x', encoding='utf-8') as decoded, \
             ExitStack() as cleanup:
            # usbmon readiness does not guarantee a blocking read can return;
            # keep reads nonblocking so stop/join works even on an idle bus.
            os.set_blocking(mon.fileno(), False)
            monitor_errors = []

            def capture():
                pending = b''
                try:
                    while not stop.is_set():
                        if not select.select([mon], [], [], 0.05)[0]:
                            continue
                        try:
                            chunk = os.read(mon.fileno(), 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            break
                        pending += chunk
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            fields = line.split()
                            if len(fields) < 4:
                                continue
                            address = fields[3].split(b':')
                            if len(address) == 4 and int(address[1]) == dev.bus and int(address[2]) == dev.address:
                                trace.write(line + b'\n')
                                trace.flush()
                except Exception as error:
                    monitor_errors.append(repr(error))

            def event(kind, **values):
                row = {'ms': round((time.monotonic() - start) * 1000, 3), 'event': kind, **values}
                events.write(json.dumps(row) + '\n')
                events.flush()
                if kind != 'in':
                    print(json.dumps(row), flush=True)

            monitor = threading.Thread(target=capture, name='target-usbmon')
            monitor.start()

            def stop_monitor():
                stop.set()
                monitor.join(timeout=1)
                if monitor.is_alive():
                    raise RuntimeError('usbmon thread did not stop')

            cleanup.callback(stop_monitor)
            usb.util.claim_interface(dev, intf.bInterfaceNumber)
            event('claimed')
            pending = bytearray()
            fresh = ''
            sent = 0
            acked = None
            frames = stray = 0
            setup_sent = not setup
            while time.monotonic() - start < args.seconds:
                if monitor_errors:
                    raise RuntimeError(f'usbmon failed: {monitor_errors}')
                try:
                    data = bytes(dev.read(epin.bEndpointAddress, args.read_size, timeout=20))
                except usb.core.USBTimeoutError:
                    data = b''
                except usb.core.USBError as error:
                    event('read_error', error=str(error))
                    if frame == bytes.fromhex('90 02') and sent and error.errno == 19:
                        event('F1_disconnect', note='verify fastboot separately')
                        break
                    raise
                if data:
                    event('in', length=len(data))
                    raw.write(data)
                    raw.flush()
                    pending.extend(data)
                    while len(pending) >= 2:
                        length = pending[1]
                        if pending[0] != 0x90 or not 1 <= length <= 64:
                            pending.pop(0)
                            stray += 1
                            continue
                        if len(pending) < length + 2:
                            break
                        payload = bytes(pending[2:length + 2]).decode('ascii', errors='replace')
                        del pending[:length + 2]
                        frames += 1
                        decoded.write(payload)
                        decoded.flush()
                        if sent:
                            fresh = (fresh + payload)[-16384:]
                    if sent and args.ack and acked is None and args.ack in fresh:
                        acked = time.monotonic()
                        event('receipt', text=args.ack)
                if acked is not None and time.monotonic() - acked >= 2:
                    break
                if setup and not setup_sent and time.monotonic() - start >= 1:
                    event('setup_submit', name=args.setup, hex=setup.hex(' '),
                          note='COM commands have no protocol response; completion is not a readback')
                    count = dev.write(epout.bEndpointAddress, setup, timeout=500)
                    event('setup_complete', length=count)
                    if count != len(setup):
                        raise RuntimeError(f'short COM setup write: {count}/{len(setup)}')
                    setup_sent = True
                if frame and setup_sent and acked is None and sent < args.repeat and time.monotonic() - start >= 3 + 3 * sent:
                    event('out_submit', hex=frame.hex(' '), attempt=sent + 1)
                    count = dev.write(epout.bEndpointAddress, frame, timeout=500)
                    event('out_complete', length=count)
                    if count != len(frame):
                        raise RuntimeError(f'short bulk write: {count}/{len(frame)}')
                    if args.zlp:
                        event('zlp_submit')
                        count = dev.write(epout.bEndpointAddress, b'', timeout=500)
                        event('zlp_complete', length=count)
                        if count != 0:
                            raise RuntimeError(f'nonempty ZLP completion: {count}')
                    sent += 1
            event('finished', sent=sent, receipt=acked is not None, frames=frames,
                  stray=stray, pending=len(pending))
    finally:
        try:
            usb.util.dispose_resources(dev)
        finally:
            stop.set()
            if monitor is not None:
                monitor.join(timeout=1)
            print('USB resources disposed; usbmon_thread_alive=' +
                  str(monitor is not None and monitor.is_alive()), flush=True)
    if args.ack and acked is None:
        raise SystemExit('No fresh device receipt; do not classify as an accepted probe')


if __name__ == '__main__':
    main()
