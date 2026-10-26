# 486：测量启动器的个人 HOME 环境修复

484 的 UID10000 程序继承了 root 环境；449 的 `execv` 只换身份，未换 HOME。新增 [user-launcher.py](user-launcher.py)，不改449、481–484冻结文件、生产库或配置权限错误的处理。

CLI保持 `user-launcher.py /run/user/10000/k449-user-… PROGRAM [ARGS…]`。按真实 `pwd.getpwuid(10000)` 设置 HOME/USER/LOGNAME，降权后为 CONFIG/DATA/CACHE/STATE_HOME 保留可访问的绝对个人路径或已存在、UID10000拥有的目录；继承root路径、相对/空值回到真实HOME下的XDG默认。runtime只接受目标UID的可用0700目录，否则使用现有 `/run/user/10000`；不创建或改个人目录，不清整份环境，不新增LIBCAMERA覆盖。继续核私有stage、普通目标用户可执行文件、无符号链接/set-ID、UID/CapEff后 `execve`，参数不经过shell。

[local-validation.json](local-validation.json) 记录三例有限本地检查：root继承、合法个人XDG、已有用户外部配置目录与非法相对项。实际Linux setgroups/setgid/setuid10000、CapEff0、chdir及exec成功，个人HOME测试文件可读，参数/无关环境保持；五个路径/exec拒绝通过。NSS账号及initgroups适配为本地测试替身，未改主机账号数据库。首轮测试harness占位替换造成执行前SyntaxError，原stderr留私有486；修正后通过，launcher未因此改动。

未访问手机、SSH、USB、PM或SDK。目标真实pwd账号、libcamera个人配置→系统配置的实际消费、`/root/.config`错误是否消失均待新窗口验证；本地sentinel检查不冒充libcamera加载，也不处理独立的build-tree fallback INFO。
