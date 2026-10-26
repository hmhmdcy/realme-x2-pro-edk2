from pathlib import Path
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');p=k/'drivers/mfd/qcom-pm8008.c';text=p.read_text();start=text.index('#define PM8008_FACTORY_ADDRESS');end=text.index('\nstatic int pm8008_probe(',start)
block=(ref/'pm8008-initial-address.c').read_text();block=block[block.index('#define PM8008_FACTORY_ADDRESS'):];assert 'goto unlock' not in block
p.write_text(text[:start]+block+text[end:])
