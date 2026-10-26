# 当前：506长测中；充电离线交接已更新

[充电交接](reference/charging-management-20261023/charging-adaptation-handoff-20261025.md)；[规则](WORKING-BOUNDARIES.md)，相机暂停，手机/SDK串行。

[508三项与回退、预充1299条通过；EUD串口问题见交接。额度消费者](reference/charging-oem-audit-20261023/tcpm-charger-input-candidate/README.md)离线38例/KO过，未装；PD/APSD未验。

[10小时观察](reference/charging-management-20261023/timeout-live-candidate/README.md)：supervisor6483/68160、worker6484/68170、CPU6485/6/68240；8643/36000秒、31%、26.2℃、平均+65mA、AUTO/Good、fault0、duty0.3。只读status；勿刷写/重启/切USB。

## 正式基线与新候选

[484](reference/kernel484/README.md)：五包99990.7.2-r33、config/stack0.1.0-r28 → 原r32/r27精确回退 → r33/r28保留，三次native APK add exit0。当前441三KO＋468 sensor，443/468/440四原厂profile；core a21fcedd…97b、451 proxy35526054…、444 IPA6/原签名。默认640×480／RAW原生，未刷Image/重启。

两forward14例：四摄Gst256张640 NV12、RAW-only24、dual12，268IPE＝242math＋26bootstrap；RAW-only零IPE、24负回执为未排队观察。实际/usr maps/有效签名native、UID10000/CapEff0、Manager lease/回执过。每相停服务、无liveFD/idle，CAMSS先卸/sensor先装；961 DB entry中954非cohort不变，回退全部逻辑entry精确。DB只用native APK恢复，原world/repo/属性/信任及回退包保持。原厂数学/系数不变，未重跑LTM矩阵。

[481](reference/kernel481/README.md)/[482](reference/kernel482/README.md)/[483](reference/kernel483/README.md)准备冻结；worker28188/start2003163终态passed/absent。stage Windows长参数及health-r1泛deleted误判失败保留；仅修传输/合法非exec PipeWire memfd验收，载荷不变。health-r2两样本1.126s过，实际库inode/SHA、保护/限制和fault0/taint0保持；非长稳/净充电/光学证明。

[489](reference/kernel489/README.md)仅两个core对象增量：487原厂三sensor属性／菜单＋488总线0x2027映射，485 Meson去构建RUNPATH，最终b345af8b…8bdd/51262920B。IPA6/签名/proxy/base/数学/KO/profile未改，rotation/delays未猜填。ARM SDK默认loader/5组件RTLD_NOW、验签、系统profile/worker解析及UID10000合成HOME三分支通过，未start CM/exec worker。SDK已还；r1/r2测试失败保留。

[486](reference/kernel486/README.md)真实pwd HOME/XDG启动器本地过；[490](reference/kernel490/README.md)r34/r29七签名包＋精确r33/r28回退、缓存961 DB仅7升级模拟通过，未上机。[491交接](reference/kernel491/HANDOFF.md)：package-only一次forward/8例短验/必恢复r33，23文件归档、本地进程/传输及独审通过，deployable=false、未绑定/上传/安装。手机仍归充电，恢复相机须用户明确指示。

恢复时先从充电取得届时boot/endpoint/guard/正式基线，核476旧363 uname pin后再复用。fresh476需 --formal-expected 私有481/formal-expected-private.json（SHA1c458491…4705），不可用默认440；新namespace/owner，481r1及终态事务不重放。原安装/交回证据在private481。475/480原solver及缺provider失败保持。

## 同帧PD10／LTM与原厂模式

[441](reference/kernel441/README.md)/[442](reference/kernel442/README.md)主摄720/1080、普通/隔离自动双遍与固定FULL/参数的真实→黑→白→同真实PD10因果证据复用。441 r7整轮失败/积压根因不改成功；442只修停止取消状态，仍保留运行错误和失败不提交。469长焦720及[474](reference/kernel474/HARDWARE.md)组合1080原厂mode2通过；未变范围不重采。

474 native/隔离各32，64 IPE＝60math+4boot，原回执无重复/负/未决；动态Manager mask4–7/stop恢复。隔离SOF12/rev11固定FULL/6008B参数，仅换真实/黑/白/同真实PD10，三输出互异、真实重复3110400B相等、实际消费采样hash匹配；非全消费图比较。scratch不作SRAM证明，含保存I/O不作纯性能比较，正式已恢复。

[473](reference/kernel473/README.md)只扩processed IPE的Manager gate，旧/新/旧96消费严格、B动态mask/stop过；串行38.272/29.403/38.389ms、gap3/0/3仅短段证据，不归因worker CPU。465/466原厂写入/IQ和SX时钟冻结；[468](reference/kernel468/README.md)4208×2368、LL4848/FLL3312、link723.2MHz，修S_FMT FLL2504/吞错。原厂mode3/IQ/个体保持；两尺寸64消费/IPE与LSC上下文过，旧1080仍3gap，失败保留。

## mode2控制响应

[476](reference/kernel476/README.md)得240消费/Pair、233SOF/9写；仍passed=false（错误零IPE断言），worker23019终态，正式sensor/栈/R8/服务恢复。[478更正](reference/kernel478/ipe-r1-correction.md)：pd10=false不等于IPE关闭，实际240 queue/成功receipt/completion、空参数；BHIST在IPE排队前按SOF保存，有额外负载。原快审/476失败保留，不改成功。

[479独审](reference/kernel479/HARDWARE.md)：曝光升2/降3、gain升2/降2，9步达原10倍MAD/5%且方向一致，首变化/三帧平台SOF+2，pending/缺SOF/失败/跨SOF为0；依据pre-IPE BHIST，不用恒定startup metadata，无独立读回/物理锁存证明。468 mode2原有2/2与范围内响应一致；本测关闭AE/DelayedControls，不填sensor全局delay。477旧owner超时在写前拒绝、480新授权、原件不重放。

## 未闭环与操作

461重入UAF修复/六周期285消费286IPE、463 FULL角色/FD、464断供观察保留。449重复/450五gap/452缺168/459长测未复现后充电false不改根因关闭，用MONOTONIC。455 BU64253寿命/456 Image仅软件ABI，需0064+r2内建mux+462r3旧FD延后析构组合，未部署；原363缺mux exports。460默认AF原厂值保持。454/458第五OV02A1B时钟/PHY/初始帧/共享资源和RAW未完。

同Manager重开/共享lease、精确crop/LSC光学、AWB锁定/AF、编码录像/长期热功耗、多摄同步及第五仍待验，见[完整范围](reference/kernel363/REMAINING-CAMERA-SCOPE.md)。WSL源码/build/ext4先461 storage的mounted_build，原32GiB卷不格式化/改锁/卸卷，留2GiB。原厂/个体/样本/二进制私存，selected镜像脱敏、不动index/无关项、不push；429及终态事务不重放。
