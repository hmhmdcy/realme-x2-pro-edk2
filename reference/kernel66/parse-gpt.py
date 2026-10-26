from pathlib import Path
import struct, uuid, zlib, json, hashlib

result = []
for lun in (0, 4):
    path = Path(f'/mnt/e/edk2-samurai-out/backup/gpt_lun{lun}_live.bin')
    blob = path.read_bytes()
    sector = 4096
    assert blob[sector:sector+8] == b'EFI PART'
    revision, length, crc = struct.unpack_from('<III', blob, sector+8)
    header = bytearray(blob[sector:sector+length])
    struct.pack_into('<I', header, 16, 0)
    assert zlib.crc32(header) == crc
    current, backup, first, last = struct.unpack_from('<QQQQ', blob, sector+24)
    entry_lba, count, entry_size, entry_crc = struct.unpack_from('<QIII', blob, sector+72)
    entries = blob[entry_lba*sector:entry_lba*sector+count*entry_size]
    assert len(entries) == count*entry_size and zlib.crc32(entries) == entry_crc
    partitions = []
    for index in range(count):
        entry = entries[index*entry_size:(index+1)*entry_size]
        if entry[:16] == bytes(16):
            continue
        begin, end, flags = struct.unpack_from('<QQQ', entry, 32)
        partitions.append(dict(index=index+1, name=entry[56:128].decode('utf-16-le').rstrip('\0'),
            first_lba=begin, last_lba=end, bytes=(end-begin+1)*sector,
            type_guid=str(uuid.UUID(bytes_le=entry[:16])), guid=str(uuid.UUID(bytes_le=entry[16:32]))))
    ordered = sorted(partitions, key=lambda p: p['first_lba'])
    gaps, cursor = [], first
    for part in ordered:
        assert part['first_lba'] >= cursor and part['last_lba'] <= last
        if part['first_lba'] > cursor:
            gaps.append(dict(first_lba=cursor, last_lba=part['first_lba']-1, bytes=(part['first_lba']-cursor)*sector))
        cursor = part['last_lba']+1
    if cursor <= last:
        gaps.append(dict(first_lba=cursor, last_lba=last, bytes=(last-cursor+1)*sector))
    result.append(dict(lun=lun, source=str(path), snapshot_only=True, sector=sector,
        sha256=hashlib.sha256(blob).hexdigest(), header_crc_pass=True, entry_crc_pass=True,
        current_lba=current, backup_lba=backup, first_usable_lba=first, last_usable_lba=last,
        partitions=partitions, gaps=gaps))
out = Path('/mnt/e/edk2-samurai-out/kernel66/gpt-backup-audit.json')
out.write_text(json.dumps(result, indent=2)+'\n')
for disk in result:
    print('LUN', disk['lun'], 'CRC OK; backup snapshot, not current device')
    for part in disk['partitions']:
        print(part['index'], part['name'], part['bytes']//1048576, 'MiB')
    print('gaps:', disk['gaps'])
