# 当前USB PM启动核验与新基线登记

2026-10-24。接通已有504正向与502完整回退的真实启动记录、压缩只读probe、12门完整采集和新boot登记。复用原同child/EOF/wait传输及原始输出认证；不增加桌面提示。

`host.py probe --context <实际context> --output <该事务内新目录>`核对原stage/restore、启动动作与实际终态，再发现新boot；`collect`增加`--camera`及`--probe-directory`，重新审核原始结果，不只信任设备passed字段。profile从实际context选取，拒绝旧组合、错载体或错驻留模块。恢复侧使用已有冷回退及重启记录，独立于正向postboot是否通过。

`adopt.py --execute-adopt`需上述完整通过，设备重新只读验证12门后才创建独立guard；原guard和原pointer留存，新pointer按原字节比较后原子替换。没有充电控制、分区、模块或MAC查询写入。504登记不伪称Image502已验证，待机/恢复保持未验。默认入口只检查本地来源。

定向检查覆盖双profile完整audit与错配拒绝、真实缓存R2原child/wait与输入篡改拒绝、恢复模块作用域和旧context拒绝、两套新guard创建及失败先于创建。模型明确使用保存的旧实机原件构造，不作为新版实机证据。实际部署进展见充电主目录和检查点。

实际启动发现并解决两处接线缺口：重复历史审核使inspect超过30秒，原检查在restart意图前拒绝，未重派有状态动作；`activation-window.py`只审核一次历史source，后续逐个核对实际读取过的文件SHA，原bound/设备检查/once/同child调度均保持。原operator仍有相同Windows绝对路径拼接问题，首次在创建动作前拒绝；本叶`fastboot-operator.py`只将原context中的stage模块换成已验证的current路径适配模块，原检查/写入/重启/进程所有权保留。其实际operator源码hash进入动作请求，postboot与`rollback-profile.py`明确审核该hash；后者只替换保存动作的源路径，冷回退算法、原key及原owner保持。两个新增定向检查覆盖未变文件复用/篡改拒绝和恢复接线。

`pm-smoke-host.py`默认只检查本地来源；显式执行从实际采用原件绑定当前504/guard，以独立supervisor持有一次worker，SSH断开不重派。采用原27例已验证且字节未变的PM primitive：sync/count先于arm、原count握手、单次mem、只清自己的alarm。worker在PM前后重做12门，另核GNSS空闲及s2idle，保存实际驻留/stats/dmesg；目标15秒、接受10–20秒。USB原key/NCM恢复由主机另行观察，不靠device标签替代。没有charger属性、模块、服务或分区写入；正常内核PM回调自行停充/重采样。未加全局追踪，结果只作当前功能短测，不证明RTC唯一原因、旧r5因果或整机长期PM。两组新增检查覆盖错误boot/模式在PM前拒绝，以及真实本地child成功/失败的同Popen终态与重复监督拒绝；不是手机待机证据。实际结果见主目录。
