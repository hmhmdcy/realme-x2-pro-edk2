# 原 a30 compact-only 基线通过

仅执行一次原 GenFv，host Linux PID1051，宿主 exec 及工具均 exit0；stdout/stderr为空。新私有目录 `E:/edk2-samurai-out/charging-management-20261023/eud-boot-compact-baseline-private-01/` 已存在，执行器拒重放。未重跑前六层，旧失败目录原样保留；未运行 gzip，没有新候选 boot/固件封装、设备/SSH/USB/PM/SDK/Git/NAV 或部署/重启。

原工具从私有 pre-rebase SEC和对应 `.efi` sidecar重定位，并从原 main压缩container生成完整7MiB compact FD。结果与直接从实际 a30 boot 提取的基线整文件相同，未忽略任何字节：

- FD7340032 bytes，SHA `a71478b42db56f46aeda543031b95743f851d175e5771a3f133991beecdfbb02`。
- SEC完整FFS55384 bytes，SHA `825690b698d922f86b2925a6fb405a3456ffeab97e6fcd47a6192e67be0a37c0`，位置仍0xfe8。
- FV vector由原工具生成 `ce270014000000000000000000000000`；header checksum `a0f4`。没有手填或事后修补。
- 141个父输入（原133项加本次SEC/sidecar/PDB map/来源等）及完整父mountinfo前后保持，原源码、工具、FFS/FV/boot缓存输出未变。

`run-compact.py` SHA `09b99fa6e85fb6caefd7ff4d9e504239874e726f892c8659e7ab588cdae04902`。公开 `result.json` 为简明收据，完整父快照及日志只留私有；私有 `result.json` SHA `c81ae504e6bf89253dea83a0f5a6831dd7084ade73ab23d45d22f976c9c1467b`。

## 已证明的路径

上次 `-F FALSE` 在 `GenFvInternalLib.c:3651` 提前返回，跳过 ARM识别，导致3071的 reset-vector生成不执行。本次恢复原默认 `ForceRebase=-1`，保留原INF的 base0xCE000000、block0x1000/blocks0x700，以及FS3 GUID，执行：

```text
GenFv -g 5473c07a-3dcb-4dca-bd6f-1e9689e7349a -i <private>/FVMAIN_COMPACT.inf -o <private>/compact.fd
```

原缓存 `8AF09F13-44C5-96EC-1437-DD899CB5EE5DSec/` 中的三个文件复制到私有同名路径，未改字节：pre-rebase `.ffs` SHA `da8f6b97…5266c`、完整 `.efi` SHA `684fc7c8…1388a`、`.map` SHA `0cd35c90…6a321`。原TE的 base0、reloc目录0/0；完整PE sidecar的 base0、reloc RVA55360/size64。源码3994读取TE machine，4002置mArm；4028–4086以FFS同basename的私有 `.efi` **rb** 读补reloc，4120重定位，4161更新TE ImageBase。3071/2290–2298据真实SEC入口生成AArch64 B，3081–3082重算FV header checksum。

TE原PDB绝对路径保持。`WriteMapFile:953` 只以 **r** 读原只读输入 `AARCH64/Silicon/Qualcomm/QcomPkg/PrePi/PrePi/DEBUG/Sec.map`，输出map指向私有目录；该输入同样纳入前后SHA。没有改PDB字符串或原map。container直接复制上次已逐字复现的 `container.ffs`，未再次压缩或重做其它模块。

## 下一步边界

至此原 mainFV、section/LZMA/guided/container 和原 compact FD的精确复现均有实际结果。若根另行批准，可在新唯一目录只将原144-byte shim与本次已核FD组成raw，要求7340176 bytes与a30 raw完全一致；再以已固定的原 gzip argv、regular fd0和原MTIME作一次整gzip/payload字节基线。尚未执行这一步；不宣称gzip、候选boot、启动或USB500已通过。
