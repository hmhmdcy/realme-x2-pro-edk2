# 483 独立准备审查

481/482 的离线准备审查通过，当前没有剩余已知静态阻断。此结论只覆盖冻结物料、生成代码、恢复设计及旧缓存协议回归；481 实际 APK 前进／回退／再前进、482 默认路径采集和外部健康查询均尚未执行。当前模板 `deployable=false`，不能将准备通过解释为已安装或实机通过。

最终审查对象为 481 `offline-template-r2`：40 个文件、29,018,019 字节，归档 SHA256 `b9524d904438527c0e632ed383ae7404ec7647520bc88fccbef9db95517aab80`。独立检查器逐项核对生成 worker／plan／queries、归档内容及属性、475 冻结物料和 440／434／正式 sensor 回退合同；当前准备源无漂移。详见 [公开回执](preparation-review-validation.json) 与 [检查器](review-preparation.py)。

静审确认的关键合同：

- 七包使用原生 APK 数据库事务及精确版本；数据库备份仅供取证，不以直接覆盖数据库冒充回退。前进 r33/r28，回退 r32/r27，四模块／四 profile 沿用冻结字节，正式回退 sensor 为 `966b29d8…4059f29`。
- 原文件、world、完整仓库成员、信任材料和属性先备份并持久化；每相位核对非七包数据库条目不变。失败保留失败状态，必要恢复不因诊断预算到期而跳过；同一存活 APK 进程等到终态，不盲杀或重放。
- 先停客户端并证明无相机 live FD／引用，再依次卸 CAMSS、m2m、ICP core、sensor，之后替换模块。部分卸载恢复允许已卸节点不存在；最终持久仓库显式 root:root、目录 0755、文件 0644。
- 482 每个前进相位计划四摄默认 640×480 各 32 帧、主／长焦 RAW 及主摄 dual 各 6 帧。清除实验 LD／LIBCAMERA 覆盖，要求实际 `/usr` 文件、maps、UID／CapEff、有效签名和 app=IPA PID；完整分类回执和 stop abort，不固定 bootstrap／数学样本数。

host preflight／transport／external health 仅做语法和静态审查，没有导入或执行。其设计核绑定哈希、一次 stage／launch、异常原件留存，以及最终实际 world／仓库／数据库属性、服务身份与 maps。外部健康尚无实际回执。480 旧实机原件的本地复审通过，只证明当时信任验证和依赖模拟；482 六份旧 440 缓存回归只证明历史协议检查，均不证明本轮安装或采集成功。

原 r1 归档及漂移回执保留，r1 的“可作为当前准备”结论不再适用。曾将工具 JSON 展示转义误读为健康查询源码错误的阻断意见已撤回；独立 AST 复核确认 CR/LF 常量、仓库 LF 和 pin 正则正确，此误判没有导致源码修改。

准备审查使用 `review-preparation.py PREPARATION --require-current-sources --output NEW_PRIVATE_RECEIPT`。就绪的未绑定模板必须启用该开关；已绑定、可部署准备始终强制源哈希无漂移，不能单独使用 `preparation_material_passed` 代替此门槛。设备尚未交还，后续实际操作仍需新的有效独占交接与绑定。本目录不复制私有 world、原厂系数或 maps；收到实际原件后另做缓存验收。
