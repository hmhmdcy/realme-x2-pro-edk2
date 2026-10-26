"""Offline six-packet/OEM/production evidence; no new MAC command or bus IO."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIVATE = ROOT.parent / 'edk2-samurai-out'
OEM = PRIVATE / 'kernel83/realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--drivers--power--oppo--gauge_ic--oplus_bq27541.c'
HEADER = PRIVATE / 'kernel85/official-oplus_bq27541.h'
CAPTURE = PRIVATE / 'charging-management-20261023/window2/fixed-query-private.json'
FIXTURE = CAPTURE.with_name('packets-private.bin')
TRM = PRIVATE / 'charging-management-20261023/ti-manual-private.txt'
PDF = TRM.with_name('ti-bq28z610-sluua65.pdf')
PROTOCOL = ROOT / 'reference/charging-management-20261023/gauge-protocol.h'
PROVIDER = PROTOCOL.with_name('samurai-gauge-protection.c')
R7 = ROOT / 'reference/charging-session-20261023/kernel-v2'
R8 = ROOT / 'reference/charging-session-20261023/thermal-bands-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OEM) == '0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87'
assert sha(HEADER) == '58c68c362fc031eb73884a59e121ba25918e6728b37572df4116f8e1277e270e'
assert sha(CAPTURE) == '8858bfa3fa9914a6f92262f549257c2dc22c037c1e1b9d95c9aaf06292a40d96'
assert sha(FIXTURE) == '662254550a4f08ed8d0b1f9b1b58139e10cec0ceace5d2b222c438730d7d5ca2'
assert sha(PDF) == 'f62ec12bb5aa23631759e59a378f36d254f9b0e2b5b6b8523a0dd081a13e4139'
text = OEM.read_text()
header = HEADER.read_text()
capture = json.loads(CAPTURE.read_bytes())

def function(source, name):
    match = re.search(r'^static (?:inline )?int ' + re.escape(name) + r'\([^;]*?\)\s*\{', source, re.M)
    assert match, name
    start = match.start(); i = source.index('{', start); level = 1; i += 1
    while level:
        level += (source[i] == '{') - (source[i] == '}'); i += 1
    return source[start:i], source[:start].count('\n') + 1, source[:i].count('\n') + 1

names = ['bq8z610_sealed', 'bq8z610_check_gauge_enable']
functions = {n: function(text, n) for n in names}
definitions = ['BQ28Z610_REG_CNTL1', 'BQ28Z610_REG_CNTL1_SIZE', 'BQ28Z610_SEAL_STATUS',
               'BQ28Z610_SEAL_BIT', 'BQ28Z610_SEAL_VALUE', 'BQ28Z610_REG_GAUGE_EN', 'BQ28Z610_GAUGE_EN_BIT']
macros = [re.search(r'^#define\s+' + name + r'\s+[^\n]+', header, re.M).group() for name in definitions]
generated = '\n'.join(macros + [functions[n][0] for n in names]) + '\n'
(HERE / 'oem-query-extracted.inc').write_text(generated)
# This list is checked, not expanded: no 0050/0052/0055/0056 selector reaches
# current production. FirmwareVersion0002 is retained separately, undecoded.
commands = [1, 0x51, 0x53, 0x54, 0x57, 0x71]
raws = {cmd: bytes.fromhex(capture['gauge'][hex(cmd)]['raw_hex']) for cmd in commands}
joined = b''.join(cmd.to_bytes(2, 'little') + raws[cmd] for cmd in commands)
assert joined == FIXTURE.read_bytes()
assert 'commands[] = { 1, 0x51, 0x53, 0x54, 0x57 }' in PROVIDER.read_text()
assert not re.search(r'\b(?:0x0050|0x0052|0x0055|0x0056|SafetyAlert|GaugingStatus|PF_EN|TCA)\b', text)
assert 'chip->cmd_addr.reg_ai = Bq28Z610_REG_TI;' in text
assert '#define BQ27541_FLAG_FC' in header and 'BIT(9)' in next(l for l in header.splitlines() if l.startswith('#define BQ27541_FLAG_FC'))

# Pin and compare the exact TCA hard predicates in R7 and frozen R8: thermal
# refactoring changes the function name, not these stop/classification guards.
checks = ['s->fault || (s->gauge_flags & 0x8000)',
          's->session_seconds >= SM_OEM_MAX_SECONDS', 's->gauge_flags & 0x4000',
          '*reason = SM_POLICY_REASON_GAUGE_CHARGE_STOP;']
for p in [R7 / 'mp2650-core.h', R8 / 'mp2650-core.h']:
    source = p.read_text()
    assert all(item in source for item in checks)
    assert source.index(checks[0]) < source.index(checks[1]) < source.index(checks[2])

binary = HERE / 'test-query-evidence'
command = ['gcc', '-std=c11', '-g', '-Wall', '-Wextra', '-Werror',
           '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
           str(HERE / 'test-query-evidence.c'), '-o', str(binary)]
subprocess.run(command, check=True, capture_output=True, text=True)
run = subprocess.run([str(binary), str(FIXTURE)], check=True, capture_output=True, text=True)
tested = json.loads(run.stdout)
assert not run.stderr and tested['passed'] and tested['real_packet_count'] == 6
values = {hex(cmd): int.from_bytes(raws[cmd][2:2 + (raws[cmd][35] - 4)], 'little')
          for cmd in commands if cmd != 0x71}
texts = TRM.read_text().splitlines()
terms = ['4.8 Terminate Charge and Discharge Alarms', '12.2.26 AltManufacturerAccess() 0x0050 SafetyAlert',
         '12.2.32 AltManufacturerAccess() 0x0056 GaugingStatus', 'PF_EN (Bit 6):',
         'TC (Bit 3):', 'FC (Bit 1):', 'DSG (Bit 6):', 'EMSHUT (Bit 29):']
anchors = {term: [i + 1 for i, line in enumerate(texts) if term in line] for term in terms}
assert all(anchors.values())
report = dict(passed=True, phase='offline-protection-query-evidence-audit',
              production_bug_confirmed=False, production_patch_created=False,
              production_whitelist_changed=False, exact_extended_2719_model_mapping_established=False,
              test=tested, existing_real_packets_replayed=values,
              real_standard_battery_status=capture['standard_words']['0xa'],
              real_battery_bits=dict(TCA=False, OCA=False, FC=False, DSG=True),
              manufacturing_raw=values['0x57'], inherited_pf_enable_bit=0,
              source_commit='23172a1571bd91156032cc9fef16284a82b63d2c',
              exact_oem_state_functions={name: dict(first_line=first, last_line=last)
                                         for name, (_, first, last) in functions.items()},
              manual_text_anchors=anchors,
              future_unverified_commands={'0x0050': 'standard TI SafetyAlert 4 payload / length8; not observed on this pack',
                                          '0x0052': 'standard TI PFAlert 4 payload / length8; not observed on this pack',
                                          '0x0056': 'standard TI GaugingStatus 4 payload including reserved byte / length8; not observed on this pack'},
              inputs={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): sha(p)
                      for p in [OEM, HEADER, CAPTURE, FIXTURE, TRM, PDF, PROTOCOL, PROVIDER,
                                R7/'mp2650-core.h', R7/'samurai-mp2650.c', R7/'oem-full-cycle.h',
                                R8/'mp2650-core.h', R8/'samurai-mp2650.c', R8/'oem-full-cycle.h']},
              tested_files={n: sha(HERE/n) for n in ['audit.py', 'test-query-evidence.c', 'oem-query-extracted.inc']},
              new_actual_mac_packets_created=0, device_accessed=False, ssh_executed=False,
              new_actual_queries=0, configuration_fet_nvm_otp_unseal_operations=0,
              old_2027_154_910_suites_rerun=False)
(HERE / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:report[k] for k in ['passed','production_bug_confirmed','test','existing_real_packets_replayed']}, indent=2))
