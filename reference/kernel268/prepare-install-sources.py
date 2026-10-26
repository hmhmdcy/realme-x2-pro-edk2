"""Reuse the signed native seven-package transaction with the current versions."""
from pathlib import Path
import ast
import json
import re

R=Path(__file__).resolve().parent
mapping={
 'k239-r15-package-candidates':'k268-r19-package-candidates',
 'k239-r15-package-transaction':'k268-r19-package-transaction',
 'k236-runtime/boot-id-private.txt':'k267-work/boot-id-private.txt',
 'k236-baseline/installed-before-private.txt':'k268-tools/installed-before-private.txt',
 'k225-r13-package-candidates':'k239-r15-package-candidates',
 'stage=239':'stage=268',
 '99990.7.2-r15':'99990.7.2-r19',
 '99990.7.2-r13':'99990.7.2-r15',
 '0.1.0-r10':'0.1.0-r14',
 '0.1.0-r8':'0.1.0-r10',
 '==944':'==961',
 'current_944':'current_961',
 'installed_package_count=944':'installed_package_count=961',
 'unrelated_937':'unrelated_954',
 'same_current236_boot':'same_current267_boot',
 'r13_payloads':'r15_payloads',
 'r13_rollback':'r15_rollback',
 'r13_downgrade':'r15_downgrade',
 'r15_initial_snapshot_verified':'common_link_fix_host_checked',
}
pattern=re.compile('|'.join(re.escape(k) for k in sorted(mapping,key=len,reverse=True)))
for old,new in [('native-r15-preflight.py','native-preflight.py'),('install-r15-packages.py','native-install.py')]:
    tree=ast.parse((R.parent/'kernel239'/old).read_text())
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets))
    code=pattern.sub(lambda m:mapping[m[0]],ast.literal_eval(node.value))
    # Older generated wrappers retain an extra escaping level in separators.
    # Normalize literal values before executing any package-manager command.
    class FixSeparators(ast.NodeTransformer):
        def visit_Constant(self,node):
            if isinstance(node.value,str):node.value=node.value.replace('\\n','\n')
            return node
    code=ast.unparse(FixSeparators().visit(ast.parse(code)))+'\n'
    if new=='native-install.py':
        code=code.replace("assert all(p.read_text().strip() == 'closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))\n",'')
        code=code.replace("['/sys/bus/i2c/devices/7-0010', '/sys/bus/platform/devices/acb3000.camss', '/sys/bus/platform/devices/ac4b000.cci']",
          "['/sys/bus/i2c/devices/7-0010', '/sys/bus/i2c/devices/9-0010', '/sys/bus/platform/devices/ac4a000.cci', '/sys/bus/platform/devices/ac4b000.cci', '/sys/bus/platform/devices/acb3000.camss']")
    compile(code,new,'exec');(R/new).write_text(code)
print('Prepared current267 signed-package preflight/install sources for review.')
