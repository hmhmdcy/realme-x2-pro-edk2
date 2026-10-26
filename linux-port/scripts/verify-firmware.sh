#!/bin/bash
# 等固件构建结束，然后逐项验证产物
set -u
RK=/home/cy122/edk2-samurai/repo
LOG=$HOME/edk2-samurai/build-kernel-embed.log

echo "=== 等待构建结束（最多 12 分钟）==="
for i in $(seq 1 72); do
	if ! pgrep -f 'build.sh -d samurai' >/dev/null 2>&1; then
		echo "构建进程已结束（第 ${i} 次检查）"
		break
	fi
	sleep 10
done
tail -4 "$LOG"

echo
echo "=== 错误检查 ==="
grep -iE 'error|failed|Failure' "$LOG" | grep -viE 'warning|errorlevel|0 error' | tail -8 || echo "无明显错误"

echo
echo "=== FD 大小应为 20MB ==="
ls -la "$RK/SM8150_UEFI-samurai.fd" 2>/dev/null || find "$RK" -maxdepth 2 -name '*.fd' | head
fd=$(ls "$RK"/*.fd 2>/dev/null | head -1)

echo
echo "=== 未压缩 FVMAIN 里是否真有新 DTB 与内核 ==="
FV="$RK/workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.Fv"
ls -la "$FV"
echo "-- realme,samurai 出现次数: $(grep -a -c 'realme,samurai' "$FV" 2>/dev/null || echo 0)"
echo "-- 旧的 xiaomi,cepheus 出现次数: $(grep -a -c 'xiaomi,cepheus' "$FV" 2>/dev/null || echo 0)"
echo "-- 内核版本串 rmx1931-samurai: $(grep -a -c 'rmx1931-samurai' "$FV" 2>/dev/null || echo 0)"
echo "-- earlycon eud 串: $(grep -a -c 'earlycon=eud' "$FV" 2>/dev/null || echo 0)"
echo "-- FFS 文件清单里有没有我们的内核:"
grep -iE 'SamuraiLinuxKernel|LinuxSimpleMassStorage|EudLogDxe' "$RK/workspace/Build/samurai/RELEASE_GCC5/FV/FVMAIN.inf" 2>/dev/null | head -5

echo
echo "=== 最终 boot.img ==="
ls -la "$RK"/boot-samurai*.img 2>/dev/null | head -5
for f in "$RK"/boot-samurai*.img; do
	[ -f "$f" ] && sha256sum "$f"
done

echo
echo "=== 变更清单 ==="
git -C "$RK" status --short
