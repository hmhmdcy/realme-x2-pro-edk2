from pathlib import Path
import difflib
import hashlib
import json
import subprocess
root=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144');out=Path('/mnt/e/edk2-samurai-out/kernel144')
source=root/'drivers/tty/serial/eud.c';before=source.read_text()
assert hashlib.sha256(before.encode()).hexdigest()=='7f5e4bf0ad5c95aad80dffacf88cc4f5178ba755cefc09a06dfb972e1cc78ba6'
assert not out.joinpath('eud-before-private.c').exists()
out.joinpath('eud-before-private.c').write_text(before)
out.joinpath('config-before-private').write_bytes(root.joinpath('.config').read_bytes())
out.joinpath('source-diff-before-private.patch').write_bytes(subprocess.check_output(['git','-C',str(root),'diff','--binary']))
text=before.replace('#include <linux/mutex.h>','#include <linux/mutex.h>\n#include <linux/printk.h>')
text=text.replace('\tstruct mutex tx_mutex;','\tstruct mutex tx_mutex;\n\tbool tx_stopping;')
needle='        eud_put(base, EUD_REG_COM_TX_ID, EUD_COM_UART_ID);'
assert text.count(needle)==1
text=text.replace(needle,'\t/* The reboot handoff sets this under the UART lock. */\n\tif (up->tx_stopping)\n\t\treturn;\n\n'+needle)
start=text.index('static void eud_reboot_cmd(');end=text.index('\nstatic void eud_rx_dispatch',start)
text=text[:start]+'''static void eud_reboot_cmd(struct eud_port *up, unsigned int len)
{
	unsigned long flags;
	const char *what;

	if (eud_reboot_pending)
		return;
	if (len == 2)
		what = "bootloader";
	else
		return;
	eud_reboot_pending = true;

	uart_port_lock_irqsave(&up->port, &flags);
	up->rx_stopping = true;
	eud_rx_irq_stop_locked(up, 0);
	uart_port_unlock_irqrestore(&up->port, flags);
	if (up->rx_irq_requested)
		synchronize_irq(up->rx_irq);

	pr_info("eud: reboot2 %s requested\\n", what);
	/*
	 * The F1 notice is queued by RX work. With nbcon, printk returning
	 * does not mean its frames have reached the FIFO. Drain the queued
	 * records before retiring the printer and giving the PHY back to ABL.
	 * Do not hold tx_mutex while waiting for the printer that needs it.
	 */
	pr_flush(1000, true);
	if (up->console_registered) {
		unregister_console(&eud_console);
		up->console_registered = false;
	}

	/* Serialize the last TTY writer with hardware shutdown as well. */
	mutex_lock(&up->tx_mutex);
	uart_port_lock_irqsave(&up->port, &flags);
	up->tx_stopping = true;
	uart_port_unlock_irqrestore(&up->port, flags);
	eud_restore_ahb2phy(up);
	writel(0, up->port.membase + EUD_REG_CSR_EUD_EN);
	readl(up->port.membase + EUD_REG_CSR_EUD_EN);
	mutex_unlock(&up->tx_mutex);
	kernel_restart((char *)what);
}
''' +text[end:]
source.write_text(text);out.joinpath('eud-candidate-private.c').write_text(text)
ref.joinpath('eud-reboot-handoff.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='a/drivers/tty/serial/eud.c',tofile='b/drivers/tty/serial/eud.c')))
report=dict(stage=144,baseline_build_tree_kernel=143,current_phone_kernel=140,
    candidate_source_sha256=hashlib.sha256(text.encode()).hexdigest(),baseline_source_sha256=hashlib.sha256(before.encode()).hexdigest(),
    wait_for_queued_console_before_phy_disable=True,printer_retired_before_hardware_disable=True,
    tty_handoff_serialized=True,post_handoff_tx_mmio_blocked=True,hardware_disable_readback=True,
    pacing_rx_and_display_gpu_charger_source_unchanged=True,actual_functions_tested=False,
    kernel_build_completed=False,deployed=False,display_accepted=False,gpu_accepted=False,charging_accepted=False,goal_complete=False)
ref.joinpath('source-preparation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K144_EUD_QUEUED_RECEIPT_AND_HARDWARE_HANDOFF_SOURCE_PREPARED_NOT_DEPLOYED')
