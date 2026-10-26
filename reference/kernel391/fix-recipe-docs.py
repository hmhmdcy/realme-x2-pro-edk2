from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for package in ['libcamera','samurai-camera-config']:
 for base,prefix in [(HERE/'recipes','../../../../reference/'),(ROOT/'linux-port/packages','../../../reference/')]:
  p=base/package/'README.md';s=p.read_text()
  if base==HERE/'recipes':s=s.replace('../../../reference/','../../../../reference/')
  s=s.replace('[360记录](../../README.md)','[360记录]('+prefix+'kernel360/README.md)')
  s='391当前：libcamera r30/config-stack r25已正式安装，默认IPE四摄／RAW／隔离IPA及普通用户PipeWire共94新增作业通过，个体配置未打入公共包；完整IQ与多摄校准继续。[391证据]('+prefix+'kernel391/README.md)。以下为历史。\n\n'+s
  p.write_text(s)
