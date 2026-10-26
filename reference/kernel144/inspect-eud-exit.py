from pathlib import Path
import re
root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
text=root.joinpath('drivers/tty/serial/eud.c').read_text()
matches=list(re.finditer(r'^static[^;{}]*\b(eud_[a-zA-Z0-9_]+)\([^;{}]*\)\n\{',text,re.M))
print('Functions: '+', '.join(m[1] for m in matches))
for match in matches:
    name=match[1]
    if not any(x in name for x in ['bootloader','send_frame','eud_put']):continue
    end=match.end();depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    print('\n'+text[match.start():end])
print('\nRelevant fields and calls:')
for i,line in enumerate(text.splitlines()):
    if any(x in line for x in ['stopping','F1','emergency_restart','kernel_restart','restart','uart_remove_one_port','unregister_console','tx_mutex','FLUSH','TX_PENDING']):print(f'{i+1}: {line}')
