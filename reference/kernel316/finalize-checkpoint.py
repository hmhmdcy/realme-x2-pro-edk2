"""Save current deployment/handoff facts and mirror only this stage's sources."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
install=json.loads((HERE/'install-r2-validation.json').read_text())
assert install['passed'] and install['transaction']['installed']
path=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(path.read_text())
d.update(current_product_four_camera_regression_frames=48,
    current_stack_main_camera_focus_evidence='../../reference/kernel315/raw-r3-validation.json',
    current_stack_main_camera_auto_exposure_af='../../reference/kernel315/raw-r3-validation.json',
    current_boot_auto_af_retest_scope='315 hardware single AF/cancel and RAW-only AF evidence reused; final316 installed AF not independently repeated.',
    current_stack_automatic_exposure_startup_slow=None,
    current_stack_automatic_exposure_startup_scope='316 RAW runs reach stable AE/AWB; startup latency has not been newly measured.',
    default_isp_backend='camss-vfe',system_dma_heap=True,cpu_isp_fallback_available=True,
    pipewire_consumer_buffer_type='MemFd',pipewire_end_to_end_zero_copy_verified=False,
    factory_distortion_and_ae_sync_block_source_verified=True,
    factory_distortion_model_decoded=False,factory_ae_sync_coefficients_applied=False,
    factory_oem_block_evidence='../../reference/kernel316/OEM-CALIBRATION.md')
d.pop('cpu_isp_and_system_dma_heap',None)
path.write_text(json.dumps(d,indent=2)+'\n')

handoff='''# Realme X2 Pro 当前检查点：316

2026-10-19。多摄／骁龙ISP校准适配目标active、未完成。本轮产品接入已完成：libcamera r25、config/stack r20、314 CAMSS已安装，默认硬件NV12＋AE/AWB、RDI直接RAW，主摄对焦沿用CPU对比度。设备仍298 Image＋305 S5K3M5模块；没有刷写或重启。

先读[当前操作规则](WORKING-BOUNDARIES.md)、[316实现和实测](reference/kernel316/README.md)、[部署锁](linux-port/camera/deployment-lock.json)。只做相关构建／功能／故障／资源检查，复用未改动基线，不默认全量扫描、固定次数或普通操作确认。

## 已完成证据

- 完整13包构建和签名通过，六IPA保留，实际升级七运行包。
- 四摄分别GStreamer640×480 NV12，主1920×1080、前1280×720，四摄RAW-only通过。RAW136请求均与内部PIX关联，AE/AWB稳定。见consumer-r3、r5-validation。
- 安装r2默认枚举四摄，系统GStreamer广角和PipeWire广角NV12各12帧。PW实际接收MemFd，不是端到端零拷贝。
- 315六模式RAW＋NV12、主摄双流／RAW-only AF及取消、缓冲恢复沿用未改动证据；不冒充316重新全量验证。
- 所有316构建／采集／安装worker终态；PW/WP各一个进程，CAMSS／两CCI休眠，相关故障增量0、taint0。

## 当前部署与源码

USB原严格密钥SSH 169.254.42.1，kernel316/host.py提供raw_ssh。305同启动guard仍适用于状态切换；普通只读不用逐条检查。当前服务和包版本在私有kernel316/device-context.json。已部署库没有强制handler或实验启用环境变量。

加载的是314 CAMSS，模块SHA 39a420145981206afe324015c6cf7cafe92aa1fae44d68b7efbffd5d4b23c730；加载note SHA 4e8c841d9c80d6958a83f02e067528cee4c5233776fb2ea15d6177823a3a8aa8。旧309模块、七旧包和world/仓库在/var/lib/samurai/k316-install-r2，本机本地签名仓库作为当前包源。首次安装脚本假设旧r24/309，不能在当前r25/314上直接重放。

正式配方已更新linux-port/packages/libcamera与samurai-camera-config。完整r25源在WSL SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera316-r25-built/src/libcamera-v0.7.2；原work/libcamera恢复。work/libcamera299-inline仍315，不要用旧构建器覆盖316包源。

316源码以reference/kernel316/pipeline、framework、313 IPA和累计0029补丁为准。后续可用refresh-pipeline.py同步pipeline／累计配方，build-packages.py --resume复用对象。生成器和已有手机run不重放；执行结果不明先查真实进程／状态。

内核314树/home/cy122/x2pro-linux/camera314-streams-kernel，samurai-raw314，提交afad7bde625bbf7bf58c145bde1f977b806da986；309维护树保留。316没有新增内核改动。V4L2核心隐藏用户空间CAP_STREAMS不表示驱动内部共享流不可用，最终handler已移除这个错误门槛；多模式NV12建议范围也已汇总，避免Range format is ambiguous。

## 继续完整目标

优先已有方案和本机原厂证据，区分SoC公共驱动、板级DT／供电、传感器驱动、libcamera算法／调校和消费者。下一步继续原厂EEPROM校验／个体绑定和正式画质，见reference/kernel316/OEM-CALIBRATION.md及kernel304/README.md。

本机HAL已定位广角序列号、带有效标志的畸变块、AE同步记录；已解码亮度／增益／曝光部分字段。实际数据在私有kernel316/unit-calibration-blocks，原始样本仍299；没有新写EEPROM、OTP、NV或persist。WB／LSC完整checksum未完成，畸变模型／内参未解码，缺主摄曝光参考，未应用个体值。原厂HAL只离线反汇编，没有执行。

还需黑电平／CCM／颜色／阴影、多摄几何／同步、真实曝光时间语义、事件丢失恢复、RAW-only内部PIX开销和连续AF。四颗实体摄像头同时工作未验证。用户延期纯色／遮光不阻塞其它工作。旧GPU／modem／SSC故障仍开放，不能声称整机健康或完整适配完成。
'''
(ROOT/'NEXT-SESSION.md').write_text(handoff)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('''继续多摄／骁龙ISP完整适配，goal active、未完成。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md及reference/kernel316/README.md。

316产品接入已落地：默认r25/config-r20＋314 CAMSS；四摄GStreamer NV12、主1080p／前720p、四摄RAW，以及安装后系统GStreamer／PipeWire广角NV12通过。设备仍298 Image＋305长焦，PW/WP正常、相机休眠，所有worker终态。不要重放旧r24/309前置的首次安装事务或旧生成器。

继续WB／LSC工厂校验、个体绑定、畸变／内参和主摄AE同步参考；OEM分析见kernel316/OEM-CALIBRATION.md。个体值尚未应用，完整画质、多摄同步、曝光时间、连续AF未完成。按改动选择必要验证，复用基线，普通调试／取流／修复无需重复确认。
''')

mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/'NEXT-SESSION.md',ROOT/'NEXT-SESSION-PROMPT.md',path]
for package,names in {
    'libcamera':['APKBUILD','0029-camss-hardware-pipeline.patch','source-lock.json','README.md'],
    'samurai-camera-config':['APKBUILD','source-lock.json','README.md',*[f'camss-{m}.yaml' for m in ['s5kgw1','imx471','imx319','s5k3m5']]]}.items():
    paths += [ROOT/'linux-port/packages'/package/name for name in names]
assert mirror.is_dir()
for source in paths:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Updated316 deployment facts, concise handoff and selected source mirror.')
