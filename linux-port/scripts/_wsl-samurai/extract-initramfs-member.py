#!/usr/bin/env python3
"""Extract one newc-cpio member (used because WSL has no cpio binary)."""
import sys


def main(archive, member, out):
    data = open(archive, "rb").read()
    off = 0
    while off + 110 <= len(data):
        if data[off:off + 6] not in (b"070701", b"070702"):
            nxt = data.find(b"070701", off + 1)
            if nxt < 0:
                break
            off = nxt
            continue
        hdr = data[off:off + 110]
        fields = [int(hdr[6 + k * 8:6 + (k + 1) * 8], 16) for k in range(13)]
        namesize, filesize = fields[11], fields[6]
        name = data[off + 110:off + 110 + namesize - 1].decode()
        body_at = off + 110 + namesize
        if name == member:
            open(out, "wb").write(data[body_at:body_at + filesize])
            print(f"extracted {name} -> {out} ({filesize} bytes)")
            return 0
        off += (110 + namesize + filesize + 3) // 4 * 4
    print(f"member not found: {member}")
    return 1


sys.exit(main(*sys.argv[1:4]))
