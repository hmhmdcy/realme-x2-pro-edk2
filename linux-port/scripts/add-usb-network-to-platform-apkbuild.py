#!/usr/bin/env python3
"""Add the usb-network glue files to samurai-platform's APKBUILD.

Idempotent.  Run with the APKBUILD path as argv[1].
"""

from pathlib import Path
import hashlib
import re
import sys

WATCHDOG = "usr_sbin_samurai-usb-network-watchdog"
INITD = "etc_init.d_samurai-usb-network"

POST_INSTALL_MARKER = "# post-install: rootfs NCM link glue"
POST_INSTALL_BLOCK = """
# post-install: rootfs NCM link glue
# usb-signaller owns the configfs gadget, but nothing
# brings usb0 UP.  u_ether only fills its RX queue and raises carrier after
# eth_open(), so a carrier-gated NetworkManager profile can never start the
# link.  Keep the board glue as the single owner of link state while the
# gadget-generation is alive, and retire the old one-shot boot service.
rm -f /etc/runlevels/boot/samurai-ncm-fallback \\
	/etc/runlevels/default/samurai-ncm-fallback \\
	/etc/init.d/samurai-ncm-fallback \\
	/usr/sbin/samurai-ncm-watchdog
if [ -x /etc/init.d/samurai-usb-network ] && command -v rc-update >/dev/null 2>&1; then
	rc-update add samurai-usb-network default >/dev/null 2>&1 || true
	rc-service samurai-usb-network restart >/dev/null 2>&1 || true
fi
"""


def main() -> int:
    path = Path(sys.argv[1])
    text = path.read_text()
    changed = False

    if WATCHDOG not in text:
        text = text.replace(
            "usr_sbin_samurai-usb-recover usr_sbin_samurai-otg-capture",
            f"usr_sbin_samurai-usb-recover {WATCHDOG} usr_sbin_samurai-otg-capture",
            1,
        )
        changed = True
    if INITD not in text:
        text = text.replace(
            "etc_init.d_samurai-usb etc_init.d_samurai-usb-recover",
            f"etc_init.d_samurai-usb etc_init.d_samurai-usb-recover {INITD}",
            1,
        )
        changed = True
    # Install lines: ensure exactly one each.  The earlier version of this
    # script inserted them unconditionally, so a second run produced four
    # duplicate copies of the same install command.
    watchdog_line = (
        ' install -Dm755 "$srcdir"/' + WATCHDOG +
        ' "$pkgdir"/usr/sbin/samurai-usb-network-watchdog\n'
    )
    initd_line = (
        ' install -Dm755 "$srcdir"/' + INITD +
        ' "$pkgdir"/etc/init.d/samurai-usb-network\n'
    )
    watchdog_re = re.compile(
        r"(?m)^\s*install -Dm755 \"\$srcdir\"/" + re.escape(WATCHDOG) +
        r" \"\$pkgdir\"/usr/sbin/samurai-usb-network-watchdog\n"
    )
    if watchdog_re.search(text):
        # Collapse duplicates, keep the first occurrence.
        first = watchdog_re.search(text).group(0)
        text = watchdog_re.sub("", text)
        anchor = ('install -Dm755 "$srcdir"/usr_sbin_samurai-usb-recover '
                  '"$pkgdir"/usr/sbin/samurai-usb-recover\n')
        text = text.replace(anchor, anchor + first, 1)
        changed = True
    else:
        anchor = ('install -Dm755 "$srcdir"/usr_sbin_samurai-usb-recover '
                  '"$pkgdir"/usr/sbin/samurai-usb-recover\n')
        if anchor in text:
            text = text.replace(anchor, anchor + watchdog_line, 1)
            changed = True

    initd_re = re.compile(
        r"(?m)^\s*install -Dm755 \"\$srcdir\"/" + re.escape(INITD) +
        r" \"\$pkgdir\"/etc/init.d/samurai-usb-network\n"
    )
    if initd_re.search(text):
        first = initd_re.search(text).group(0)
        text = initd_re.sub("", text)
        anchor = ('install -Dm755 "$srcdir"/etc_init.d_samurai-usb-recover '
                  '"$pkgdir"/etc/init.d/samurai-usb-recover\n')
        text = text.replace(anchor, anchor + first, 1)
        changed = True
    else:
        anchor = ('install -Dm755 "$srcdir"/etc_init.d_samurai-usb-recover '
                  '"$pkgdir"/etc/init.d/samurai-usb-recover\n')
        if anchor in text:
            text = text.replace(anchor, anchor + initd_line, 1)
            changed = True
    # Alpine APKBUILD checksums are sha512 in hex.
    srcdir = path.parent
    # Insert checksum lines just before the closing quote of sha512sums.
    lines = []
    for name in (WATCHDOG, INITD):
        digest = hashlib.sha512((srcdir / name).read_bytes()).hexdigest()
        line = f"{digest}  {name}"
        existing = re.compile(r"(?m)^[0-9a-f]{128}  " + re.escape(name) + r"$")
        if existing.search(text):
            text = existing.sub(line, text)
        else:
            lines.append(line)
    if lines:
        # APKBUILD expects sha512sums="<first line>..." with no blank line
        # after the opening quote; a leading empty line counts as an empty
        # checksum entry and abuild reports "1 of N did NOT match".
        marker = text.rstrip()
        assert marker.endswith('"'), "sha512sums block does not end with a quote"
        head = marker[:-1]  # drop closing quote
        if head.endswith('sha512sums="'):
            raise SystemExit("refusing to write an empty sha512sums block")
        if head.endswith('\n'):
            text = head + "\n".join(lines) + '\n"\n'
        else:
            text = head + "\n" + "\n".join(lines) + '\n"\n'
        changed = True

    # abuild consumes two words of $sha512sums per $source entry, so the
    # block must follow source= exactly.  Appending checksums at the end
    # silently shifts every later entry and abuild then reports a bogus
    # "FAILED" on the final file.  Reorder here so the caller never has to
    # remember.
    sums_match = re.search(r'(?ms)^sha512sums="(.+?)"\n', text)
    src_match = re.search(r'(?m)^source="(.+?)"\n', text, re.S)
    if sums_match and src_match:
        sums: dict[str, str] = {}
        for line in sums_match.group(1).splitlines():
            parts = line.split()
            if len(parts) == 2 and re.fullmatch(r"[0-9a-f]{128}", parts[0]):
                sums[parts[1]] = parts[0]
        sources = src_match.group(1).split()
        if all(name in sums for name in sources):
            ordered = [f"{sums[name]}  {name}" for name in sources]
            block = 'sha512sums="' + "\n".join(ordered) + '"\n'
            text = text[:sums_match.start()] + block + text[sums_match.end():]
            changed = True

    post_install = path.parent / "samurai-platform.post-install"
    post_text = post_install.read_text()
    if POST_INSTALL_MARKER not in post_text:
        assert post_text.rstrip().endswith("exit 0"), "unexpected post-install tail"
        head = post_text.rstrip()[: -len("exit 0")].rstrip("\n")
        post_text = head + "\n" + POST_INSTALL_BLOCK + "\nexit 0\n"
        post_install.write_text(post_text)
        changed = True

    path.write_text(text)
    print("APKBUILD updated" if changed else "already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
