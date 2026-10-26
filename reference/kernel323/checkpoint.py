from pathlib import Path
import json,shlex,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['tele-lsc-decode-validation.json','tele-trigger-tree-validation.json','tele-mode-profile-validation.json','native-r1-validation.json','native-r1-image-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
observation=json.loads((host.PRIVATE/'probe-r1-observation.json').read_text());assert observation['state']['terminal'] and not observation['worker_live']
code='''
from pathlib import Path
import json
services={}
for name in ['pipewire','wireplumber']:
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name:rows.append(dict(pid=int(p.name),uid=p.stat().st_uid))
  except (FileNotFoundError,ProcessLookupError):pass
 services[name]=rows
assert all(len(v)==1 and v[0]['uid']==10000 for v in services.values())
print(json.dumps(dict(stage=323,services=services)))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);services=json.loads(q.stdout)
(HERE/'restored-services-validation.json').write_text(json.dumps(services,indent=2)+'\n')
p=HERE/'tele-lsc-decode-validation.json';d=json.loads(p.read_text());d.update(original_reader_crosscheck_pending=False,original_reader_crosscheck='tele-trigger-tree-validation.json');p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text());d.update(
 current_camera_evidence='../../reference/kernel323/README.md',final_health_evidence='../../reference/kernel323/native-r1-validation.json',
 in_progress_stage=323,in_progress_evidence='../../reference/kernel323/README.md',in_progress_installed=False,
 lsc_tele_factory_trigger_tree_decoded=True,lsc_tele_factory_ife_roots=6,lsc_tele_factory_core_regions=94,
 lsc_tele_factory_profile_temporarily_applied=True,lsc_tele_individual_values_applied=False,
 lsc_tele_factory_evidence='../../reference/kernel323/tele-trigger-tree-validation.json',lsc_tele_hardware_evidence='../../reference/kernel323/native-r1-image-validation.json',
 system_services=dict(stage=323,services={k:[x['pid'] for x in v] for k,v in services['services'].items()},evidence='../../reference/kernel323/restored-services-validation.json'))
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：322','# 当前检查点：323')
s=s.replace('全部321/322构建／采集／安装worker终态，当前PW/WP pid7579/7582',f"全部321/322/323构建／采集／安装worker终态，当前PW/WP pid{services['services']['pipewire'][0]['pid']}/{services['services']['wireplumber'][0]['pid']}")
s=s.replace('kernel322/host.py提供raw_ssh','kernel323/host.py提供raw_ssh')
pos=s.index('真实个体LSC已临时应用通过')
s=s[:pos]+'''323已完成：保留的306长焦原厂调校中6个IFE LSC根、94基础区域、6golden区域独立解码，并与原厂解析器完整触发树/网格对应，归并三套。Default为25/278/488；625含额外LED1，因此组装器新增显式LED索引，缺省多分支拒绝。本轮用LED0，396组AEC/CCT与分支行为通过。原厂mode0 4208x3120、mode3 2104x1560，模拟窗口均4216x3120、偏移8/4、bin1/2，参考原点同为8/8；当前内核16个相关几何寄存器一致。固定CamX约定映射span2103/1559、first0/0、step2/2；目标HAL赋值仍未独立反汇编。诊断Default/lux100/CCT6500的factory表经系统IPA在长焦内部图案上off/factory各稳定3帧，图像变化明确；没有长焦个体数据应用或正式画质主张。/var/lib/samurai/k323-lsc-r1已终态，媒体/服务恢复，故障0/taint0、电源关闭。详见reference/kernel323/README.md。无需重跑reader或本轮取流。

'''+s[pos:]
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP完整适配，goal active。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel323/README.md。r26/config-r21＋318 CAMSS保持。322广角真实个体LSC、323长焦工厂LSC均经系统IPA→ISP内部图案临时试验通过，默认未启用。继续长焦个体/主摄/前摄对应调校和模式映射、动态触发及正式光学/多摄校准。320分组解码已消除原4零；用户关灯继续独立工作；未知checksum不是全部可回退实验硬门槛。所有本轮worker已终态，勿重放旧安装或采集。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json','reference/kernel322/assemble-profile.py']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print(json.dumps(services,indent=2));print('Recorded323 and mirrored changed public tools/evidence; deployed stack preserved.')
