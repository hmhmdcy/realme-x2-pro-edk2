#!/bin/bash
# 修 earlycon 的页映射 bug：CSR_EUD_EN(+0x1014) 不在框架映射的那一页里。
# 修完重编 Image，并重新生成补丁。
set -eu
LK=/home/cy122/x2pro-linux/linux
cd "$LK"

python3 - <<'PY'
p = "drivers/tty/serial/eud_earlycon.c"
src = open(p).read()
old = """static int __init eud_setup(struct earlycon_device *device, const char *opt)
{
	void __iomem *base = device->port.membase;

	if (!base)
		return -ENODEV;

	/*
	 * Enable the EUD block if an earlier boot stage did not.  The EDK2 port
	 * of this device enables it in BDS, but the Android boot chain does not
	 * touch it at all.  The interrupt mask is deliberately left alone:
	 * arming interrupt sources before the interrupt controller and a driver
	 * exist would only risk a spurious interrupt later.
	 */
	writel_relaxed(1, base + EUD_REG_CSR_EUD_EN);

	device->con->write = eud_write;
	return 0;
}
"""
new = """static int __init eud_setup(struct earlycon_device *device, const char *opt)
{
	void __iomem *csr;

	if (!device->port.membase)
		return -ENODEV;

	/*
	 * Enable the EUD block if an earlier boot stage did not.  The EDK2 port
	 * of this device enables it in BDS, the Android boot chain does not
	 * touch it at all.
	 *
	 * CSR_EUD_EN sits one 4 KiB page above the COM FIFO, outside the window
	 * the earlycon framework maps for us - it maps 64 bytes, which is the
	 * page the FIFO lives in - so it needs a mapping of its own.  Writing
	 * through the framebuffer pointer would take a data abort here and kill
	 * the boot before any output.
	 */
	csr = ioremap(device->port.mapbase + EUD_REG_CSR_EUD_EN, sizeof(u32));
	if (csr) {
		writel_relaxed(1, csr);
		/* deliberately leaked: this console lives for the whole boot */
	}

	/*
	 * The interrupt mask is deliberately left alone: arming interrupt
	 * sources before the interrupt controller and a driver exist would only
	 * risk a spurious interrupt later.
	 */
	device->con->write = eud_write;
	return 0;
}
"""
assert old in src, "没找到要替换的 eud_setup"
open(p, "w").write(src.replace(old, new, 1))
print("eud_earlycon.c 已修")
PY

grep -n -A8 'csr = ioremap' drivers/tty/serial/eud_earlycon.c

echo
echo "=== 合入原提交并重编 Image ==="
git add drivers/tty/serial/eud_earlycon.c
git -c user.name=cy122 -c user.email=cy122@localhost commit -q --amend --no-edit
git log --oneline -3
make -s ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig >/dev/null 2>&1 || true
nohup make -j12 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image \
  > $HOME/x2pro-linux/build-image2.log 2>&1 &
echo "重新构建中：$HOME/x2pro-linux/build-image2.log"
