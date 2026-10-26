from pathlib import Path
import hashlib
import re

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
image = root/'arch/arm64/boot/Image'
assert hashlib.sha256(image.read_bytes()).hexdigest() == '2b244772eb7e15ce587722cd3fed37f775a05d4562a4ac2e6b80701aeb04dc45'
queries = {
    'include/linux/serial_core.h': (r'nbcon|__uart_port_lock|port->cons', 6),
    'kernel/printk/nbcon.c': (r'write_atomic|write_thread|device_lock|ATOMIC_UNSAFE|nbcon_legacy_emit_next_record', 5),
    'kernel/printk/printk.c': (r'nbcon_atomic|nbcon_offload|have_boot_console|have_legacy_console|have_nbcon_console', 4),
    'drivers/tty/serial/serial_core.c': (r'port->cons|uport->cons|uart_console_device|register_console|nbcon', 3),
    'include/linux/console.h': (r'CON_NBCON_ATOMIC_UNSAFE|nbcon_device_try_acquire|nbcon_device_release', 4),
    'drivers/tty/serial/eud.c': (r'console_write|uart_port_lock|uart_port_unlock|rx_console|console_registered|eud_remove', 2)
}
for filename,(expression,pad) in queries.items():
    lines = root.joinpath(filename).read_text().splitlines()
    indexes = {idx for number,line in enumerate(lines) if re.search(expression,line)
        for idx in range(max(0,number-pad),min(len(lines),number+pad+1))}
    print(filename)
    for index in sorted(indexes):
        print(f'{index+1}: {lines[index]}')
