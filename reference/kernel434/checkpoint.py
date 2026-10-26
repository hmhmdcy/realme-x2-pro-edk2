"""Record physical IFE progress while keeping production IPA/history pending."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['hardware','source','reopen','intree-build']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
archive=ROOT/'archive/NEXT-SESSION-through433-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：434（原厂GTM实机生效、双bank重复性、重开流修复）

完整多摄／ISP目标active。先读WORKING-BOUNDARIES、434/README。r2主摄61组测试图+19组实景，FULL/真实PD10/统计同SOF，GTM回执与像素变化匹配。正式环境恢复，无fault、taint0，未永久安装。**生产IPA GTM→已生效版本→不可变数学对象→IPE成功历史未接通。** 本轮IPE jobs0；自动双遍48帧48历史仍431证据。

## 源码与产物

维护kernel source354 HEAD9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3，branch samurai-vfe175-gtm-reopen434，parent433 04f8c5a3，clean。唯一改camss-vfe-17x.c开流顺序：SM8150 PIX在首包参数defer前持output_lock清理旧流遗留软件RUP位，保留RDI位，运行中排队/ACK/SOF不改。patch reference/kernel434/gtm-reopen.patch。实际vfe_enable体ASAN/UBSAN覆盖残留位、二次打开、错误清理、非PIX，passed。十匹配模块W1/Werror诊断0，共享构建outputs/config/symvers恢复。

private kernel434 qcom-camss-intree-r1.ko2935224B SHA3edb28d1fc5f23eb208ecc9532db4fcb1617f3f0f3ff821c0af2f60a90006ca2，core439608B/d391fa24和m2m141624B/e6828a0c同431。source-validation核对唯一文件/patch零fuzz offset/模块hash。板级DT、sensor、电源和生产用户候选未改。新GTM UAPI需匹配CAMSS，未混装正式旧模块。

## 434实机结果与失败

r1先加载433r2候选，测试图61/61/61、九GTM阶段通过；紧接实景FULL STREAMON ENODATA、0帧。原因：停流最终RUP软件位留下，新流pixel_prepare清DS4配置，而gtm_defer先于原enable_output清位，整包WB+原厂DS4+GTM被延后，DS4校验未配置。失败worker完整恢复正式环境，无新fault taint0；全部原日志/样本保留private runtime-collected-r1，不隐藏失败。

r2加载434修复模块，同次加载连续pattern61组+scene19组，九/三阶段，退出0/fixture恢复0，worker/client终态。最终formal notes同before，PW/WP恢复，DMA资源释放，newfaults空、taint0。runtime-collected-r2已收集265项；无需重启或请求用户恢复。所有本地exec/build终态，无远端活worker。guard仍429用户硬重启后新boot，SSH正常。

测试图九阶段：disable、identity、明确半增益诊断非工厂表、原厂432main step0、step2、step0重复、step0再重复跨另一bank、disable、identity。按真实统计cookie/generation/status/bank与SOF分组，不能用probe proposed phase或参数DQ当生效。每组只有一FULL hash和一有效PD10 hash；disable=identity，half不同，两个stock各不同，stock0三个阶段跨bank完全相等，r1/r2九组hash各自相等。平均Y175.6234→half127.8636；stock0 178.3989、stock2 182.8306。实景关闭79.34→stock0 87.20→关闭79.34，19帧同SOF；PNG已看，室内物体可识别，仍雾感偏绿，绝对画质未验收。

PD10 stride768/60packedrows，active640/row，128padding被probe哨兵填不同值，因此全bufferhash会不同；判断稳定必须比较active。FULL460800B完整NV12。用户QBUF后改写payload验证内核copy，没影响加载。r2pattern保留SOF0–3、8–64有缺号，三输出保留集合相同；同步落盘probe不验收连续视频帧率。scene0–18连续。没有硬件逐项读回GTM LUT、DC SRAM，也没有本轮IPE消费GTM验证。

## 继承的GTM/DC/生产候选

433原厂完整Execute七例及官方GPL DMI64 oracle见其README。CPU lowc30→highc2c，不用HWCDM swap。type9/536B flags0/cookie非零/enabled0或1/reserved0/64unsigned18base+signed26slope；disable全payload、重复GTM拒绝。填inactivebank并恢复共享DMI/CGC。type3/32B真实PIX ACK推进active/generation，每缓冲输入SOF快照。pending/armed/deferred保护，新cookie不冒认旧ACK；stop清。实际driver/queue/ACK/SOF hostASAN/UBSAN和ARM64各9stockLUT+每例200拒绝通过，434不改live逻辑。

432：45stockGTMroots/45叶子，经独立BIN→OEMXML→本机Parse2085f0逐字节一致，464序列化→360runtime。完整原TMC11四摄×3步12调用，rear9有效GTMLUT/front3禁用；portable model2 host/ARM各27exact，12native selector/swap/bank组合。private roots、axes、coeff、ASM，未完整legacy/manual/v2/TMC10。禁止把原厂非零GTM份额清零。

DC与GTMbank不同：RTtype2→kind0→DC/IPbank0，coarse DC1/IP0/sumclear1，FULL DC0/IP1/clear0。同一bank两遍同步；430修nativefinaldistributor丢DC，cold/persistent重复相等，固定FULL只变真实PD10因果改变输出。片内DC整表没有逐字节读回，a7scratch不是统计。429自加越界readl造成Oops已删除，用户硬重启并四摄恢复；危险429build2core da4591...禁止加载，不猜MMIO。

生产候选仍 /mnt/samurai-full282/libcamera431-pd10-auto/src/libcamera-v0.7.2 build7/IPA4。431r4 native/isolated主摄各24帧，48真实同kernelSOF FULL/PD10自动双遍48最终数学提交+4 bypass/DC切换job，52direct0failed，formal restored。DS4仅main4608mode2原厂16B块；单pending数学回执、250ms图像等待、保留迟到统计上下文、NV12同FD相邻Y/UV合并FULL单plane+PD10plane，持有到两DQ/requestDONE/stopjoin；core按validatedDC处理single/dual session切换。其它摄像头/尺寸/视频/第五2MP/光学多摄同步仍363清单。

## 下一步（生产IPA接入）

GTM硬件功能已证明，不需重复整个硬件矩阵。复制/维护新libcamera候选，接432原厂mode选择与GTMmodel2数学，复用当前typed参数和actual回执：统计N生成后续IFE cookieX→实际ACK后的图像M及其PD10/统计标记X→取不可变TMC/ADRC X用于IPE/LTM→最终成功历史关联。图像M的新统计不能倒称已作用其上游GTM；IFE已ACK物理版本与IPE成功math history分开，IPEfailure不能假回滚IFE。保持frontdisabled、缺统计hold、非零GTMshare和失败历史。先相关主机/ARM检查与匹配build，再main普通/隔离IPA自动实景，失败和正式恢复如实保留。

每次WSL source/build/ext4先root import storage284.mounted_build，原32GiB盘不可重建。Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。host434继承433→429guard与原key/knownhosts。private全部kernel434，public仅自有代码脱敏证据；public_module导出/scoped本地commit，保留mirror无关index和三工作树差异，不push。434之前mirror HEAD b2f3b25a。完整目标保持active。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从434继续完整多摄/ISP目标：原厂GTM真实IFE功能已验证，修复重开流残留PIX RUP导致DS4首包延后的ENODATA。kernel HEAD9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3 clean/branch samurai-vfe175-gtm-reopen434，十模块W1/Werror0，CAMSS3edb28d1…；r2同次加载pattern61组+scene19组FULL/真实PD10/统计同SOF，原厂LUT改变像素，同表跨GTMbank输出相同，ACK版本与像素变化匹配。r1pattern通过scene0帧ENODATA保留。正式环境恢复，无fault taint0，所有worker终态，未永久安装。**尚未把GTM接生产IPA/最终history，本轮IPEjob0**，生产候选仍431build7/IPA4，48自动双遍48成功历史。下一步432原厂GTM选择/model2→typed IFE提交→真实cookie关联immutable TMC/ADRC→对应图像FULL+PD10 IPE/LTM→成功history实景，IFE已ACK物理状态与IPE历史分开，不能M新统计倒称影响M上游GTM，非零GTMshare保留/frontdisabled/hold。DC RT2→kind0→bank0粗遍clear写/full读政策及repeatability沿用430/431，未逐字节导出DC SRAM，a7scratch不是统计。先读434README/NEXT/WORKING-BOUNDARIES，storage284挂原盘，429新guard，原件像素私存，不猜MMIO，scoped提交；当前画面仍雾感偏色未验收。\n')
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());d.update(stage=434,latest_work_stage=434,latest_work_phone_accessed=True,last_live_hardware_evidence_stage=434,last_successful_scene_stage=434,last_successful_automatic_ipe_scene_stage=431,
  ipe_gtm_driver_hardware_verified=True,ipe_gtm_hardware_application_verified=True,ipe_gtm_model2_production_ipa_integrated=False,ipe_gtm_applied_version_math_history_association_verified=False,ipe_full_factory_tone_pipeline_complete=False,in_progress_installed=False,
  ife_gtm_hardware_evidence=prefix+'reference/kernel434/hardware-validation.json',ife_gtm_hardware_scope='434 r2 main fixed-exposure IFE only:61 pattern+19 scene same-SOF FULL/PD10/stats; two stock LUTs and both GTM banks; IPE jobs0; production IPA and math-history binding pending',
  ife_gtm_reopen_stale_pix_rup_fixed=True,ife_gtm_candidate_stage=434,ife_gtm_candidate_installed=False,latest434_ife_same_sof_sets=80,latest434_ipe_jobs=0,formal_disk_modules_unchanged_after434=True,
  current_device_health='434 r2: IFE-only GTM pattern61+scene19 same-SOF sets; formal modules/services/resources restored, no new fault, taint0',
  current_device_loaded_module_state='Formal420 CAMSS and419 core/adapter restored after434 r2; loaded notes matched baseline',current_device_last_successfully_restored_experiment='434 r2 main IFE GTM fixed-exposure pattern and scene')
 if '/kernel/' in rel:d.update(maintained_branch='samurai-vfe175-gtm-reopen434',maintained_commit='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3')
 p.write_text(json.dumps(d,indent=2)+'\n')
note='434当前：原厂GTM真实IFE生效，修复重开流残留PIX更新位；61组测试图与19组实景的FULL/真实PD10/统计按SOF对应，双bank重复相等。正式环境恢复、无新增fault、taint0；未永久安装。生产IPA的GTM/已生效版本与最终数学历史尚未接通，本轮IPEjob0，自动双遍仍431的48帧48提交。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel434/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel434/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel434/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith(('433当前：','434当前：'));p.write_text(note+'[434证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();p.write_text(t.replace('[433 IFE GTM与ACK/SOF驱动候选](reference/kernel433/README.md)','[434 原厂GTM实机与重开流修复](reference/kernel434/README.md)'))
print(json.dumps(dict(stage=434,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
