"""Extract the functions actually compiled in the optional candidate."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
source = (HERE / 'eud.c').read_text()
sha = lambda b: hashlib.sha256(b).hexdigest()
pieces, rows = [], []


def add(name, text, start, end):
    body = text[start:end]
    pieces.append(body)
    rows.append({'name': name, 'line': text.count('\n', 0, start) + 1,
                 'sha256': sha(body.encode())})


for row in json.loads((HERE / 'function-manifest.json').read_text())['extracted']:
    if row['kind'] == 'define':
        m = re.search(r'^#define\s+' + row['name'] + r'\s+[^\n]+', source, re.M)
        add(row['name'], source, m.start(), m.end())
for name in ['EUD_RX_POLL_MS', 'EUD_INT_RX', 'EUD_RX_IRQ_EMPTY_MAX',
             'EUD_RX_IRQ_GRACE_MS', 'EUD_IRQ_FAULT_EMPTY', 'EUD_IRQ_FAULT_WATCHDOG',
             'EUD_IRQ_FAULT_MASK']:
    m = re.search(r'^#define\s+' + name + r'\s+[^\n]+', source, re.M)
    add(name, source, m.start(), m.end())
header = (HERE / 'eud-com-window.h').read_text()
for text, kind, name in [(header, 'enum', 'eud_com_window_state'),
                         (header, 'struct', 'eud_com_window_result'),
                         (source, 'struct', 'eud_tx_record'), (source, 'struct', 'eud_rx_frame'),
                         (source, 'enum', 'eud_rx_source'), (source, 'struct', 'eud_rx_snapshot'),
                         (source, 'struct', 'eud_port')]:
    m = re.search(r'^' + kind + ' ' + name + r' \{', text, re.M)
    add(name, text, m.start(), text.index('\n};', m.end()) + 3)
pieces.append('static struct eud_port *eud;\nstatic bool eud_reboot_pending;')
functions = ['to_eud_port', 'eud_put', 'eud_send_frame', 'eud_tx_work', 'eud_tx_empty',
             'eud_start_tx', 'eud_stop_tx', 'eud_stop_rx', 'eud_startup', 'eud_shutdown',
             'eud_restore_ahb2phy', 'eud_rx_irq_stop_locked', 'eud_reboot_cmd',
             'eud_rx_collect_locked', 'eud_console_rx_locked', 'eud_console_write_legacy',
             'eud_rx_irq', 'eud_rx_snapshot_locked', 'eud_rx_work']
for name in functions:
    m = re.search(r'^static [\w\s*]+?\b' + name + r'\([^;]*?\)\n\{', source, re.M)
    a = m.start()
    while source[a] == '\n': a += 1
    add(name, source, a, source.index('\n}', m.end()) + 2)
start = source.index('/* Internal COM software window.')
end = source.index('static int eud_probe_locked(', start)
add('complete-window-implementation', source, start, end)
for name in ['eud_remove_locked', 'eud_remove']:
    m = re.search(r'^static void ' + name + r'\([^;]*?\)\n\{', source, re.M)
    add(name, source, m.start(), source.index('\n}', m.end()) + 2)
(HERE / 'candidate-functions.inc').write_bytes(('\n\n'.join(pieces) + '\n').encode())
(HERE / 'candidate-function-manifest.json').write_bytes((json.dumps({
    'candidate_sha256': sha((HERE / 'eud.c').read_bytes()),
    'header_sha256': sha((HERE / 'eud-com-window.h').read_bytes()),
    'extracted': rows}, indent=2) + '\n').encode())
