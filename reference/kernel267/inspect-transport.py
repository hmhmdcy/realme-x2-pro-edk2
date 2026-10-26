"""Display transport control flow with all endpoint/identity literals redacted."""
from pathlib import Path
import ast
import re
import sys

p=Path('/mnt/e/edk2-samurai-out')/(sys.argv[1] if sys.argv[1:] else 'kernel260/host.py')
assert p.name in ['host.py','linux-host.py']
tree=ast.parse(p.read_text())
class Redact(ast.NodeTransformer):
    def visit_Constant(self,node):
        if isinstance(node.value,str):
            s=node.value
            if any(x in s for x in ['PRIVATE KEY','ssh-ed25519','AAAAC','fe80:']) or re.search(r'\b[0-9a-f]{8}-[0-9a-f-]{27}\b',s):
                node.value='<redacted identity/endpoint>'
        return node
print(ast.unparse(Redact().visit(tree)))
