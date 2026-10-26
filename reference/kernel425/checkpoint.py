from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['io','multipass','source','intree-build']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
archive=ROOT/'archive/NEXT-SESSION-through424-2026-10-21.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text='''# 当前检查点：425（原厂PD10粗级IO已恢复；DC双遍原固件命令确认，尚未实拍）

完整多摄／骁龙ISP目标active、未完成。先读WORKING-BOUNDARIES与reference/kernel425/README。425是真实底层进展：维护内核代码、原厂完整双遍prepare、构建通过；不是新的设备采集。424交接归档archive/NEXT-SESSION-through424-2026-10-21.md，不重跑旧矩阵或旧实拍。

## 425当前源码与已验证结果

维护内核/mnt/samurai-full282/source354，branch samurai-ipe-coarse-io425，commit faf093770826a3bbe4b6f21f3b93303c62591627，parent419 07d2ca735f88649587c0e89802febff6dbf2b443。三文件补丁增加camss_a5_ipe_pd10_quarter与共享camss_a5_ipe_encode_io可选粗级端口。普通runtime仍传NULL，尚无实际粗级session提交/PD10像素生产，没有新UAPI或板级改动。源码干净、零fuzz复现。

本机完整HAL InitializeFormatParams0x453ab8/SetConfigIOData0x2e4b88证明Camx PD10=18，固件格式10，单平面。quarter=((full+7)/4)&~1；stride=ceil(qw*4/192)*192；slice=ceil(qh/8)*4；bytes=stride*slice。本机与较新Camx额外256byte/32line规则不同。640x480→160x120,stride768,slice60,46080B；650→164x120同bytes。未猜PD10像素位序。

check-io实际候选C函数，64组/24invalid每架构，host ASAN/UBSAN和ARM64静态qemu156928B一致；PD10layout和84B描述符对照本机原指令，NULLcoarse与旧419NV12/NV21输出相同，错误输出保持。小布局有效不代表满足DC最小尺寸。

check-multipass使用实际ARM64 C IO→完整原厂HAL Create/Execute/Destroy→完整ICP CONFIG_IO/frame prepare，无enqueue/无DMA。在640/650两宽、DC0时配置2但实际stripe1遍且无PD10引用；DC1实际2遍、PD10地址引用1处、LTM控制写2次。striping/job/CDM实际变化；PD10改址仅改变对应命令输入地址。scratch71488/75584，不能用单遍48。CONFIG_IO+2896=配置遍次，不是BL容量；HAL minBL181024。完整原件私存kernel425。测试初期DC0也应2遍/读PD10的断言被原厂否定，已修正，不是原厂函数失败。

W=1/Werror core-only内核构建24.27s、零诊断，boot.o/ipe.o等实际重编。core候选SHA ae2ca7e3ede81ccb019422d7250376c23377537d2c328571817a3390db179099，未安装。构建terminal；共享目录恢复，包括原本不存在的ICP .ko/.o；qcom-camss.ko与before逐字节相同。勿用旧报告的“standard helper build”字段；425已改成仅core构建的准确元数据。

## 下一实际工作：硬件生产PD10与完整粗级运行时

固定CamxChi /home/cy122/x2pro-linux/refs/CamxChi-k117，rev9f17f1b568626b393e785b369c5dc94543774d7a；原HAL camera.qcom.so SHA e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde；ICP SHA a22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。sources私存425/sources。

本机SetConfigIOData无新参考的fromDownscale绑定，HAL无fromDownscale/InternalDownscale/DownscaleInput字符串。不能凭此宣称所有内部降采样不存在，但不能套新版本标志或向硬件提交空PD10。固定参考IFE DS4端口输出ISPFormatPD10并开videoDS4R2PDEnable；DS410/precrop/roundclamp来源已私存。当前camss-vfe-17x只注册FULL/params/stats三个输出，VFE175尚无DS4注册/DMA生命周期。

优先从原厂实际DS4寄存器/WM/R2PD恢复VFE175 DS4生产，严格对齐FULL的尺寸/裁剪/同SOF；然后接IPE粗级backing所有权、C multipass striping、scratch容量、运行时session和frame端口1地址。原厂LTMDCStripeConfiguraion0x1556a0及mode0x155770/outW0x1557a8/outH0x1557b8可复用。native-model.py全HAL和firmware-model.py全FW能做反例/差分。当前用户UAPI未扩展。禁止把普通像素变化、scratch额外字节、DC标志当粗级统计生产通过。接通后实际检查粗级内容→DC写入→全尺寸IP消费，再合入IPA当前同SOF/最终回执数值历史并实拍。

GTM另属IFE/BPS域：原厂TMC输出确有非零GTM份额，尚未实际应用；实际GTM Execute0x31fc00/setting0x37c818已定位。需本机树/数学与IFE参数生效版本→对应图像IPE因果绑定，不能把当前hist算出的曲线声称已应用上游同帧，不能清零gtmFraction伪造完整。

## 设备与已有IPA成果（本轮没有访问设备）

最近实际424：普通/隔离IPA各205真实主摄图像，402数值提交、各161 Scanning，最终两次Focused。已看图：中心细节提升仍雾感偏色。当前793direct、failed/cancel/firsterror0、25starts/stops，核心电源/时钟/IRQ/映射/DMA/导入释放，users/running/fatal/pinned/orphans0，桌面owner_refs53；PW/WP恢复。历史taint512保持。worker/client/collector终态，425无新手机实验/照片。

正式仍420 libcamera99990.7.2-r31/配置0.1.0-r26，419 core SHA63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632与adapter46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f。Image363/DT389/CAMSS389/FW/SGowner不改。候选424 IPA SHA324a821f1c72f0ebb983d73f33a4500c4d696640932c362e0020e10958088129未永久安装。424已修LTM衰减lux而非曝光乘积，缺BG/lux持有committed，不推进历史；token/epoch/fail仍校验。原生主摄4608x3456单曝光unityDRC/HDR/LEDoff/no-face策略非完整Android，前摄原厂TMC关闭保持。其它镜头/视频/2592硬测/第五2MP身份mux等见reference/kernel363/REMAINING-CAMERA-SCOPE.md。

每次WSL source/build/ext4访问先root storage284.mounted_build挂原32GiB镜像，不重建/格式化。Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。构建/命令handle须terminal后才改依赖输入或部署。原厂ELF/系数/ASM/CDM/完整日志/图像仅private，公共作者代码+脱敏摘要；本地scoped mirror护其它index，不push。没有需要用户输入的实际阻塞；继续功能工作。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从425继续完整多摄ISP目标，先读NEXT与425README。已在维护内核加入本机PD10 quarter布局/可选IO，64组C跨架构/native对照及Werror core构建通过，未部署。完整原HAL+FW确认粗级端口存在时DC0实际1遍/DC1实际2遍，PD10地址真实消费、scratch71488/75584；不能延用单遍48或把标志当统计。当前关键是VFE175 DS4硬件生产与FULL同SOF配对→IPE粗级backing/C striping/scratch/session/frame绑定→DC产出/fullIP消费实拍；较新IPE内部downscale未证明本机支持，不能套标志/空PD10。源码faf09377/branch425干净；425无手机访问，最近实拍424各205帧/402数值提交/两次AF成功仍偏色雾感，正式r31/r26+419不改。GTM IFE域非零份额与因果生效版本仍缺；其它镜头/视频/第五2MP保持scope。原厂私存，WSL先storage284，构建terminal后改源，本地提交不push。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=425,latest_work_stage=425,in_progress_installed=False,
  ipe_ltm_pd10_coarse_io_candidate_implemented=True,ipe_ltm_pd10_coarse_io_candidate_installed=False,
  ipe_ltm_coarse_native_two_pass_prepare_verified=True,ipe_ltm_coarse_pd10_pixel_producer_implemented=False,
  ipe_ltm_full_dc_coarse_pass_implemented=False,ipe_full_factory_tone_pipeline_complete=False,
  ipe_ltm_coarse_latest_evidence=prefix+'reference/kernel425/README.md',
  latest_work_phone_accessed=False)
 if '/kernel/' in rel:d.update(maintained_branch='samurai-ipe-coarse-io425',maintained_commit='faf093770826a3bbe4b6f21f3b93303c62591627',maintained_core_io_candidate_stage=425)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='425当前：内核PD10粗级IO与Werror构建通过，完整原厂程序确认DC开关实际增加IPE遍次并读取独立PD10；现场粗级生产／统计／消费尚未接通，没有新增实拍或安装候选，正式r31/r26+419保持。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel425/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel425/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel425/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('424当前：');p.write_text(note+'[425证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[424 LTM输入域修正、恢复与AF实拍](reference/kernel424/README.md)';assert needle in s;p.write_text(s.replace(needle,'[425 PD10粗级IO与原厂DC双遍](reference/kernel425/README.md)'))
print(json.dumps(dict(stage=425,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
