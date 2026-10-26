---
<!-- from HANDOVER-NEXT.md, section 14 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 14. EUD log ring: 真机验证通过（2026-10-07 02:45）

镜像 `E:\edk2-samurai-out\boot-samurai-eudlog2.img`
sha256 `cf2364723022b2491bf763d5359547fc6226518829c119539b2d5153ec0e71a8`，已刷机验证：

- 重启后约 **3.5 秒** EUD CTL 9501 出现（BDS 里开 EUD）
- `eudtool com-up` → `Qualcomm EUD Port 9505 (COM14)` 立即就绪
- `comlog.exe COM14 30` → **12523 字节 / 1571 帧 / 12 遍完整回放**
- 日志里含**主机 attach 之前**产生的早期 DXE 行
  （`SimpleFbDxe: Retrieve MIPI FrameBuffer parameters from PCD`）——以前必丢的内容，现在拿到了
- 无 overflow（ERROR 级别下 80KB 环远远够）

**中途发现的设计缺陷（第一版 eudlog 镜像）**：排空驱动原本门控在 `CTL_OUT_1` 的读回，
并设 15 秒兜底。实测该读回不可靠，且兜底在"人手动敲 com-up"之前就触发了，
于是缓冲被推进真空、主机抓到 0 字节（当时屏幕上的
`[EUD-LOG] no host attach seen, replaying anyway` 就是这条路径）。

**修正**：去掉门控与兜底，改成**循环回放** —— 每遍把消费指针回卷到环内最旧字节、
整卷重发，遍间停 2 秒；EUD 就绪后维持 120 秒，之后转为只转发新数据（避免长时间占用回调）。
主机在任何时刻 attach 都能拿到完整一份，且不再需要猜测主机状态。

**后续可做**：

1. 每遍加一个分隔标记行，便于阅读（现在是 12 份副本叠在一起）。
2. 若把 `PcdDebugPrintErrorLevel` 开到全量 DEBUG，环会填满，按当前 ~1.2KB/s 每遍约 68 秒 ——
   循环仍保证完整，但回调占用会偏高，建议先做流控优化（TX 状态轮询 / 加大帧长）再开。
3. **首次抓取已经暴露出一个以前看不见的真固件错误**：
   `ERROR: C40000002:V03051003/V03051002 I0 6D33944A-EC75-4855-A54D-809C75241F6C 9FFCF718`
   （BdsDxe 的 GUID，每遍出现 9-11 次）—— 值得下一步查。
---
