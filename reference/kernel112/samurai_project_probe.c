// SPDX-License-Identifier: GPL-2.0-only
/* Bounded read-only SMEM 135 reader using the owning kernel driver's API.
 * Copy the record bytes without assuming the downstream ABI version.
 * This external diagnostic module intentionally retains the normal OOT taint.
 */
#include <linux/debugfs.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/seq_file.h>
#include <linux/soc/qcom/smem.h>
#include <linux/unaligned.h>

static struct dentry *root;
static u8 project_record[128];
static size_t record_size;
static size_t copied_size;

static int project_show(struct seq_file *s, void *unused)
{
	size_t i;
	seq_printf(s, "{\"smem_record_bytes\":%zu,\"copied_bytes\":%zu,"
		   "\"memory_read_only\":true,\"raw_hex\":\"", record_size, copied_size);
	for (i = 0; i < copied_size; i++)
		seq_printf(s, "%02x", project_record[i]);
	seq_puts(s, "\"}\n");
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(project);

static int __init samurai_project_init(void)
{
	void *data;
	struct dentry *file;
	if (!of_machine_is_compatible("realme,samurai")) {
		pr_err("samurai-project: board compatible gate failed\n");
		return -ENODEV;
	}
	data = qcom_smem_get(QCOM_SMEM_HOST_ANY, 135, &record_size);
	if (IS_ERR(data))
		return PTR_ERR(data);
	if (record_size < 13 || record_size > 4096)
		return -EINVAL;
	copied_size = min(record_size, sizeof(project_record));
	memcpy_fromio(project_record, (void __iomem *)data, copied_size);
	root = debugfs_create_dir("samurai_project_metadata", NULL);
	if (IS_ERR(root))
		return PTR_ERR(root);
	file = debugfs_create_file("project-private.json", 0400, root, NULL, &project_fops);
	if (IS_ERR(file)) {
		debugfs_remove_recursive(root);
		return PTR_ERR(file);
	}
	return 0;
}

static void __exit samurai_project_exit(void)
{
	debugfs_remove_recursive(root);
	memzero_explicit(project_record, sizeof(project_record));
}
module_init(samurai_project_init);
module_exit(samurai_project_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only stock Realme project metadata via qcom_smem_get");
