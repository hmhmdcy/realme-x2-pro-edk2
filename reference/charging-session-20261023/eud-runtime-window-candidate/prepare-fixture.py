"""Extract unchanged Image-linked EUD functions. No driver patch or switch."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
AUDIT = HERE.parents[1] / 'charging-oem-audit-20261023'
SOURCE = AUDIT / 'apsd-integration/current-r7/snapshots/drivers--tty--serial--eud.c'
EXPECTED = '16670a85501bf1bb1d8ae5bd856d991a73ac199028e33275f34f1774991c7bfd'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
raw = SOURCE.read_bytes()
assert sha(raw) == EXPECTED
text = raw.decode()
functions = [
    'to_eud_port', 'eud_put', 'eud_send_frame', 'eud_tx_work',
    'eud_tx_empty', 'eud_start_tx', 'eud_stop_tx', 'eud_stop_rx',
    'eud_startup', 'eud_shutdown', 'eud_restore_ahb2phy',
    'eud_rx_irq_stop_locked', 'eud_rx_collect_locked',
    'eud_console_rx_locked', 'eud_console_write_legacy',
]
defines = [
    'EUD_REG_COM_TX_ID', 'EUD_REG_COM_TX_LEN', 'EUD_REG_COM_TX_DAT',
    'EUD_REG_COM_RX_ID', 'EUD_REG_COM_RX_LEN', 'EUD_REG_COM_RX_DAT',
    'EUD_REG_INT1_EN_MASK', 'EUD_REG_INT_STATUS_1', 'EUD_REG_CSR_EUD_EN',
    'EUD_AHB2PHY_ONE_WAIT', 'EUD_COM_UART_ID', 'EUD_TX_CHUNK',
    'EUD_TX_BYTE_US', 'EUD_TX_FRAME_US', 'EUD_TX_JOURNAL_DEPTH',
    'EUD_TX_SOURCE_TTY', 'EUD_TX_SOURCE_CONSOLE', 'EUD_RX_MAX_FRAME',
    'EUD_RX_UART_ID', 'EUD_RX_CMD_ID', 'EUD_RX_CHAR_ID', 'EUD_RX_CHAR_ID2',
    'EUD_INT_RX_PENDING', 'EUD_RX_QUEUE_DEPTH', 'EUD_IRQ_FAULT_QUEUE',
    'EUD_IRQ_FAULT_HEADER',
]
parts = []
manifest = []


def add(kind, name, a, b):
    body = text[a:b]
    manifest.append({'kind': kind, 'name': name, 'source_line': text.count('\n', 0, a) + 1,
                     'sha256': sha(body.encode())})
    parts.append(body)


for name in defines:
    match = re.search(r'^#define\s+' + name + r'\s+[^\n]+', text, re.M)
    assert match, name
    add('define', name, match.start(), match.end())
for kind, name in [('struct', 'eud_tx_record'), ('struct', 'eud_rx_frame'),
                   ('enum', 'eud_rx_source'), ('struct', 'eud_port')]:
    match = re.search(r'^' + kind + ' ' + name + r' \{', text, re.M)
    assert match, name
    add(kind, name, match.start(), text.index('\n};', match.end()) + 3)
parts.append('static struct eud_port *eud;')
for name in functions:
    match = re.search(r'^static [\w\s*]+?\b' + name + r'\([^;]*?\)\n\{', text, re.M)
    assert match, name
    a = match.start()
    while text[a] == '\n':
        a += 1
    add('function', name, a, text.index('\n}', match.end()) + 2)
(HERE / 'actual-functions.inc').write_text('\n\n'.join(parts) + '\n')
result = {'source': str(SOURCE), 'source_sha256': EXPECTED,
          'image_source_commit': 'ba61a62293e0f6bc5838c06f2e85e033e3d702a8',
          'actual_functions': len(functions), 'extracted': manifest,
          'driver_patch_created': False}
(HERE / 'function-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'extracted_functions': len(functions), 'source_hash_verified': True}))
