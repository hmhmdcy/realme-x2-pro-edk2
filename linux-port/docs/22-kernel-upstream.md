
---

## 22. 内核侧进入 GitHub：从上游 fork（2026-10-07 16:2x）

### 22.0 TL;DR

内核源码的来源是**官方 tarball**（不是 git clone），本地只有"整棵树一次性导入"的 squashed baseline + 我们两个补丁，
**没有任何上游对象**，所以本地树不能直接推（会变成 335 MB 的全新历史）。

正解是**从上游 fork**：`torvalds/linux` → `hmhmdcy/linux`。因为 GitHub 的 fork 网络共享对象，
把两个补丁落到上游 tag 上之后，push 只需要传增量（几百 KB）。

上游对齐情况（已核实）：

```
$ git ls-remote --tags https://github.com/torvalds/linux.git 'v7.3-rc6*'
4eeccbed21e50c19f97be9d325511f3de6343f2d        refs/tags/v7.3-rc6
a90ee4305c4a5df72c11b31dacfdc76e00fcf78a        refs/tags/v7.3-rc6^{}   ← 与 baseline 记录一致 ✓
```

### 22.1 内核侧的现状

| 位置 | 内容 |
|---|---|
| `~/x2pro-linux/linux-7.3-rc6.tar.gz` | 源码 tarball（源头） |
| `~/x2pro-linux/linux` | 解包后 `git init`；3 个提交；**无 remote** |
| `b0630f810` | `baseline: Linux v7.3-rc6 pristine (upstream a90ee4305c4a)`（squashed 导入） |
| `e4858b30a` | `tty: serial: add Qualcomm EUD COM early console` |
| `0450fd895` | `arm64: dts: qcom: add realme samurai (X2 Pro) bring-up description` |
| `.git` | 346 MB（单 pack 335 MiB，101,683 objects） |
| `~/x2pro-linux/patches/` | 上面两个提交的 `format-patch` 产物 |
| EDK2 仓库 `linux-port/` | 2026-10-07 镜像（提交 `42a3923`，656 KB / 83 文件） |

### 22.2 新的上游工作区

```
~/x2pro-linux/upstream/          新建（不要动 ~/x2pro-linux/linux）
  origin → https://github.com/hmhmdcy/linux.git      （推送目标，fork）
  up     → https://github.com/torvalds/linux.git     （拉取源，上游）
  正在 git fetch --depth=1 up refs/tags/v7.3-rc6     （约 1.2 GB）
```

**目标结构**：`samurai-bringup` 分支 = 真正的 `v7.3-rc6` + 我们的两个提交，
这样 `git log` / `git blame` / `git format-patch` / 社区复现全都正常。

### 22.3 后续命令（fetch 跑完后执行）

```bash
cd ~/x2pro-linux/upstream
git rev-parse refs/tags/v7.3-rc6          # 应为 a90ee4305c4a5df72c11b31dacfdc76e00fcf78a

git checkout -b samurai-bringup refs/tags/v7.3-rc6
git am "/mnt/e/RealmeX2Pro edk2/linux-port/patches/0001-tty-serial-add-Qualcomm-EUD-COM-early-console.patch"
git am "/mnt/e/RealmeX2Pro edk2/linux-port/patches/0002-arm64-dts-qcom-add-realme-samurai-X2-Pro-bring-up-description.patch"
git log --oneline -3

git push -u origin samurai-bringup        # 增量几百 KB
timeout 60 git ls-remote origin samurai-bringup
```

`git am` 能干净应用的原因是：本地 baseline 的 tree 与上游 tag 的 tree **内容完全一致**（只差一个父提交）。

### 22.4 本轮新增脚本（`linux-port/scripts/`）

| 脚本 | 用途 | 是否幂等 |
|---|---|---|
| `mirror-linux-port.sh` | 把 `E:\RealmeX2Pro edk2\linux-port\{README,docs,dts,patches,scripts,refs,initramfs,eud_earlycon.c}` 镜像进 EDK2 仓库并提交推送 | 是 |
| `fork-linux.sh` | 查上游 tag / commit，用 GitHub API 建 fork，等 fork 就绪 | 是 |
| `fetch-upstream-bg.sh` | 配置 `origin`(fork) + `up`(上游) 两个远端，后台 `--depth=1` 拉 v7.3-rc6 | 是（会重拉） |

### 22.5 已知的坑

1. **fork 不广播上游 tag**：对 `hmhmdcy/linux` 执行 `git fetch refs/tags/v7.3-rc6` 会报
   `couldn't find remote ref`，**必须从 `torvalds/linux` 拉**（对象同一个网络，不影响后续推送到 fork）。
2. **`git fetch` 不支持断点续传**：中途断了要重头拉 1.2 GB，所以 WSL 必须一直开着直到拉完。
   被中断就直接重跑 `fetch-upstream-bg.sh`。
3. **GitHub 代理时通时断**：`http.proxy = http://127.0.0.1:7890`，会出现
   `Failed to connect to github.com port 443 via 127.0.0.1` / `Connection reset by peer`；
   所有网络脚本都要写成可重跑、带重试的形式（`push-fork.sh` 就是这么做的）。
4. **浅克隆 push 的风险**：从 `--depth=1` 的克隆 push 到自己的 fork 通常可以（浅边界提交在 fork 网络里已存在）；
   若报 `shallow update not allowed`，改成不带 `--depth`、只带 `--filter=blob:none` 重新拉。
5. **脚本自身的 bug（已修）**：早期版本只在 `.git` 不存在时才 `git remote add`，导致
   `.git` 已存在时 `git fetch up ...` 报"仓库不存在"。现在改成 `git remote get-url ... || git remote add ...`。

### 22.6 安全：那个 PAT 必须轮换

调试时 `~/.git-credentials` 里的 **classic PAT 被明文打印到了会话记录里**（135 字节的文件里其实有**两条** GitHub 凭据，
一条 `user:token@`、一条裸 `token@`）。它带 `repo` 权限的话等于账号下所有仓库的完整读写权。

**待办：GitHub → Settings → Developer settings → PAT → Revoke 旧 token，新建只勾 `public_repo` 的即可，
然后直接写进 `~/.git-credentials`（不要贴到任何对话里）。**