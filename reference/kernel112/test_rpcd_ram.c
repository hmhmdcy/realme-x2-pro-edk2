// SPDX-License-Identifier: GPL-3.0-or-later
/* Exercise real RPC method handlers and the mapped filesystem on host tmpfs. */
#define _GNU_SOURCE
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "apps_std.c"
#include "rpcd_builder.h"

static char trial[256];
static void directory(const char *suffix)
{
	char path[512]; snprintf(path, sizeof(path), "%s/%s", trial, suffix);
	assert(!mkdir(path, 0700));
}
static void fixture(const char *suffix, const char *value)
{
	char path[512]; snprintf(path, sizeof(path), "%s/%s", trial, suffix);
	int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
	assert(fd >= 0 && write(fd, value, strlen(value)) == (ssize_t)strlen(value));
	close(fd);
}
static void readable(struct apps_std_ctx *ctx, const char *path, const char *value)
{
	int fd = hexagonfs_openat(ctx->fds, ctx->rootfd, ctx->rootfd, path);
	char buf[64] = {0}; struct stat st;
	assert(fd >= 0);
	assert(!hexagonfs_fstat(ctx->fds, fd, &st) && S_ISREG(st.st_mode));
	assert(hexagonfs_read(ctx->fds, fd, sizeof(buf) - 1, buf) == (ssize_t)strlen(value));
	assert(!strcmp(buf, value));
	assert(!hexagonfs_close(ctx->fds, fd));
}
int main(void)
{
	strcpy(trial, "/dev/shm/samurai-rpc-test-XXXXXX"); assert(mkdtemp(trial));
	directory("sensors"); directory("sensors/registry"); directory("sensors/registry/registry");
	directory("sensors/config"); directory("dsp"); directory("dsp/sdsp");
	directory("socinfo"); directory("oppoVersion"); directory("acdb");
	fixture("sensors/registry/file1", "FILE1"); fixture("sensors/registry/file2", "FILE2");
	fixture("sensors/registry/sns_reg_version", "OLD");
	fixture("sensors/registry/registry/sample", "SENSOR");
	fixture("sensors/sns_reg.conf", "CONFIG");
	fixture("socinfo/platform_subtype", "Unknown"); fixture("oppoVersion/modemType", "4");
	assert(hexagonfs_enable_ram_registry("/tmp") < 0);
	char regdir[512]; snprintf(regdir, sizeof(regdir), "%s/sensors/registry", trial);
	assert(!chmod(regdir, 0777));
	assert(hexagonfs_enable_ram_registry(regdir) == -EPERM);
	assert(!chmod(regdir, 0700));
	struct hexagonfs_dirent *root = construct_root_dir(trial, "sdsp"); assert(root);
	struct apps_std_ctx ctx = {0};
	ctx.rootfd = hexagonfs_open_root(ctx.fds, root); assert(ctx.rootfd >= 0);
	readable(&ctx, "/mnt/vendor/persist/sensors/registry/file1", "FILE1");
	readable(&ctx, "/persist/sensors/registry/file2", "FILE2");
	readable(&ctx, "/persist/sensors/registry/registry/sample", "SENSOR");
	readable(&ctx, "/persist/sensors/registry/registry/../sns_reg_version", "OLD");
	readable(&ctx, "/proc/oppoVersion/modemType", "4");
	readable(&ctx, "/sys/devices/soc0/platform_subtype", "Unknown");
	assert(hexagonfs_ram_open(ctx.fds, "/proc/oppoVersion/modemType", "w") < 0);
	assert(hexagonfs_ram_open(ctx.fds, "/persist/sensors/registry/../../../escape", "w") < 0);
	char link[512]; snprintf(link, sizeof(link), "%s/sensors/registry/link", trial);
	assert(!symlink("/etc/passwd", link));
	assert(hexagonfs_ram_open(ctx.fds, "/persist/sensors/registry/link", "w") < 0);
	char env[] = "ADSP_LIBRARY_PATH", path[] = "/persist/sensors/registry/registry/../sns_reg_version", mode[] = "w";
	uint32_t opened = 0;
	struct fastrpc_io_buffer inputs[5] = {{0}, {.p=env, .s=sizeof(env)}, {0}, {.p=path, .s=sizeof(path)}, {.p=mode, .s=sizeof(mode)}};
	struct fastrpc_io_buffer outputs[1] = {{.p=&opened, .s=sizeof(opened)}};
	assert(!apps_std_fopen_with_env(&ctx, inputs, outputs));
	struct { uint32_t fd, size; } command = {opened, 9};
	struct { uint32_t written, eof; } result = {0};
	char value[] = "version=3";
	struct fastrpc_io_buffer in[2] = {{.p=&command, .s=sizeof(command)}, {.p=value, .s=9}};
	struct fastrpc_io_buffer out[1] = {{.p=&result, .s=sizeof(result)}};
	assert(!apps_std_fwrite(&ctx, in, out) && result.written == 9 && !result.eof);
	command.size = 100;
	assert(apps_std_fwrite(&ctx, in, out) == AEE_EBADPARM);
	struct fastrpc_io_buffer flush[1] = {{.p=&opened, .s=sizeof(opened)}};
	assert(!apps_std_fflush(&ctx, flush, NULL));
	assert(!hexagonfs_close(ctx.fds, opened));
	readable(&ctx, path, "version=3");
	int appended = hexagonfs_ram_open(ctx.fds, path, "a"); assert(appended >= 0);
	assert(hexagonfs_ram_write(ctx.fds, appended, 1, "\n") == 1);
	assert(!hexagonfs_close(ctx.fds, appended));
	readable(&ctx, path, "version=3\n");
	assert(hexagonfs_ram_write(ctx.fds, -1, 1, "x") == -EBADF);
	int readonly = hexagonfs_openat(ctx.fds, ctx.rootfd, ctx.rootfd, "/proc/oppoVersion/modemType");
	assert(readonly >= 0 && hexagonfs_ram_write(ctx.fds, readonly, 1, "x") == -EROFS);
	assert(!hexagonfs_close(ctx.fds, readonly));
	puts("PASS: aliases, parent registry, OEM attributes, real RPC writes/readback/append/flush, traversal/symlink/RO/buffer limits");
	return 0;
}
