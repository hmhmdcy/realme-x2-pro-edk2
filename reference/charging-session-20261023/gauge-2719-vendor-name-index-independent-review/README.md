# Vendor name-index review

Accepted within its name-only scope. The retained first pass failed on three
zero-inode, zero-metadata unused slots in /lost+found. The narrow correction
counts/skips only those unused slots; allocated entries and unexpected unused
metadata still fail validation. The failed source, result and stdout remain.

The saved successful index contains2884 unique entries:128 directories,2511
regular files and245 symlinks. Root plus those128 directories match exactly
129 saved debugfs queries, all terminal0. Only /lost+found has skipped slots,
three total. The reviewed command is ls -p without -w, and symlinks are not
recursed. Source input hash is checked before enumeration; the post-check is
file metadata, not a second whole-image hash.

No .bqz/.bqfs/.df.fs/.srec filename appears in this vendor index. This does not
cover embedded/compressed contents, other names, symlink targets, partitions or
OTAs, and does not identify the2719 pack or query protocol. The reviewer read
only source and saved small JSON/stdout, reran no tools, and did not read the
large image or the root's subsequent five candidate-content files.
