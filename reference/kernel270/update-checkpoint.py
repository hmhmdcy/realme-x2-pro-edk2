"""Record the actual deployment and preserve the unfinished optical/ISP scope."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
P=Path('/mnt/e/edk2-samurai-out/kernel270')
identity=json.loads((R/'postboot-identity-validation.json').read_text())
reg=json.loads((R/'three-camera-regression-validation.json').read_text())
assert identity['matching_candidate_boot_read_back'] and reg['passed'] and reg['frames']==192
old=ROOT/'NEXT-SESSION.md';archive=ROOT/'archive/NEXT-SESSION-before270-deployment-update-2026-10-18.md';assert not archive.exists();shutil.copyfile(old,archive)
current='''# Realme X2 Pro 当前检查点

2026-10-18：[270多摄适配进行中](reference/kernel270/README.md)。S5K3M5长焦已接入公共驱动/静态DT，现有前摄和两颗后摄可原生枚举、采集。**长焦真实样片仍近乎暗场，完整光学成像、多后摄GUI、主摄和骁龙硬件ISP未完成；goal保持active。**

## 当前部署与启动身份

手机已完成一次受控切换：只刷boot270，完整分区读回SHA256 `0904b3b6616652e08709891cfdee34f1f733ff1e7022b7749bedea758108e4e8`。Image183/logdump保持，release仍`7.3.0-rc6-rmx1931-samurai-k132+`，774个模块、961个包。新S5K3M5模块SHA256 `22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72`，现机已有CCI模块与本次构建逐字一致，其余773模块未替换。七个相机/依赖模块加载note与磁盘一致。[部署读回](reference/kernel270/postboot-identity-validation.json)、[实际绑定](reference/kernel270/postboot-hardware-validation.json)。

当前运输入口`reference/kernel270/host.py`，严格原SSH主机密钥、新鲜发现的私人USB端点，读取私人`postboot-verified-private.json`。手机guard `/var/lib/samurai/k270-work/boot-id-private.txt`。269及更早guard/PID已失效；不要绕过旧guard或覆盖旧记录。当前桌面/音频服务身份由手机`/var/lib/samurai/k270-services-current-private.json`维护，续作先核。新启动为正常锁屏，未改锁屏/idle偏好；新启动的自动旋转实屏效果和多后摄Snapshot菜单未验收。

用户态r19/config-r14/PipeWire/SPA/GStreamer1.6.9-r3沿用，APK数据库未变。CPU软件ISP/system heap与Snapshot Cairo/禁用GL、Vulkan、offload回退保持；默认GPU故障未修。269新完整Image/773模块构建仍保留且未部署，本轮不是把269完整内核晋升为已验收系统。[269历史](reference/kernel269/README.md)。

## 本轮已经验证

- 新S5K3M5完成正常chip-ID探测并绑定，标准cam枚举IMX471前摄、IMX319后摄和S5K3M5长焦；首个长焦模式2104×1560，RAW/RGB各12帧通过。[首次采集](reference/kernel270/telephoto-capture-validation.json)。
- 两颗后摄经标准libcamerasrc/CPU JPEG，各36帧并各保存一张私人JPEG，IMX319输出1600×1200、长焦2048×1536；这只证明编码/采集路径，不是长焦光学画质通过。[JPEG](reference/kernel270/two-rear-jpeg-validation.json)。
- 14段独立标准cam调用，共192帧，包含前摄/两后摄交替、长焦SIGINT正常结束和重开。每段资源回收、三MCLK关闭、fault增量0、taint0，无服务重启。[回归](reference/kernel270/three-camera-regression-validation.json)。
- 同一启动S5K3M5物理sensor彩条36帧，生成正确白黄青绿品红红蓝黑彩条；CSID测试图案未改，结束后sensor pattern恢复0、PM正常。[彩条](reference/kernel270/telephoto-bars-validation.json)。
- 同request的24组RAW/RGB曝光诊断：稳定6帧/档，2ms实际metadata2001us，RAW均值64.074/std0.531/max68；32ms实际31991us，均值65.020/std0.930/max87，99.998% RAW≤80。表明真实场景仍近黑电平，不能以非零噪声或JPEG成功宣称可用成像。[配对统计](reference/kernel270/telephoto-paired-validation.json)。

旧269启动上的Snapshot前后切换/两张GUI JPEG也在本轮通过，但它只覆盖IMX471与IMX319；不扩写为新启动三摄GUI验收。旧启动原Snapshot意外重启与modem watchdog仍未解决，原pstore私人备份保持。当前受控启动pstore为空不抹去旧故障。

## 源码、回退与下一步

维护候选WSL `/home/cy122/x2pro-linux/camera270-kernel`，分支`samurai-multicamera270`，sensor提交`20393178c30c9043d5fbf1ffc9aa7889421f5db0`，板级提交`edd2e8c14a760b8a889b9313f45acfc1d015a7fb`。正常19.2MHz配置由标准compatible/时钟选择，不再依赖lab provider、机型根判断或驱动内电压常数；P L2/L6等接线在DTS。匹配Image183模块W=1零诊断、四类schema、实际供电函数882个ASan/UBSan API故障模型通过；模型不是内核并发或硬件故障注入。两提交本地保持，尚未发布。

私人PC目录`E:/edk2-samurai-out/kernel270`，含新boot、原boot267锁、双端模块回退、自己拍摄的JPEG、原日志和当前启动身份。只有boot已刷一次，logdump/NV/校准/工厂备份未刷；切换前source NV哈希核对通过。模块/工具上传、guard采用、quiesce、restart2、flash、拍摄及各构建目录都已执行，不可重放。新上传probe位于`/run/samurai-camera270-probes/telephoto-paired-probe270`；首次上传在写入前失败，确认0字节/无capture context后分块恢复成功。

优先确认长焦镜头无遮挡/场景光照，继续曝光/增益/RAW空间响应和AF/模式核对。异步问题已请求用户调整正常照明、稍远场景，尚未获得答复，不能假定物理位置已改变。新sensor仍报告Selection默认区域和静态属性缺失，需依据真实模式补齐，不能用假几何或虚构delay消除日志。随后补标准GUI多后摄选择、颜色/方向/画质、完整模式/录像、GPU与长稳。

S5KGW1主摄已对本机Sunny/Qtech两份BIN完成边界检查与各两种schema投影交叉验证：每份10模式、51初始化记录，包含11条WRITE_BURST，uint32数组/8字节对齐不能沿用旧单值qword读法。原始BIN未改，未对主摄上电/写寄存器。首次XML导出达到16MiB上限，完整退出后新目录按64MiB文件/256MiB内存/15秒CPU/20秒墙钟限制成功，原失败保留。[主摄数据](reference/kernel270/gw1-metadata-validation.json)、[交叉核对](reference/kernel270/gw1-crosscheck-validation.json)。实际模组变体、主摄driver、C-PHY端点、AF及候选人像sensor仍待完成。

目前使用骁龙CSIPHY/CSID/VFE RDI采集RAW，再由libcamera CPU软件ISP处理；没有接通Spectra硬件成像处理，GPU软件ISP也不等于Spectra。完整kernel/rootfs重建、其它硬件状态和规则仍见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)、[操作边界](WORKING-BOUNDARIES.md)。目标未完成。
'''
old.write_text(current)
readme=R/'README.md';text=readme.read_text()
text=text.replace('## 当前已取得的新证据','## 当前部署与最新结论\n\nboot270已实际刷写并逐字读回，Image183不变，774模块/961包；270新guard及现机状态以[检查点](../../NEXT-SESSION.md)和[实际绑定](postboot-hardware-validation.json)为准。S5K3M5已过chip-ID与RAW/RGB采集，三摄14段192帧交替/中断/重开通过。两后摄可生成JPEG，但长焦真实样本仍是暗场，光学成像未验收；物理sensor彩条正确，24组RAW/RGB曝光统计仍近黑电平。[回归](three-camera-regression-validation.json)、[两后摄JPEG](two-rear-jpeg-validation.json)、[彩条](telephoto-bars-validation.json)、[曝光](telephoto-paired-validation.json)。\n\n以下准备段按部署前阶段解释；本轮已部署，不可重复切换。\n\n## 当前已取得的新证据')
text=text.replace('当前已验收实体sensor只有IMX471前摄和IMX319后摄。S5K3M5尚待真实chip ID、RAW及应用验收；','当前IMX471前摄、IMX319后摄及S5K3M5长焦均已真实绑定/采集。S5K3M5的chip ID、RAW/RGB、彩条和JPEG编码已验证，但真实光学场景仍近黑电平，新启动三摄GUI与AF尚待验收；')
text+='\n\n## 主摄后续输入\n\n本机Sunny/Qtech S5KGW1各10个模式和51条初始化已通过边界解析和两种独立schema视图交叉核验，保留11条突发写入及真实uint32向量。没有主摄硬件操作，不能把数据解析当成支持。[数据](gw1-metadata-validation.json)、[交叉核对](gw1-crosscheck-validation.json)。\n'
readme.write_text(text)
hardware=ROOT/'linux-port/docs/HARDWARE-STATUS.md';text=hardware.read_text();title=text.index('\n')
note='''

270续作（2026-10-18）：boot270/Image183，774模块/961包。新增S5K3M5长焦公共资源驱动及静态设备树已上机，标准cam真实枚举前摄/IMX319后摄/S5K3M5长焦；RAW/RGB各12帧、三摄14段192帧交替/正常中断/重开通过，六rails/三MCLK回收及fault0/taint0。两后摄各36帧并生成JPEG，但**长焦真实样本仍近乎暗场，尚非可用光学成像**；S5K3M5自身彩条正确，2ms/32ms配对RAW仍近黑电平。主摄GW1两家模组数据交叉核对完成，未上电；新三摄GUI、AF/更多模式/录像/画质/长稳、Spectra硬件ISP与GPU仍未完成。旧Snapshot/modem watchdog不因本次正常启动而算修复。[270证据](../../reference/kernel270/README.md)、[当前检查点](../../NEXT-SESSION.md)。以下269及更早部署和模块数均按阶段解释。
'''
text=text[:title]+note+text[title:]
hardware.write_text(text)
camera=ROOT/'linux-port/camera/README.md';text=camera.read_text();title=text.index('\n')
text=text[:title]+'\n\n270当前：boot270/Image183，774模块/961包；新增S5K3M5长焦完成公共供电/标准DT、chip-ID、RAW/RGB和彩条验证，前摄及两后摄192帧交替回归通过。两后摄可生成JPEG，但长焦真实样本近黑电平，光学成像仍未完成；GW1主摄仅数据解析交叉核对完成，新三摄GUI、AF、录像、画质、GPU/Spectra仍开放。[270](../../reference/kernel270/README.md)、[检查点](../../NEXT-SESSION.md)。旧部署锁记录只覆盖旧组合，尚未将新增长焦整合为完整rootfs/APK发行。\n'+text[title:]
camera.write_text(text)
index=ROOT/'DOCS-INDEX.md';text=index.read_text();needle='| Camera应用、实体前后摄与内部TPG | '
assert text.count(needle)==1;text=text.replace(needle,needle+'[270第二后摄部署/暗场与主摄数据](reference/kernel270/README.md)、',1);index.write_text(text)
report=dict(stage=270,authoritative_checkpoint_updated=True,old_checkpoint_archived=str(archive.relative_to(ROOT)),
 rear_streaming_distinguished_from_optical_acceptance=True,full_goal_remains_incomplete=True,
 source_commit=json.loads((R/'kernel-commit-validation.json').read_text())['board_commit'])
(R/'documentation-update-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
