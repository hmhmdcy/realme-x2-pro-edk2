from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel388/finalize-local.py').read_text().replace('stage=388','stage=390').replace('reference/kernel388','reference/kernel390')
s=s.replace('NEXT-SESSION-through387-2026-10-21.md','NEXT-SESSION-through389-2026-10-21.md')
s=s.replace('c9cc081b508604c0b2222fa77bb2cf9b864ec516','dcc9c88587a00ed5ffe7126fc2c93d3f4384f0dc')
s=s.replace('camera: use direct IPE DMA and retain exported buffer owners','camera: deploy the normal SM8150 ICP platform and verify shared ownership')
s=s.replace('/mnt/e/edk2-samurai-out/kernel388','/mnt/e/edk2-samurai-out/kernel390')
ast.parse(s);(HERE/'finalize-local.py').write_text(s)
print('Prepared390 scoped local export and commit.')
