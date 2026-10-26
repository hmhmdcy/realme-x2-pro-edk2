"""Prepare an optional pre-reset observer; OEM ranges remain diagnostic parameters."""
from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'firmware-context-validation.json').read_text())['passed']
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c'];before={n:(P/(n+'.before')).read_text() for n in names};after=dict(before)
s=after[names[0]];anchor='fail:\n\tpublish_start_failure(a5);';assert s.count(anchor)==1
s=s.replace(anchor,'''fail:
\t/* An optional owner observer runs with RAM/PM still owned, before any
\t * CPU/reset teardown. It must not re-enter lifecycle operations.
\t */
\tif (a5->cpu_release_attempted && a5->failure_snapshot)
\t\ta5->failure_snapshot(a5);
\tpublish_start_failure(a5);''');after[names[0]]=s
s=after[names[1]];anchor='\tbool boot_expired;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n\tvoid (*failure_snapshot)(struct camss_a5 *a5);')
anchor=' * Failed teardown retains mapped backing; do not unbind until cleanup succeeds.'
s=s.replace(anchor,''' * An optional failure_snapshot observer runs under the lifecycle mutex,
 * before CPU/block reset and release of any backing or PM reference. Keep
 * the observer and its data valid through start; it must be bounded, avoid
 * allocation/MMIO and never re-enter lifecycle/command operations.
 * Failed teardown retains mapped backing; do not unbind until cleanup succeeds.''');after[names[1]]=s
s=after[names[2]].replace('#include <linux/firmware.h>','#include <linux/elf.h>\n#include <linux/firmware.h>').replace('#include <linux/slab.h>','#include <linux/slab.h>\n#include <linux/unaligned.h>')
anchor='static unsigned int group_devices;';assert s.count(anchor)==1
helper='''

/* Temporary diagnostic ranges are supplied from the verified ELF profile.
 * No OEM symbol address is part of the reusable SoC transport API.
 */
static unsigned int snapshot_offsets[4], snapshot_words[4];
static unsigned int snapshot_offset_count, snapshot_word_count;
static const u8 *snapshot_boot_code;
module_param_array(snapshot_offsets, uint, &snapshot_offset_count, 0444);
module_param_array(snapshot_words, uint, &snapshot_word_count, 0444);

static bool snapshot_ranges_valid(u32 bytes)
{
\tunsigned int i;

\tif (!snapshot_offset_count || snapshot_offset_count > ARRAY_SIZE(snapshot_offsets) ||
\t    snapshot_offset_count != snapshot_word_count)
\t\treturn false;
\tfor (i = 0; i < snapshot_offset_count; i++) {
\t\tif (!IS_ALIGNED(snapshot_offsets[i], sizeof(u32)) ||
\t\t    !snapshot_words[i] || snapshot_words[i] > 96 ||
\t\t    snapshot_offsets[i] > bytes ||
\t\t    snapshot_words[i] > (bytes - snapshot_offsets[i]) / sizeof(u32))
\t\t\treturn false;
\t}
\treturn true;
}

static void failure_snapshot(struct camss_a5 *a5)
{
\tunsigned int i, j, k, count;
\tu32 words[8], offset;
\tbool match;

\tdev_info(a5->dev, "A5 pre-reset snapshot begin ranges=%u\\n", snapshot_offset_count);
\tif (!a5->power_held || !a5->firmware.cpu || !snapshot_boot_code ||
\t    a5->firmware.bytes < 4096 || a5->firmware.mapped != a5->firmware.bytes ||
\t    !snapshot_ranges_valid(a5->firmware.bytes)) {
\t\tdev_info(a5->dev, "A5 pre-reset snapshot unavailable\\n");
\t\treturn;
\t}
\tdma_rmb();
\tmatch = !memcmp(a5->firmware.cpu, snapshot_boot_code, 4096);
\tdev_info(a5->dev, "A5 pre-reset snapshot code-match=%u\\n", match);
\tif (!match)
\t\treturn;
\tfor (i = 0; i < snapshot_offset_count; i++) {
\t\tfor (j = 0; j < snapshot_words[i]; j += ARRAY_SIZE(words)) {
\t\t\tcount = min_t(unsigned int, ARRAY_SIZE(words), snapshot_words[i] - j);
\t\t\toffset = snapshot_offsets[i] + j * sizeof(u32);
\t\t\tmemset(words, 0, sizeof(words));
\t\t\tfor (k = 0; k < count; k++)
\t\t\t\twords[k] = get_unaligned_le32(a5->firmware.cpu + offset + k * sizeof(u32));
\t\t\tdev_info(a5->dev, "A5 pre-reset snapshot data offset=%x count=%u values=%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x\\n",
\t\t\t\t offset, count, words[0], words[1], words[2], words[3],
\t\t\t\t words[4], words[5], words[6], words[7]);
\t\t}
\t}
\tdev_info(a5->dev, "A5 pre-reset snapshot end\\n");
}

static int configure_snapshot(struct camss_a5 *a5, const struct firmware *firmware)
{
\tstruct camss_a5_fw_layout layout;
\tu32 table;
\tunsigned int i, count;
\tint ret;

\ta5->failure_snapshot = NULL;
\tsnapshot_boot_code = NULL;
\tif (!snapshot_offset_count && !snapshot_word_count)
\t\treturn 0;
\tret = camss_a5_fw_inspect(firmware, CAMSS_A5_FW_WINDOW, &layout);
\tif (ret)
\t\treturn ret;
\tif (!snapshot_ranges_valid(layout.span))
\t\treturn -EINVAL;
\ttable = get_unaligned_le32(firmware->data + 28);
\tcount = get_unaligned_le16(firmware->data + 44);
\tfor (i = 0; i < count; i++) {
\t\tconst u8 *header = firmware->data + table + i * sizeof(Elf32_Phdr);

\t\tif (get_unaligned_le32(header) == PT_LOAD &&
\t\t    !get_unaligned_le32(header + 8) &&
\t\t    get_unaligned_le32(header + 16) >= 4096 &&
\t\t    (get_unaligned_le32(header + 24) & PF_X)) {
\t\t\tsnapshot_boot_code = firmware->data + get_unaligned_le32(header + 4);
\t\t\ta5->failure_snapshot = failure_snapshot;
\t\t\treturn 0;
\t\t}
\t}
\treturn -ENOEXEC;
}
'''
s=s.replace(anchor,anchor+helper)
anchor='\tphase = "start";\n\tret = camss_a5_start(a5, firmware);\n\trelease_firmware(firmware);';assert s.count(anchor)==1
s=s.replace(anchor,'''\tphase = "snapshot-profile";
\tret = configure_snapshot(a5, firmware);
\tif (!ret) {
\t\tphase = "start";
\t\tret = camss_a5_start(a5, firmware);
\t}
\ta5->failure_snapshot = NULL;
\tsnapshot_boot_code = NULL;
\trelease_firmware(firmware);''');after[names[2]]=s
patch=[]
for n in names:
 (P/(n+'.proposed')).write_text(after[n]);patch.extend(difflib.unified_diff(before[n].splitlines(True),after[n].splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+n,tofile='b/drivers/media/platform/qcom/camss/'+n))
(HERE/'pre-reset-observer.patch').write_text(''.join(patch));(HERE/names[2]).write_text(after[names[2]])
report=dict(stage=372,parent=json.loads((HERE.parent/'kernel371/source-state.json').read_text())['commit'],changed=names,applied=False,
 pre_reset_observer_optional=True,firmware_specific_addresses_only_runtime_diagnostic_parameters=True,
 maximum_ranges=4,maximum_words_per_range=96,code_page_compared_bytes=4096,installed=False,phone_cpu_started=False)
(HERE/'proposal-state.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
