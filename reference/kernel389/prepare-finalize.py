from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel388/finalize-local.py').read_text().replace('stage=388','stage=389').replace('reference/kernel388','reference/kernel389')
s=s.replace('NEXT-SESSION-through387-2026-10-21.md','NEXT-SESSION-through388-2026-10-21.md')
s=s.replace('c9cc081b508604c0b2222fa77bb2cf9b864ec516','b9a393e3cc0cfd74e8804546ad91137389b962ac')
s=s.replace('camera: use direct IPE DMA and retain exported buffer owners','camera: integrate the SM8150 ICP platform owner and prepare board deployment')
s=s.replace('/mnt/e/edk2-samurai-out/kernel388','/mnt/e/edk2-samurai-out/kernel389')
ast.parse(s);(HERE/'finalize-local.py').write_text(s)
print('Prepared scoped local checkpoint export and commit.')
