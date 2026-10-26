from pathlib import Path
import ast

ref=Path(__file__).parent
s=(ref/'build-package.py').read_text().replace('modules-root174','modules-root175')
s=s.replace("label+'-build-private.log'","label+'-v2-build-private.log'")
s=s.replace('Image-k175-lifetime-private','Image-k175-lifetime-v2-private').replace('logdump-k175-lifetime.img','logdump-k175-lifetime-v2.img')
s=s.replace('port_irq174_preserved=True','clock_lifetime_fix_included=True,first_candidate_not_deployed=True,port_irq174_preserved=True')
ast.parse(s);(ref/'build-package-v2.py').write_text(s)
print('K175_BUILD_V2_PREPARED',flush=True)
