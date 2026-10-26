from pathlib import Path
import ast

here=Path(__file__).resolve().parent;root=here.parents[1]
source=(root/'kernel204/observe-pending-newboot.py').read_text().replace('kernel204','kernel205/reboot-r2').replace('k204','k205r2').replace('stage=204','stage=205')
source=source.replace("here.parent/'kernel188/host.py'","here.parent.parent/'kernel188/host.py'")
ast.parse(source);(here/'observe-pending-newboot.py').write_text(source)
print('Prepared same-startup read-only observer.')
