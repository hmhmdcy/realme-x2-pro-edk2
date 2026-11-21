#!/usr/bin/python3
"""Read-only daily health service for the stock MP2650 charging path."""
import json
import os
import sys
from pathlib import Path

PSY = Path('/sys/class/power_supply')
USB = PSY / 'samurai-usb-input'
MP = PSY / 'mp2650-input'
BATTERY = PSY / 'bq28z610-0'
CLIENT = Path('/sys/bus/i2c/devices/0-005c')


def value(path, default=None):
    try:
        return path.read_text().strip()
    except OSError:
        return default


def number(path):
    text = value(path)
    return int(text) if text is not None else None


def snapshot():
    link = CLIENT / 'driver'
    driver = link.resolve().name if link.exists() else None
    typecs = list(PSY.glob('tcpm-source-psy-*'))
    typec = typecs[0] if typecs else None
    return {
        'driver': driver,
        'usb_online': number(USB / 'online'),
        'usb_current_max': number(USB / 'current_max'),
        'typec_current_max': number(typec / 'current_max') if typec else None,
        'typec_current_now': number(typec / 'current_now') if typec else None,
        'typec_voltage_now': number(typec / 'voltage_now') if typec else None,
        'charger_status': value(MP / 'status'),
        'battery_status': value(BATTERY / 'status'),
        'battery_current_now': number(BATTERY / 'current_now'),
        'battery_voltage_now': number(BATTERY / 'voltage_now'),
        'battery_capacity': number(BATTERY / 'capacity'),
        'battery_health': value(BATTERY / 'health'),
    }


def healthy(data):
    return (data['driver'] == 'mp2650'
            and data['usb_online'] == 1
            and (data['usb_current_max'] or 0) >= 50000
            and (data['typec_current_max'] or 0) >= 50000
            and data['typec_voltage_now'] == 5000000)


def main():
    assert len(sys.argv) == 2
    action = sys.argv[1]
    data = snapshot()
    if action == 'status':
        print(json.dumps({'healthy': healthy(data), **data}, sort_keys=True))
        return 0
    if action == 'start':
        if not healthy(data):
            print(json.dumps(data, sort_keys=True), file=sys.stderr)
            return 1
        print(json.dumps({'started': True, **data}, sort_keys=True))
        return 0
    if action == 'stop':
        print(json.dumps({'kernel_owned': True, **data}, sort_keys=True))
        return 0
    raise SystemExit('usage: samurai-charging start|stop|status')


if __name__ == '__main__':
    raise SystemExit(main())
