#!/usr/bin/env python3
"""Dump the V4L2 media graph of a media device.

Why this exists: `ls /sys/class/video4linux/v4l-subdev*` and an ioctl with the
wrong `struct media_entity_desc` layout both report "0 entities" on a healthy
qcom-camss graph. That false negative sent an earlier session chasing a
non-existent CAMSS registration bug.

Authoritative layout (include/uapi/linux/media.h):

    __u32 id;            // offset 0  (in/out)
    char  name[32];      // offset 4
    __u32 type;          // offset 36
    __u32 revision/flags/group_id
    __u16 pads;          // offset 52
    __u16 links;         // offset 54
    __u32 reserved[4];
    union { dev{major,minor}; ... raw[184] };   // offset 60

MEDIA_IOC_ENUM_ENTITIES = _IOWR('|', 1, 256 bytes), and the next lookup
sets `id |= MEDIA_ENT_ID_FLAG_NEXT` (1<<31).

Usage: media-graph.py [device]     (default /dev/media0)
Exit 1 if the graph has no entities.
"""
import fcntl
import os
import struct
import sys

SIZE = 256
NEXT = 1 << 31
ENUM = (3 << 30) | (ord("|") << 8) | 1 | (SIZE << 16)


def entities(device):
    fd = os.open(device, os.O_RDWR)
    out = []
    wanted = NEXT
    try:
        while len(out) < 256:
            buf = bytearray(SIZE)
            struct.pack_into("<I", buf, 0, wanted)
            try:
                fcntl.ioctl(fd, ENUM, buf)
            except OSError:
                break
            eid = struct.unpack_from("<I", buf, 0)[0]
            name = struct.unpack_from("32s", buf, 4)[0].rstrip(b"\0").decode(errors="replace")
            etype = struct.unpack_from("<I", buf, 36)[0]
            pads, links = struct.unpack_from("<HH", buf, 52)
            major, minor = struct.unpack_from("<II", buf, 60)
            out.append(dict(name=name, type=etype, pads=pads, pads_links=links,
                            major=major, minor=minor, id=eid))
            wanted = (eid & 0xFFFF) | NEXT
    finally:
        os.close(fd)
    return out


def main():
    device = sys.argv[1] if len(sys.argv) > 1 else "/dev/media0"
    found = entities(device)
    print(f"{device}: {len(found)} entities")
    for e in found:
        print("  %-30s type=0x%04x pads=%d links=%d dev=%d:%d"
              % (e["name"], e["type"], e["pads"], e["pads_links"],
                 e["major"], e["minor"]))
    if not found:
        print("\nAn empty graph is NOT the same as a broken driver: check that\n"
              "the media device is the one you mean, and that the ioctl layout\n"
              "above (256 bytes, id at 0) is the one the kernel exposes.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())