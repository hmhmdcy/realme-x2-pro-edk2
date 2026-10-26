from pathlib import Path
import re
root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name,patterns in [('kernel/printk/printk.c',['bool pr_flush','static bool __pr_flush','void console_stop','void console_start']),('kernel/printk/nbcon.c',['void nbcon_kthread_stop','static int nbcon_kthread_func','static bool nbcon_emit_next_record']),('include/linux/printk.h',['bool pr_flush'])]:
    text=root.joinpath(name).read_text();lines=text.splitlines();print(name)
    selected=set()
    for i,line in enumerate(lines):
        if any(x in line for x in patterns):selected.update(range(max(0,i-15),min(len(lines),i+115)))
    for i in sorted(selected):print(f'{i+1}: {lines[i]}')
