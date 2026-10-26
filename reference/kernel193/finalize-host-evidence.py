from pathlib import Path
import json,hashlib,ast
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel193';out=Path('/mnt/e/edk2-samurai-out/kernel193')
for p in [ref/'README.md',ref/'write-checkpoint.py']:
 text=p.read_text()
 old='依赖已有CCI的标准genpd管理，不直接操作GDSC寄存器。'
 assert old in text
 text=text.replace(old,'依赖已有CCI的标准genpd管理，不直接操作GDSC寄存器；接口语义见[内核运行时PM文档](https://docs.kernel.org/power/runtime_pm.html)。')
 old='使用已有`i2c-qcom-cci`驱动，实际注册master0/1为i2c-6/7。'
 assert old in text
 text=text.replace(old,'使用已有`i2c-qcom-cci`驱动，实际注册master0/1为i2c-6/7；[changeset接口文档](https://docs.kernel.org/devicetree/changesets.html)。')
 p.write_text(text)
for p in ref.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in ref.glob('*.json'):json.loads(p.read_text())
assert len((root/'NEXT-SESSION.md').read_bytes())<=6500
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='host-analysis-manifest-private.json'}
(out/'host-analysis-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(stage=193,python_syntax_files=len(list(ref.glob('*.py'))),private_host_files_hashed=len(manifest),current_checkpoint_bytes=len((root/'NEXT-SESSION.md').read_bytes()))))
