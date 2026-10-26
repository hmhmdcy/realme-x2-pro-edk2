"""Save this offline progress without changing the deployed baseline."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
names=['factory-gamma-validation.json','gamma-math-validation.json','hal-fragment-validation.json','gamma-interpolation-validation.json','pipeline-role-validation.json','representation-validation.json']
for name in names:assert json.loads((HERE/name).read_text())['passed'],name
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 path=ROOT/relative;d=json.loads(path.read_text())
 d.update(current_camera_evidence=prefix+'reference/kernel350/README.md',in_progress_stage=350,
  in_progress_evidence=prefix+'reference/kernel350/README.md',in_progress_installed=False,
  factory_downstream_gamma_full_tree_extracted=True,
  factory_downstream_gamma_extraction_evidence=prefix+'reference/kernel350/factory-gamma-validation.json',
  factory_downstream_gamma_interpolation_verified=True,
  factory_downstream_gamma_interpolation_evidence=prefix+'reference/kernel350/gamma-interpolation-validation.json',
  factory_downstream_gamma_role_pending=True,factory_downstream_gamma_role_evidence=prefix+'reference/kernel350/pipeline-role-validation.json',
  factory_final_tone_default_pending=True,factory_ife_gamma_default_enabled=False,current_adaptation_goal_status='active')
 path.write_text(json.dumps(d,indent=2)+'\n')
entry='''350已完成原厂IPE Gamma完整提取与数值复现，详见reference/kernel350/README.md。五BIN177roots/898curves*257，与原厂parser全部树/开关/控制轴一致，global75unique。parser新目录E ext4 /mnt/samurai-full282/parser350，各work以1000运行；原始payload/mode树保持，完整数据只privatekernel350。14mode/usecase所选根私存mode-profiles-private.json，绑定复用349。

350通用gamma_segments.h模板64/256区分：host/ARM各64段41cases10660bytes，256段101cases103828bytes零差。实际原HAL正常编码片段355148..35528c，97有效curves99328bytes/460071instructions零差，无math/log桩。完整Gamma15 DoInterpolation483c58..4841dc：412calls（375factory/18RGB排列/12mixed/3pointercopy/4badweight），5332702instructions/495memcpy桩无math桩；portable host/ARM各1240records1279680bytes零差（另4badcurve）。工具初版缺explicit template argument已修，失败log保留。HAL runtimechannel1032(enumI+257f)，序列化1040(enumQ+257f+pad)，HAL输出G/B/R；portable normalized单channel API[0,1]，没有采用范围外端点epsilon，尚未IPA/tree集成。check-hal-fragment已改main guard以复用loader。SDK/private/camss350-math只有小工具，无workbind/phoneworker。

350处理链证据：pinned9f17f1b源码IFE动态mask/ContrastCurve影响enable，输出64greenbase；IPE GetGammaOutput接IFE/BPS，与Gamma15precalc不同。LTM13setting使用inverseGamma，有reserve igamma_en；static ignoreChromatixRGammaFlag可forceRGAMMA_EN0，useHardcodedGamma可取硬编码，target值未恢复。170/175 published lists均CST→LTM→CCM→Gamma→ChromaEnh，但未证明目标Titan/全部runtimeenable。实际281 cameraHAL e2b1b9...debugsymbols + rawregistry + RELR绑定CST34f8d0/LTM35e238/CCM350368/Gamma351bd8连续24byte槽；opaque字段不当enable、邻接不冒充physicalgraph。pipeline-role-validation/primary-sources已记录，包括170file。vendor源/asm只private。

350 representation对75unique曲线每4点抽样成65，0精确表达，最大continuous误差10DN10=2.493/255、maxRMS1.517DN10，所有fine/coarse delta可表达；只曲线域不含IGamma/LTM/CCM/ADRC/hardwareinteger，不作最终默认证明。没有手机活动，仍349最后观察338+r27/r22+344etc；348/349Gamma仍未安装。下一步优先从保留BIN解LTM reserve/IGamma、IPE CCM13和static settings覆盖，确定finaltone方案，不能直接Gamma15∘Gamma16或把256段送VFE64/旧OPEtype4。完整目标active。
'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text().replace('# 当前检查点：349','# 当前检查点：350',1)
start=s.index('下一步优先从保留BIN完整提取Gamma15_IPE');end=s.index('\n\n原严格密钥USB',start)
s=s[:start]+entry.rstrip()+s[end:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal active。先读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel350/README。350已从5原BIN完整解IPE Gamma177roots/898curves，与原parser XML一致/global75unique；完整HAL DoInterpolation412calls与portable host/ARM各1279680bytes零差，编码片段97curves99328bytes零差，generic64/256分清。没有手机活动/安装，仍349最后观察338+r27/r22+344etc；348kernel/349GammaIPA已组合实测未安装。新发现LTM inverseGamma接IFEgreen64、reserve/staticflags可覆盖，CCM位于后级Gamma之前；170/175源码与实际HAL registry支持组件关系但不证明targetruntimeflags/physicalgraph。下一步优先提取LTM reserve/IGamma、IPE CCM13和static settings，确定输出域后再组合发布，勿简单复合两Gamma。private350表/源码/asm/样本不镜像，parser大目录放E ext4，无phoneworker/SDKbind。AE/防频闪/模式/光学/同步/连续AF等仍未完成。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('350当前：原厂IPE Gamma完整树、原HAL插值/编码已核对；LTM逆Gamma及静态覆盖影响最终色调，继续提取。没有改手机默认。[350详情](../../reference/kernel350/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths.extend(ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json'])
for source in paths:
 target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded350 offline extraction/interpolation/chain progress; deployed baseline preserved; goal active.')
