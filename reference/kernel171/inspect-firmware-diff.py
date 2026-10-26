from pathlib import Path
import ast, json, lzma, struct, uuid, zlib

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel171')
ns = {}
exec(compile((ref.parent / 'kernel104/verify-firmware.py').read_text().split('dt_audit=')[0], 'parsers', 'exec'), ns)
compat = Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb').read_bytes()
ns.update(compat=compat, lzma=lzma, struct=struct, uuid=uuid, zlib=zlib)
node = next(n for n in ast.parse((ref / 'build-package.py').read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'unpack')
exec(compile(ast.Module(body=[node], type_ignores=[]), 'unpack', 'exec'), ns)
old = ns['unpack']((out.parent / 'kernel164/boot-partition-k164-panel-handoff.img').read_bytes())
new = ns['unpack']((out / 'firmware/boot-candidate-private.img').read_bytes())
for guid, m in old['modules'].items():
    n = new['modules'][guid]
    if m['body'] == n['body']:
        continue
    (out / (guid + '-before-private.ffs-body')).write_bytes(m['body'])
    (out / (guid + '-after-private.ffs-body')).write_bytes(n['body'])
    diffs = [i for i, (a, b) in enumerate(zip(m['body'], n['body'])) if a != b]
    groups = []
    for i in diffs:
        if not groups or i > groups[-1][-1] + 32:
            groups.append([i])
        else:
            groups[-1].append(i)
    rows = []
    for g in groups[:8]:
        start = max(0, g[0] - 24); end = min(len(m['body']), g[-1] + 25)
        if end - start > 250:
            continue
        rows.append(dict(start=start, end=end, before_ascii=repr(m['body'][start:end]), after_ascii=repr(n['body'][start:end])))
    print(json.dumps(dict(name=n['name'], before_bytes=len(m['body']), after_bytes=len(n['body']),
                         different_bytes=len(diffs), group_count=len(groups), examples=rows)), flush=True)
