# 461：新启动后六次停流重开及实际FULL事件

只替换452候选的core为461 `9b352a12…`，保持441三模块、IPA6、旧444 proxy／签名和443主摄原厂mode4调校。复用449现成客户端，在同一个CameraManager／camera／回调线程内依次720p→1080p→720p，分别运行native与隔离IPA；没有重编客户端或重复442的LTM黑白扰动。

首个r1在开流前因证据目录basename与跟踪实例名不一致被助手拒绝。没有图像或trace实例，worker退出、正式模块／服务／充电与PM恢复通过。修正工具后先在缓存新拓扑上验证constructor，再生成新预检和独立r2；r1失败原件保留，没有重放。

## r2原件审计

| 模式 | 720p第一周期 | 1080p | 720p第二周期 | 消费／物理IPE |
| --- | ---: | ---: | ---: | ---: |
| native | 42 | 52 | 48 | 142／142 |
| 隔离IPA | 47 | 49 | 47 | 143／144 |

[逐帧检查](inspect-lifecycle.py)及[收据](lifecycle-r2-validation.json)通过：285消费＝268次成功调校数学＋17 bootstrap；286次物理IPE中有1次停流时排入但未交给应用。原始回执没有过滤，0重复／负结果；每个周期的同SOF PD10、GTM来源、WB、成功历史及原NV12字节／亮度均核对。只重接被实际日志交错拆开的应用记录，保留全部回执标记。

六周期均正常stop、CPU租约恢复，CameraManager只启动一次／模式，camera及线程身份保持。native IPA在应用进程内；隔离IPA在三次configure中有三个worker。真实/proc的core／IPA／可执行文件／UID10000／零capability和FULL FD见证各覆盖两种模式的第一周期，其余周期按原始日志及回执审计，不能写成六次现场/proc见证。

## 新FULL角色与缺口证据

从本次媒体图PIX FULL source pad、sysfs库存解析到video3／minor3，实际应用FD一致；本次不把该编号当作后续启动常量。[463](../kernel463/README.md)门槛实际捕获303次qbuf、286次dqbuf。全部286次V4L2 dq与同线程、index和微秒截断时间戳的vb2 dq唯一关联，285张消费图都匹配真实FULL DQ。8CPU跟踪环overrun／commit overrun／drop均0；新实例删除，global／display／radio所选控制保持。

[缺口检查](inspect-full-gaps.py)及[收据](full-gap-validation.json)仍发现native 1080p早期SOF4、7缺失，邻FULL DQ间隔66.601／66.993ms；其它五周期未见消费SOF缺口。两帧有PD10／统计，无成功FULL DQ，邻帧间没有额外FULL vb2完成。两个区间的软件queued／owned快照最低均0。它提供缓冲供给线索，尚不能证明SOF当时物理FIFO状态、空队列持续时间、责任层或唯一根因；不能从两种模式的先后运行推断native／隔离的因果差异。

## 终态与适用边界

worker8634实际退出；327原件（含285张NV12）已取回PC私有，归档SHA `3cf822ea92ce74a419ac4c99cc5a36f7fab024af540e3232295fe46c50387634`。正式440库／包、434模块、服务恢复；PW8860／WP8882正常重启，phoc／phosh保持。camera PM全suspended、m2m／core释放，无用户目录／进程残留。

450行非空MONOTONIC相机日志均保留在后续完整dmesg，无指定fault或日志丢失指示，taint0。独立终态检查再次核worker退出、正式模块notes、trace删除、实际服务UID和两份fresh managed样本；R7保护、native100mA及限制保持。初次独立健康采集器误读不存在的camera_after键，未输出数据；只修采集器后重读一次，失败stderr保留，没有重跑相机。100mA状态不代表电池净充电。

手机随后交充电执行一次500→100诊断并已由对方终态交回，当前没有新相机SSH。461未永久安装。新库的6次普通开停流通过；并未在实机强制stop准确重入sendSync，那个确定UAF由原完整函数ASAN及10例修正版覆盖。442两尺寸LTM消费因果按相同调校／参数数学复用；旧偶发缺口、长期稳定性、画质和完整多摄目标均未宣称完成。
