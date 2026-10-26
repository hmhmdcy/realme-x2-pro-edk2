---
<!-- from HANDOVER-NEXT.md, section 17 (extracted 2026-10-08; full original:
     archive/HANDOVER-NEXT-full-2026-10-08.md) -->

## 17. 子模块已按方案 A 解决（2026-10-07 03:45）

ArmMmuLib 修复**不再需要手工打补丁**：

- 已用 `gh` 建好 fork `hmhmdcy/edk2`（fork of tianocore/edk2）
- 子模块本地提交 `60dbefd0`「ArmMmuLib: do not print from the live block split path」
- 已推到分支 **`samurai-armmmulib`**（远端校验：`refs/heads/samurai-armmmulib` = 60dbefd0）
- `.gitmodules` 的 `Common/edk2` 已改为 `url = https://github.com/hmhmdcy/edk2.git` +
  `branch = samurai-armmmulib`（与 `Platform/EFI_Binaries` 指向 `hmhmdcy/edk2-msm-binary` 同一套做法）
- 父仓库提交 `c10cf90` 固定新指针，**已推到 fork/master**

于是 `git clone --recursive https://github.com/hmhmdcy/edk2-realme-x2-pro` 直接得到带修复的树，
零手工步骤。补丁 `Platform/Realme/sm8150/patches/armmmulib-no-debug-in-mmu-off-path.patch` 保留，
供"使用上游 submodule URL"的人兜底。

**后续维护**：若把 edk2 子模块 rebase 到更新的上游版本，需把这一行删除重放到新版本，再推同名分支
（`git -C Common/edk2 push fork HEAD:refs/heads/samurai-armmmulib`），最后在父仓库更新指针。

**网络注意**：本机 GitHub 访问走代理、**时好时坏**（`GnuTLS handshake failed` /
`connection reset` / `via 127.0.0.1`）；push 经常要重试 2–3 次才能成功，
且 `git ls-remote` 成功并不代表 push 一定成功。`gh` 在 WSL 与 Windows 均已登录（hmhmdcy）。

### 已推送的提交（fork/master = c10cf90）

```
c10cf90 Common/edk2: pin the submodule to the fork carrying the ArmMmuLib fix
f756f44 docs: note how to apply the ArmMmuLib patch
18e965b docs: EUD log ring verification, ArmMmuLib root cause, boot option noise
a3b70b8 samurai: ship the ArmMmuLib full-DEBUG fix as a patch
2d26a5a SetCPUFreqDxe: print UINT32 frequencies unsigned and keep going
1da715f samurai: do not auto-enumerate every device as a boot option
04da4b4 samurai: EUD COM log ring + cyclic replay drainer
```

---
