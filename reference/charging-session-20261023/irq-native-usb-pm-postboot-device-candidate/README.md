# 当前 USB PM 正向与回退的新boot只读检查

2026-10-24。设备侧离线完成，未操作手机。复用原IRQ postboot collector，增加当前两套组合和当前依赖/保护缓存检查；不是实机postboot、待机恢复或完整充电适配已经完成的证明。

| 分支 | 内核/Image/FAT | manifest/USB驻留 | 共同保持 |
| --- | --- | --- | --- |
| forward_504 | 504/f647/4453 | 34ead/d046，要求新增stateless依赖 | bootedd、charger97c、保护7848、startup500及相机481/468 |
| restored_502 | 502/085d/ace2 | 18e8/7cb，要求该新增依赖不存在 | 同上 |

`profiles.json` 来自现成双文件配套、实际6818回退worker及固定Image504材料。`device.py` 自包含两套固定值，不在手机上读取主机配置文件。请求明确profile、目标版本、原stage/rollback结果、来源旧boot与独立启动事务；完整采集必须使用先前严格密钥probe观察到的精确新boot。旧502/5fca/10ec组合不能误作当前组合。

原25个函数逐字复用，包括原厂命名IRQ解析、文件/模块note、充电保护/Full、相机、服务、EUD和瞬时电流检查。原collector主体只改名为collect_base；外层在同一个只读mac_evidence fd持有期间取前后缓存，并增加原PM库存格式。当前cache getter/helper沿冻结版本复用，只接受未捕获0/0或已终态1/1，拒绝捕获中1/0、实例或内容变化；不触发MAC查询。

新audit共12门：身份前后、完整载体、安装与真实驻留、充电、相机、EUD、瞬时电流、服务/fault、原IRQ注册，再加保护缓存与原生系统PM依赖。依赖必须连接实际IRQ provider和legacy DWC控制器，两侧同一devlink，runtime_pm=0、sync_state_only=0、status="not tracked"，对应原DL_FLAG_STATELESS代码；回退侧必须没有这条新增连接。仍只覆盖DEVICE/on/active前提，明确不把拓扑快照当挂起/恢复、USB恢复或IRQ物理因果验收。

`identity-probe.py` 同样复用原只读身份函数，按目标502/504检查新boot、板号、rootfs与taint；身份不符不会进入载体或缓存采集。主机端还需审核实际启动记录、发送该probe、绑定12门完整采集、审核原传输/原始结果及adoption，尚未接齐；不可用原只认10门的host/adopt直接认领。

## 验证范围

六组定向检查与两个Linux默认入口通过，原本地child实际wait0。两个分支在明确模型中通过完整12门；模型基于已保存的旧实机postboot数据，只替换本轮组合字段并增加显式模拟的PM连接和缓存。旧原件字节保持，不把模型写为新实机证据。

覆盖25原函数/原collector主体及缓存方法复用、两组合与错配拒绝、依赖方向/标志/当前前提、Full/未知预算/来源结果/缓存变化、两目标版本身份、新鲜只读fd与inode替换拒绝、异常清理与错误身份零缓存访问。未知预算仍不提升通过；Full仍按原状态语义检查。未重跑旧矩阵。

collector继承Linux fcntl，Windows Python默认导入失败已留在history；目标Linux/现有WSL默认及测试均通过，没有为此修改生产判断。默认命令只输出source/read-only状态；无request时不采集。没有实际guard、lease、adoption、控制或分区写入。

下一步主机审核/压缩只读传输/新基线登记接线，齐备后再核手机当前状态并安排串行实机。图标专项已收敛，桌面不改；快充、温界、完整预充/再充与长期待机恢复仍独立待验。
