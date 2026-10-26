from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['codec','producer-geometry','source','intree-build']:
 assert json.loads((HERE/(n+'-validation.json')).read_text())['passed'],n
archive=ROOT/'archive/NEXT-SESSION-through425-2026-10-21.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
text='''# 当前检查点：426（四摄原厂DS4参数与VFE175寄存器编码恢复；DMA／实拍未接通）

完整多摄／骁龙ISP目标active、未完成。先读WORKING-BOUNDARIES与reference/kernel426/README。425是progress：PD10布局/IO与原厂DC双遍确认；426新增提取、原指令验证、内核代码和构建。425归档archive/NEXT-SESSION-through425-2026-10-21.md。

## 426实际结果

维护内核/mnt/samurai-full282/source354，branch samurai-vfe175-ds4-codec426，HEAD dbefc5bdd8de8da07128171423f098a38d6e45b0，parent425 faf093770826a3bbe4b6f21f3b93303c62591627；中间1ebfb0711是初版，后补显式linux/bits.h。新增camss-vfe-175-ds4.c/.h及Kbuild，vfe_175_ds4_encode只构造Y/filter/C/R2PD四寄存器，检查高度2..8192偶数、每系数<=256及sum256..512，保留无关位、清旧PD8模式，失败输出保持/允许inplace。没有MMIO、模块开启、DS4节点/DMA注册、用户UAPI、DT/传感器变化，运行时未引用。当前实际DS4生产仍未实现。

从保留333索引/原BIN和模式树提取IFE DS4/DS16/显示四类原厂reserve。SunnyGW1 4根/4普通上下文，IMX471 4/2，Qtech3M5 20/4，IMX319 36/4，共64根*4pass、14上下文*4tag=56模式查询。原厂ParameterParser XML逐项一致，原GetModule选择一致；分析副本仅过滤非目标表解析标记，数据区/模式树不改。系数/XML/全对象私存kernel426。既有物理来源，不认证EEPROM或把QtechGW1另算摄像头。

完整原HAL DS4 Parse 0x1fcdf0输出200B，四pass运行时数组offset136，与独立BIN解码完全相同。真实RunCalculation0x31d130读对象140/144/148，即PASS_FULL系数；不是猜某份pass。64根系数作为first-DS4编码夹具，4高度*3旧寄存器种子=768组，hostASAN/UBSAN和ARM64静态qemu12288B与完整DS410/R2PD原指令0差。每架构10invalid及inplace过。14完整Create/Execute只绑定已选ds4to1v10_ife_full_dc4（不是DS16/显示绑定），Getter由framework provider返回外部原管理器选定并本机Parse生成的对象；寄存器写传输记录provider，数学/依赖更新不替换。未声称全模式管理器也在Unicorn内执行。DS16硬件未实现。

完整原指令DS410→PreCrop→RoundClamp→R2PD同calculated frame覆盖128/640/650/1920/4096五组几何：DS4滤波0xd60起；前裁剪Y0xd84/C0xda4；独立round/clamp Y0xd98/C0xdb8，保留10bit/roundbits0/pattern3；PD10 packmode0，R2PD0xd6c；0x4c模块使能合计0x5500（Y/C降采样+precrop+R2PD）。原厂GPL总线DS4=WM5、packer0、活动宽align(qw*4,16)bytes，高qh/2。backing仍425规则192byte/4packedrows，不能把WM活动宽度当stride。这些仅配置证据，非实际像素/统计产出。

W=1/Werror构建r3 48.30s，CAMSS/core/adapter+7匹配媒体helper共10模块零诊断；qcomcamss含真实codec符号，SHA101cc9b977d5c7582215391772130c19393b38150708b8fe888d0bdda9081d44；core与425同SHAae2ca7e3ede81ccb019422d7250376c23377537d2c328571817a3390db179099。r1缺显式bits.h（已修源码）；r2缺匹配VB2/ISP/m2m符号（已补目标），未忽略错误。均terminal后再改源/重建，共享构建目录恢复；源码干净、零fuzz/offset重放，候选未安装。当前没有活动构建或设备事务。

## 下一步直接做真正DS4传输，不绕回重复矩阵

当前camss-vfe-17x只注册FULL output0/params1/stats2，vfe_register_meta_nodes只处理metadata；VFE175 full验证器只接受1/2/3输出。需补DS4图像格式/节点、WM5传输、队列/启停/错误回收，再应用precrop/filter/depth/R2PD和原厂系数。PD10不是NV12，也不能假装metadata；注意格式描述与upstream接口范围。现有vfe_add_ds可声明额外output，公共video格式换算/注册需补PD10布局，普通分支保持。

现有175 SOF标签遍历所有活动output，组合完成vfe_buf_done可复用，但要验证FULL+DS4共享组合组与缓冲断粮/晚开/重开/停止时不提前DONE，SG覆盖范围与32bit IOVA不放宽。FULL MNDS输出/裁剪→DS4四分之一输出必须同SOF；先得到有效PD10现场样本，再接IPE，不能提交空/虚构backing。原厂precrop/round/R2PD完整模型已在ds4-model.py和check-producer-geometry.py，可继续作为oracle。

随后接IPE粗级backing所有权、C multipass striping、scratch/session/frame端口1地址，再确认DC统计写入与fullIP消费，最后与IPA同SOF触发/最终成功数值历史合并实拍。425已有实际C IO→完整HAL striping→完整FWprepare证明：640/650宽粗级端口存在时DC0实际1遍、DC1实际2遍；PD10改址仅改变对应硬件地址。scratch71488/75584不可用单遍48；CONFIG_IO+2896是配置遍次，不是BL容量，HAL minBL181024。当前旧C stripe固定单遍，实际接口仍未接粗级路径。

较新IPE fromDownscale机制尚未证明本机支持，勿套新版本标志。GTM另属IFE/BPS，TMC有非零GTM份额尚未应用；本机GTM Execute0x31fc00/setting0x37c818待恢复树/数学与上游生效版本→同图像IPE因果绑定，不能把当前hist算出的曲线冒充已改同帧上游或清零份额伪造完整。

## 保留的运行时与来源

426无手机访问。最近424主摄普通/隔离各205帧、402数值提交、两次Focused，仍雾感偏色；793direct、failed/cancel0，资源/服务恢复，历史taint512保留。具体见424证据，不是426新健康读数。

正式仍420 r31/r26、419生产core63131c.../adapter46f91c...，Image363/DT389/CAMSS389未被本轮修改。候选424 IPA324a821f...未永久安装；已修lux历史坐标、缺BG/lux持有committed、最终成功回执提交，主摄4608x3456单曝光unityDRC/HDR/LEDoff/no-face策略非完整Android；前摄原厂TMC关保持。其它镜头/视频/2592硬测/第五2MP身份mux等见reference/kernel363/REMAINING-CAMERA-SCOPE.md。

CamxChi固定9f17f1b568626b393e785b369c5dc94543774d7a，原HAL SHAe2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde，281 debugdata精确符号复用；原厂GPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6、生成寄存器头296复用。每次WSL source/build/ext4访问先root storage284.mounted_build挂原32GiB镜像，不格式化。Unicorn PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。先等进程handle终态才改依赖/部署。原件/系数/ASM/XML/寄存器/图像仅private，本地scoped mirror护其它index、不push；没有用户输入阻塞，继续功能工作。
'''
assert len(text.encode())<=6500,len(text.encode());(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从426继续完整多摄ISP目标。先读NEXT和426README。四摄64根原厂DS4数据/四pass与原XML/56模式查询一致，完整HAL Parse+DS410/R2PD和实际kernel C768组0差，14CreateExecute只绑定IFEfullDC4。新DS4寄存器codec已入qcomcamss，HEADdbefc5bdd/branch426，Werror匹配10模块构建r3通过，r1显式bits.h/r2依赖目标已修。未安装、无手机访问、无DS4 DMA！直接接真正VFE175 DS4图像格式/节点、WM5队列/停启/回收，应用已恢复原厂precrop0xd84/da4、filterd60、10bitroundd98/db8、R2PDd6c和0x4c使能5500；backing192byte/4rows，不能当NV12/metadata。验证与FULL同SOF、断粮与回收，实取PD10后接IPE粗级backing/Cstripe/scratch/session/frame，验证DC产出/fullIP消费再IPA实拍。425已有双遍native oracle/scratch71488/75584，旧C固定单遍。GTM上游生效版本因果及多摄/视频/第五2MP仍缺。最近实拍424 410帧/402提交/2次AF、仍雾感偏色；正式r31/r26+419没改。原件私存，先storage284，构建terminal后改源，scoped本地提交不push。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());prefix='../../../' if '/kernel/' in rel else '../../'
 d.update(stage=426,latest_work_stage=426,in_progress_installed=False,latest_work_phone_accessed=False,
  vfe175_ds4_oem_reserves_recovered=True,vfe175_ds4_register_codec_candidate_implemented=True,
  vfe175_ds4_register_codec_candidate_installed=False,vfe175_ds4_pixel_dma_runtime_implemented=False,
  vfe175_ds4_latest_evidence=prefix+'reference/kernel426/README.md',
  ipe_ltm_full_dc_coarse_pass_implemented=False,ipe_full_factory_tone_pipeline_complete=False)
 if '/kernel/' in rel:d.update(maintained_branch='samurai-vfe175-ds4-codec426',maintained_commit='dbefc5bdd8de8da07128171423f098a38d6e45b0',maintained_vfe_ds4_codec_candidate_stage=426)
 p.write_text(json.dumps(d,indent=2)+'\n')
note='426当前：四摄原厂DS4参数与模式选择核对完成，VFE175 DS4／PD10寄存器编码入内核、原指令对照及Werror构建通过。DS4队列／DMA和完整DC实拍未接通，候选未安装，正式r31/r26+419未改。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel426/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel426/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel426/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('425当前：');p.write_text(note+'[426证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';s=p.read_text();needle='[425 PD10粗级IO与原厂DC双遍](reference/kernel425/README.md)';assert needle in s;p.write_text(s.replace(needle,'[426 原厂DS4参数与VFE175编码](reference/kernel426/README.md)'))
print(json.dumps(dict(stage=426,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
