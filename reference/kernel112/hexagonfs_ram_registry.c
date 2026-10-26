// SPDX-License-Identifier: GPL-3.0-or-later
/* Real registry writes confined to a tmpfs copy; no stock partition access. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <linux/openat2.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <unistd.h>
#include "hexagonfs.h"

static int registry_fd = -1;
struct ram_file { int fd; };

int hexagonfs_enable_ram_registry(const char *path)
{
	struct open_how how = { .flags = O_RDONLY | O_DIRECTORY | O_CLOEXEC,
		.resolve = RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS };
	struct stat st;
	struct statfs fs;
	int fd;
	if (registry_fd != -1)
		return -EBUSY;
	fd = syscall(SYS_openat2, AT_FDCWD, path, &how, sizeof(how));
	if (fd < 0)
		return -errno;
	if (fstat(fd, &st) || fstatfs(fd, &fs)) {
		int ret = -errno; close(fd); return ret;
	}
	if (fs.f_type != TMPFS_MAGIC || st.st_uid != geteuid() || (st.st_mode & 077)) {
		close(fd);
		return -EPERM;
	}
	registry_fd = fd;
	return 0;
}

static void ram_close(void *data)
{
	struct ram_file *ctx = data;
	close(ctx->fd);
	free(ctx);
}
static ssize_t ram_read(struct hexagonfs_fd *fd, size_t size, void *ptr)
{
	ssize_t n = read(((struct ram_file *)fd->data)->fd, ptr, size);
	return n < 0 ? -errno : n;
}
static int ram_seek(struct hexagonfs_fd *fd, off_t off, int whence)
{
	return lseek(((struct ram_file *)fd->data)->fd, off, whence) < 0 ? -errno : 0;
}
static int ram_stat(struct hexagonfs_fd *fd, struct stat *st)
{
	return fstat(((struct ram_file *)fd->data)->fd, st) ? -errno : 0;
}
static struct hexagonfs_file_ops ram_ops = {
	.close = ram_close, .read = ram_read, .seek = ram_seek, .stat = ram_stat,
};

static const char *registry_relative(const char *path)
{
	const char *prefixes[] = { "/persist/sensors/registry/",
		"/mnt/vendor/persist/sensors/registry/", NULL };
	for (int i = 0; prefixes[i]; i++)
		if (!strncmp(path, prefixes[i], strlen(prefixes[i])))
			return path + strlen(prefixes[i]);
	return NULL;
}

int hexagonfs_ram_open(struct hexagonfs_fd **fds, const char *path, const char *mode)
{
	const char *relative = registry_relative(path);
	struct open_how how = { .resolve = RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS |
		RESOLVE_NO_MAGICLINKS, .mode = 0600 };
	struct hexagonfs_fd *fd;
	struct ram_file *ctx;
	struct stat st;
	int flags, realfd, index;
	bool plus = strchr(mode, '+') != NULL;
	if (registry_fd < 0 || !relative || !*relative)
		return -EROFS;
	if (strspn(mode + 1, "b+") != strlen(mode + 1) || strlen(mode) > 3)
		return -EINVAL;
	switch (mode[0]) {
	case 'r': flags = plus ? O_RDWR : O_RDONLY; how.mode = 0; break;
	case 'w': flags = (plus ? O_RDWR : O_WRONLY) | O_CREAT | O_TRUNC; break;
	case 'a': flags = (plus ? O_RDWR : O_WRONLY) | O_CREAT | O_APPEND; break;
	default: return -EINVAL;
	}
	how.flags = flags | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK;
	realfd = syscall(SYS_openat2, registry_fd, relative, &how, sizeof(how));
	if (realfd < 0)
		return -errno;
	if (fstat(realfd, &st) || !S_ISREG(st.st_mode)) {
		close(realfd); return -EINVAL;
	}
	for (index = 0; index < HEXAGONFS_MAX_FD && fds[index]; index++) {}
	if (index == HEXAGONFS_MAX_FD) {
		close(realfd); return -EMFILE;
	}
	fd = calloc(1, sizeof(*fd));
	ctx = malloc(sizeof(*ctx));
	if (!fd || !ctx) {
		free(fd); free(ctx); close(realfd); return -ENOMEM;
	}
	ctx->fd = realfd;
	fd->is_assigned = true; fd->ops = &ram_ops; fd->data = ctx;
	fds[index] = fd;
	return index;
}

ssize_t hexagonfs_ram_write(struct hexagonfs_fd **fds, int fileno, size_t size,
			   const void *ptr)
{
	struct stat st;
	ssize_t n;
	int realfd;
	if (fileno < 0 || fileno >= HEXAGONFS_MAX_FD || !fds[fileno])
		return -EBADF;
	if (fds[fileno]->ops != &ram_ops)
		return -EROFS;
	realfd = ((struct ram_file *)fds[fileno]->data)->fd;
	if (fstat(realfd, &st))
		return -errno;
	if (size > 1024 * 1024 || st.st_size + size > 16 * 1024 * 1024)
		return -EFBIG;
	n = write(realfd, ptr, size);
	return n < 0 ? -errno : n;
}

int hexagonfs_ram_flush(struct hexagonfs_fd **fds, int fileno)
{
	if (fileno < 0 || fileno >= HEXAGONFS_MAX_FD || !fds[fileno])
		return -EBADF;
	if (fds[fileno]->ops != &ram_ops)
		return 0;
	return fsync(((struct ram_file *)fds[fileno]->data)->fd) ? -errno : 0;
}
