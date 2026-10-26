from pathlib import Path
p=Path('/home/cy122/pmos-samurai-kernel136/kernel/drivers/of/Kconfig');text=p.read_text();old='\t  realme samurai. Development only; leave disabled for normal builds.\n';assert text.count(old)==1
p.write_text(text.replace(old,old+'\t  Read the ID without programming sensor stream registers.\n\t  Restore GPIOs, clocks and PMIC values before returning.\n'))
