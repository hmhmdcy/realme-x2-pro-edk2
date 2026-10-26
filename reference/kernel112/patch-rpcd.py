#!/usr/bin/env python3
"""Apply the reviewed RAM-only sensor filesystem trial to upstream v0.4.0."""
from pathlib import Path
import shutil

src = Path('/home/cy122/hexagonrpc-v04-k112')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel112')
pending = {}
def edit(name, old, new):
    p = src / 'hexagonrpcd' / name
    s = pending.get(p, p.read_text())
    assert s.count(old) == 1, (name, old)
    pending[p] = s.replace(old, new)

shutil.copyfile(ref / 'hexagonfs_ram_registry.c', src / 'hexagonrpcd/hexagonfs_ram_registry.c')
edit('hexagonfs.h', '#endif', '''int hexagonfs_enable_ram_registry(const char *path);
int hexagonfs_ram_open(struct hexagonfs_fd **fds, const char *path, const char *mode);
ssize_t hexagonfs_ram_write(struct hexagonfs_fd **fds, int fd, size_t size, const void *ptr);
int hexagonfs_ram_flush(struct hexagonfs_fd **fds, int fd);

#endif''')
edit('hexagonfs.c', '\tif (ret)\n\t\tgoto err;\n\n\treturn ret;',
     '\tif (ret < 0)\n\t\tgoto err;\n\n\treturn ret;')
edit('apps_std.c', '\tchar rw_mode;', '\tconst char *rw_mode;')
edit('apps_std.c', '''\trw_mode = ((const char *) inbufs[4].p)[0];
\tif (rw_mode == 'w' || rw_mode == 'a') {
\t\tfprintf(stderr, "Tried to open %s for writing\\n",
\t\t\t\t(const char *) inbufs[3].p);
\t\treturn AEE_EUNSUPPORTED;
\t}''', '''\trw_mode = inbufs[4].p;
\tif (!inbufs[1].s || !inbufs[3].s || !inbufs[4].s)
\t\treturn AEE_EBADPARM;
\tif (*rw_mode == 'w' || *rw_mode == 'a' || strchr(rw_mode, '+')) {
\t\tfd = hexagonfs_ram_open(ctx->fds, inbufs[3].p, rw_mode);
\t\tif (fd < 0) {
\t\t\tfprintf(stderr, "RAM registry open failed %s: %s\\n",
\t\t\t\t(const char *)inbufs[3].p, strerror(-fd));
\t\t\treturn AEE_EFAILED;
\t\t}
\t\t*out = fd;
\t\tprintf("ram-open(%s, %s) -> %d\\n", (const char *)inbufs[3].p, rw_mode, fd);
\t\treturn 0;
\t}''')
edit('apps_std.c', 'if (((const char *) inbufs[1].p)[inbufs[1].s - 1] != 0\n\t ||',
     'if (!inbufs[1].s || !inbufs[3].s || !inbufs[4].s\n\t || ((const char *) inbufs[1].p)[inbufs[1].s - 1] != 0\n\t ||')
edit('apps_std.c', '\tmemset(outbufs[0].p, 0, outbufs[0].s);\n\n\treturn 0;',
     '''\tstruct apps_std_ctx *ctx = data;
\tconst uint32_t *fdnum = inbufs[0].p;
\tif (inbufs[0].s < sizeof(*fdnum) || hexagonfs_ram_flush(ctx->fds, *fdnum))
\t\treturn AEE_EFAILED;
\treturn 0;''')
edit('apps_std.c', 'ignore fflush(%u)', 'fflush(%u)')
edit('apps_std.c', 'static uint32_t apps_std_fseek(', '''static uint32_t apps_std_fwrite(void *data,
                               const struct fastrpc_io_buffer *inbufs,
                               struct fastrpc_io_buffer *outbufs)
{
\tstruct apps_std_ctx *ctx = data;
\tconst struct { uint32_t fd, buf_size; } *in = inbufs[0].p;
\tstruct { uint32_t written, is_eof; } *out = outbufs[0].p;
\tssize_t n;
\tif (inbufs[0].s < sizeof(*in) || outbufs[0].s < sizeof(*out) ||
\t    in->buf_size > inbufs[1].s)
\t\treturn AEE_EBADPARM;
\tn = hexagonfs_ram_write(ctx->fds, in->fd, in->buf_size, inbufs[1].p);
\tif (n < 0) {
\t\tfprintf(stderr, "RAM registry write failed: %s\\n", strerror(-n));
\t\treturn AEE_EFAILED;
\t}
\tout->written = n; out->is_eof = n < in->buf_size;
\tprintf("ram-write(%u, %u) -> %zd\\n", in->fd, in->buf_size, n);
\treturn 0;
}

static uint32_t apps_std_fseek(''')
edit('apps_std.c', '''\t\t.impl = apps_std_fread,
\t},
\t{ .def = NULL, .impl = NULL, },''', '''\t\t.impl = apps_std_fread,
\t},
\t{ .def = &apps_std_fwrite_def, .impl = apps_std_fwrite, },''')
edit('interfaces/apps_std.def', 'HEXAGONRPC_DEFINE_REMOTE_METHOD(9,',
     'HEXAGONRPC_DEFINE_REMOTE_METHOD(5, apps_std_fwrite, 1, 1, 2, 0)\nHEXAGONRPC_DEFINE_REMOTE_METHOD(9,')
edit('rpcd_builder.c', '#include <string.h>', '#include <string.h>\n#include <stdio.h>')
edit('rpcd_builder.c', '#define SYSFS_SOCINFO', '#define OPPO_VERSION "/oppoVersion/"\n#define SYSFS_SOCINFO')
edit('rpcd_builder.c', '\tstruct hexagonfs_dirent *persist_dir, *vendor_dir;',
     '\tstruct hexagonfs_dirent *persist_dir, *vendor_dir;\n\tchar *oppo;')
edit('rpcd_builder.c', '\tn_prefix = strlen(prefix);', '''\tn_prefix = strlen(prefix);
\toppo = malloc(n_prefix + strlen(OPPO_VERSION) + 1);
\tif (!oppo) return NULL;
\tstrcpy(oppo, prefix); strcat(oppo, OPPO_VERSION);''')
edit('rpcd_builder.c', '''\t\t\t\t\thfs_mkdir("registry", 1,
\t\t\t\t\t\thfs_map("registry", sns_reg)
\t\t\t\t\t)''', '\t\t\t\t\thfs_map("registry", sns_reg)')
edit('rpcd_builder.c', '\treturn hfs_mkdir("/", 6,', '''\tif (hexagonfs_enable_ram_registry(sns_reg)) {
\t\tfprintf(stderr, "Refusing registry root: requires private tmpfs directory\\n");
\t\treturn NULL;
\t}
\treturn hfs_mkdir("/", 7,
\t\t\thfs_mkdir("proc", 1, hfs_map("oppoVersion", oppo)),''')
edit('rpcd.c', '\troot_dir = construct_root_dir(device_dir, dsp);',
     '\troot_dir = construct_root_dir(device_dir, dsp);\n\tif (!root_dir)\n\t\tgoto err;')
for p, contents in pending.items():
    p.write_text(contents)
print('RPCD_RAM_TRIAL_PATCH_APPLIED')
