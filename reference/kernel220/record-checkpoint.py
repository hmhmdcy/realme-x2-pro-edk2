from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel220')
r=json.loads((private/'current-work-private.json').read_text());r.update(state='r6 two-mode exposure-metadata defect reproduced; full r7 incremental build live, original214 tree protected in snapshot',
 active_build_session=97784,build_state_file=str(private/'incremental-build-state-private.json'),
 candidate_retained_directory='/home/cy122/x2pro-linux/libcamera214-root/work/libcamera220-built',
 original214_backup_while_build_live='/home/cy122/x2pro-linux/libcamera214-root/private/libcamera214-before220-r2',
 phone_still='boot219 e49 module plus full r6/config-r1; full mode N',
 next='Poll97784; source snapshot must restore after terminal. Validate all13 r7/r2 APKs and5IPA/full features; stage isolated runtime, repeat2MP/4MP metadata and forced-isolation config. Preserve original r6 rollback and complete coherent package deployment only after physical candidate success')
(private/'current-work-private.json').write_text(json.dumps(r,indent=2)+'\n')
(here/'README.md').write_text('''# 220：切换模式后的曝光元数据

2026-10-16，手机仍为已验证的boot219/e49模块/完整r6/config-r1，当前实验参数N。新USB邻居与当前启动身份已核对，建立k220-baseline guard；49条当前相机payload、媒体图/休眠与三DSP检查通过。[基线](baseline-validation.json)。

标准客户端当前只暴露Contrast/Gamma，手动曝光API仍开放。分别取36帧2MP与4MP RGB，仅采集元数据和DelayedControls数值，不映射或保存像素。4MP元数据与本模式行时长吻合；2MP的1290行应换算约17057.85µs，却报10117µs。72组元数据都符合缓存的4MP行时长。[根因](metadata-root-cause-validation.json)、[2MP](exposure-metadata-r6-1920x1088-validation.json)、[4MP](exposure-metadata-r6-2296x1728-validation.json)。这不代替实际曝光延迟/光度标定。

源码显示IPA init先缓存sensorInfo，configure只更新控制范围，未刷新模式时序。候选通过IPAConfigInfo传入当前sensorInfo，并在每次配置时更新曝光换算，拒绝零速率/行长。[三文件补丁](libcamera-refresh-sensor-timing.patch)、[源码锁](candidate-source-validation.json)。参考[原始元数据实现](https://lists.libcamera.org/pipermail/libcamera-devel/2025-March/049410.html)与[其它IPA的逐次传递方式](https://lists.libcamera.org/pipermail/libcamera-devel/2024-December/047902.html)，没有复制其它镜头标定。

完整r7/r2构建进行中，保留全部原管线与子包。使用原214完整对象缓存和官方abuild build/rootpkg/index阶段；原214目录先快照保护，终态后恢复，候选完整源/对象另存。最初宿主沿chroot绝对软链接找不到源码归档，在编译前退出并恢复了原目录；实际缓存归档SHA512正确，已恢复已有候选继续。[原失败](initial-build-preflight-failure-validation.json)。手机包尚未替换。

关灯/室内窗边条件保持，无闪光灯、外部照明、场景图片或定位坐标公开。GNSS真实fix、后置四摄及其余全外设目标继续active；旧[219验收](../kernel219/README.md)保持。
''')
old=(repo/'NEXT-SESSION.md').read_text();archive=repo/'archive/NEXT-SESSION-through219-2026-10-16.md'
if not archive.exists():archive.write_text(old)
first=old.index('2026-10-16');end=old.index('\n\n## 当前部署',first)
old=old[:first]+'2026-10-16，220进行中：手机保持219已验收boot/模块/r6；已实测2MP曝光元数据错用4MP行时长，r7三文件修复完整构建中。[220记录](reference/kernel220/README.md)、[219验收](reference/kernel219/README.md)、[边界](WORKING-BOUNDARIES.md)。全外设goal active。'+old[end:]
start=old.index('- 完整r6构建session40635');end=old.index('\n- IPA验证',start)
old=old[:start]+'''- 当前220构建exec session97784，原31076因宿主chroot软链接检查失败终态，未开始编译且原目录已恢复；已保留候选后显式续作。现在SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera为工作副本，原214在/private/libcamera214-before220-r2；97784终态后自动恢复，活进程未明时不可重启/移动源码。官方build/rootpkg/index保留完整功能，输出/packages220，候选终态保留/work/libcamera220-built。当前手机用k220-baseline guard，仍r6未升级；下一步13包/5IPA核验、2MP/4MP及隔离代理元数据对照。详情私人kernel220/current-work-private.json。
''' + old[end:]
# Detailed retained helper hashes and historical readiness remain in219/archive.
start=old.index('- TFTP207');end=old.index('\n- 前摄CCI',start)
old=old[:start]+'- TFTP207/MCFG、MM191/GNSS/SSC及BT185、Wi-Fi部署保持，详细指纹见219记录。'+old[end:]
if len(old.encode())>6500:
 start=old.index('- r6事务');end=old.index('\n- 本轮私人',start)
 old=old[:start]+'- r6事务verified，旧r5七包/world/repo/config与降级模拟保持，见219。220回退应保留当前r6七包，不能套用更早r5/r4步骤。'+old[end:]
assert len(old.encode())<=6500,len(old.encode());(repo/'NEXT-SESSION.md').write_text(old)
print(json.dumps(dict(stage=220,live_build_session=97784,phone219_deployment_preserved=True,checkpoint_bytes=len(old.encode()),goal_active=True)))
