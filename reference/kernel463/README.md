# 463：按媒体角色选择 FULL 跟踪节点

修正459工具只验证“节点存在、minor与编号一致”而未验证角色的缺口。新[选择器](full-role.py)从指定PIX实体的FULL source pad及双向enabled/immutable链接找到video节点，再和实际sysfs库存核名称与dev major:minor；不默认video0，也不把video3当作跨启动常量。

[GuardedPlan](guarded-trace.py)复用冻结459生命周期实现，只增加图指纹／PIX角色验证并绑定到plan key。它在操作tracefs之前拒绝原r2的RDI0选择，既不默默替换旧selection，也不重写历史收据。新选择必须写入 `pixel_entity`、`full_role_graph_sha256` 并与同次probe绑定；实例名和token应使用新唯一值，不能复用宿主样例文件。

[验证](role-validation.json)实际读取314、417缓存媒体图以及457库存，均解析到当时的video3/minor3；原459 RDI0选择被拒绝。18个反例覆盖错平台／图／链接／角色／库存／进程／启动窗口与零发射；额外编号变更用例将device path改为video27、dev改为81:97，结果随实际库存变化。FD与事件用例为宿主模型，**没有新的手机／SDK／内核trace或实机角色验收**。

## 新窗口如何取证

`render-role-query.py`只在PC生成只读查询源码，故意没有SSH或执行入口。未提供同次handoff、baseline、实际应用身份时，生成脚本在读取设备之前拒绝。有效查询要求handoff十分钟内、完整boot与既有guard匹配、原应用pid/start_ticks/exe SHA/四Uid10000/CapEff0不变；仅运行 `media-ctl -p`、读video库存和该应用的字符FD，前后核进程与boot相同。默认不会创建guard、切换服务、开流、改变模块、USB或充电。

下一串行窗口由已有控制器用原SSH身份执行它，结果只存PC私有。用 `from_observation()`核同boot/window、库存和进程FD，再生成角色绑定；同一窗口的trace能力probe仍须实读，不能用缓存图冒认fresh。查询结果不是owner授权凭据，外层事务仍负责资源与正式恢复。

开流前可按当前图配置过滤，应用启动后必须补实际打开FD见证。验收还须调用 `check_emission()` 确认所选minor真实出现v4l2 qbuf和dqbuf；available/enable为真或零条记录都不通过。原r2只有vb2／IRQ记录，不能拿来补造这个新门槛。

本轮只证明软件角色门槛能拒绝已知错误；未重跑无改动的LTM扰动或相机窗口，未宣称旧FULL缺口修复。已保留的546条vb2完成→出队→回调关联继续见[459原审计](../kernel459/RUNTIME-TRACE.md)。

后续[461 r2](../kernel461/HARDWARE-SUMMARY.md)已实际使用本门槛：新boot、441模块重新加载后实读媒体图／sysfs，解析FULL到video3/minor3；native／隔离应用各有一次真实FD见证。捕获303 qbuf和286 dqbuf，全部286条DQ与vb2 DQ唯一配对、285消费帧匹配，跟踪无覆盖且实例已删。该结果补齐真实事件门槛，原宿主收据的历史false字段保持原意。native 1080p仍有两处FULL缺口，角色正确不代表缺帧根因已修复。
