# 温区 Full / SOC 退出：独立 charger ko

冻结来源为 `thermal-full-soc-exit-candidate`，delivery `780e6591e09062da575910f1a771fd5a1605df416f79f8f9740298b844239e25`。本叶只构建单模块，复用97c的实际Image502 intree方法和原284 Ubuntu/root storage guard。实际复制三个新源（C、mp2650-core.h、oem-full-cycle.h）、97c原reattach header和R8未变依赖，共10个输入；没有混入其它DWC/Image实验。

新模块 SHA256 `824e1f382d391d51befa6f47454f321e4e69bb728048a35ee3e03d7099cc30c6`，159,792 bytes；note SHA256 `53e4fdb0a188963adf960733f463aea26425aee92267c201fab7317664518dcc`。完整私有导出路径与身份在 `module-identity.json`。AArch64/intree，k363原vermagic，actual Image502 config/autoconf一致；54个强导入全由Image502 builtin提供，W=1/Werror零诊断。这不证明运行时类型ABI、实机热区退出行为或可直接部署。

唯一原exec session79319实际exit0；原make PID792（modules_prepare，17.048s）及2603（charger.ko，3.350s）都由原Popen wait到终态0。`ko-result.json`含原命令/日志摘要、10输入与tracked before/after；shared/502/原97c模块、原forward包及18e8清单均保持。私有原始日志在 `/home/cy122/charging-management-20261023/thermal-full-soc-exit-module-01/`。无新anchor、卸卷或存活构建；284窗口已归还。

`method-delta.patch`给出与冻结97c builder的准确变化：源覆盖、额外原97c输入保护、唯一目录/导出名；Kbuild/等待、ELF-note、配置及导入验证方法复用。`build-ko.py --check-local`只查冻结小源码，不访问storage；`--execute`原唯一输出已存在，禁止重放。源级11组91断言收据直接复用，旧矩阵未重跑。

没有更改当前97c、18e8manifest、手机或保护查询实例，没有制作payload/cohort/host。旧97c `97c16c…8ffdd`及其note `fe15a2…2016`仍在原私有目录；这里只保存独立新产物，未执行回退或安装。后续采用必须另审真实当前身份、同boot更新及Full连续性，不能将本次编译当成已完成实机适配。
