from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['hardware','source','bls','rear-profile','rear-math','native-gtm']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
live=json.loads((HERE/'runtime-r1-validation.json').read_text());assert live['state']['terminal'] and live['state']['passed'] and not live['worker_live'] and not live['client_live']
archive=ROOT/'archive/NEXT-SESSION-through437-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：438（广角／长焦原厂 tone 与真实 PD10 自动链路通过）

完整多摄/ISP目标active。先读WORKING-BOUNDARIES、reference/kernel438/README。广角IMX319 mode2/1632x1224及长焦S5K3M5 mode3/2104x1560各自原厂GTM/TMC11/LTM+同SOF真实PD10+最终成功历史接通。普通原生IPA各40/56实拍、38/53math，连续8locked，各2/3显式bootstrap；共96图91math+5bootstrap，typed GTM实际cookie/gen和前序来源统计、上一成功lux逐帧核对，两bank。两路各4/5个未重算AWB但相同实际WB的锁定帧，继承437状态修复。隔离路径未新增这两摄实拍，不能冒认。

## 当前源码、数据与部署

438只扩展私有模式配置，没有修改框架/IPA/内核源码或复制算法，也没有创建libcamera438树。实际仍 /mnt/samurai-full282/libcamera437-awb-history/src/libcamera-v0.7.2，build1/IPA5：IPA8117008B/a4c0b7e6765504ccc440f1332bf84e8a0ea7a8ec35c38b0a9354d5aab8ae587e；签名3d2eea586a17ba5c3816f25acdba72bdff8740a9fdcedb4209008aa57ed08e57；库50923736B/af3bc105448c2d04407362992aa1682b6504956ded26a57d568544470f799c51、proxy1674864B/093df5faa73b42b741e2b61d862fefc292fcf7ced2ccfb6f6f9389f70b182dcf。438/storage候选树不存在时返回437；SDK bind只串行使用。

内核仍source354 HEAD9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3/samurai-vfe175-gtm-reopen434；匹配434 CAMSS3edb28d1/core d391fa24/m2m e6828a0c。正式仍420/419、Image363/DT389，r1临时模块/服务/资源全恢复，newfault0/taint0、worker/client终态，未永久安装438。

私有kernel438/factory-imx319-private.yaml、factory-s5k3m5-private.yaml分别来自实际formal420 profile和其原模式选择。343/349/350/351/412/426/431/432现有数据复用；DS4 UID33 PASS_FULL、GTM UID21、TMC11 UID63、LTM UID42属于各自文件，不代表表相同。rear IPE CCM全部单位，保留原IFE CCM。原本长焦TMC10关但11开，未混用。单曝光/linearAE/no-face，明确父DRC1、HDR比值1、LED0；广角Gamma多HDR节点按实际轴选择ratio1分支，CCT仍要求唯一，没有宣称完整HDR动态支持。

438 actual ARM profile对象两摄各3组TMC/GTM/LTM/immutable上游/原hist hold-refresh通过；6份512B实际GTMLUT与各自原完整HAL+native parsed root零差。main通用轴与CST/CV桥继承已核数学，模组LTM/TMC/Gamma/GTM/DS4表各自独立。actual手机profile/module/library与launch manifest和本地准备文件hash对应。

## BLS与前摄缺口

formal420查询hash全部匹配：主摄两模式、广角、长焦以及前摄2304x1728仍有实验BLS0/norm1；前摄1928x1088已是3840。436先修主摄候选，438在广角/长焦候选恢复各自原厂IFE960U14→3840U16及2175/2048归一化。广角16根288区复核299原parser、长焦19根152区复核306原parser，同源SHA；长焦BPS990未拿来用于IFE。原件不改、无个体暗场完成宣称。

前摄Sunny IMX471本轮新有界解码+原parser核对1IFE根5区，同样960/零阈值/enable1，但完整front profile尚未应用。前摄原TMC10/11和GTM关闭，LTM/Gamma仍开；IPE CCM28区25个非单位矩阵，IFE CCM原关闭，不能套rear单位矩阵或打开IFE替代。下一步439接前摄原IPE CCM13动态树与原禁用TMC/GTM下的LTM/Gamma，保留开关和BLS，再真实PD10/版本历史实拍。前摄1928x1088缺原厂模式绑定，不强套2304调校。

## 其它未完成与环境

原厂tone当前只TMC11 model2，manual/v2flags原值1、非零GTM份额保留；完整legacy/manual/v2/HDR分支、更多尺寸/视频、整合发布、颜色/平场/噪声/清晰度未验收。438末帧物体可辨、有室内噪声；预览按NV12/sYCC全范围BT601解码，不改应用像素，不当绝对色准。CCT4864/5934K是不同FOV的参考估计，不是多摄白点一致性认证。第五2MP、个体光学、多摄几何同步等363全范围保留。

每次WSL source/build/ext4先root 284/storage.py mounted_build原32GiB E盘，不格式化重建；429新guard原key/knownhosts，USB SSH正常。不猜MMIO，不恢复429越界诊断。DC仍RT2→kind0→bank0 coarse clear/write、FULL read，未逐字节dump SRAM，a7scratch不是统计。原件/系数/照片/全日志/private ELF仅E:/edk2-samurai-out/kernel438。438开始mirror HEAD5609244b81d2a417f374683abb79b42d4d47f1d7；public_module导出/scoped本地commit，保留无关index/worktree/untracked，不push。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/ISP目标。438已将广角IMX319 mode2 1632x1224、长焦S5K3M5 mode3 2104x1560各自原厂GTM/TMC11/LTM+同SOF真实PD10+成功history实拍：40/56帧、38/53math，两路连续8locked，共96图91math+5显式bootstrap，两GT M bank/前序source统计/上一成功lux通过。各自原BLS960恢复3840/norm2175/2048，LSC和完整tone保留；实际ARM profiles各3组输出与各自原完整GTM512B零差。无新源码/新build，仍437源libcamera437-awb-history、IPA a4c0b7e6/sign3d2eea58/libaf3bc105/proxy093df5fa，kernel434 HEAD9bc07e63。正式环境恢复无fault taint0未永久安装。原生两摄测试，不冒认新增隔离。下一步前摄：原TMC10/11和GTM关，但LTM/Gamma开且IPE CCM25个非单位矩阵，不能套rear桥/IFE CCM替代；新原parser已核front IFEBLS1根5区960但未应用front全profile。优先439做前摄CCM13动态树+保留disabled语义再PD10/历史实拍。读438README/NEXT/WORKING-BOUNDARIES。原factory refs350/351/412/426/432与mode343复用，未知前摄1928裁剪不套原mode1；完整多模式视频/光学/第五2MP/几何同步继续，284挂原盘/SDKbind串行/429guard/原件私存/scoped commit不push。\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());d.update(stage=438,latest_work_stage=438,last_live_hardware_evidence_stage=438,last_successful_scene_stage=438,last_successful_automatic_ipe_scene_stage=438,
 maintained_userspace_ipa_candidate_stage=437,maintained_userspace_ipa_candidate_build=1,ipe_auto_tone_latest_evidence=prefix+'reference/kernel438/README.md',ipe_auto_dual_pass_evidence=prefix+'reference/kernel438/hardware-validation.json',
 ipe_wide_and_tele_original_auto_tone_verified=True,ipe_wide_tele_same_sof_pd10_gtm_history_verified=True,ipe_wide_tele_awb_locked=True,ipe_wide_tele_evidence=prefix+'reference/kernel438/hardware-validation.json',
 ipe_front_nonidentity_ccm_and_disabled_tmc_gtm_integration_pending=True,ipe_front_bls_original_parser_verified=True,ipe_full_factory_tone_pipeline_complete=False,ipe_main_image_quality_accepted=False,in_progress_installed=False,
 latest438_wide_frames=40,latest438_tele_frames=56,latest438_live_images=96,latest438_math_commits=91,
 current_device_health='438 wide/tele ordinary original tone96 images91math+5bootstrap,8consecutive AWB locks each;formal modules/services/resources restored,no newfault taint0',current_device_last_successfully_restored_experiment='438 r1 wide and tele factory tone with real same-SOF PD10')
 p.write_text(json.dumps(d,indent=2)+'\n')
note='438当前：广角/长焦各自原厂GTM/TMC11/LTM与真实同SOF PD10自动链路实拍通过，96图91数学提交，两路连续8白平衡锁定；复用437源码和434内核，只扩展私有配置及原BLS。前摄IPE非单位矩阵/禁用tone语义及完整画质继续；正式恢复，无fault/taint0，未永久安装。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel438/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel438/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel438/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('437当前：');p.write_text(note+'[438证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();assert '[437 主摄AWB稳态与生效增益关联](reference/kernel437/README.md)' in t
p.write_text(t.replace('[437 主摄AWB稳态与生效增益关联](reference/kernel437/README.md)','[438 广角长焦原厂tone与PD10实拍](reference/kernel438/README.md)'))
print(json.dumps(dict(stage=438,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
