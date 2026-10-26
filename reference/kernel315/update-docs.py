"""Update current handoff and mirror only this stage's public changes."""
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
next_text='''# Realme X2 Pro 当前检查点

2026-10-19：[315 libcamera RAW与硬件处理流](reference/kernel315/README.md)已实机通过。六种现有板级模式的RAW＋NV12默认AE/AWB、四摄RAW-only、主摄双流／RAW-only单次AF及双流取消、广角双流缓冲暂停恢复已验证。累计902完成请求／1405应用缓冲，868请求以SOF事件时间关联，最大差61,511ns。完整多摄／骁龙ISP目标active、未完成。

只验证当前改动，复用未变更基线，不默认全量扫描、固定规模、重复哈希或普通操作确认。[当前规则](WORKING-BOUNDARIES.md)。

## 设备与源码

USB原严格密钥SSH169.254.42.1，同一305 boot guard：/var/lib/samurai/k305-geometry-r2/boot-id-private.txt。设备7.3.0-rc6-rmx1931-samurai-k298+，实际298 Image＋305长焦模块＋309 CAMSS。产品libcamera r24/config-r19/PW-SPA-Gst1.6.9-r3仍RAW＋CPU ISP，315候选未安装。

当前加载309 CAMSS note SHA19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113，安装模块SHA09eaf871562f79431009df0b6f3adda026b2da9cd57a1d76dfdf3b284d123eae，原模块备份/var/lib/samurai/k309-module-install-r1/qcom-camss-before.ko。长焦SHA d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9。

309维护内核树/home/cy122/x2pro-linux/camera309-link-kernel，samurai-link309／f7ee1b4735a217e2aebdcae1cd385ed8823fc710。314共享流候选/home/cy122/x2pro-linux/camera314-streams-kernel，samurai-raw314／afad7bde625bbf7bf58c145bde1f977b806da986。315无最终内核改动，分支已切回314；两个旧.rej未跟踪、不构建。完整Image／模块重建待做，临时314候选已经卸载。

SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline现在是315，非Git提取树。使用reference/kernel315/build-candidate.py，取315 pipeline／framework及313 IPA／mojom／四个YAML；旧313／312等脚本会覆盖实现。匹配的新库、IPA、代理必须一起使用。build-runtime.py编当前应用，prepare-probe.py打包；生成脚本不重放，当前源文件／补丁为权威。[源码](reference/kernel315/source-state.json)、[部署锁](linux-port/camera/deployment-lock.json)。

## 315 当前实现

标准Raw／Viewfinder角色支持RAW-only、NV12-only、RAW＋NV12同请求。拓扑发现同CSID的RDI与PIX，没有板级节点／地址硬编码。RAW应用缓冲直接DMA，不逐帧复制。RAW-only保留四个内部640×480NV12缓冲以支持统计／CPU对焦，后续可优化开销。

libcamera内部V4L2Device增加带标准FRAME_SYNC事件时间的信号，旧frameStart保留。分别以每路线上的kernelSequence查SOF时间；两路／控制元数据就绪才完成请求，差须≤min(1ms,帧周期/8)。缺事件／不匹配报错误帧。软件事件时间不是硬件帧ID，也不是曝光开始。SOE缓冲时间原型已在构建前撤回，prepare-sof.py／build-kernel.py禁用，最终使用原EOF缓冲时间；SensorTimestamp真实曝光语义仍待完善。

r1广角双流34请求；r2其它三摄双流、四摄RAW-only、广角NV12-only；r3新增主4608×2592／前1928×1088双流、广角120ms缓冲暂停、主摄AF。六模式双流202请求，RAW-only四基本模式141请求；全部默认3A稳定。应用实际读DMABUF，长度／时间／控制有效。普通流两路序号恰好相同，未声称故意错位／独立重开后序号不同的libcamera场景已覆盖。

r3广角暂停后少输出4帧槽，恢复33请求／66缓冲及3A，无错配；不宣称无损。主摄双流AF224请求／23镜头命令／Focused；双流取消44请求／1命令／Idle；RAW-only AF224请求／23命令／Focused，均无命令错误。仍是313 ContrastAf从NV12 Y评分、扫描冻结3A，非硬件BAF／PDAF、连续AF或距离标定。光学范围仍为主4608×3456到640×480，同一场景。

最终相关库Werror第2次构建通过。k315-raw-r1～r3的worker／fixture／应用／IPA均终态，原309模块与PW/WP恢复，CAMSS／两CCI休眠，九路电源关闭用户0，相关fault增量0、taint0。无活跃采集／构建。不要重放这些run。[覆盖](reference/kernel315/coverage-validation.json)、[收尾](reference/kernel315/final-health-validation.json)。

## 沿用证据和待办

[314](reference/kernel314/README.md)：复用上游streams，适配175IPP／元数据；修复先关输入再停IPP导致超时及先回收DMA导致RDI首帧缺SOF。r1～r4失败保留，r5四摄原生双路分别停／重开259路帧通过。不是四颗实体摄像头同时工作。

[313](reference/kernel313/README.md)：复用ContrastAf；修复IPA configure缓存重置造成动态镜头ControlId失效，init只保留独立范围。主摄DAC208～926，标准Auto／Trigger／State／FocusFoM。停止后禁止AF／镜头写入。

[312](reference/kernel312/README.md)：六模式sensorConfig位深／尺寸选择；v2目录按实际时序匹配，默认start即AE/AWB。新增主16:9／前1928测得曝光／增益写入SOF＋2。缺图像后重映射请求、缺统计从确认历史补控制且AwbLocked=false，不伪造统计。

下一步接产品包、PipeWire／GStreamer消费者并选择硬件路径；完善曝光时间语义、故意错位／SOF事件丢失恢复、RAW-only内部PIX开销。继续正式黑电平、CCM／颜色、阴影、个体EEPROM校验／绑定和多摄几何／同步；304解码值仍未应用。其它OEM／Quad Bayer模式、完整裁剪／binning、其它输出、主其它模式AF、连续AF和距离图待办。用户延期纯色／遮光不阻塞其它工作。保持SoC／板级／主线内核／驱动／用户空间分层；旧GPU／modem／SSC问题开放。
'''
(ROOT/'NEXT-SESSION.md').write_text(next_text)
prompt='''继续多摄／骁龙ISP适配，goal active、未完成。读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel315/README.md。按改动验证，复用基线，免全量扫描／固定规模／重复哈希／普通操作确认。

315已完成libcamera RAW-only／NV12-only／RAW＋NV12同请求。六现有模式双流默认AE/AWB、四基本模式RAW-only、主双流和RAW-only单次AF／双流取消、广角120ms双流暂停恢复通过。902完成请求／1405应用缓冲，868次RAW／PIX SOF事件时间关联，最大差61,511ns，全部匹配；r1～r3已终态，不重放。最终相关Werror库构建第2次通过。产品接入及完整校准仍未完成。

设备实际298 Image＋305长焦＋309 CAMSS，USB原严格密钥169.254.42.1，同一305 boot guard。临时314模块已经卸载，309 note19f4c3571053c60ea81004c89c9e570a7532f33e6f23c7fbb00076b176fd1113，PW/WP恢复，PM／九路电源释放，fault0/taint0，无活跃采集／构建。产品r24/config-r19仍RAW＋CPU ISP。

SDK /home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline现在是315，使用reference/kernel315/build-candidate.py；取315 pipeline/framework、313 IPA/mojom/YAML，旧313等入口会覆盖实现。新库／IPA／代理配套。315无最终内核改动，复用314树camera314-streams-kernel，samurai-raw314／afad7bde625bbf7bf58c145bde1f977b806da986；309维护树保留。弃用SOE原型在构建前已撤回，prepare-sof.py/build-kernel.py禁用。生成脚本不重放。

RAW应用缓冲直接DMA；RAW-only暂保留内部640×480NV12供3A和CPU对焦。标准FRAME_SYNC事件时间关联独立帧号，非曝光时间／硬件ID；最终缓冲和SensorTimestamp仍EOF语义。故意错位／独立重开后不同序号、事件丢失恢复尚未实测。AF仍ContrastAf、单场景主4608×3456→640×480，非BAF/PDAF/连续/距离标定。

下一步产品包与PipeWire/GStreamer消费者接入，完善帧时间语义与恢复，优化RAW-only内部PIX开销。然后继续正式黑电平／CCM／阴影／个体EEPROM校验绑定、多摄几何同步；304解码值未应用。四颗实体摄像头同时、其它OEM模式、完整裁剪binning和光学校准仍未完成。用户延期纯色／遮光不阻塞。分清SoC／板级／主线／驱动／用户空间；旧GPU／modem／SSC问题开放。
'''
(ROOT/'NEXT-SESSION-PROMPT.md').write_text(prompt)
headline='315（2026-10-19）：libcamera候选接入RAW-only、NV12-only及RAW＋硬件NV12同请求；六模式默认AE/AWB、四摄RAW-only、主摄双流／RAW-only AF和取消、一次缓冲暂停恢复通过。902请求／1405应用缓冲，868次SOF事件时间关联均匹配。RAW直接DMA，RAW-only暂保留内部PIX；事件时间不是曝光时间或硬件帧ID。仅临时候选，已恢复309，产品仍RAW＋CPU ISP，完整校准与产品接入未完成。[315实现与实测](../../reference/kernel315/README.md)。以下按历史阅读。\n\n'
for rel in ['linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md']:
 p=ROOT/rel;p.write_text(headline+p.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
changed=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
changed += [ROOT/rel for rel in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for p in changed:
 dest=mirror/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print('Updated315 handoff and mirrored',len(changed),'changed public files.')
