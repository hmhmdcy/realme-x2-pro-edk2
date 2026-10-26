# 450：旧统计在同步 IPA 回执前释放本地所有权

2026-10-23。[449](../kernel449/README.md)的9000帧缓存审计发现5次旧统计负回执重复，第二次-ENOENT。底层statsProcessed在同步IPA调用之后才删除本地histogram／order；等待隔离proxy时能够重入回调，再次处理同一token。[0061](0061-camss-retire-statistics-before-proxy-call.patch)先取得SOF／token并删除map／deque记录，再调用IPA；调用前后检查running／epoch，停流或换epoch立即返回。

只改管线该段，原厂参数、IPA6／签名／proxy、焦点算法／工作区／容量租约和441 build4模块继续复用。新核心3503c173…，增量构建122.52秒。[源码验证](source-validation.json)、[构建](build-validation.json)、[输入](runtime-inputs-validation.json)。正式组合仍440 r32／r27和434模块，候选未安装。

用真实448／450源码块执行同步嵌套回调，宿主ASAN／UBSAN先复现旧实现的重复回执及额外删除下一条记录，修复后8例通过，覆盖嵌套追加、幂等、回调内停止／更换epoch、预先停止／旧epoch、空token／已消费记录。[重入验证](retirement-validation.json)。既有finish的请求所有权守卫逐字保持，[边界检查](reentry-validation.json)通过。

## 实机取消与9000帧原始回执回归通过

r1被测试启动器遗留的k449目录前缀检查拦住，相机未出图／IPE完成0，fixture恢复完成，正式栈、资源、充电和残留检查通过；事务结束不重放。

修正目录检查后，r2的6秒取消取得94张图，源端成功95张（92 math＋3 bootstrap），其中1张完成但appsink未拉取；95次物理IPE完成。同SOF PD10／GTM／WB及严格历史通过，子进程正常exit9、GST_STATE_NULL及容量掩码恢复通过。[取消审计](cancellation-validation.json)。这份局部通过不覆盖观察器或整个r2。

随后只读温度观察器的退出检查失败，日志没有finished记录，长期用例未开始；整个[r2事务](runtime-r2-validation.json)仍为passed=false。旧探针逐批读取sysfs，停止期间不检查取消，并在3秒未退出后强制结束；本轮未记录观察器具体退出码，不把信号原因冒认为实测。新观察器在字段间检查取消，等待改为8秒，并将观察器退出断言放到临时目录清理之后。宿主实际函数的正常／读途中取消／预先取消通过，慢读取消0.2秒后结束且不读取下一字段。[观察器验证](observer-validation.json)。生产core未再改，也不重复已通过的相机取消用例。

唯一遗留的r2用户目录已在事务结束、无相关进程且captures为空后精确清除。[目录清理](directory-cleanup-validation.json)、[r2无残留](residual-r2-validation.json)通过；随后手机交给充电会话做USB拔插／换口，期间未访问SSH。

充电明确交回窗口后，先采用其新可信manifest78332c70…f5abe及实际SDP100mA／MaxPower100、charge cap250mA／CV8725000；同a30 boot／k449 guard。[preflight](preflight-validation.json)通过后只开新r3长期事务，未重放旧事务；复用449已通过的同一Manager六周期和450 r2相机取消证据。

r3实际uid10000／CapEff0的隔离消费者完成9000图／9000物理IPE，8997 math＋3 bootstrap，正常exit0、GST_STATE_NULL和容量恢复；七份运行见证核实应用实际450 core映射及独立IPA身份。[严格审计](hardware-validation.json)逐帧原始回执、同SOF PD10／GTM／WB和成功历史全部通过，重复负回执为0。原厂443 mode4及444 IPA／签名／proxy均未改；[事务](runtime-r3-validation.json)通过，观察器exit0／未超时，301个完整样本。

PTS跨度299.576秒、平均30.039fps，仍有5个单SOF缺口，最大间隔66.544ms；不接受无丢帧或编码录像。不能把相对449的33→5直接归因于本修复：两次USB供电基线和观察器开销不同，场景／热条件也非配对控制。[缓存时延](latency-validation.json)显示5个缺SOF都有PD10和观察、均无IPE_PAIR，FULL所有权根因仍待[452诊断](../kernel452/README.md)。内核环形日志仅保留8731次完成，9000总数由最终驱动计数及消费者逐帧链共同确认。

[正式恢复](current-state-validation.json)、[r3无残留](residual-r3-validation.json)通过：440／434、epoch0、资源全释放、ICP／CAMSS／两CCI suspended、P/W各1 uid10000、taint0／新故障0；充电三模块／服务／实际源预算和限流快照逐字段不变。worker／应用／proxy／观察器均退出，临时目录全清，日志已收回后明确交还手机给充电；451比较未插入本窗口。

本改动只处理统计淘汰重入，不宣称修复33个SOF缺口或441历史积压。LTM独立消费因果证明沿用[442](../kernel442/README.md)的真实／黑／白／真实PD10对照；443原厂mode4数据未改。编码录像、无丢帧30fps、功耗／热和完整多摄／光学目标继续开放。完整日志、照片和二进制只在私有kernel450和手机事务目录。

## 已授权的并行续作

[IPC分析](IPA-LATENCY-NEXT.md)已给出[451](../kernel451/README.md)同线格式proxy优化，只构建worker，实际AArch64新编码／旧解码契约通过，实机收益待验。[其它模组模式](OEM-MODES-NEXT.md)确认长焦现有mode3和原厂配置可用于720p／1080p双遍消费者；全输入缩放不等于正常16:9画幅录像。[镜头资料](LENS-SCOPE-NEXT.md)确认广角／长焦BU64253及第五OV02A1B现存原件；[453](../kernel453/README.md)真实in-tree模块与原C解析通过，仍核DT／PM框架边界及两模组原厂AF v9参数。[热接入](LIVE-LENS-ATTACHMENT.md)没有现成configfs loader，新增lens关系还需受控桥接及sensor／CAMSS重新注册。支线均不访问手机，主线统一协调硬件窗口。
