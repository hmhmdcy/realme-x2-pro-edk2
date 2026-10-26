
---

## 23. 内核侧上 GitHub：完成 fetch 与分支，卡在 push（2026-10-07 16:3x）

### 23.0 TL;DR

**最重要的一条经验：WSL 里访问 GitHub 必须绕过 Windows 那个代理。**

```
$ git -c http.proxy= -c https.proxy= ls-remote up HEAD      # 直连
602042bf29f6efde39cfb5fdd9289bf4854bc0c5        HEAD        rc=0   ✓

$ git ls-remote up HEAD                                      # 走代理(127.0.0.1:7890)
fatal: unable to access 'https://github.com/torvalds/linux.git/':
       GnuTLS, handshake failed: The TLS connection was non-properly terminated.   ✗
```

关掉代理后，**1.2 GB 的 v7.3-rc6 只用了 39 秒**就拉完（之前走代理半小时都下不完，每次都在 20~30 秒被 reset 掉）：

```
$ git config --local http.proxy "" && git config --local https.proxy ""
$ git fetch --depth=1 up refs/tags/v7.3-rc6:refs/tags/v7.3-rc6
From https://github.com/torvalds/linux
 * [new tag]             v7.3-rc6   -> v7.3-rc6        (16:28:57 → 16:29:36)
```

**结论：以后 WSL 里所有 GitHub 操作（clone/fetch/push）都在仓库里设 `http.proxy ""`、`https.proxy ""`。**

### 23.1 已完成

`~/x2pro-linux/upstream`（fork 的工作区）：

```
a89e94cd5  arm64: dts: qcom: add realme samurai (X2 Pro) bring-up description
9c9adca57  tty: serial: add Qualcomm EUD COM early console
a90ee4305  Linux 7.3-rc6        (grafted, tag: v7.3-rc6)   ← 真正的上游提交
```

改动文件核对无误：

| 提交 | 文件 |
|---|---|
| `9c9adca57` | `drivers/tty/serial/Kconfig`、`Makefile`、`eud_earlycon.c`（新增 100 行） |
| `a89e94cd5` | `Documentation/devicetree/bindings/arm/qcom.yaml`、`vendor-prefixes.yaml`、`arch/arm64/boot/dts/qcom/Makefile`、`sm8150-samurai.dts`（293 行）、`eud_earlycon.c`（+27/-） |

**内核侧从此是标准的「upstream + 2 个提交」结构**，`git log` / `git blame` / `git format-patch` 全部正常。

### 23.2 还没做：`git push`

`git push -u origin samurai-bringup` 输出为空，`git ls-remote origin samurai-bringup` 也查不到
→ **分支还没上到 GitHub**。没有足够时间查，最可能的原因是：

- 这是 `--depth=1` 的浅克隆（`git log` 里标着 `(grafted)`）。GitHub 对浅仓库推上来的分支有两种反应：
  报 `shallow update not allowed`，或者把整棵树当增量传（1 GB 级，被 150 秒超时掐掉，所以什么都没打印）。

**下一条命令（给足时间，看它到底报什么）：**

```bash
cd /home/cy122/x2pro-linux/upstream
timeout 600 git push -u origin samurai-bringup
timeout 60  git ls-remote origin samurai-bringup
```

对照处理：

| 报什么 | 怎么办 |
|---|---|
| `shallow update not allowed` | `git fetch --unshallow up`（约 5 GB；直连很快）后重推 |
| 一直传、很慢 | 让它传完（fork 网络里已有对象，理论只该传几百 KB） |
| TLS / 连接错 | 确认 `git config --local http.proxy ""` 还在（§23.0） |
| `empty ident name` | `git config user.name cy122; git config user.email cy122@localhost`（本轮踩过，`git am` 前必须设） |

成功标志：`git ls-remote origin samurai-bringup` 返回 `a89e94cd5…refs/heads/samurai-bringup`。

### 23.3 本轮确认的几个事实（别重复推导）

1. **上游对齐**：`v7.3-rc6` tag 对象 `4eeccbed21e50c19f97be9d325511f3de6343f2d`，peeled commit
   `a90ee4305c4a5df72c11b31dacfdc76e00fcf78a`（作者/提交者 Linus Torvalds
   `<torvalds@linux-foundation.org>`，2026-10-04T20:45:25Z，message 只有一行 `Linux 7.3-rc6`），
   parent `7704c4c5bb127673b4f0ead839919db573559e38`。
2. **我们本地 baseline 的 tree 与上游不同**：本地 `b66cfc195852b68d92a99eb9db0b947b429e275f`，
   上游 `18cdff87967594810218424b52c69529757a6a78`（大概是解包 tarball 时丢了可执行位之类）。
   → 所以"用 GitHub API 拿元数据、本地合成那个上游 commit"这条捷径**走不通**；只能用 `git am` 打到真提交上。
3. **fork 不广播上游 tag**：对 `hmhmdcy/linux` 执行 `git fetch refs/tags/v7.3-rc6` 会报
   `couldn't find remote ref`，**必须从 `torvalds/linux` 拉**（对象同一个网络，不影响推回 fork）。
4. **`git fetch` 不能断点续传**：断了要从头来；所以之前"后台 + 多次重试"的方案注定失败，
   而"绕过代理直连"能在一次 39 秒内解决。

### 23.4 本轮新增脚本（`linux-port/scripts/`）

| 脚本 | 用途 |
|---|---|
| `probe-upstream.sh` | 对比"直连 vs 代理"连通性；从 GitHub API 取上游 commit 元数据；对比本地/上游 tree |
| `fetch-noproxy.sh` | 仓库级关闭代理 + `--depth=1` 拉 v7.3-rc6（本轮成功的那条） |
| `finish-upstream.sh` | 设 git 身份 + `git am` 两个补丁 + push + 远端确认 |

### 23.5 待办清单

1. `git push -u origin samurai-bringup`（§23.2）；
2. 成功后把 `samurai-bringup` 链接补进 §22/本节；
3. **Revoke 那个泄露的 classic PAT**，新建只勾 `public_repo` 的，直接写进 `~/.git-credentials`（别贴到对话里）；
4. 回到主线任务：§21 的内核 EUD 改动（逐字节流控 + chunk 4）→ 然后 §20.6 的面板/触控。