from pathlib import Path
ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
needle='\t  Leave disabled for normal builds and use the static board tree.'
p=k/'drivers/of/Kconfig';s=p.read_text();assert s.count(needle)==1;p.write_text(s.replace(needle,'\t  Restore the sleep pin states when removing the overlay.\n'+needle))
for p in ref.glob('build-overlay-helper*.py'):
 s=p.read_text();assert s.count(needle)==1;p.write_text(s.replace(needle,'\t  Restore the sleep pin states when removing the overlay.\n'+needle))
print('Development Kconfig help now describes pin restoration')
