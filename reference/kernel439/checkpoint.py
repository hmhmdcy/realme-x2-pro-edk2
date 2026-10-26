from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['hardware','source','colour-math','front-profile','front-math','front-module','ipa','build','replay-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
live=json.loads((HERE/'runtime-r1-validation.json').read_text());assert live['state']['terminal'] and live['state']['passed'] and not live['worker_live'] and not live['client_live']
archive=ROOT/'archive/NEXT-SESSION-through438-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：439（前摄原厂 IPE CCM13 自动链路与实拍通过）

完整多摄/ISP目标active。先读WORKING-BOUNDARIES和reference/kernel439/README。前摄IMX471 mode1/2304x1728原厂非单位IPE CCM13、LTM/Gamma与真实同SOF PD10、实际GTM/WB版本和最终成功数学历史已接通；原IFE CCM、TMC10/11、GTM关闭状态保持。原生40图38math+2bootstrap，隔离43图41math+2bootstrap，共83图79成功math；隔离停机后1份未入队提案丢弃，不算图像/成功历史。两路末尾8连续locked，分别4/5帧相同实际WB保持锁定。关闭GTM时实际只观测bank0。

## 当前源码和部署

候选 /mnt/samurai-full282/libcamera439-front-colour/src/libcamera-v0.7.2，从437复制，9源文件变化。build1/IPA5：库50935792B/32cd8d4145ccb1c0f7c47a2e2d0dd9b36e8dd2364c68570d89dbbbc9c88e51be；IPA8183768B/3f83969b6e23311fed22f3f03dba6af514c4e16a293994fbf9903a50f6782e7a；sign bd9869b26859582c9f6e2533a9441e44c5e81fca39b4fcf97f5d075fc90b3791；proxy仍093df5faa73b42b741e2b61d862fefc292fcf7ced2ccfb6f6f9389f70b182dcf。Mojom未变、0050补丁零fuzz/offset重放。439/storage只在新候选不存在时回437。

内核仍source354 HEAD9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3/samurai-vfe175-gtm-reopen434，匹配434 CAMSS3edb28d1/core d391fa24/m2m e6828a0c；未改板级/SoC/sensor。正式仍420/419、Image363/DT389。本轮临时模块/服务/资源已恢复，newfault0/taint0，worker/client均终态，未永久安装。

## 数学、配置和证据

通用色彩数学区分IFE整数偏移逐级截断/11位量化与IPE浮点偏移逐级插值/13位量化，矩阵均12位Q(7+shift)。共享已有五级调校树选择器，IPE RGB到GBR排列仍由原底层编码器负责。原HAL DoInterpolation0x47ebf0+完整CC13计算/CDM，对主机/ARM64各1164例181584B零差：737原厂区域、前摄243插值及小数偏移边界随机；旧IFE oracle byte相同。ARM64前摄完整原树3坐标与原指令零差；实际IPA DSO的未来CCT/手动控制延迟生效、旧帧冻结、失败不提交、重启及main legacy/bypass/GTM回归通过。

前摄private kernel439/factory-imx471-private.yaml复用343/350/351/412/426/432及438原BLS解析。mode1/2304: CCM UID47/28区25不同非单位矩阵；LTM42/3AEC，TMC11 63/1，Gamma3，GTM21，DS4 33/PASS_FULL。编号不代表跨文件同表。IFE CCM关、TMC10/11关、GTM关，LTM/Gamma开，BLS960U14恢复3840U16/norm2175/2048。1928x1088缺原mode绑定不改。

每帧冻结实际WB/ISP上下文中的CCT/手动矩阵并复制进同帧统计观察，成功IPE图像后提交颜色数学历史和实际有效矩阵元数据。缺CCT明确保持上一成功颜色、首次单位矩阵；不编造CCT。两路SOF12保存真实FULL460800B、PD1046080B、IPA6008B及同帧输出。固定输入5次硬件回放：stock重复==原实拍逐字节；单独关闭LTM或IPE CCM均改变像素，source像素未改。83图+5replay=88硬件完成。未新增DC SRAM逐字节dump或PD10扰动，DC清理/遍次沿用430/434。

439预览为近距离键盘/桌面，偏暗，末端CCT1500K达到下限，曝光/增益达上限；不能以锁定作绝对色准/清晰度完成。NV12/sYCC全范围BT601仅诊断解码。原件/系数/照片/日志/ELF仅E:/edk2-samurai-out/kernel439。

## 下一步与完整范围

439实拍只前摄；主摄437、广角/长焦438证据保留，不能冒认已在439整合版重验。主摄原BLS/tone候选kernel437，广角/长焦kernel438各自private profiles；后两路438共96图91math+5bootstrap、各8locked、GTM两个bank，实际仍437源码。下一步整合四摄当前配置+439库+434模块为可恢复发布套件，并在同一cohort回归，随后更多尺寸/视频及legacy/manual/v2/HDR完整分支、光学/色板/均匀场/噪声清晰度。第五2MP、个体校准和多摄几何同步等363完整范围仍未完成。

每次WSL source/build/ext4先root调用284/storage.mounted_build，挂原E盘32GiB，不格式化；SDK bind串行。清理20261022删除旧.o/.a/重复未剥离文件和缓存，共8.8GiB含E盘构建卷；保留当前420/435/436/437与source354，WSL压缩并恢复稀疏。439新候选已另建，旧中间文件缺失可正常重建。429 guard/key/knownhosts，USB SSH正常；不恢复429越界诊断。镜像本地提交见git与private local-mirror-validation；439开始HEAD41def451b6bc9716d94674cb77f6ead7a39490c1，保留无关index/worktree/untracked，public导出/scoped commit不push。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/ISP目标。439已接前摄IMX471 mode1/2304x1728原厂IPE CCM13非单位树+LTM/Gamma+真实同SOF PD10，保留IFE CCM/TMC10/11/GTM关闭，原BLS960恢复3840/norm2175/2048。原生40图38math+2bootstrap，隔离43/41+2，共83图79成功math，另1停机提案丢弃，两路8连续AWBlocked；关闭GTM实测bank0。5硬件回放stock重复==实拍，关LTM或CCM均变像素；88总完成，正式模块/服务/资源恢复，newfault0/taint0未永久安装。共享色彩浮点/整数路径，原HAL1164例host/ARM64零差，旧IFE不变；完整原树/实际IPA未来CCT与手动控制冻结/失败history/旧主摄回归通过。候选libcamera439-front-colour，库32cd8d41 IPA3f83969b signbd9869b2 proxy093df5fa，build1 IPA5 Mojom未变，0050补丁。kernel434 source354 HEAD9bc07e63未改。读439README/NEXT/WORKING-BOUNDARIES。下一步整合四摄候选配置(主437、wide/tele438、front439)+439库+434模块为可恢复发布cohort并回归；439物理只前摄不冒认四摄。前摄近距离键盘暗样本CCT贴1500K/增益曝光上限，不算绝对色准或清晰度。未知1928裁剪、完整模式视频/HDR、个体光学/第五2MP/多摄几何同步继续。原32GiB盘284挂载、SDKbind串行、429guard、原件私存、scoped本地commit不push。\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());d.update(stage=439,latest_work_stage=439,last_live_hardware_evidence_stage=439,last_successful_scene_stage=439,last_successful_automatic_ipe_scene_stage=439,
 maintained_userspace_ipa_candidate_stage=439,maintained_userspace_ipa_candidate_build=1,maintained_userspace_ipa_candidate_source='/mnt/samurai-full282/libcamera439-front-colour/src/libcamera-v0.7.2',maintained_userspace_ipa_candidate_evidence=prefix+'reference/kernel439/build-validation.json',
 ipe_auto_tone_latest_evidence=prefix+'reference/kernel439/README.md',ipe_auto_dual_pass_evidence=prefix+'reference/kernel439/hardware-validation.json',
 ipe_front_nonidentity_ccm_and_disabled_tmc_gtm_integration_pending=False,ipe_front_original_auto_colour_tone_verified=True,ipe_front_original_ife_ccm_disabled=True,ipe_front_original_ipe_ccm_enabled=True,ipe_front_original_tmc_gtm_disabled=True,ipe_front_same_sof_pd10_colour_history_verified=True,ipe_front_native_and_isolated_verified=True,ipe_front_evidence=prefix+'reference/kernel439/hardware-validation.json',
 latest439_delivered_images=83,latest439_successful_math_commits=79,latest439_bootstrap_images=4,latest439_discarded_stop_proposals=1,latest439_fixed_input_replays=5,latest439_stock_replay_matches_live=True,latest439_all_four_camera_cohort_retest_pending=True,
 ipe_full_factory_tone_pipeline_complete=False,ipe_front_absolute_quality_accepted=False,in_progress_installed=False,
 current_device_health='439 front83 delivered/79math+4bootstrap,1 stop proposal discarded;5 fixed-input replays,stock equals live;formal modules/services/resources restored,no newfault taint0',current_device_last_successfully_restored_experiment='439 r1 front factory IPE CCM and LTM with real same-SOF PD10')
 p.write_text(json.dumps(d,indent=2)+'\n')
note='439当前：前摄原厂IPE CCM13与LTM/Gamma及真实同SOF PD10实拍通过，83图79成功数学提交+4bootstrap；5回放stock重复等于实拍，关LTM或CCM均改变输出。原TMC/GTM/IFE CCM关闭保留。正式恢复，无fault/taint0，未永久安装；绝对画质、四摄整合发布及完整范围继续。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel439/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel439/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel439/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('438当前：');p.write_text(note+'[439证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();old='[438 广角长焦原厂tone与PD10实拍](reference/kernel438/README.md)';assert old in t;p.write_text(t.replace(old,'[439 前摄原厂IPE CCM与自动PD10实拍](reference/kernel439/README.md)'))
print(json.dumps({'stage':439,'next_bytes':(ROOT/'NEXT-SESSION.md').stat().st_size,'full_goal_complete':False,'passed':True}))
