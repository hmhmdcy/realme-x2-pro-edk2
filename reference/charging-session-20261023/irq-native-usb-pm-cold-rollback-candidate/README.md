# 当前 USB PM：两文件冷回退执行器

离线设备组件，默认入口只打印来源信息；本轮没有运行身份、request、lease、SSH、手机/USB/SDK、停充、刷写或重启。它接收显式 `--execute-rollback` 和stdin请求；尚无当前版本的连接式回退派发器，不能直接套旧R8工具。

载荷复用实际当前cohort的逆向包 `6ff66d18…35ab8`（25,858B），只允许原USB7cb和manifest18e8两个root:0600成员，实际解码核hash。替换顺序为USB→manifest；charger97c、保护7848、服务6145、启动500和其它文件保持。只恢复磁盘，绝不热卸/加载USB、不AUTO、不改载体，也不把旧文件读回当作旧模块已驻留。

三种显式组合由真实当前完整身份、两个载体和live note共同决定：

| 分支 | 内核／载体 | USB驻留 | 与原stage的boot关系 |
| --- | --- | --- | --- |
| `staged_same_boot_old_resident` | 502／bootedd／ace2 | 7cb | 同一boot |
| `booted_504_new_resident` | 504／bootedd／4453 | d046 | 原source boot已结束 |
| `booted_502_new_resident` | 502／bootedd／ace2 | d046 | 原source boot已结束 |

每种都保持charger97c/保护7848。新boot回退不以整套新postboot先通过为前提：主机仍须从留存source、实际写入/重启原件和原key当前只读采集构造请求；设备独立核当前UUID、精确version、板型/rootfs、完整分区、驻留note、live状态和保护。不能根据uname或包名猜组合，不能用过去的身份代替现在的身份。

原冷回退的12个读取/原子/安全函数及20个BaseDevice方法逐字复用。原manager614同步stop仅用于进入INHIBIT；若已经实际INHIBIT则不重复stop。USB源预算为0、ENODATA或未知时可在新鲜电气/保护信息和硬件帽确认下恢复**惰性磁盘文件**，不猜新额度或解除fault/timeout。继承CV、双路输入/CC帽及非破坏寄存器集保持，REG14不读。实际在线Full停充后仍须保留logical Full/cause/session0，holding可清零；丢失事实则在写文件前拒绝。

source复核内嵌冻结当前stage规则，核17份原始request/result/样本/两备份/source/监督终态和设备原launch-claim。请求里的 `source_stage_observations` 必须来自实际已审核的source同boot fetch。source boot结束后只回放那些**历史**观察来认证原终态，当前旧PID一律记录 `source_boot_ended`，不去给新boot的同号进程认领旧身份。同boot分支还会读取原进程现在的状态；live/unknown/PID复用仍拒绝。

`current_cache` 是当前original-key采集得到的opaque MAC缓存字节hash、base64和三个kernfs身份字段。设备持有只读fd并持续比较同一实例；允许新boot尚未捕获的schema1 `attempted=0 terminal=0`，或已经结束的 `1/1`，拒绝进行中的 `1/0`。原7848 getter源码已确认读操作只格式化缓存，初始0也不发总线命令。本工具不触发新MAC查询、不重武装实例，不解释0056/TCA位语义；普通独立保护状态仍需新鲜并通过。

请求的精确字段和类型由 `unpack()` 定义，新增当前cache和历史source观察两项；新boot分支的activation绑定必须来自真实原action请求/结果、原child wait0、写入先于reboot及正确载体，而不是手填digest。设备校验这些绑定与物理当前组合，不能代替主机对原命令的认证。`contract.json`记录新schema、三profile、载荷、范围及未生成运行身份；后续主机binder须同时使用留存来源审核和新鲜当前probe。

只使用原atomic writer进行同步临时文件/fsync/rename/目录fsync/readback。任一失败都保留原终态、临时文件及实际partial状态，不自动重放或猜回滚；租约在第一文件后失效也不会继续写第二文件。全部cache/journal/lock描述符独立尝试关闭，关闭失败不能把文件已还原提升为整笔事务成功。

七项受影响组合通过：三组合真实两文件包/原atomic函数、实际stage算法产生的17原件与跨boot进程语义、未知预算/旧fault/Full保留、错误profile/cache/Full丢失零写入、原子故障/到期partial、缓存实例/全部cleanup、原12函数/20方法/内嵌stage字节复用。设备、进程、I/O边界为明确模型，FakeFS只复用旧边界类；没有重跑旧矩阵。默认入口原child wait0。

**成功只表示 `staged_original/runtime_pending`。** 完整恢复仍须把logdump还原ace2，正常重启，再验证USB7cb/manifest18e8真正驻留及保护/预算/相机状态。尚需当前版本的saved-action审核、原key新鲜probe/binder、连接式监督派发及恢复后重启接线；新boot postboot/adoption也待补齐。实机窗口尚未安排。
