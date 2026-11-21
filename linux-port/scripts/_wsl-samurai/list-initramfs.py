#!/usr/bin/env python3
"""List a newc cpio archive's members without needing the cpio binary."""
import sys


def parse(path):
    data = open(path, "rb").read()
    off = 0
    count = 0
    while off + 110 <= len(data):
        magic = data[off:off + 6]
        if magic not in (b"070701", b"070702"):
            # A concatenated archive (or padding) can break the walk; resync
            # on the next header instead of giving up.
            nxt = data.find(b"070701", off + 1)
            if nxt < 0:
                print(f"  end: no further header after {off}")
                break
            off = nxt
            continue
        hdr = data[off:off + 110]
        try:
            # newc stores each field as 4 bytes written as 8 hex characters
            fields = [int(hdr[6 + k * 8:6 + (k + 1) * 8], 16) for k in range(13)]
        except ValueError:
            print(f"  stop: bad field at {off}")
            break
        # newc header field order: ino, mode, uid, gid, nlink, mtime,
        # filesize, devmajor, devminor, rdevmajor, rdevminor, namesize, check
        namesize, filesize = fields[11], fields[6]
        if not 2 <= namesize <= 4096 or filesize > len(data):
            print(f"  stop: namesize={namesize} filesize={filesize} at {off}")
            break
        raw = data[off + 110:off + 110 + namesize]
        try:
            name = raw[:-1].decode()
        except UnicodeDecodeError:
            print(f"  stop: undecodable name at {off}: {raw[:20]!r}")
            break
        print(f"  {name:<46s} {filesize:>10d}")
        count += 1
        off += (110 + namesize + filesize + 3) // 4 * 4
    print(f"  members={count} bytes={len(data)}")


parse(sys.argv[1])
