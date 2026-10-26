from pathlib import Path
import json,hashlib,shutil,ast
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel192';out=Path('/mnt/e/edk2-samurai-out/kernel192');source=out.parent/'kernel117/CamxChi'
manifest=json.loads((source/'source-manifest.json').read_text());byname={r['path']:r for r in manifest['files']}
runtime=Path('/home/cy122/x2pro-linux/parser-k117');tool='chi-cdk/tools/buildbins/linux64/ParameterParser'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(runtime/'ParameterParser')==sha(source/tool)==byname[tool]['sha256']
schemas=['camxsensordriver.xsd','camxsensorcommon.xsd','camxmoduleconfig.xsd']
for name in schemas:
 relative='chi-cdk/api/sensor/'+name
 assert sha(runtime/'api/sensor'/name)==sha(source/relative)==byname[relative]['sha256']
report=dict(stage=192,repository=manifest['repository'],commit=manifest['commit'],tool_sha256=byname[tool]['sha256'],runtime_copy_matches_fixed_source=True,original_target_schemas_match_fixed_source=True,analysis_schema_changes_are_private_copies_only=True)
(ref/'tool-integrity-validation.json').write_text(json.dumps(report,indent=2)+'\n')
xmlout=out/'vendor-prefix-xml';xmlout.mkdir()
for p in Path('/home/cy122/x2pro-linux/parser-k192-batch').rglob('*.xml'):
 if p.name not in ['sensorDriverData.xml','cameraModuleData.xml']:continue
 relative=p.relative_to('/home/cy122/x2pro-linux/parser-k192-batch');dest=xmlout/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
assert len(list(xmlout.rglob('*.xml')))==12
old='精确1.05/1.10V与主线8mV电压网格的约束差异也未解决；本轮没有擅自抬高输出。'
new='原厂生产pm8008_write_voltage()先检查请求上下限，再按8mV向上取整；抽取原函数、拦截I/O并运行ASan/UBSan，确认1.05/1.10V请求实际编程1.056/1.104V，1.8/2.8V不变。主线精确1.05/1.10V约束无可选电压，采用[1050000,1056000]/[1100000,1104000]微伏范围各只产生一个原厂等效值。[电压语义核对](pmic-voltage-contract-validation.json) 这是原厂软件编程值的证据，不是模拟电压实测；本轮没有写LDO/VSET。'
for p in [ref/'README.md',ref/'write-checkpoint.py']:
 text=p.read_text();assert old in text;p.write_text(text.replace(old,new))
nextp=root/'NEXT-SESSION.md';text=nextp.read_text();text=text.replace('四组PLDO父供电、冷地址、CCI及出图仍待解；IMX471主线仅ACPI/vana','OEM 1.05/1.10V实际取整1.056/1.104V已核；四组PLDO输入/冷地址/CCI/出图待解；IMX471主线仅ACPI/vana');assert len(text.encode())<=6500;nextp.write_text(text)
native=json.loads((ref/'native-health-validation.json').read_text());assert not native['new_faults_since192_baseline']
for p in ref.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in ref.glob('*.json'):json.loads(p.read_text())
manifest={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='host-analysis-manifest-private.json'}
(out/'host-analysis-manifest-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(stage=192,tool_and_schemas_integrity_verified=True,private_xml_saved=12,python_syntax_files=len(list(ref.glob('*.py'))),private_host_files_hashed=len(manifest),next_session_bytes=len(text.encode()))))
