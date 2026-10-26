from pathlib import Path
import re
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');text=(k/'drivers/media/i2c/imx471.c').read_text()
start=text.index('struct imx471_mode {');print(text[start:text.index('};',start)+2])
start=text.index('static const struct imx471_mode imx471_modes');end=text.index('\n};',start)+3;print(text[start:end])
for match in re.finditer(r'(?:static )?const struct cci_reg_sequence\s+(\w+)\[\]\s*=\s*\{(.*?)\n\};',text,re.S):
    selected=[(int(a,16),int(b,16)) for a,b in re.findall(r'CCI_REG8\((0x[0-9a-fA-F]+)\),\s*(0x[0-9a-fA-F]+)',match[2]) if 0x0340<=int(a,16)<=0x034f or 0x0408<=int(a,16)<=0x040f or 0x0900<=int(a,16)<=0x0902]
    if selected:print(match[1],[(hex(a),hex(b)) for a,b in selected])
