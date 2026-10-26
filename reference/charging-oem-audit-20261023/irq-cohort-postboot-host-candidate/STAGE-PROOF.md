# 独立 stage 证据审核 API

`stage-proof.py` 是纯本地 read/hash/验证组件，不依赖 IRQ activation operator、后续 postboot host 或任何传输入口。默认仅核已有冻结源，不调用 `review_stage`、读未来身份或创建目录。root 的后续 context validator 可懒加载此文件，避免循环依赖。

稳定接口：

```python
review = review_stage(stage_directory, fetch_directory, expected_transaction=stage_transaction)
expected_guard_stage = guard_stage_fields(review)
```

两个目录必须是实际 stage-host R2 私有事务目录及其原 `fetch-<16hex>-private` 子目录。缺任一原件、矛盾、失败或未知过程链即抛错，没有 mkdir/request/guard/pointer 写入。没有接受手填 `passed=true` 的入口。

审核复用冻结502 adoption 的完整 `review` 和 stage-host 的实际比较函数，重核原 context/完整 postboot/采用执行源码和请求、真实终态及 endpoint。历史 pointer 使用 adoption 保留的实际 `adoption-pointer-private.json`，其原始字节必须等于 stage binding 中的 hash；不会为了历史审核要求当前 global pointer 仍未变化。

另核 stage 原 request/固定三文件载荷、实际 worker/supervisor 源、唯一 launch intent、执行的 launch/fetch 原始源码及 envelope、原 key/固定 endpoint argv 和本机同 SSH child 终态。原 launch 的 SSH 非零不会单独否定已由后续真实 fetch 取回的原子进程终态，但原 transport 必须已 wait 终态；fetch 必须真实 rc0。取回的每份 raw 必须与响应内 base64/长度/hash、私有文件字节完全一致。

supervisor 原 launch/self/terminal 与 worker 的实际 Popen/self/terminal 按 PID/start_ticks/argv、父进程、源boot/request及真实整数退出码逐项交叉。不能以 PID absent 或 JSON stage 标签替代 terminal0。原进程仍 alive/unknown、缺终态、另一 PID/argv、bool 伪退出码均拒绝。新 boot 后允许原件标 source_boot_ended，不能归属当前同 PID。

stage 成功还须满足实际 before/stopped/after 的原保护/预算/限额、精确 Full 前态、环境保持和最终 REG08 INHIBIT；复用原 worker 的实际 pure helpers。原三个备份与固定旧文件 SHA 相符，新文件事实和临时文件路径/状态精确，旧 resident notes 保留。采证 proof 摘要须与源 postboot/guard/result 一致。历史样本通过不等于现在新鲜或新 boot 已验收。

`review` 稳定输出包括 `source_boot_id`、`source_version`、完整原 `identity`，以及 `adoption` 原字段加 `actual_fresh_validation_sha256`。后者是由实际已认证 worker 在设备读到、并由其 proof/result 一致报告的摘要；host 没有声称已取回 fresh-validation 原始字节。

`guard_stage_fields` 只规范化真实 review 的七个字段：transaction_id/request_sha256/result_sha256/host_binding_sha256/worker_sha256/supervisor_sha256/evidence。evidence 恰14项，名称已与 session 的设备 guard 合同对齐。request、worker source、supervisor source由原上传 request/执行源码所绑定；它们不是本轮 fetch 未返回过的“新读回”。其余项来自实际取回 raw。设备路径从已核 actual argv 的固定事务 root 映射；后续 guard 仍必须在设备实际读这些文件并对 hash，不能把本地源的 hash 当设备已新读成功。

`test-stage-proof.py` 仅执行本次新审核函数的13个保存材料边界，旧完整502审核与传输身份为明确 fake 边界；正常载荷/备份复用真实已缓存字节。它没有运行旧27/10/20/26矩阵、原设备collect或任何网络/设备/构建。所有临时身份只在测试临时目录，不生成真实stage/activation/postboot request。

本锚不等于 IRQ carrier 激活、postboot 或物理接受。完整 host 的后续层须等待根独立 boot-only operator 实际冻结及真实材料，重核只写 boot 的原 fastboot child/读回，再封装设备 schema。
