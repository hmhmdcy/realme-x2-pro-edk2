"""Private optional software-window candidate from the exact Image source."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
source = HERE.parents[1] / 'charging-oem-audit-20261023/apsd-integration/current-r7/snapshots/drivers--tty--serial--eud.c'
raw = source.read_bytes()
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(raw) == '16670a85501bf1bb1d8ae5bd856d991a73ac199028e33275f34f1774991c7bfd'
base = raw.decode()
text = base


def replace(old, new, count=1):
    global text
    assert text.count(old) == count, (old[:90], text.count(old), count)
    text = text.replace(old, new)


replace('#include <linux/reboot.h>', '#include <linux/reboot.h>\n#include <linux/pm.h>\n\n#include "eud-com-window.h"')
replace('        struct uart_port port;\n', '        struct uart_port port;\n        bool window_quiet;\n        bool window_irq_enabled;\n        bool window_system_pm;\n        bool window_runtime_pm;\n        enum eud_com_window_state window_state;\n        u64 window_cookie;\n')
replace('static int eud_console_rx_locked(struct eud_port *up);',
        'static int eud_console_rx_locked(struct eud_port *up);\nstatic bool eud_reboot_pending;')
replace('if (up->tx_stopping)\n', 'if (up->tx_stopping || up->window_quiet)\n')
replace('        if (!port->state)\n                return;\n        tport = &port->state->port;',
        '        if (READ_ONCE(up->window_quiet) || !port->state)\n                return;\n        tport = &port->state->port;', 2)
replace('if (uart_tx_stopped(port)) {', 'if (uart_tx_stopped(port) || up->window_quiet) {')
replace('        schedule_work(&up->tx_work);\n}',
        '        if (!READ_ONCE(up->window_quiet))\n                schedule_work(&up->tx_work);\n}')
replace('static int eud_startup(struct uart_port *port)\n{\n        return 0;\n}',
        'static int eud_startup(struct uart_port *port)\n{\n        return READ_ONCE(to_eud_port(port)->window_quiet) ? -EBUSY : 0;\n}')
# A close racing quiet must not drain its TTY FIFO against the software gate.
replace('                while (n < EUD_TX_CHUNK && kfifo_get(&tport->xmit_fifo, &ch)) {',
        '                while (!up->window_quiet && n < EUD_TX_CHUNK &&\n                       kfifo_get(&tport->xmit_fifo, &ch)) {', 2)
replace('if (kick && !READ_ONCE(eud->rx_stopping))',
        'if (kick && !READ_ONCE(eud->rx_stopping) &&\n            !READ_ONCE(eud->window_quiet))')
replace('if (kick && !READ_ONCE(up->rx_stopping))',
        'if (kick && !READ_ONCE(up->rx_stopping) &&\n            !READ_ONCE(up->window_quiet))', 2)
replace('static bool eud_reboot_pending;\n\nstatic void eud_restore_ahb2phy',
        'static void eud_restore_ahb2phy')
# The reboot decision and quiet gate share exactly one short UART critical
# section. It does not acquire window_lock from the RX work being joined.
replace('\tif (eud_reboot_pending)\n\t\treturn;\n\tif (len == 2)\n\t\twhat = "bootloader";\n\telse\n\t\treturn;\n\teud_reboot_pending = true;\n\n\tuart_port_lock_irqsave(&up->port, &flags);',
        '\tif (len != 2)\n\t\treturn;\n\twhat = "bootloader";\n\tuart_port_lock_irqsave(&up->port, &flags);\n\tif (eud_reboot_pending || up->window_quiet) {\n\t\tuart_port_unlock_irqrestore(&up->port, flags);\n\t\treturn;\n\t}\n\teud_reboot_pending = true;')
replace('if (!up->rx_irq_started || up->rx_stopping || up->rx_bootloader_pending)',
        'if (!up->rx_irq_started || up->rx_stopping || up->window_quiet ||\n            up->rx_bootloader_pending)')
replace('if (!up->rx_stopping && up->rx_irq_enabled) {',
        'if (!up->rx_stopping && !up->window_quiet && up->rx_irq_enabled) {')
replace('if (up->rx_stopping) {', 'if (up->rx_stopping || up->window_quiet) {')
replace('if (!READ_ONCE(up->rx_stopping))\n',
        'if (!READ_ONCE(up->rx_stopping) && !READ_ONCE(up->window_quiet))\n')
replace('static int eud_probe(struct platform_device *pdev)',
        (HERE / 'window-implementation.inc').read_text() + '\n\nstatic int eud_probe_locked(struct platform_device *pdev)')
replace('        if (eud)\n                return -EBUSY;',
        '        if (eud || eud_window_orphan)\n                return -EBUSY;')
replace('static void eud_remove(struct platform_device *pdev)',
        'static int eud_probe(struct platform_device *pdev)\n{\n        int ret;\n\n        mutex_lock(&eud_window_lock);\n        ret = eud_probe_locked(pdev);\n        mutex_unlock(&eud_window_lock);\n        return ret;\n}\n\nstatic void eud_remove_locked(struct platform_device *pdev)')
replace('        unsigned long flags;\n\n        uart_port_lock_irqsave(port, &flags);\n        up->rx_stopping = true;',
        '        unsigned long flags;\n        bool borrowed = up->window_quiet;\n\n        uart_port_lock_irqsave(port, &flags);\n        if (borrowed) {\n                eud_window_orphan = up->window_cookie;\n                up->window_state = EUD_COM_REMOVED;\n                up->tx_stopping = true;\n        }\n        up->rx_stopping = true;')
replace('        uart_remove_one_port(&eud_uart_driver, port);\n        eud_restore_ahb2phy(up);',
        '        uart_remove_one_port(&eud_uart_driver, port);\n        if (borrowed)\n                cancel_work_sync(&up->tx_work);\n        /* A live software borrower never changed AHB2PHY. Do not impose\n         * probe history on its external controller/PHY session during unbind.\n         * The endpoint is terminal; end(old_cookie) returns ENODEV and\n         * acknowledges cancellation before a later probe may touch hardware.\n         */\n        if (!borrowed)\n                eud_restore_ahb2phy(up);')
replace('static const struct of_device_id eud_com_dt_match[] = {',
        'static void eud_remove(struct platform_device *pdev)\n{\n        mutex_lock(&eud_window_lock);\n        eud_remove_locked(pdev);\n        platform_set_drvdata(pdev, NULL);\n        mutex_unlock(&eud_window_lock);\n}\n\nstatic const struct of_device_id eud_com_dt_match[] = {')
replace('                .dev_groups     = eud_groups,',
        '                .dev_groups     = eud_groups,\n                .pm             = &eud_window_pm_ops,')
(HERE / 'eud.c').write_bytes(text.encode())
patch = ''.join(difflib.unified_diff(base.splitlines(True), text.splitlines(True),
                                  fromfile='a/drivers/tty/serial/eud.c', tofile='b/drivers/tty/serial/eud.c'))
header = (HERE / 'eud-com-window.h').read_text()
(HERE / 'eud-com-window.h').write_bytes(header.encode())
patch += ''.join(difflib.unified_diff([], header.splitlines(True),
              fromfile='/dev/null', tofile='b/drivers/tty/serial/eud-com-window.h'))
(HERE / '0001-eud-optional-software-window.patch').write_bytes(patch.encode())
(HERE / 'candidate-result.json').write_bytes((json.dumps({
    'base_sha256': sha(raw), 'candidate_sha256': sha(text.encode()),
    'header_sha256': sha(header.encode()), 'patch_sha256': sha(patch.encode()),
    'csr_and_ahb_window_writes': False, 'consumer_present': False,
    'automatic_activation': False, 'shared_source_modified': False,
    'scope': 'optional COM software quiet only; no electrical route/USB/charging acceptance'}, indent=2) + '\n').encode())
print(json.dumps({'candidate_created': True, 'candidate_sha256': sha(text.encode())}))
