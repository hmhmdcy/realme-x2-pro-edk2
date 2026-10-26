"""Inspect exact native supplier lifetime code; no phone access."""
from pathlib import Path
import sys
ref=Path(__file__).resolve().parent
sys.path.insert(0,str(ref.parent/'kernel284'));import storage
source=storage.mounted_build().parent/'source354'
for file,needles in [('drivers/power/supply/power_supply_core.c',[
    'struct power_supply *power_supply_get_by_name(', 'void power_supply_put(',
    'void power_supply_unregister(', 'int power_supply_set_property(']),
    ('drivers/usb/dwc3/core.c',['static int dwc3_psy_notifier('])]:
    text=(source/file).read_text()
    for needle in needles:
        pos=text.index(needle)
        end=text.index('\n}',pos)+2
        print(text[pos:end])
for name in ['core.c','gadget.c']:
    lines=(source/'drivers/usb/dwc3'/name).read_text().splitlines()
    for i,line in enumerate(lines):
        if 'vbus_draw_work' in line or 'current_limit' in line:
            print(name+':'+str(i+1)+': '+line.strip())
