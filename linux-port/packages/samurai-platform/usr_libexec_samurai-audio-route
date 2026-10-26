#!/usr/bin/python3
"""UCM routing for Samurai; jack reports retain ownership of DAPM pins."""
import argparse
import fcntl
import os
from pathlib import Path
import re
import subprocess
import time

PLAY = ['QUAT_MI2S_RX Audio Mixer MultiMedia1', 'SLIMBUS_0_RX Audio Mixer MultiMedia1']
CAP = 'MultiMedia2 Mixer SLIMBUS_0_TX'
TX = {n: 'AIF1_CAP Mixer SLIM TX' + str(n) for n in [0, 1, 5, 7]}


class Controls:
    def __init__(self, card):
        self.card = card

    def command(self, operation, name, value=None, iface='MIXER'):
        args = ['amixer', '-c', self.card, operation, "iface=" + iface + ",name='" + name + "'"]
        if value is not None:
            args.append(str(value))
        result = subprocess.run(args, capture_output=True, text=True, timeout=8)
        if result.returncode:
            raise RuntimeError('ALSA ' + operation + ' failed for ' + name + ': ' + result.stderr.strip())
        text = result.stdout
        hit = re.search(r': values=(.*)', text)
        if not hit:
            raise RuntimeError('Missing ALSA control value: ' + name)
        return {'value': hit[1].strip(), 'items': re.findall(r"Item #\d+ '([^']+)'", text)}

    def read(self, name, iface='MIXER'):
        return self.command('cget', name, iface=iface)

    def write(self, name, value):
        result = self.command('cset', name, value)
        if number(result, result['value']) != value:
            raise RuntimeError('ALSA readback mismatch: ' + name)


def number(control, value):
    if value in ['on', 'off']:
        return int(value == 'on')
    if isinstance(value, str) and value in control['items']:
        return control['items'].index(value)
    value = int(value)
    if control['items'] and not 0 <= value < len(control['items']):
        raise ValueError('Enum value out of range')
    return value


def playback(target):
    if target == 'speaker':
        return [(PLAY[1], 0), (PLAY[0], 1)]
    # RX0/1 belong to AIF1 on this board. INT0 is the earpiece DAC.
    return [(PLAY[0], 0),
            ('SLIM RX0 MUX', 'AIF1_PB'), ('SLIM RX1 MUX', 'AIF1_PB'),
            ('RX INT1_1 MIX1 INP0', 'RX0'), ('RX INT2_1 MIX1 INP0', 'RX1'),
            ('RX INT1_1 INTERP', 'RX INT1_1 MIX1'), ('RX INT2_1 INTERP', 'RX INT2_1 MIX1'),
            ('RX INT1 DEM MUX', 'CLSH_DSM_OUT'), ('RX INT2 DEM MUX', 'CLSH_DSM_OUT'),
            ('COMP1 Switch', 1), ('COMP2 Switch', 1), (PLAY[1], 1)]


def capture(target):
    plan = [(CAP, 0)] + [(name, 0) for name in TX.values()]
    if target == 'mic':
        plan += [('CDC_IF TX1 MUX', 'ZERO'), ('AMIC MUX1', 'ZERO'),
                 ('DMIC MUX5', 'DMIC0'), ('ADC MUX5', 'DMIC'),
                 ('CDC_IF TX5 MUX', 'DEC5'), (TX[5], 1)]
    else:
        # OEM headset wiring is AMIC2/ADC2; use the existing AIF1 mono FE.
        plan += [('CDC_IF TX5 MUX', 'ZERO'), ('DMIC MUX5', 'ZERO'),
                 ('AMIC MUX1', 'ADC2'), ('ADC MUX1', 'AMIC'),
                 ('CDC_IF TX1 MUX', 'DEC1'), (TX[1], 1)]
    return plan + [(CAP, 1)]


def route_plan(mode, headphones=False, headset=False):
    if mode == 'init':
        return playback('headphones' if headphones else 'speaker') + capture('headset' if headset else 'mic')
    if mode in ['speaker', 'headphones']:
        return playback(mode)
    if mode in ['mic', 'headset']:
        return capture(mode)
    return [(name, 0) for name in PLAY] + [(CAP, 0)] + [(name, 0) for name in TX.values()] + [
        ('SLIM RX0 MUX', 'ZERO'), ('SLIM RX1 MUX', 'ZERO'),
        ('RX INT1_1 MIX1 INP0', 'ZERO'), ('RX INT2_1 MIX1 INP0', 'ZERO'),
        ('RX INT1_1 INTERP', 'ZERO'), ('RX INT2_1 INTERP', 'ZERO'),
        ('COMP1 Switch', 0), ('COMP2 Switch', 0),
        ('CDC_IF TX1 MUX', 'ZERO'), ('CDC_IF TX5 MUX', 'ZERO'),
        ('AMIC MUX1', 'ZERO'), ('DMIC MUX5', 'ZERO')]


def apply(controls, plan):
    # Resolve every enum before the first mutation; restore the previous route
    # if a later ALSA operation fails. Never write jack pins or volume controls.
    names = list(dict.fromkeys(name for name, value in plan))
    before = {name: controls.read(name) for name in names}
    resolved = [(name, number(before[name], value)) for name, value in plan]
    current = {name: number(value, value['value']) for name, value in before.items()}
    if all(current[name] == value for name, value in dict(resolved).items()):
        return
    try:
        for name, value in resolved:
            if current[name] != value:
                controls.write(name, value)
                current[name] = value
    except Exception as original:
        failures = []
        enables = [name for name in PLAY + [CAP] + list(TX.values()) if name in before]
        for name in enables:
            try:
                controls.write(name, 0)
            except Exception as error:
                failures.append(str(error))
        for name in [n for n in names if n not in enables] + [n for n in enables if n in TX.values()] + [n for n in enables if n not in TX.values()]:
            try:
                controls.write(name, number(before[name], before[name]['value']))
            except Exception as error:
                failures.append(str(error))
        if failures:
            raise RuntimeError(str(original) + '; route rollback failed: ' + '; '.join(failures)) from original
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['init', 'off', 'speaker', 'headphones', 'mic', 'headset'])
    parser.add_argument('card')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.card):
        parser.error('Invalid ALSA card identifier')
    if b'realme,samurai\0' not in Path('/sys/firmware/devicetree/base/compatible').read_bytes():
        raise RuntimeError('Samurai device required')
    path = Path('/proc/asound') / ('card' + args.card if args.card.isdecimal() else args.card)
    card_path = path.resolve(strict=True)
    if not re.fullmatch(r'card\d+', card_path.name):
        raise RuntimeError('ALSA card resolution failed')
    descriptor = os.open('/dev/snd/controlC' + card_path.name[4:], os.O_RDONLY | os.O_CLOEXEC)
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Another UCM route operation is still active')
                time.sleep(.05)
        controls = Controls(args.card)
        jacks = {}
        for name in ['Headphone Jack', 'Mic Jack']:
            value = controls.read(name, iface='CARD')
            jacks[name] = number(value, value['value'])
        # Class-H mode, analog gains and all jack-owned pins are untouched.
        apply(controls, route_plan(args.mode, jacks['Headphone Jack'], jacks['Mic Jack']))
    finally:
        os.close(descriptor)


if __name__ == '__main__':
    main()
