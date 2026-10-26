from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['queue','runtime-codec','source','intree-build','hardware-investigation']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
source=json.loads((HERE/'source-state.json').read_text());hardware=json.loads((HERE/'hardware-investigation-validation.json').read_text())
assert not hardware['complete_ds4_dma_verified'] and not hardware['complete_automatic_tmc_ltm_chain_verified']
archive=ROOT/'archive/NEXT-SESSION-through426-2026-10-21.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text=f'''# 当前检查点：427（DS4底层输出候选已上机；帧内停滞／overflow未解决）

完整多摄／骁龙ISP目标active，未完成，无需用户输入。先读WORKING-BOUNDARIES、reference/kernel427/README.md。426是progress，427有实际内核接线、Werror构建与实机失败定位，不能标为自动链路完成。

## 当前源码与实机结果

维护内核 /mnt/samurai-full282/source354，branch samurai-vfe175-ds4-dma427，HEAD {source['commit']}，parent426 dbefc5bdd8de8da07128171423f098a38d6e45b0。427/ds4-dma.patch相对426，12文件。真实DS4图像节点msm_vfe0_ds4、标准VIDEO_CAPTURE_MPLANE/DMA-SG、独立WM5/group1、参数块8（flags/reserved0，仅系数；流生命周期开关）。本地QP10 FourCC未上游保留，明确description避免核心WARN；逻辑mbus0x2027，像素位序未验证。未改变DT、传感器、OTP/NV/persist。

四摄原厂系数沿用426的提取/模式选择/原Parse和DS410。DS4数据寄存器+precrop+10bitround+PD10pack已接MMIO；原HAL节点ProgramIQModuleEnableConfig 0x2a8900补充发现DS4 Y/C局部crop/round/clamp使能0xd8c/dac=0xe00。夹具节点0xff74 FULL、+4 DS4 bool=1，calc输入沿用DS410+PreCrop+Round+R2PD，完整汇总21寄存器；不是完整HAL节点初始化或真实IFE striping。7组几何actual C与原指令72B逐字一致、hostASAN/UBSAN+ARM64 qemu通过。裁剪几何仍由夹具提供，须恢复真实IFE几何，不能把局部oracle当硬件验收。

运行候选640x480 FULL对应160x120 PD10，stride768/slice60/46080B；WM活动宽640bytes、高60，frame_inc是含slice padding的layout.bytes。32bit IOVA/SG/16B对齐约束保留。缓冲拥有后arm WM、写地址FIFO、单次reg_update，空队列不启DS4。修复旧RDI fallback提前启动，WM arm顺序对齐现有路径；顺序修正本身未解决物理问题。断粮/重开/共享SOF/独立完成/缺校准与SOF错误仅模型通过，实机尚未验收。

实际临时事务r1..r8均terminal，正式模块/服务/格式恢复。r1探针memcmp附加字段过严；r2/3诊断不足，r3还发生未先poll构建终态便准备载荷，不能依赖其新版诊断；r4起source+binary SHA guard且终态后stage。r5加FULL对照/SOF；r6 FIFO顺序仍失败；r7局部使能仍失败；r8诊断确认DMA部分写入而无完整DONE。

最新r8 FULL-only对照24帧正常、tail未改；同开656 SOF但FULL/DS4均0交付。停流后安全读未交付映射：DS4仅首buffer前4 packedrows变化，前三行到byte639、第四行到511，后续全未写；FULL首buffer也只写一部分，其它buffer未写。不是图像/统计成功，不交IPE、不推进IPA历史。IRQ status1见0x800/1000；OEM281 camif error_mask1=0xefff7e80命中、原camif归overflow。无新SMMU/WARN并不代表无硬件错误！原先ISR未报告这些错误。r8诊断时间窗内错误IRQ密集，最后源码只在前4SOF事件输出，日志收敛后构建不改像素配置。最新实际二进制SHA b5b94ec927765f0ca007696fd89d53d37d1386ffdd2c941d6d7f202704df466d，最终源码/构建是后续只改日志版本，别混为一个。

## 下一步直接定位帧内回压

优先对照原厂真实IFE裁剪/striping、模块局部使能与输出端口、WM消费/行数/队列，解决0x800/1000内部overflow；不要重跑已过数学矩阵或盲加新版ISP位。现有partial DMA证明开始写但不能证明格式/完整像素。内核对这些错误应最终有可追踪失败回执，未交付的SOF不能推进任何数值历史。完整DS4后再验同帧FULL配对、断粮恢复/晚开/重开/独立停止。

随后连接真实PD10→IPE粗级backing、C multipass striping、scratch/session/frame端口1，验证DC写出/full IP消费，再合并IPA自动触发和最终成功历史实拍。425原HAL+FW oracle已证明DC双遍：640/650 scratch71488/75584，不能用单遍48；CONFIG_IO+2896是遍次，不是BL，HAL minBL181024。旧C固定单遍；较新fromDownscale未证本机支持。

TMC11实际触发/BHIST1024+曝光/gain/lux→LTM13与IPEGamma及6008B request/成功history沿用423/424，当前同帧上游GTM生效版本因果仍缺。IFE/BPS GTM与IPE LTM必须区分；TMC非零GTM份额不能清零伪造完整。前摄OEM TMC关保持，单曝光unityDRC/noHDR/noLED/no-face不等于完整AndroidAEC。

## 设备与恢复

same394启动，Image363/DT389/CAMSS389正式、420 r31/r26+419 core/adapter未永久改。首次reload前793 IPE direct成功已归档，reload后每模块生命周期jobs=completed=failed=cancelled=0，无新IPE job；这不是历史job失败。owner_refs53桌面枚举，资源/电源/映射均释放，taint历史512不增，PW/WP各1恢复。最新成功现场照片仍424：410帧/402history/2Focused且仍雾感偏色；本轮pattern失败使scene分支未执行。其它模式/视频/第五2MP身份等见363/REMAINING-CAMERA-SCOPE。

所有构建/设备worker终态后才能改依赖或新部署。每次WSL source/build/ext4访问先root storage284.mounted_build挂原32GiB镜像；source354/build不重建格式化。Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。OEM原件、完整ASM/寄存器/系数/图像只在private；公共保留泛化代码与脱敏记录。本地mirror scoped提交保护其它index和3处工作树，不push；完整目标继续active。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从427继续完整多摄ISP目标。先读NEXT与427README。DS4标准图像节点/WM5/group1/原厂参数与MMIO候选已接入，完整节点enable汇总恢复局部d8c/dac E00。模型/Werror通过；实机FULL-only24帧正常，同开656SOF但无FULL/DS4 DONE，DS4仅首buffer前4packedrows部分写入。IRQ1 800/1000命中OEM EFFF7E80 overflow，不能称无硬件错误。r1..8终态恢复正式模块/PW/WP，历史taint512，reload后IPE生命周期计数0而非失败；新scene未执行。下一步定位真实IFE几何/striping与消费者帧内回压，验完整PD10及停启后再接IPE粗级双遍/DC/fullIP，合并IPA自动history实拍。GTM仍是独立上游因果缺口。候选未永久安装，正式r31/r26+419不改；最终源码仅把诊断限前4SOF，见source-state。先storage284，terminal后改依赖，原件私存，scoped本地提交不push。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=427,latest_work_stage=427,in_progress_installed=False,latest_work_phone_accessed=True,current_device_revalidated_stage=427,
  current_device_revalidation427_scope='Temporary DS4 experiment failed; formal module build-ids/services/resources restored. No new scene or IPE frame.',
  vfe175_ds4_latest_evidence=prefix+'reference/kernel427/README.md',vfe175_ds4_pixel_dma_runtime_implemented=False,
  vfe175_ds4_transport_candidate_connected=True,vfe175_ds4_transport_candidate_installed=False,vfe175_ds4_partial_dma_observed=True,
  vfe175_ds4_valid_complete_frame_count=0,vfe175_ds4_full_sof_pairing_verified=False,vfe175_ds4_hardware_error_status1='0x1800',
  latest427_ipe_module_lifetime_counters_reset_by_reload=True,latest427_ipe_jobs=0,last_successful_scene_stage=424,
  ipe_ltm_full_dc_coarse_pass_implemented=False,ipe_full_factory_tone_pipeline_complete=False)
 if '/kernel/' in rel:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'],maintained_vfe_ds4_codec_candidate_stage=427,maintained_vfe_ds4_transport_candidate_stage=427)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='427当前：原厂DS4已接底层图像输出候选并上机；FULL单独24帧正常，同开只有部分DMA写入且发生内部overflow，尚无完整DS4帧或自动DC实拍。已恢复正式驱动与桌面服务，r31/r26+419未永久改。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel427/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel427/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel427/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('426当前：');p.write_text(note+'[427证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[426 原厂DS4参数与VFE175编码](reference/kernel426/README.md)';assert needle in s;p.write_text(s.replace(needle,'[427 DS4底层接线与实机帧内停滞](reference/kernel427/README.md)'))
print(json.dumps(dict(stage=427,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
