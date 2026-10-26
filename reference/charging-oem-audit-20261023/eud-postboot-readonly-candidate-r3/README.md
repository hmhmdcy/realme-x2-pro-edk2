# Postboot R3：marker 前缀歧义拒绝

R3在完整保留R1和Full-only R2的基础上，**只改变实际 `decode_ring()`**。R2的精确Full/normal helper与check_charging函数字节不变，沿用其11项实际函数/common.healthy差分收据；R1其余9组只引用冻结收据，没有重跑。

独审确认的软件反例为：一条完整Success报告旁再有一条截断/畸形 `[SAMURAI-EUD-OFF]`，旧decoder先按fullmatch筛选，只看见完整行，因而错误给ready。R3先计retained history中所有含 `[SAMURAI-EUD-OFF` 前缀的记录，**仅恰一条前缀记录、且它完整符合白名单并满足原字段规则才ready**。完整Success旁出现截断、畸形、缺右括号或带日志前缀的第二条记录，全部not-ready。

公开receipts仍只含原严格白名单完整行，畸形内容不被发布。新增marker_prefix_count留在私有原始check结果；原receiver字节保持，只发布既有白名单及ready状态。marker缺失、失败、重复等原规则和“callback_success_independently_proven=false/不证明物理路由或SDP500”边界全部保留。

`r2-to-r3.patch` 为完整device差异，仅新增前缀记录计数、ready门和私有计数字段。`revision-source-result.json` 独立比较全部函数：仅decode_ring有变化，Full两函数精确hash绑定，R1/R2逐文件hash未变。payload/contract及新boot身份、分区、R8/481、只读reserved RAM范围、default check-local/显式root窗口和newendpoint契约均不变；详见R1 README/contract。

`test-marker-result.json` 仅执行实际decoder的6个受影响病例：单一完整报告通过；加截断/畸形/缺右括号/带日志前缀的第二条marker全部拒绝；无关私有文本不影响完整报告。实际R2函数接受两项歧义反例也被直接复现。没有执行采集、旧十组、R2 Full测试或设备；Full测试通过仅由实际函数保持逐字不变而复用。

本叶只交离线候选，未运行设备/SSH/USB/SDK/Git、创建guard、CSR访问、控制或恢复动作。普通失败仍保留私有原件。冻结hash交root及session独立差异复核，不能据此宣称实际新boot/EUD-off/图标已验收。
