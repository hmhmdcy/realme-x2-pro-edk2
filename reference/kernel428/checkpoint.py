from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['native-crop-production','runtime-codec','source','intree-build','hardware','pixel-layout']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
source=json.loads((HERE/'source-state.json').read_text());hardware=json.loads((HERE/'hardware-validation.json').read_text())
assert hardware['total_paired_full_frames']==hardware['total_ds4_frames']==144 and hardware['ipe_jobs']==0
archive=ROOT/'archive/NEXT-SESSION-through427-2026-10-21.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text=f'''# 当前检查点：428（原厂 Crop 修正色度坐标；四摄 DS4 完整同帧输出通过）

完整多摄／骁龙 ISP 目标 active，未完成，无需用户输入。先读 WORKING-BOUNDARIES、reference/kernel428/README.md。427 是实际接线和失败定位的 progress；428 是原厂真实几何生产纠错、底层修复和四摄实机通过的 progress。下一步直接接 IPE 粗级消费，不重跑已过数学矩阵。

## 维护源码与修复根因

原32GiB镜像 /mnt/samurai-full282，source354/build。HEAD {source['commit']}，branch {source['branch']}，parent427 a993cd8a1db892bb5d68d9e6bcccfcc048aec9fd。precrop-chroma.patch 相对427仅一文件修正色度crop X：交织色度分量宽仍等于FULL，只有高度减半。427夹具注入半宽X，局部oracle只证明错误输入的寄存器一致，不能当有效几何。428先绕过precrop诊断r3成功，再原使能恢复且X修正r4/r5/r6成功；precrop-isolation.patch仅中间诊断，不要安装。

执行本机HAL完整FULL Crop Create315e88/Execute3161b0，path0 VideoFull（1是FD）。构造cfg必须有效可写；最后hook确认无写原映像。cfg/full尺寸和MNDS比例+144给定，产生calculated+2c78 preCrop：640x480时Y(0,0,639,479)、C(0,0,639,239)。再原PreCrop/DS410/Round/R2PD/NodeEnable，7组actual C逐字一致、hostASAN/UBSAN+ARM64 qemu过。5组wholeCrop生产检查过；MNDS完整执行、任意sensor ROI/striping未完成，不能扩大范围。原厂系数和4物理模块/模式选择沿用426；原件私存。

最新Werror build r2 10匹配模块终态通过，CAMSS a9096d39b368eff3c59c133fd03e493d65294edc0635cf6c5ded46df9f5050c7，core ae2ca7e3ede81ccb019422d7250376c23377537d2c328571817a3390db179099不变425，m2m不变427。共享build输出和配置恢复，源码干净、补丁无fuzz/offset复放。无DT/传感器/ABI/队列变化，无永久安装。

## 最终硬件与像素结论

r6 worker终态通过：主GW1 4608x3456/tele3M5 2104x1560/frontIMX471 2304x1728/wideIMX319 1632x1224，各现有一模式顺序拍。FULL640x480 NV12+DS4160x120 PD10，stride768/slice60/46080B，WM5/group1。main FULLonly24；8个pattern/scene各18DS4，共144完整帧，全部同SOF FULL完成伙伴，共236同时FULL。每次断粮一处预期SOF缺口、恢复成功；DS4独立停流后FULL至少再6帧。所有mmap尾部与PD10行padding未改。采样前4SOF共32诊断未命中OEM CAMIF错误掩码，不代表所有错误注入验收。

V4L2 timestamp是DONE完成时刻，seq才是SOF标签；两个DONE差最多154us，不要求时间戳相等。r5旧探针3缓冲且每FULL落盘导致main-scene一个DS4无FULL伙伴，不能声称r5有144配对。r6四缓冲、只保存FULL第4/18帧+所有DS4后通过。未来生产仍必须丢弃孤立粗级帧，hold已提交历史，不能依赖probe永不掉帧。

r1尺寸替换损坏460800前置失败，r2tele复现partialDMA，r3bypass诊断成功，r4恢复precrop+正确X成功；r5/r6四摄成功。均终态恢复正式模块、媒体格式、PW/WP。r6私有capture-collected-r6，公共hardware/pixel-layout/source等validation可复查。

PD10每8byte：6个高8bit字节，随后LE低12bit按同6分量顺序各2bit，高4reserved；分量存储Y00,Y10,Y01,Y11,Cb,Cr，raster索引0,2,1,3。3普通色条共7904恒定邻域10bit差最多3；main ShadeColorBars有垂直渐变，不能套等值色条。4路scene全24排列各自最佳均列优先，参考只是近似4x4均值，不等于精确原厂filter相位；144帧reserved高4均零。pd10.py为诊断decoder，QP10仍本地未保留FourCC。已查看front FULL/coarse构图色彩相符，但上游仍雾/偏色，未声称最终画质校准完成。

## 下一步直接接真实 PD10 → IPE

425原HAL/FW已经证明DC0一遍/DC1两遍、PD10端口1影响CDM重定位，640/650 scratch71488/75584；CONFIG_IO+2896是遍次，不是BL，HAL minBL181024。旧维护C仍固定单遍48，不得继续。连接真实PD10 backing所有权、C multipass striping、scratch/session/frame端口1；先证明DC统计实际写出及full IP消费，然后合并IPA。避免新固件fromDownscale猜测，本机未证。

处理域：GTM在IFE/BPS上游，LTM在IPE。TMC非零GTM份额与同图像实际应用版本因果仍缺，不得清零伪造完成。423/424现有IPA实际曝光/gain/lux+同SOF preWB1024BHIST+IFEgamma→原TMC11→LTM13/IPEGamma→6008B request、最终成功才提交数学history、单pending/缺BG或lux hold。424最后自动IPE现场410帧/402history/2Focused且雾偏色；428是新IFE现场成功，不是新自动IPE成功。front OEM TMC关保持；单曝光unityDRC/noHDR/noLED/no-face不等于完整AndroidAEC。

same394启动、Image363、DT389/CAMSS389正式、420 r31/r26+419 core/adapter未改。427reload前793历史IPE完成保留，reload后当前生命周期jobs/completed/failed/cancelled=0，428无IPE job；不是历史失败。owner_refs53桌面枚举，资源/映射/电源释放，taint历史512不增。其它模式/视频/第五2MP身份见363/REMAINING-CAMERA-SCOPE。

每次WSL source/build/ext4前先root storage284.mounted_build挂原镜像，不能重建格式化。构建/worker先poll terminal再stage/deploy；无pending shell或remote worker。Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。OEM原件/ASM/系数/图像仅private；泛化代码/证据public。mirror scoped本地commit保留其它index和3处工作树，不push，完整目标继续active。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从428继续完整多摄ISP目标，先读NEXT和428README。已执行原HAL完整FULL Crop生产纠正DS4色度X半宽夹具错误；正确X按交织分量全宽，Y半高，原precrop使能恢复。维护HEAD906a6b9d，最终build r2；r6四物理摄像头各pattern+scene共144真实PD10全部同SOF FULL配对，断粮/恢复/独立停流通过。PD10列优先亮度Y00,Y10,Y01,Y11，实际数据/填充检查过。正式模块和服务已恢复，taint512，当前IPE job0。下一步直接接425双遍模型：真实PD10 backing、multipass striping、scratch/session/frame port1，证明DC统计写出和full IP消费，再补GTM应用因果及IPA自动TMC/LTM最终成功history实拍。428只完成IFE现场，最后自动IPE仍424。先storage284、terminal后依赖、原件私存、scoped本地提交不push；目标active。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=428,latest_work_stage=428,in_progress_installed=False,latest_work_phone_accessed=True,current_device_revalidated_stage=428,
  current_device_revalidation428_scope='Temporary four-camera FULL/DS4 capture passed; formal modules/services/resources restored. No IPE job.',
  vfe175_ds4_latest_evidence=prefix+'reference/kernel428/README.md',vfe175_ds4_pixel_dma_runtime_implemented=True,
  vfe175_ds4_transport_candidate_connected=True,vfe175_ds4_transport_candidate_installed=False,
  vfe175_ds4_valid_complete_frame_count=144,vfe175_ds4_full_sof_pairing_verified=True,vfe175_ds4_last_test_stage=428,
  vfe175_ds4_last_test_sampled_camif_error_bits=0,vfe175_ds4_hardware_error_status1='0x0',
  vfe175_ds4_hardware_error_scope='First four SOF samples per stream in428; historical427 overflow was0x1800',
  vfe175_ds4_precrop_chroma_x_corrected=True,
  vfe175_ds4_pd10_pixel_layout_verified=True,latest428_ipe_jobs=0,last_successful_scene_stage=428,
  last_successful_automatic_ipe_scene_stage=424,ipe_ltm_full_dc_coarse_pass_implemented=False,ipe_full_factory_tone_pipeline_complete=False)
 if '/kernel/' in rel:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'],maintained_vfe_ds4_codec_candidate_stage=428,maintained_vfe_ds4_transport_candidate_stage=428)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='428当前：原厂FULL Crop纠正DS4色度裁剪X，四摄共144完整PD10全部与FULL同SOF配对，断粮恢复／独立停流和像素排列检查通过。尚未接IPE粗级消费者，完整自动TMC／LTM仍未完成；正式模块／服务已恢复。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel428/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel428/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel428/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith(('427当前：','428当前：'));p.write_text(note+'[428证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[427 DS4底层接线与实机帧内停滞](reference/kernel427/README.md)';replacement='[428 四摄DS4同帧输出与原厂裁剪纠错](reference/kernel428/README.md)';assert needle in s or replacement in s;p.write_text(s.replace(needle,replacement))
print(json.dumps(dict(stage=428,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
