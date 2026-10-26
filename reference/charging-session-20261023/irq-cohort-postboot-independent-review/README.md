# IRQ collector R2 独立薄审

结论：**接受限定的只读设备组件范围**，绑定作者 R2 delivery `6efc3e39…ddd81a3`；独立结果为 `review-result.json`。不表示未来完整 host/stage/启动/adopt 流程已认证，也不表示物理 IRQ 递送或图标时延已通过。

R1 的新实际函数反例保留在 `shared-action-result.json`：已有47/48有效注册，再出现49的 `usbin-plugin, unrelated-action` 时被跳过；反方向会拒绝。只隔离提取实际 parser 跑这一新反例和方向对照，未导入作者模块、运行入口或旧27。`test-shared-action.py` 是当时R1源码pin的历史执行器，当前作者R2已变化，不应把它当R2重跑入口。

R2先用逗号/空白分隔整行精确目标token，再拒共享/非末尾/重复。静态核实只有parse_interrupts变化，helper在device中逐函数完全相同，原502的21个函数保持。作者10新边界/default的既有收据绑定当前生产源；原27只按R1历史收据复用，本审没有重跑。作者首次R2元数据引用错误原件已保留，正确反例SHA `603ddb01…c73fe5` 从本审真实原件重新计算；执行脚本与当前元数据脚本分列，diff只一行引用，断言体保持，未靠重跑掩盖历史。

同时核对18个文件/历史pins、精确新manifest整结构、新USB/保护disk及live notes、bootedd/logdumpace2/#502、实际supply OF唯一provider与五属性/两动态命名IRQ。每CPU差分在CPU集合变化、映射变化或回退时不可比；注册/增长始终不冒充物理或延迟通过。原只读分区/系统采集保持，无CSR、充电/服务/guard/pointer写。未来真实stage、源guard/endpoint、同child终态及其来源认证仍须host实现；stage SHA形状不等于认证。

R2复核只读/hash/AST，无作者入口/测试、编译、设备、SSH/USB、SDK/Git或新请求生成。作者原叶未修改。

归档修订3补充：`archive-review-result.json` 独立绑定新清单 `b2c1d2de…271689b`。原R2清单6efc逐字另存；R1 README原3893字节无改名为 `.md.inc`，原路径/存放路径由archive-layout显式映射。顶层只新增一段归档说明，其余源码、补丁、所有测试收据和R1delivery保持。软件仍revision2，原独审 `aca075ee…f8b9b7b` 未改；本补充不重跑同步、入口、测试或设备操作。
