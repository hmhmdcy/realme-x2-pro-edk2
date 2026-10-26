from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
current=json.loads((HERE/'current-state-validation.json').read_text());assert current['passed']
archive=ROOT/'archive/NEXT-SESSION-through391-2026-10-21.md';assert not archive.exists();shutil.copyfile(ROOT/'NEXT-SESSION.md',archive)
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../reference/'),('linux-port/camera/kernel/source-lock.json','../../../reference/')]:
 p=ROOT/relative;d=json.loads(p.read_text())
 d.update(stage=392,in_progress_stage=392,latest_work_stage=392,current_device_revalidated_stage=392,icp_latest_device_experiment_stage=392,ipe_latest_hardware_stage=392,ipe_latest_stage_actual_frames=24,ipe_latest_stage_RT_frames=24,ipe_latest_stage_non_RT_frames=0,ipe_latest_stage_frames_scope='392 logs:24 hardware frame completions =20 completed+4 cancelled;26 V4L2 jobs include2 expected pre-image-submit rejections. Includes failed-timing r1 actual work; previous391 counts excluded.',ipe_actual_cancel_branch_verified=True,ipe_cancel_concurrency_verified=True,ipe_exact_dma_pending_abort_instant_verified=False,ipe_input_validation_error_concurrency_verified=True,ipe_input_validation_error_affects_peer=True,ipe_reopen_after_input_failure_verified=True,ipe_hardware_error_concurrency_verified=False,current_boot_auto_af_retest_scope='No optical or AF scene validation392; cancellation/input error/default application recovery only.',icp_next_step='Core must explicitly classify known-safe pre-image-submission rejection versus submitted/uncertain DMA; isolate local errors without poisoning peer. Keep unknown MAP/FRAME/UNMAP retention and reset-ACK proof. True hardware-error concurrency remains unverified, followed by OEM Gamma/LTM/CCM full IQ and all363 camera scope. Same390 boot, r30/r25 installed391.')
 for key,name in [('current_camera_evidence','README.md'),('in_progress_evidence','README.md'),('device_closeout_evidence','current-state-validation.json'),('current_readonly_device_evidence','current-state-validation.json')]:d[key]=prefix+'kernel392/'+name
 d['ipe_cancel_and_input_recovery_evidence']=prefix+'kernel392/hardware-validation.json';d['ipe_installed_default_camera_recovery_evidence']=prefix+'kernel392/runtime-r3-validation.json'
 d['ipe_current_cumulative_counters']={k:current['m2m'][k] for k in ['jobs','completed','direct_completed','cancelled','failed','first_error']}
 d['ipe_current_failed_counter_scope']='2 expected alias/peer failures392, first_error=-22 cumulative; fatal=false and reopened default GStreamer12 verified'
 if relative.endswith('deployment-lock.json'):
  d['final_health_evidence']=prefix+'kernel392/current-state-validation.json';d['system_services']=dict(stage=392,services=current['services'],evidence=prefix+'kernel392/current-state-validation.json',current_boot_revalidated=True)
 p.write_text(json.dumps(d,indent=2)+'\n')
for relative,link in [('linux-port/camera/README.md','../../reference/kernel392/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel392/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel392/README.md')]:
 p=ROOT/relative;s=p.read_text().split('\n\n',1)[1]
 p.write_text('392当前：四种在途取消、双上下文及输入别名拒绝／重新打开恢复已实测，默认r30 GStreamer另12帧；累计预期failed2保留，当前fatalfalse、DMA/PM回收。已知输入错误会影响peer，后续收敛局部错误边界；真实硬件错误并发／完整IQ／多摄校准仍未完成。[392证据]('+link+')。以下为历史。\n\n'+s)
p=ROOT/'DOCS-INDEX.md';p.write_text(p.read_text().replace('[391 正式IPE用户空间与94作业实机](reference/kernel391/README.md)','[392 在途取消与输入错误恢复实机](reference/kernel392/README.md)'))
checkpoint='''# 当前检查点：392（取消与输入错误恢复实测，目标active）

读WORKING-BOUNDARIES.md、reference/kernel392/README.md。完整多摄／ISP校准目标仍active，用户关灯黑场／噪点不单独判故障。391全部部署资料已归档archive/NEXT-SESSION-through391-2026-10-21.md；390内核／板级与391用户空间保持，本轮无内核、DT、模块、FW、包或个体配置改动，无重启／刷写／卸载。

## 新证据与实际状态

在正式平台上使用真实V4L2客户端，/dev/kmsg新尾部等到本次CONFIG_IO后发取消。r1前三用例通过：输出先STREAMOFF、捕获先STREAMOFF、直接close；全部实际cancelled增加，重启帧Y正确。r1第四首次在活动作业期间才计算peer CRC，约10ms准备导致取消太晚，三个作业正常完成但取消计数不增，断言失败；该窗口保留为失败，资源已回收／服务恢复。没因客户端时序改驱动。

r2只把peer准备移到启动之前，补并发取消和别名输入错误，未重跑前三。并发取消实际cancel+1，peer和同fd重启Y正确。同一个导出DMABUF作输入输出触发核心物理别名-EINVAL；当前adapter视为全设备错误、停后端/fatal，peer报-EIO。全部关闭后fatal清除，重新打开Y正确。两次失败是预期错误路径，非硬件fault注入，不能据此宣称未知DMA/IRQ/超时并发恢复完成。

r3只补默认r30应用恢复，无LD_LIBRARY_PATH／配置覆盖的广角GStreamer640×480 NV12完成12帧，IPE增加12/bus-errors0/fixture恢复。历史failed2和first_error=-22保持，未通过模块重载清零掩盖。实际job_abort计数4，硬件24次完成日志（20正常＋4上层取消）；26个V4L2作业=20completed+4cancelled+2预期失败。含r1失败时序窗口的真实工作量，不能重复累计或丢掉。合成正常输出7个核对有效Y，另一个r1首次正常完成的活动帧未做像素验收。精确DMA-pending瞬间未采样。

当前累计jobs132/completed126/direct126/cancel4/failed2/first_error=-22，starts/stops20；旧391基线106。当前fatal/running/pinned/orphans/users均0。最后FW单session12帧/43消息/43IRQ，INIT/PC完成、watchdog/protocol0。三次worker/client/collector都终态，无dump/timeout、新fault0/taint0；CPU/IRQ/PM/backing/map/import释放，ICP/CAMSS/双CCI suspended，17clks0，9rails disabled/users0。PW10271/WP10274各一/uid10000，owner_refs53是桌面CAMSS句柄；测试close后曾短暂owner_refs2来自延迟fput，外层等归0后恢复桌面。

不要复用旧“failed必须0/first_error必须0”作为当前健康检查，也不要因此重置平台。读392/current-state-validation.json，区分累计预期失败与活动fatal；新工作应核对计数增量。

## 正式部署保持

同一390启动，host392→host391→host390；guard=/var/lib/samurai/k390-active/boot-id-private.txt，经private390/postboot-adoption-private.json。原USB SSH密钥／known_hosts保持，旧378guard失效，不重新授权。真实icp@ac10000绑定qcom-sm8150-icp，正常CAMSS/ICP同模块、五模块/FW/DT永久部署，无test/overlay。

包：五libcamera 99990.7.2-r30，config/stack0.1.0-r25；391共13包/7实装，完整功能保留、六IPA签名通过且二进制同r29。四份个体/etc Preview配置未改，公共包无个体表。部署核心SHA b948765ea94423d628a1d455a7de8f737a84b45b3bee969a949b6886a4dee6b8；维护源/mnt/samurai-full282/libcamera391-ipe-r30-built/src/libcamera-v0.7.2。正常包配方已更新。391原默认四摄／RAW／隔离IPA82＋PipeWire12共94direct证据保持，不重复全部回归。

WSL Ubuntu root，源码/build访问先284/storage.py::mounted_build()；现32GiB ext4 backing不能格式化／重建。驱动source354 branch samurai-icp-platform389，HEAD a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07，干净。Image363/源ba61a62293e0f6bc5838c06f2e85e033e3d702a8，release7.3.0-rc6-rmx1931-samurai-k363+；后续模块源不同。boot389 SHAe0256ff5bad0f6a2139de8690974d5fc25a0b58cad4cec1bb22f26bf0280884f，logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da保持。实际DT389七SID/5仅IOVA节点，原camera_mem保持。

389-intree-r4 qcom-camss SHA24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288，adapter SHAa0167f6acce4edad159d43101a723846ed494cf71fe3bb27857d2d145b44a7b8；core/helper/SG同388，新SG owner符号不可混旧SG。原778＋新增3=781。FW=/lib/firmware/qcom/sm8150/camera-icp.elf/SHAa22bc8adbb4ae97e4f8d728eecb1fd19c1bf866250b0bb7e668951c41c159e63。390正常卸载/重载、owner导出生命周期和111direct已实测。

## 下一步和完整范围

本轮发现已知未提交图像DMA的输入别名拒绝仍让peer失败。优先让SoC核心明确报告安全局部拒绝／已提交／未知完成边界，adapter只隔离可证明安全的局部错误；不能仅按errno猜测、不能放松未知MAP/FRAME/UNMAP的引用保留及A5/IRQ+IPE resetACK。真实硬件错误并发仍待独立验证。

然后推进原厂Gamma/LTM/CCM完整IQ，保留reference/kernel363/REMAINING-CAMERA-SCOPE.md全部第五2MP身份/mux、多模式、动态帧长/防频闪、几何/多摄同步、连续AF与光学画质。仍1:1 NV12/NV21 IQ旁路、显式V4L2所有权，异步implicit-fence发布/缩放未证明；不得把取消验证缩成总目标完成。光照相关测试等合适环境，旧SSC间歇EPERM/daemon4未宣称修复。

回退：391设备k391-install-r2/repository/rollback有签名r29/r24七包，backup有world/repo；r1已实测回退，r2新包保持。内核仍390原两模块/原缺失三模块与FW记录、boot366 SHA c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924；restore-files.py --offline-files-only只恢复文件/depmod，须停消费者回收DMA并配合boot366，不全量重装778模块。392未执行任何回退。

保留373/375/376/379启动与ACK、381未知DMA/reset、388 DMA-only SG禁sg_page/sg_phys及自有IOMMU别名、377/378失败审计、383 Unicorn全局MEM_READ破坏ThumbIT/SP。private=/mnt/e/edk2-samurai-out/kernel392及前序，FW/HAL/ASM/CDM/全日志/图像/个体配置不公开。公共mirror=/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150，只有本地提交，不push/PR，保留其它改动。
'''
(ROOT/'NEXT-SESSION.md').write_text(checkpoint)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续active多摄/ISP目标。读WORKING-BOUNDARIES.md、NEXT-SESSION.md、reference/kernel392/README.md。392实测四种活动作业取消及输入别名拒绝/peer错误/全关闭再打开恢复；r1前三通过，第四因peer CRC准备太晚未取消，保留失败；r2只补两用例，r3默认r30 GStreamer另12帧通过。26新增作业=20completed+4cancel+2预期失败，硬件完成24；累计jobs132/completed126/cancel4/failed2/first_error=-22，fatalfalse并已恢复，不要按旧全0断言误判或重置。全部worker/client/collector终态、无fault/taint、资源回收、桌面恢复。无内核/DT/模块/FW/包/配置改动，保持390正式平台和391签名r30/r25；host392→390guard，旧378不可用。source354 a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07干净，源码访问先mounted_build。下一步核心明确安全局部输入拒绝与已提交/未知DMA边界、adapter隔离可证局部错误；当前别名-EINVAL仍使peer-EIO，是收敛项。真实硬件错误并发未验，不能以输入拒绝冒充。继续原厂Gamma/LTM/CCM完整IQ及363全范围第五2MP/模式/帧长/几何/同步/连续AF/光学。关灯黑噪点按低照度解释，目标未完成。\n')
print(json.dumps(dict(stage=392,checkpoint_updated=True,expected_error_counters_preserved=True,passed=True)))
