"""Update the current checkpoint around actual libcamera request evidence."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
state=json.loads((HERE/'source-state.json').read_text());health=json.loads((HERE/'current-state-validation.json').read_text())
assert health['passed'] and health['m2m']['completed']==48 and health['taint']==512
assert json.loads((HERE/'hardware-validation.json').read_text())['passed']
text='''# 当前检查点：418（libcamera IPE请求链路真机通过）

读WORKING-BOUNDARIES.md、reference/kernel418/README.md。完整目标active。已开灯；工期数周粗估。417归档archive/NEXT-SESSION-through417-2026-10-21.md；推进实际请求与校准，勿扩已通过TMC矩阵。

## 418已完成

候选libcamera=/mnt/samurai-full282/libcamera418-request-iq/src/libcamera-v0.7.2，基于已安装391 r30。新增0041-camss-ipe-request.patch（4文件：camss_ipe.h/cpp、camss_vfe构造传ipeMedia、include/linux/qcom-ipe-a5.h），零fuzz复现、源hash匹配、ARM64库构建通过。库SHA55721a2340f3f71f6aadba4e0ba8ade380901ab3774a9961c4eb847c68d9d303，private418/libcamera.so.0.7.2。未打新包/永久装，IPA算法/接口/签名不变；不要把候选误称正式已部署。

CamssIpe复用v0.7.2 MediaDevice allocateRequests、V4L2 setControls/queueBuffer、V4L2Request notifier；控制typeU8/elem1/elems6008/dims6008核对，request池深度同buffer。每OUTPUT显式params，CAPTURE无request；无参数传0旁路；明确params在旧驱动返回ENOTSUP不吞。新驱动旧调用走request旁路。3方完成input/output/request后释放job、归还请求；requestReady reinit禁电平通知，仅Queued调用finishRequest，避免在V4L2Request::requestReady栈内stop销毁pool；serial拒旧延后通知误认新job。pre-adopt设置失败直返，partial QBUF/queue失败stop并signal一次；STREAMOFF失败先close/join再释放图像/requestFD。原IFE SOF wrapper保护。

实际wrapper ASanUBSan37项覆盖三方6顺序、startup/shape/alloc/control/QBUF/reqqueue/reinit/STREAMOFF失败、timeout/reentry/耗尽/旧通知。ARM64实库探针16帧，NV12 640x480和NV21 650x480 stride672，各0/1/2/2/3/4/0/1=bypass/colour/Gamma0/Gamma0/LA2048/LA1024/bypass/colour；全有效像素等406固定参考。输入未改/尾部/timestamp通过，Gray内块128/64，不称整个彩色图恒定。重开+立即stop两次4个wrapper失败回调；内核18任务16done2cancel，另2排队buffer尚未成job，不能说kernel4cancel。

候选相机pipeline标准request旁路81processed：四摄各12=48、主RAW+NV12 6（RAW6匹配）、隔离IPA27（实际独立PID、五control阶段/GAMMA_ACK1）。另RAW-only6对不启IPE。candidate全epoch99jobs=97done+2cancel，failed0，starts/stops10。97=wrapper16+pipeline81；pipeline生成包仍全零，非零只合成诊断，**IPA原厂算法参数尚未接**。IFE已有CC/Gamma，未经输入域证明不要再叠加原厂RGB曲线。

r1失败测试buffer布局：exporter482高逻辑Y/UV双平面，探针只写plane0整体bytesused，libcamera报holes；无图像DMA/无新fault，修改探针为同导出DMA-BUF连续单平面+尾部后r2通过。生产代码不因此改变。418-r1pid6197/r2pid6637、clients/collector皆terminal，root /var/lib/samurai/k418-libcamera-r1..r2，勿重启旧事务。

## 设备与底层

最新418恢复正式core395/adapter393/CAMSS389、r30/r25原配置/loaded notes核对；四摄各12=48应用/48IPE，extra0，error/cancel0，starts/stops4。ICP/CAMSS双CCI suspended、资源释放、17clk0/9railsdisabled-users0，PW6915/WP6920 uid10000单例，owner_refs53桌面句柄正常。guard394仍/var/lib/samurai/k394-recovered/boot-id-private.txt。**taint512来自417-r2已修的WARN，本轮新fault0，保持记录不清不盲重启**。

内核417 branch samurai-ipe-request-iq417 commit f0b6ea869e3e748e6c1ccfe06865ac8d02c3ef3a干净，418未改内核/DT/板级/传感器；private417 intree-r3配对：core419848B SHA63131c5719526ca796955f4d833380a12c36c62557ccf539e85bd58c0f070632、adapter131888B SHA8fa34a55d07a47c7acadbb8f71b16062c96b7a4657e268744e7077538daf65f2。r2缺buf_out_validate别用。UAPI本地CID USER_BASE+1240非上游分配；packet6008固定无指针/CDM，全零旁路/否则v1 size6008 knownflags reserved/padding0；colour104 gamma3072 LTM2800。req1OUTPUT+显式ctrl，CAPTURE正常；s_ctrl仅worker，EXECUTE_ON_WRITE重复复制，imageimport前setup/copy/check；buf_out_validate ANY→NONE拒隔行。

417失败详417README，事务皆terminal；其恢复49IPE含front extra1是历史，本轮正式48direct。395 reset2us/readback/双IPE freshACK再退役修复保留，保护394丢ACK重启/ramoops。Image363 release7.3.0-rc6-rmx1931-samurai-k363+、DT389/logdump365/SGownerFW保持。

## 下一步

先核对带417 typedIQ/418 wrapper的真实失ACK、复位、取消/引用回收，然后可发布417+418通道候选（当前正式包仍r30）。接IPA prepare/result与407..416算法时，以每帧实际元数据/统计/输入域为依据，history成功commit失败discard。只补真正需要的LA/mask/weights/scalars/inverseGamma/IFE-IPE域缺口，做非零LTM/LCE/连续恢复实机，不重复大TMC矩阵。

reference/kernel363/REMAINING-CAMERA-SCOPE.md全scope有效：第五2MP/OV02A1B身份共享mux勿猜OV02A10，多模式/帧长/防频闪、持续AF/光学、几何/多摄同步，implicitfences/SSC/旋转未全复验。SoC/板级DT/主线实验UAPI/驱动/用户空间分层描述。

## 原厂数学与环境

416纠正415：IPE input=SP340非SP240，2cfa9c actual2760调校管理器不是版本；binder2d6564..2d6590仅cache(node149a8).version1设请求1否则保初始0，ptr3024。HDRmodule88/92=AEC槽1/0 time/sensitivity比，control2零。1002+4输入/16binding、154完整TMC11 Execute（4物理14context72calc）两架构等；12module0/property旧1保留。合成stats/UID/缺失，不代表Android或硬件自动调校。细节及413/414全部数值证据见416与归档，不再误追全局版本表。

数值易错项见416/417：darkY不clipanchor1，nohist BYTE1，原地平滑左值已更新，firstgain>=1024别夹unity，signeddelta大正值也置bit11。408raw124/140身份未解，90次计算非帧、历史存atten前/ADRC后待commit。406 explicitIP位别恢复HAL DC/quarter gate；mask halo/crop保留。405 copy/check后MAP，unknownDMA整parcel+images引用保留。

每次WSL访问source/build/ext4先root storage284.mounted_build()挂原32GiB，勿重建格式化；source354/build在/mnt/samurai-full282。root PYTHONPATH=/home/cy122/.local/lib/python3.14/site-packages。原厂系数/夹具/二进制/图像日志私存/mnt/e/edk2-samurai-out/kernel418及前序。公共仅作者代码/脱敏报告；mirror本地scoped commit护无关index，不push/PR。保护NV/OTP/个体备份/密钥/电池温控，未知事务先查。
'''
assert len(text.encode())<=6500,len(text.encode())
prior=(ROOT/'NEXT-SESSION.md').read_text();archive=ROOT/'archive/NEXT-SESSION-through417-2026-10-21.md'
assert not archive.exists();archive.write_text(prior)
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
    path=ROOT/rel;d=json.loads(path.read_text());assert d['latest_work_stage']==417
    d.update(stage=418,in_progress_stage=418,latest_work_stage=418,in_progress_installed=False,
        in_progress_evidence=prefix+'kernel418/README.md',latest_stage_device_mutated=True,latest_stage_phone_accessed=True,
        current_device_revalidated_stage=418,ipe_latest_hardware_stage=418,icp_latest_device_experiment_stage=418,
        current_camera_evidence=prefix+'kernel418/README.md',current_readonly_device_evidence=prefix+'kernel418/current-state-validation.json',
        device_current_taint=512,device_force_restart_currently_needed=False,
        kernel_source_scope='417 kernel unchanged clean;418 isolates r30 libcamera candidate and connects existing V4L2 request/control APIs.No board/DT/sensor/IPA algorithm change.',
        in_progress_installed_scope='418 temporary libcamera and417 kernel candidate tested then unloaded;formal395/393 andr30/r25 restored.Unpackaged candidate.',
        ipe_media_request_iq_libcamera_integrated=True,ipe_media_request_iq_ipa_parameter_generation_integrated=False,
        ipe_media_request_iq_libcamera_scope='Actual CamssIpe typed packet method and three-way completion;16 nonzero probe frames,4 cancel callbacks;81 camera pipeline requests still bypass payload.IPA automatic numeric generation not connected.',
        ipe_media_request_iq_libcamera_evidence=prefix+'kernel418/hardware-validation.json',
        ipe_media_request_iq_libcamera_patch=prefix+'kernel418/0041-camss-ipe-request.patch',
        ipe_media_request_iq_forced_fault_recovery_verified=False,
        ipe_cc_per_frame_runtime_api_scope='418 actual libcamera CamssIpe supports typed6008 packet in standard Media Request;pool reclaimed after input/output/request completion.Nonzero explicit IQ rejected on legacy driver;automatic pipeline payload bypass.',
        ipe_ltm_runtime_submission_scope='418 actual candidate library supports typed colour/Gamma/LTM per request;fixed nonzero16 probe pixels equal references.Pipeline81 explicit bypass packets;formal395/393 restored,default advanced IQ remains off.',
        ipe_ltm_runtime_submission_enabled=False,ipe_ltm_product_default_enabled=False,ipe_ltm_curve_product_integrated=False,
        ipe_latest_stage_actual_frames=97,ipe_latest_stage_RT_frames=97,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_native_cc_frames=12,
        ipe_latest_stage_normal_restored_frames=48,ipe_ltm_latest_enabled_frames=4,ipe_gamma_latest_successful_test_frames=4,
        ipe_latest_stage_frames_scope='Candidate97 completions=16 wrapper diagnostics+81 camera pipeline(all bypass);2 kernel cancellations/4 wrapper cancelled callbacks separate.Raw-only6 pairs noIPE.Restored normal48 outside candidate epoch.',
        ipe_current_cumulative_counters={k:health['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']},
        ipe_current_counter_epoch='418-r2 restored normal395 lifetime:48 direct,starts/stops4;four cameras12 each,no extras.',
        ipe_current_failed_counter_scope='418-r1 test logical plane layout failed before imageDMA;r2 candidate99jobs97done2cancel noerrors;restored normal48 noerrors.Known417-r2 WARN retained.',
        current_health_scope='418-r2 restored formal395/393:four cameras48app/48IPE,resources released,17clocks0/9railsdisabled/PMsuspended,single services.Known417 WARN taint512,no new418faults.',
        icp_next_step='Verify forced lostACK/reset with417 typed requests and418 wrapper then publish channel candidate;connect IPA per-frame generation/result and407..416 math with real metadata/statistics/input-domain proof.History success-commit/failure-discard;avoid double IFE/IPE CC/Gamma.Full363 camera scope remains.')
    path.write_text(json.dumps(d,indent=2)+'\n')
(ROOT/'NEXT-SESSION.md').write_text(text)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从418继续完整多摄/骁龙ISP目标active。读NEXT-SESSION/WORKING-BOUNDARIES/reference/kernel418/README。候选CamssIpe接417typed6008 Media Request，三方完成+Queued finish避回调内pool销毁，37ASanUBSan模型及16非零wrapper像素等参考，4wrapper取消=2kernelcancel。候选pipeline81request帧（四摄48/dual6/isolated27），RAW-only6无IPE；**自动IPA参数仍旁路**。未打包/永久装，候选树libcamera418-request-iq基于r30；内核f0b6ea869e3e748e6c1ccfe06865ac8d02c3ef3a干净复用417。正式395/393 r30/r25恢复四摄48direct，PW6915/WP6920，guard394，taint512源417已修WARN、本轮fault0不清标记不盲重启。418两事务终态。先typed请求失ACK/复位回收再可发布通道；IPAprepare/result与407..416算法接入需实际元数据/统计/输入域及history成功commit失败discard，防IFE已有CC/Gamma重复叠加。勿扩TMC已过矩阵，363第五摄/光学/AF/同步全scope有效。WSL先storage284挂原ext4；原厂私存，公共本地commit不push/PR。\n')
note='418当前：候选libcamera接入逐帧Media Request，实库16非零参数帧与固定参考像素一致、4取消回调正常；四摄/双流/隔离IPA共81处理图像请求通过，但IPA参数仍旁路。正式395/393 r30/r25已恢复四摄48帧，本轮新fault0、历史taint512保留。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel418/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel418/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel418/README.md')]:
    p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith('417当前：')
    p.write_text(note+'[418证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[417 Media Request逐帧IQ真机验证](reference/kernel417/README.md)','[418 libcamera IPE请求链路真机验证](reference/kernel418/README.md)'))
print(json.dumps(dict(stage=418,next_bytes=len(text.encode()),full_goal_active=True)))
