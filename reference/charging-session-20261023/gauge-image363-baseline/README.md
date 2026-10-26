# Image363 私有基线复现

只执行根已批准的基线门：固定 ba61 源、原 CONFIG、原工具链和构建身份；不引入 B，不构建模块或 DTB，不封装启动载体，不接触设备。

唯一执行 `run-baseline.py --execute-baseline` 已通过：宿主 exec session12309、WSL worker PID484，最终退出0。子 namespace worker1521，Image目标39.51秒。只读终态汇总 session36426 退出0。私有目录 `/home/cy122/charging-management-20261023/gauge-image363-baseline-01` 保留，执行器拒绝已存在目录重放。

原284 storage guard 在显式 Ubuntu/root 下通过。原 O、固定提交导出的源、396项 initramfs 和临时目录均在私有 home 中独立建立；O和initramfs复制后校验字节/属性及无共享硬链接。子 mount namespace 先递归 private 并实核传播字段及父 mountinfo，再仅映射四个 canonical 路径。原树/父挂载在执行后再次核对。

原 bq `5976585a…f7cb7c`、vmlinux `8e2bc2bd…f4dd96`、Image `15746aab…9d6468`、CONFIG `23e088a9…8f30ed` 全字节复现。3247个 built-in leaf及32个 libstub 成员内容/顺序不变，实际全部 `.o` 差异清单为空，396项私有initramfs保持。原共享O/源/initramfs全内容与属性、Git HEAD/index、父mountinfo均前后相同。

本叶只认证原363基线。实际命令、日志、namespace证明、原/后全树清单和空变化清单在私有目录；公开 `result.json` 绑定对应原件SHA。没有引入 B、重跑旧函数测试、构建模块/DTB、封装或部署。根已在基线真实通过后另行授权B501阶段，该阶段须使用另一个私有副本，不修改本叶和本基线原件。

首次运行在私有目录创建前的只读索引快照停下：source354 的 `.git` 是 worktree 指针文件。已保留 `prelaunch-failure-01.json`，改为只读 `git rev-parse --git-path index` 后才启动当前唯一有状态执行。该次预检没有复制、namespace 或构建。
