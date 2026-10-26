from pathlib import Path
import hashlib,json,shlex,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['trigger-tree-validation.json','profile-assembly-validation.json','ipa-mesh-validation.json','native-r1-validation.json','native-r1-image-validation.json']:
 d=json.loads((HERE/name).read_text());assert d.get('passed',d.get('all_full_trees_match',False))
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
print(json.dumps(dict(stage=322,services=services)))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);services=json.loads(q.stdout)
(HERE/'restored-services-validation.json').write_text(json.dumps(services,indent=2)+'\n')
p=HERE/'factory-selector-validation.json';d=json.loads(p.read_text());d.update(association_scope='gain multiset only; does not distinguish trigger trees',definitive_association='trigger-tree-validation.json');p.write_text(json.dumps(d,indent=2)+'\n')
source=host.PRIVATE/'sources/iqsettingutil.cpp'
(HERE/'trigger-source.json').write_text(json.dumps(dict(repository='https://github.com/comprehensive9/vendor_qcom_proprietary',commit='36fc163a534963a5b3af52186af5efcc63401ad2',path='camx/src/hwl/iqsetting/iqsettingutil.cpp',sha256=hashlib.sha256(source.read_bytes()).hexdigest(),function='IQSettingUtils::GetIndexPtTrigger',lines=[257,320]),indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text())
d.update(current_camera_evidence='../../reference/kernel322/README.md',final_health_evidence='../../reference/kernel322/native-r1-validation.json',
 in_progress_stage=322,in_progress_evidence='../../reference/kernel322/README.md',in_progress_installed=False,
 lsc_individual_values_applied=True,lsc_individual_values_applied_scope='temporary IMX319 internal-pattern profiles; installed defaults unchanged',
 lsc_individual_default_enabled=False,lsc_factory_trigger_tree_decoded=True,lsc_factory_unique_complete_profiles=3,
 lsc_factory_selector_evidence='../../reference/kernel322/trigger-tree-validation.json',lsc_individual_hardware_evidence='../../reference/kernel322/native-r1-image-validation.json',
 lsc_dynamic_scene_trigger_integration=False,lsc_factory_checksum_verified=False,
 system_services=dict(stage=322,services={k:[x['pid'] for x in v] for k,v in services['services'].items()},evidence='../../reference/kernel322/restored-services-validation.json'))
# Correct the stale pre318 nested value using the existing318 deployment evidence.
d['kernel_modules']['qcom_camss']['sha256']='2f8a94f5bd34694d52a0ff262f7df668d5cbea46a2109fa5b195d510f50547fa'
p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('# 当前检查点：321','# 当前检查点：322')
s=s.replace('全部321构建／采集／安装worker终态，当前PW/WP pid6642/6645',f"全部321/322构建／采集／安装worker终态，当前PW/WP pid{services['services']['pipewire'][0]['pid']}/{services['services']['wireplumber'][0]['pid']}")
s=s.replace('kernel321/host.py提供raw_ssh','kernel322/host.py提供raw_ssh')
start=s.index('下一步：将7个原厂LSC根')
s=s[:start]+'''322已完成：七个原厂根的完整触发树/表/golden与原厂XML对应，归并三套完整配置，不能只按增益集合判断。GetIndexPtTrigger区间内保持，间隙线性插值。Default UID25/130，Usecase33为1262，Preview/Feature1.12四根相同。显式Default/lux100/CCT6500生成factory与unit配置，非当前场景测量。504组真实触发组合通过。实际AArch64 IPA两份884字Q10与独立Python模型完全一致。系统已安装r26 IPA在广角内部灰阶图上运行off/factory/unit；每种稳定3帧，真实unit区别于factory。43,008像素近似模型p99约1.69～1.95/255；不据此声称光学校准完成。实验root为/var/lib/samurai/k322-lsc-r1；已终态、服务/媒体恢复、所有相机电源关闭、故障增量0/taint0。详见reference/kernel322/README.md。

真实个体LSC已临时应用通过，默认仍未启用。继续其它三摄原厂调校/个体布局/模式映射、动态触发与原厂有效性约定；未知checksum不是全部可回退实验的硬门槛。正常光线的阴影/颜色/黑电平、畸变内参、多摄几何同步、真实曝光时间和连续AF仍待完成。用户已关灯，可独立工作继续。四实体同时工作未验证；旧GPU/modem/SSC问题开放。目标不可缩减为已完成的兼容功能。
'''
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续多摄/骁龙ISP完整适配，goal active。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel322/README.md。r26/config-r21＋318 CAMSS保持。322已关联完整原厂触发树，广角真实个体LSC经系统IPA→ISP内部图案临时试验通过，默认未启用。下一步继续其它三摄调校/单位数据/模式映射和动态触发，正常光学、多摄校准仍待完成。320分组解码已消除原4零；用户已关灯继续独立工作；未知checksum不是全部可回退实验的硬门槛。不要重放已终态安装或试验。\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json']]
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print(json.dumps(services,indent=2));print('Recorded322, mirrored public sources; r26/r21 and318 deployment preserved.')
