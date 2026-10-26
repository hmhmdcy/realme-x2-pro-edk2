from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for name in ['static','frame','numeric-history','kernel-payload','build','device-read']:
    assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
source=json.loads((HERE/'candidate-source-state.json').read_text());assert source['patch_zero_fuzz_reproduced'] and not source['automatic_runtime_generation_integrated']
archive=ROOT/'archive/NEXT-SESSION-through421-2026-10-21.md';assert not archive.exists()
archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
next_text='''# 当前检查点：422（完整数值帧组装，未接自动IPA）

用户明确继续优先复用原厂数据、接完整自动TMC/LTM并实拍，尽量底层收敛。读WORKING-BOUNDARIES及reference/kernel422/README。完整多摄目标未完成。421完整交接归档archive/NEXT-SESSION-through421-2026-10-21.md，不重跑已完成事务/大算法矩阵。

## 422已完成

新增libipa/ltm13_static.{h,cpp}，已有352/403逆Gamma直接复用。RGB2Y/亮度比/权重/mask核和归一化/LA/mask表：6份选定原厂叶去重输入+24边界+7非法；host ASanUBSan/ARM64各23680B零差；实际目标60150指令、30memcpy。第六mask归一化项实际固定加4，包括指数0，不能直译参考负移位UB。

libipa/ltm13_frame.{h,cpp}组合强度→平滑→保留候选历史→衰减→TMC11 PCHIP/contrast→ADRC→13组LUT，输出2800B与既有typed kernel payload布局相同。输出及下一state全部成功后才写，输入不变。四变体各有/无ADRC8组+5非法，host/ARM各41704B零差，与实际temporal/inverse/sampling/ADRC及原packer核对，复用413保存生成输出。forward共用保存主摄表仅数值夹具，不是各模式真实绑定；前摄原厂TMC关闭，有ADRC前摄也是显式夹具，不能启前摄默认。

8份payload经过当前维护源实际codec和6008B packet validator：92BIQ+2736BLUT逐字节正确、caller/tail保持。最初想复用405源却因后来增加request validator/includes而来源断言失败；已编译当前源/UAPI，原失败保留kernel-payload-r1-failure。16段packer夹具最初短record退出，改固定268B/类型2，保留frame-check-r1-failure。

ipe_numeric_history.h单未决提案策略12ASanUBSan场景：每摄像头最多一份未完成计算，绑定epoch/SOF/token/baseRevision；其它观测不可代提交，失败不更新，stop/旧epoch清退。**组件尚未接实际IPA，不等于数学历史运行已完成**。

## 候选与真实设备

新树/mnt/samurai-full282/libcamera422-tmc-ltm/src/libcamera-v0.7.2，从421复制。24文件0043补丁零fuzz复现；公共libipa11个新cpp及history头，SDK ninja构建50.22s成功。新增数学尚无IPA引用，静态链接剔除了未用对象，因此libcamera/IPA/proxy及签名字节全部与421相同，不把构建通过当自动调参/不要无意义重拍。私有IPA接口仍2，kernelUAPI仍1/6008B，未永久安装。

422只读设备确认同guard394、taint512历史保留，239jobs=completed=direct，failed/cancel/firsterror0、starts/stops17、users0/running/fatal/pinned/orphans0，owner_refs53桌面CAMSS句柄；ICP/CAMSS/双CCI suspended。未采新帧、未切服务/文件/模块/重启，不声称本轮新增故障增量或完整资源回归。

正式仍420部署的419core/adapter、libcamera99990.7.2-r31/config0.1.0-r26；421观测history及重入修复候选未安装。内核source354 branch samurai-ipe-error-buffer419 commit07d2ca735f88649587c0e89802febff6dbf2b443。Image363/DT389/CAMSS389/FW/SGowner保持。生产core SHA63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632，adapter46f91cc8dd024626f05a276e63dd8384bb6a056d15bf441c7d44a91ab4c2e06f；禁止e27吞ACK核心当生产。保护394/395lostACK复位退役证明及417历史WARN/419原workerfalse，不重启清历史。

## 直接接续

421已接真实同SOF BHIST1024/曝光/增益/IFErevision及最终图像+RAW配对回执，四摄/RAW/隔离已验；统计先发布再同步IPA，防重入误判缺统计和stop用已释放paramsbuffer。421r2主摄12/12观测提交；隔离29图像28有统计元数据匹配、SOF7确实缺统计无token，1旧成功superseded不能倒退。不要重复launch旧事务/模型。

在422候选真正连接407..416+422模块到IPA及6008B同帧request：工厂选根/实际触发、原厂TMC生命周期缓存、实际IFEgreen/forward绑定、统计来源域、色彩/CST/IPEGamma职责。原厂TMC前摄关闭/长焦11开10关；不得伪造单曝光为双槽HDR或DRC/darkGain/rawAEC124/140。完整LTM还需核实DC粗级统计/IP依赖、非零局部像素，设置DC标志不等于已验收统计。连接后再实拍/连续参数/恢复，不用另写应用滤镜代替。

全scope仍reference/kernel363/REMAINING-CAMERA-SCOPE.md：四摄基础可用，第五2MP身份/mux未完、不要猜OV02A10；模式/帧长/防频闪、连续AF/光学/几何/多摄同步、implicitfences/SSC/旋转未全复验。

每次WSL源码/build/ext4访问先root storage284.mounted_build挂原32GiB镜像，不重建格式化。rootPYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。私有原表/ELF/汇编/输入输出/log/图像在/mnt/e/edk2-samurai-out/kernel422及前序。公共仅作者代码/脱敏报告，local scoped mirror护无关index、不push。保护NV/OTP/备份/密钥/电池温控；用户开灯，实拍按实际曝光解释。无活动build/SDK bind/手机worker。
'''
assert len(next_text.encode())<=6500,len(next_text.encode());(ROOT/'NEXT-SESSION.md').write_text(next_text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从422继续用户授权的原厂调校复用/完整自动TMC-LTM/实拍。先读NEXT-SESSION和422README。已完成静态LA/mask/weight/scalar、完整typed13LUT帧组装、singlepending数学history策略及原HAL/host/ARM/当前kernelcodec对照。候选公共libipa已构建，但数学无IPA引用、最终库/IPA/proxy字节与421相同，自动生成/数学history回执未连接、无新硬件帧。正式420 r31/r26+419生产模块未改，422只读239direct/0failed/cancel、四设备suspended/taint512/guard394保持。直接接真实选根/触发/统计域/IFEgreen/forward、TMC缓存及同帧request，再实拍，不重跑矩阵或旧事务；前摄原厂TMC关闭/长焦11开10关；DRC/HDR/raw124/140不能伪造，DC粗级/IP统计仍需证明。421重入修复和真实观测/回执完整交接见archive421。WSL先storage284，原厂私存，public仅作者代码，本地提交不push，完整多摄scope未完。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    p=ROOT/rel;d=json.loads(p.read_text());d.update(stage=422,latest_work_stage=422,
        current_device_revalidated_stage=421,latest_read_only_device_stage=422,
        in_progress_installed=False,ipe_numeric_frame_assembly_verified=True,
        ipe_numeric_frame_assembly_evidence=('../../../' if '/kernel/' in rel else '../../')+'reference/kernel422/README.md',
        ipe_numeric_tmc_ltm_history_integrated=False,ipe_media_request_iq_ipa_parameter_generation_integrated=False,
        ipe_numeric_static_library_built_not_runtime_referenced=True)
    p.write_text(json.dumps(d,indent=2)+'\n')
note='422当前：补齐原厂LTM静态参数和完整13组LUT类型化帧组装，host/ARM及当前kernel codec对照通过，公共libipa构建完成；数学尚未被IPA调用，自动调参及实拍未完成。正式r31/r26+419驱动保持，本轮只读239direct/错误取消0。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel422/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel422/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel422/README.md')]:
    p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('421当前：');p.write_text(note+'[422证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';text=p.read_text();needle='[421 真实观测与统计发布重入修复](reference/kernel421/README.md)';assert needle in text;p.write_text(text.replace(needle,'[422 原厂数值帧组装与自动链路边界](reference/kernel422/README.md)'))
print(json.dumps(dict(stage=422,next_bytes=len(next_text.encode()),full_goal_complete=False,passed=True)))
