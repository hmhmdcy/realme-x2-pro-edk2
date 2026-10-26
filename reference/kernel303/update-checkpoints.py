from pathlib import Path
import hashlib, json, shutil, subprocess
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
names = ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'DOCS-INDEX.md',
         'linux-port/camera/README.md', 'linux-port/camera/kernel/README.md',
         'linux-port/docs/HARDWARE-STATUS.md', 'linux-port/camera/deployment-lock.json',
         'linux-port/camera/kernel/source-lock.json']
archive = ROOT / 'archive/camera-before303-2026-10-19'
assert not archive.exists()
archive.mkdir()
records = []
for name in names:
    source = ROOT / name
    target = archive / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    records.append(dict(path=name, sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
(archive / 'manifest.json').write_text(json.dumps(dict(stage=303, files=records), indent=2) + '\n')
(ROOT / 'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-19：[303硬件AE候选](reference/kernel303/README.md)。按用户新目标恢复适配，目标active、未完成。本轮手机不可达，无新增实机试验、刷写、重启或安装；当前启动未复核。以下设备版本来自最后已验证记录。

## 当前部署与启动身份

设备#298／7.3.0-rc6-rmx1931-samurai-k298+；内核树`/home/cy122/x2pro-linux/camera279-isp-kernel`，samurai-blc298／c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117。778模块、boot276、DT及固件沿用302记录。产品libcamera0.7.2-r24／config-r19及PW／SPA／Gst1.6.9-r3仍按RAW＋CPU ISP解释；303候选未安装。

Image SHA eb8054e69991528cad4f126d7723b7ef4869b288fb85c992f4803cbfeab5ddaf；logdump dfef7be4f358c5c16e8e716a60c24da8a139de73b1e07912d70f2b58613d80df；boot 0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64；DTB dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d。

303/host.py保留原严格密钥和#298 guard。USB网络接口未发现、两次SSH失败；先恢复连接并核实真实状态，勿以旧身份盲目切换。上次entity为main8-0010／lens8-0072、tele6-002d、wide9-0010、front7-0010，仅供历史定位，生产代码按entity发现。[部署锁](linux-port/camera/deployment-lock.json)、[源码锁](linux-port/camera/kernel/source-lock.json)

## 实现与验收边界

- SoC保留298 VFE175 WB／BLS、图像／参数／Y BHIST共享SOF。303未改内核、DT、通用libipa或产品包；模组曝光策略只在独立YAML。[分层收据](reference/kernel303/checkpoint-validation.json)
- 302最终实机960帧／36次控制变化及144图像分区响应通过，真实写入SOF＋2；范围仅IMX319当前模式。隔离请求有时延后一图像帧，元数据按实际有效上下文。[302](reference/kernel302/README.md)
- 303复用AgcMeanLuminance／Histogram／ExposureModeHelper接入候选，按epoch／SOF／revision等待控制生效。真实DSO与线程proxy各720帧合成延迟模型通过，共1440帧；三档可达亮度收敛、极暗上限及旧帧／未知上下文／停流重开通过，不计作摄像头出帧。[DSO](reference/kernel303/ipa-contract-validation.json)、[proxy](reference/kernel303/proxy-contract-validation.json)
- QEMU不实现生产Process使用的clone3，独立worker未启动，完整隔离IPC仍未通过；生成序列化13字节字段与往返另测通过，不替代IPC。Auto只支持启动时双Auto或双Manual，混合和运行中切换拒绝；WB固定、无RGB AWB，无动态帧长／防频闪／完整IQ。
- IMX319驱动曝光／增益分写、未用group-hold控制簇。联合恒EV实机测试包已编译，未执行；不能据模型认定物理锁存。必要时在sensor驱动层修正。
- 原厂IMX319 BLS16模式／288区域均960 U14；本机EEPROM双读一致但完整布局／校验未核实、未应用。OEM参考及临时WB不是本机正式暗场／色彩校准。[299](reference/kernel299/README.md)
- 最后实机健康沿用302：图／控制恢复、供电／PM自然回收、无新增所测故障。961包／50相机载荷／778模块全量核对沿用300。本轮未重新确认这些状态；旧GPU／modem／SSC缺陷未关闭，whole_system_healthy=false。

## 源码回退与下一步

SDK `/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline` **现为303源码**，续作使用303/build-candidate.py，不能重放302／300／299安装器覆盖。303 private根`E:/edk2-samurai-out/kernel303`；独立joint及AE包和哈希见303两份bundle收据，均未上机。302已测源码和最终可运行包已核对保全；源码回退方法见[303](reference/kernel303/README.md)。

接回手机后先核当前boot及资源，再`303/launch-capture.py joint r1 isolated`，按终态poll并执行`analyse-joint.py r1`；脚本不会重复已有运行目录。20000µs×2与10000µs×4共18次联合变化，核36真实写入、有效帧及BHIST／四Y分区过渡。只有实机分析passed后启动器才允许AE。补真机隔离、变光收敛、取消／丢SOF／worker错误恢复，再推进RGB统计／AWB、多摄／模式、EEPROM校验与正式IQ。纯色／遮光延期不妨碍其它测试。

内核构建输出/mnt/samurai-full282/build；按284/storage.py核backing并保留Rust环境。稳定回退#290及独立778模块、k132776／248备份保留；旧产物清理与重建见[维护收据](reference/maintenance-2026-10-19/README.md)。旧302运行均终态，不盲目重放。[操作边界](WORKING-BOUNDARIES.md)
''')
(ROOT / 'NEXT-SESSION-PROMPT.md').write_text('''继续多摄像头／骁龙ISP校准目标（active、未完成）。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md和reference/kernel303/README.md。

303仅主机：AE候选AArch64 Werror、真实DSO和线程proxy各720帧合成模型通过；QEMU clone3 ENOSYS，独立worker未启动，不能记为隔离IPC通过。序列化另测通过。手机未连接，当前boot未复核；最后已验证#298，产品RAW＋CPU ISP，候选未安装。

SDK work/libcamera299-inline现为303，使用303/build-candidate.py，勿重放302/299源码安装器。已测302源码和可运行包保全。接回设备核当前身份和资源后先做303联合曝光增益恒EV实测：launch-capture.py joint r1 isolated、poll终态、analyse-joint.py r1。不要重放旧终态运行。只有实测passed才启动AE。若复现分写锁存问题，在IMX319驱动层修正；不往SoC/DT或应用硬编码模组策略。

之后补真机隔离／变光收敛／错误恢复、RGB统计与AWB、多摄多模式、EEPROM校验和正式暗场／色彩／阴影。旧GPU、modem watchdog、SSC EPERM仍开放。
''')
banner = '303（2026-10-19）：目标恢复active。手机不可达、当前启动未复核，最后实机记录#298／产品RAW＋CPU ISP；候选复用通用AGC，真实DSO及线程各720帧合成模型通过，未上机。QEMU clone3 ENOSYS，独立IPC未验收；联合锁存、硬件AE实景、AWB及多摄完整校准待办。'
for name, prefix in [('linux-port/camera/README.md','../../'),('linux-port/camera/kernel/README.md','../../../'),('linux-port/docs/HARDWARE-STATUS.md','../../')]:
    p = ROOT / name
    p.write_text(banner + '[303源码与边界](' + prefix + 'reference/kernel303/README.md)。以下按历史阅读。\n\n' + p.read_text())
for name, prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    p = ROOT / name
    d = json.loads(p.read_text())
    d.update(stage=303, previous_lock_archive=prefix+'archive/camera-before303-2026-10-19/'+name,
             inline_userspace_candidate_source=prefix+'reference/kernel303/pipeline/camss_vfe.cpp',
             inline_candidate_build_evidence=prefix+'reference/kernel303/build-validation.json',
             experimental_ipa_source_evidence=prefix+'reference/kernel303/README.md',
             candidate_hardware_ae_source_implemented=True, candidate_hardware_ae_only_synthetic_validation=True,
             candidate_ae_dso_and_threaded_model_frames=1440, candidate_isolated_ipc_verified=False,
             phone_current_boot_not_reverified=True, inline_userspace_candidate_installed=False,
             experimental_hardware_ae_integrated=False, hardware_pipeline_ipa_integrated=False,
             full_automatic_hardware_pipeline_ipa_integrated=False, product_camera_path='RAW plus CPU ISP', goal_complete=False)
    p.write_text(json.dumps(d,indent=2)+'\n')
p = ROOT / 'DOCS-INDEX.md'
s = p.read_text(); anchor = '[302硬件IPA控制／有效帧](reference/kernel302/README.md)'
assert s.count(anchor) == 1
p.write_text(s.replace(anchor, '[303硬件AE候选／主机验证](reference/kernel303/README.md)、'+anchor))
(ROOT / 'sessions/303-hardware-ae-candidate-and-joint-latch-preparation.md').write_text('# 303：硬件AE候选与联合锁存验收准备\n\n'+banner+'\n\n[源码、构建、主机验证、保留失败与上机顺序](../reference/kernel303/README.md)。1440帧为合成输入，不是摄像头出帧；无手机安装、刷写或重启。\n')
subprocess.run(['python3', str(ROOT/'linux-port/scripts/generate-session-index.py')], check=True)
print('Recorded303 candidate; device state remains unverified, goal active and incomplete.')
