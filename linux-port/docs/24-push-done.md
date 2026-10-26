

---

## 24. `samurai-bringup` 已推上 GitHub（2026-10-07 16:46）

### 24.0 TL;DR

§23.5 第 1 条已完成，不用再试：

```
$ cd ~/x2pro-linux/upstream
$ timeout 1800 git push -u origin samurai-bringup
remote: Create a pull request for 'samurai-bringup' on GitHub by visiting:
remote:      https://github.com/hmhmdcy/linux/pull/new/samurai-bringup
To https://github.com/hmhmdcy/linux.git
 * [new branch]          samurai-bringup -> samurai-bringup
branch 'samurai-bringup' set up to track 'origin/samurai-bringup'.
PUSH_RC=0  end 16:46:06            # start 16:41:42，约 4 分 24 秒

$ git ls-remote origin samurai-bringup
a89e94cd558ca171b35a622087f8998839925eee        refs/heads/samurai-bringup   ✓
```

- 分支：https://github.com/hmhmdcy/linux/tree/samurai-bringup
- 开 PR：https://github.com/hmhmdcy/linux/pull/new/samurai-bringup

### 24.1 纠正 §23.2 的两条猜测（都是实测结果）

| §23.2 的猜测 | 实测 |
|---|---|
| 浅克隆会被拒：`shallow update not allowed` | **没有**。GitHub 接受 `--depth=1` 仓库推上来的新分支 |
| 增量只有几百 KB（fork 网络里已有对象） | **不是**。整份快照 pack 都传了（本地 285 MiB），约 4.5 分钟 |

原因：**fork 不广告上游 tag**（§22.5 第 1 条），协商时对端只报自己的 master/其他分支，
Git 看不出服务器已经有 `a90ee4305`，于是把 `--depth=1` 的那一份快照整包上传。

> 教训：**"从上游 fork 就能免费共享对象"只在被广告的引用能到达 base commit 时才成立。**
> 下次要传内核分支，先 `git ls-remote origin | grep -c refs/tags` 看一眼 tag 有没有被广告。

### 24.2 两个操作坑（这次踩到并解决）

1. **`nohup … &` 起的后台 push 活不过 WSL distro 回收。**
   第一次 16:39 起的后台 push，16:41 再去看时 distro 已被回收：进程没了、
   `/tmp/push.log` 整个消失，只在 `.git/objects/pack/` 留下 `tmp_pack_*` 垃圾。
   正确做法是**让一个前台 `wsl.exe` 附着到 push 结束**（PowerShell）：

   ```powershell
   Start-Process wsl.exe `
     -ArgumentList '--','bash','/mnt/e/edk2-samurai-out/push-branch.sh' `
     -RedirectStandardOutput 'E:\edk2-samurai-out\push.log' `
     -RedirectStandardError  'E:\edk2-samurai-out\push.err' -WindowStyle Hidden
   ```

   脚本本体已收进 `scripts/push-branch.sh`（关代理 → push → `ls-remote` 验证，可重复跑）。
2. 残留的 `tmp_pack_*` 不影响 push，但会让 `git count-objects` 报 `garbage found`；
   随手 `rm -f .git/objects/pack/tmp_pack_*` 即可。

### 24.3 待办清单（§23.5 更新后）

| # | 事项 | 状态 |
|---|---|---|
| 1 | `git push -u origin samurai-bringup` | ✅ 完成，`a89e94cd5`（2026-10-07 16:46） |
| 2 | 把分支链接补进交接文档 | ✅ 本节 §24.0 |
| 3 | **Revoke 泄露的 classic PAT**，新建只勾 `public_repo` 的、直接写进 `~/.git-credentials` | ⬜ 需要人在 GitHub 网页上操作 |
| 4 | §21 的内核 EUD 改动（逐字节流控 + `EUD_COM_CHUNK 4`）→ 重编内核 → 真机验证 | ⬜ 下一件主线任务 |
| 5 | §20.6：面板 SOFEF03F_M、触控 S3706、WCN3990、充电、传感器 | ⬜ 主线继续 |