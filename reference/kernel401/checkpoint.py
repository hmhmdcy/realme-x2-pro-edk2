"""Record the Gamma candidate without advancing last physical evidence400."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
source=json.loads((HERE/'source-state.json').read_text())
for name in ['contract','parcel','transfer','firmware-parcel','intree-build']:
 assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert not source['installed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 for k in ['stage','in_progress_stage','latest_work_stage']:d[k]=401
 for k in ['maintained_branch','kernel_source_branch','candidate_kernel_source_branch']:d[k]=source['branch']
 for k in ['maintained_commit','kernel_source_commit','candidate_kernel_source_commit']:d[k]=source['commit']
 d.update(current_camera_evidence=prefix+'kernel401/README.md',latest_stage_device_mutated=False,latest_stage_phone_accessed=False,source_worktree_is_undeployed_candidate=True,candidate_source_clean=True,a5_icp_candidate_source_installed=False,
 kernel_source_scope='401 typed Gamma candidate and corrected generic program type20; offline tested and built, not installed. Last device evidence400; formal core395/adapter393/CAMSS389/Image363/board389.',
 in_progress_installed_scope='401 no phone access or installation. Last400 temporary conversion experiment was unloaded and formal395/393 restored.',
 ipe_gamma_candidate_api=source['new_api'],ipe_gamma_iq_bytes=6016,ipe_gamma_iq_page_bytes=8192,ipe_gamma_lut_bytes=3072,ipe_gamma_lut_in_retained_request=True,ipe_gamma_new_coherent_buffers=0,ipe_gamma_hardware_verified=False,
 ipe_gamma_offline_evidence=prefix+'kernel401/README.md',ipe_generic_program_type=20,ipe_gamma_program_type=12,ipe_generic_type20_hardware_verified=False,
 ipe_program_tag_correction_scope='401 original HAL submit proves generic20/Gamma12/skip255. Prior0-generic label withdrawn. Physical400 observations retained, corrected401 tags not yet hardware verified.',
 ipe_colour_chain_hardware_scope='400 source399 generic0 tag, fixed640x480 NV12/NV21 diagnostic pair, eight modes. 401 generic20 correction and Gamma remain untested physically.',
 ipe_latest_stage_actual_frames=0,ipe_latest_stage_RT_frames=0,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=0,ipe_latest_stage_normal_restored_frames=0,ipe_latest_stage_frames_scope='401 offline only, no frames or fresh hardware checks; last physical400 counters/evidence retained separately.',
 ipe_ife_user_role_audit=prefix+'kernel401/ife-role-audit.json',ipe_full_factory_interpolation_activated=False,
 current_health_scope='Last physical400 fixed conversion/CC pixels and restored normal camera/resource checks;401 no fresh phone check. Full Gamma/LTM/optical/AF/SSC/rotation not broadly revalidated.',
 icp_next_step='Temporarily hardware verify corrected generic20 and Gamma diagnostic/factory LUTs with same-request ownership; then LTM/full IQ. Resolve IFE CCM/Gamma vs IPE roles, standard media request/libcamera/factory triggers, and full remaining363 scope.')
 assert d['current_device_revalidated_stage']==400 and d['ipe_latest_hardware_stage']==400
 p.write_text(json.dumps(d,indent=2)+'\n')
archive=ROOT/'archive/NEXT-SESSION-through400-2026-10-21.md'
assert not archive.exists();archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：401（Gamma候选离线通过，最后实机400）

先读WORKING-BOUNDARIES.md、reference/kernel401/README.md。完整多摄／骁龙ISP目标active，用户已开灯出门，按实际照明和曝光判断样本。400完整交接归档archive/NEXT-SESSION-through400-2026-10-21.md。

## 当前候选与证据

源码samurai-ipe-gamma401，HEAD b8ce3ce92745a11b039e1335e87bbb2dd783c2c7，父399 de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7，四文件，干净未部署。401未访问手机，无新帧／安装／重启，不能把历史400设备状态称作401复验。

原HAL GammaExecute、完整WriteDMI和AddNestedCmdBufferInfo执行证明：IQ2192→0x6060；三条12B间接opcode10 DMI，寄存器0x6008，selector1/2/3，对应G/B/R各1024B；实际嵌套记录目的4/16/28，源0/1024/2048。inline76为软件命令，不直接送硬件。原提交器证明普通programType20、Gamma12、skip255；此前0=generic结论撤回。400实际像素历史有效，但不等于修正标签后的401硬件验证。

新内核内部API camss_a5_ipe_run_gamma_status，typed三通道256项base10/signed-delta10，范围base0..1023/delta-512..511；锁内kmemdup3072B、先校验再coherent分配/MAP，避免3KiB栈。完整LUT复制进现有request，未知DMA时随request保留，临时CPU副本所有出口释放，不新增独立coherent缓冲。IQ6016/PAGE_ALIGN8192，2592empty/2624pre/2656post最多3项，2752CST/2808CC/2852CV、2896DMI36B、2944LUT3072B。原job/frame/colour布局与reset/free/quiesce/stop函数体保持。

实际C完整参数页：主机ASan/UBSan和AArch64QEMU各3450组/9993772B零差（1121CC、2232chain、97Gamma），6040非法无写、NULLcolour及32bit上界通过。85生命周期用例含copy后调用方篡改、copyENOMEM、invalid校验前拒绝、未知MAP/FRAME/UNMAP保留，无CPU副本泄漏。完整原FW CONFIG_IO+frame准备19组，当前C原生条带与原HAL整512KiB CDM/32Bjob全等，停硬件enqueue前，NV12/1:1范围。W1/Werror构建成功诊断0，核心388520B/SHA862c79c94424ba4dedc1936f1394aa9aa992c6f613452e6fe4a1fc3f20eb6f7b，共享配置/outputs/symvers恢复。构建与FW/parcel工具进程均终态。

首个Gamma夹具命令数组指针2592错，真实2600；修夹具后通过，旧脚本/失败私存401。没有改原HAL指令绕过。

## 最后物理400与正式部署

400临时399core/固定400adapter，640x480 NV12/NV21各8模式=16direct，error0。固定CST/CV根来自SunnyIMX319 mode0Preview，CV第一保留叶仅诊断，不冒称实际运行插值。identity全等转换对、zeroY0UV128、half围绕黑色缩放误差半LSB；R/Bswap和signedoffset有实像素效应，两格式归一化所有字节相同。支持所测固定组合RGB域，完整矩阵/offset量纲/饱和/舍入未证明；luma拟合三模型训练同分，只能推断。全Gamma/LTM/自动调校未验收。

之后恢复正式core395/adapter393，r30四摄各12共48direct/starts-stops4/error0/extra0；CPU/IRQ/PM/backing/maps/import释放、ICP/CAMSS/双CCI suspended、17clks0、9railsdisabled/users0、taint0。PW13169/WP13172各单例uid10000，owner_refs53桌面句柄。400 worker12945/client13157/collector13040终态且cmdline不活跃，不重启旧事务。无test_chain_mode/test_cc_mode/dropACK，无新dump/timeout/fault/reboot。

正式core395 SHA68ab5b3d6626a51ae91dd13003aed8e199a58f3ba34c1fd24ebad7e16c688a88、adapter393 SHAff2bfa7a9439b2ef67087ff6f5db8c9d26e9a92596cd1f63b14c3a047111d4c1、CAMSS389 SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288。Image363/release7.3.0-rc6-rmx1931-samurai-k363+、boot/静态DT389/logdump365、SGownerAPI、FW、r30/r25保持。host401委托400…394，guard=/var/lib/samurai/k394-recovered/boot-id-private.txt，原USBkey/knownhosts。395失ACK恢复通过，394失败reboot/206061Bramoops及旧回退副本保护。

## 接续与分层

接着临时实机验证generic20修正和Gamma单位/零/半幅/分通道诊断及原厂曲线，核对像素与重置后重载，再LTM/fullIQ。r30代码审查证实IPA已有IFE CCM及64段Gamma参数路径，IPE目前只queue图像、无typed颜色元数据；源码支持不等于当前配置启用。定义IFE输入传递函数、CCM位置和LTM/inverseGamma关系，避免重复处理，不能混用IFE64和IPE256或简单复合两曲线。接标准media request/libcamera与原厂触发插值，不把固定test参数当产品API。

399契约保留：CC actualtype2/offsetsigned11（396type1/13位错），CSTQ10signed13/subtractsigned11/addclamp10，CSTIQ2092→5a60、CC2188→5e60、CV2200→6460；CV原Parse证明native顺序r/g/b/yoff/ap/am/bp/bm/cp/cm/dp/dm/kcr/kcb，packet低ap/bp/cp/dp高am/bm/cm/dm末cb/cr。17CST/71CV根1350叶与原XML一致，14mode上下文28选择匹配；350/351已恢复Gamma/CCM/LTM树，未完整产品激活。

363/REMAINING-CAMERA-SCOPE.md继续：第五2MP身份/mux、多模式、帧长/防频闪、几何/多摄同步、连续AF/光学；implicit异步fence未证明，SSC/旋转未全面复验。source/build必须先root storage284.mounted_build()挂原32GiB ext4，勿格式化重建；rootPython PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原厂FW/HAL/OEM/ASM/CDM/图像/个体表私存401及前序，公共mirror只本地提交、不push/PR、保护无关index。400镜像HEAD4b72d50cfd073a844df9113e9b5315c3d8e1c9a1，401收尾脚本应检查后提交。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从401继续完整多摄/ISP目标。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel401/README.md。Gamma原HAL DMI/嵌套/开关及programType20generic/12Gamma已核实（旧0generic标签撤回），typed LUT同request保留；3450参数页/85生命周期/19完整原FW条带、W1Werror通过，源码b8ce3ce92745a11b039e1335e87bbb2dd783c2c7 branch samurai-ipe-gamma401干净未部署。401未访问手机；最后物理400固定CST/CV+CC16帧通过，随后恢复正式395/393四摄48和资源释放。下一步实机验证修正tag及Gamma，再LTM/fullIQ；明确IFE已有CCM/Gamma路径和IPE分工、接标准request/libcamera与全部363范围。guard394/host401，旧400事务全终态不可重启。用户已开灯，按实际光照；source/build先root storage284挂原ext4，原厂表/日志/图像/密钥私存。\n')
note='401当前：原厂Gamma DMI及LUT同请求所有权接入候选，构建与离线验证通过；普通程序标签修正为20，Gamma12。未访问手机／未部署，Gamma与修正标签待实机。最后实机400转换链像素通过并恢复正式395/393。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel401/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel401/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel401/README.md')]:
 p=ROOT/rel;p.write_text(note+'[401证据]('+link+')。以下为历史。\n\n'+p.read_text())
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[400 转换链组合实像素与恢复](reference/kernel400/README.md)','[401 原厂Gamma与LUT所有权候选](reference/kernel401/README.md)'))
print(json.dumps(dict(stage=401,checkpoint_updated=True,last_device_stage=400,full_goal_active=True)))
