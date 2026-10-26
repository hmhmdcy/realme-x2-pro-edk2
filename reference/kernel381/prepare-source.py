from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'ipe-quiesce-validation.json').read_text())['passed']
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-resources.c','camss-icp-a5-resources.h']
before={name:(P/(name+'.before')).read_text() for name in names};after=dict(before)
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
s=before[names[0]]
s=replace(s,'#include <linux/module.h>','#include <linux/module.h>\n#include <linux/mm.h>\n#include <linux/of.h>')
s=replace(s,'#include "camss-icp-a5-boot.h"','#include "camss-icp-a5-boot.h"\n#include "camss-icp-a5-ipe.h"')
s=replace(s,'#define IPE_CONFIG_IO 5U','#define IPE_CONFIG_IO 5U\n#define IPE_FRAME_PROCESS 6U')
s=replace(s,'#define CONFIG_BYTES 4096U','#define CONFIG_BYTES 4096U\n#define REQUEST_IOVA 0x07800000U\n#define REQUEST_MAX 0x100000U\n#define IMAGE_INPUT_IOVA 0x20000000U\n#define IMAGE_OUTPUT_IOVA 0x24000000U\n#define IMAGE_WINDOW 0x04000000U\n\nstatic bool has_ipe_sid_group(struct device *dev);')
s=replace(s,'a5->session_opcode != IPE_CONFIG_IO)','a5->session_opcode != IPE_CONFIG_IO &&\n\t\t    a5->session_opcode != IPE_FRAME_PROCESS)')
s=replace(s,'(a5->session_opcode == IPE_CONFIG_IO && bytes != 56))','(a5->session_opcode == IPE_CONFIG_IO && bytes != 56) ||\n\t\t    (a5->session_opcode == IPE_FRAME_PROCESS && bytes != 72))')
s=replace(s,'a5->session_opcode == IPE_DESTROY) ?','a5->session_opcode == IPE_DESTROY ||\n\t\t\t a5->session_opcode == IPE_FRAME_PROCESS) ?')
s=replace(s,'\ta5->config_owner = NULL;\n}', '\ta5->config_owner = NULL;\n\ta5->request_fw_mapped = false;\n\ta5->request_owner = NULL;\n}')
s=replace(s,'return a5->firmware.cpu || a5->shared.cpu || a5->heap.cpu || a5->config.cpu;', 'return a5->firmware.cpu || a5->shared.cpu || a5->heap.cpu || a5->config.cpu ||\n\t       a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu;')
s=replace(s,'struct camss_a5_fw_memory *memories[] = { &a5->config, &a5->heap, &a5->shared, &a5->firmware };','struct camss_a5_fw_memory *memories[] = {\n\t\t&a5->image_output, &a5->image_input, &a5->request,\n\t\t&a5->config, &a5->heap, &a5->shared, &a5->firmware,\n\t};')
s=replace(s,'\tif (a5->cpu_enabled)\n\t\treturn -EBUSY;\n\tcapture_shared_state(a5);','\tif (a5->cpu_enabled || a5->ipe_dma_pending)\n\t\treturn -EBUSY;\n\tcapture_shared_state(a5);')
s=replace(s,'\tinvalidate_sessions(a5);\n\tcapture_shared_state(a5);','\tif (a5->ipe_dma_pending) {\n\t\tret = camss_a5_ipe_quiesce(&a5->resources);\n\t\tif (ret)\n\t\t\treturn ret;\n\t\ta5->ipe_dma_pending = false;\n\t}\n\tinvalidate_sessions(a5);\n\tcapture_shared_state(a5);')
s=replace(s,'\ta5->io_configs = a5->config_maps = a5->config_unmaps = 0;','\ta5->io_configs = a5->config_maps = a5->config_unmaps = 0;\n\ta5->frames_submitted = a5->frames_completed = 0;\n\ta5->transfer_maps = a5->transfer_unmaps = 0;')
s=replace(s,'\twritel(0, base + A5_INT_ENABLE);\n\twritel(7, base + A5_INT_CLEAR);','\tif (a5->engine_dma_capable) {\n\t\tret = camss_a5_ipe_quiesce(&a5->resources);\n\t\tif (ret)\n\t\t\tgoto fail;\n\t\tdev_info(a5->dev, "A5 IPE reset ACKs verified before CPU release\\n");\n\t}\n\twritel(0, base + A5_INT_ENABLE);\n\twritel(7, base + A5_INT_CLEAR);')
s=replace(s,'\tif (a5->cpu_enabled)\n\t\treturn -EBUSY;\n\t/* A cooperative stop','\tif (a5->cpu_enabled || a5->ipe_dma_pending || camss_a5_backing_owned(a5))\n\t\treturn -EBUSY;\n\t/* A cooperative stop')
s=replace(s,'\ta5->dev = dev;\n\tret = dma_set_mask','\ta5->dev = dev;\n\ta5->engine_dma_capable = has_ipe_sid_group(dev);\n\tret = dma_set_mask')
start=s.index('static int config_region_locked(');end=s.index('\nint camss_a5_ipe_configure_nv12(',start);old=s[start:end]
wire=old[:old.index('\tif (map && a5->command_queued)')]
wire=wire.replace('static int config_region_locked(struct camss_a5 *a5,\n\t\t\t\tstruct camss_a5_session *session, bool map)','static int region_packet_locked(struct camss_a5 *a5,\n\t\t\t\tstruct camss_a5_session *session,\n\t\t\t\tstruct camss_a5_fw_memory *memory, bool map)')
assert 'static int region_packet_locked' in wire
a=wire.index('\tif ((map && a5->config_fw_mapped)');b=wire.index('\tret = session_token(a5);',a)
wire=wire[:a]+'\ta5->command_queued = false;\n\tif (!memory || !memory->cpu || !memory->bytes ||\n\t    memory->mapped != memory->bytes)\n\t\treturn -EINVAL;\n'+wire[b:]
wire=wire.replace('a5->config.iova','memory->iova').replace('a5->config.bytes','memory->bytes')+'\treturn ret;\n}\n\n'
wire=wire.replace('\ta5->command_queued = false;\n','').replace('\tif (session->a5 != a5','\ta5->command_queued = false;\n\tif (session->a5 != a5',1)
wrapper=old[:old.index('\tret = session_token(a5);')]+ '\tret = region_packet_locked(a5, session, &a5->config, map);\n'+old[old.index('\tif (map && a5->command_queued)'):]
wrapper=wrapper.replace('\tu8 packet[56] = {};\n','')
s=s[:start]+wire+wrapper+s[end:]
# Outstanding request mappings are retired through full stop. Do not issue a
# destroy that could invalidate a live DMA owner while those buffers survive.
anchor='\tif (a5->config_fw_mapped && a5->config_owner == session) {'
s=replace(s,anchor,'\tif (a5->request_fw_mapped && a5->request_owner == session)\n\t\treturn -EBUSY;\n'+anchor)
sid=r'''
static bool has_ipe_sid_group(struct device *dev)
{
	static const u32 specs[][2] = {
		{ 0x2222, 0 }, { 0x2080, 0x20 }, { 0x20a0, 0x20 },
		{ 0x2100, 0x20 }, { 0x2120, 0x20 }, { 0x20c0, 0 }, { 0x2140, 0 },
	};
	struct device_node *provider = NULL;
	struct of_phandle_args args;
	unsigned int i;
	bool valid = false;

	if (of_count_phandle_with_args(dev->of_node, "iommus", "#iommu-cells") != (int)ARRAY_SIZE(specs))
		return false;
	for (i = 0; i < ARRAY_SIZE(specs); i++) {
		if (of_parse_phandle_with_args(dev->of_node, "iommus", "#iommu-cells", i, &args)) {
			valid = false;
			goto out;
		}
		if (!provider)
			provider = of_node_get(args.np);
		valid = args.np == provider && args.args_count == 2 &&
			args.args[0] == specs[i][0] && args.args[1] == specs[i][1];
		of_node_put(args.np);
		if (!valid)
			goto out;
	}
out:
	of_node_put(provider);
	return valid;
}
'''.replace('\\t','\t')
s+='\n'+sid+'\n'+(HERE/'transfer-methods.c').read_text();after[names[0]]=s
s=before[names[1]];s=replace(s,'struct camss_a5_fw_memory firmware, shared, heap, config;','struct camss_a5_fw_memory firmware, shared, heap, config;\n\tstruct camss_a5_fw_memory request, image_input, image_output;')
s=replace(s,'\tbool config_fw_mapped;','\tbool config_fw_mapped;\n\tbool engine_dma_capable, ipe_dma_pending, request_fw_mapped;\n\tstruct camss_a5_session *request_owner;\n\tu32 frames_submitted, frames_completed, transfer_maps, transfer_unmaps;');after[names[1]]=s
after[names[2]]=before[names[2]].replace('#include <linux/errno.h>','#include <linux/errno.h>\n#include <linux/io.h>\n#include <linux/iopoll.h>')+'\n'+(HERE/'ipe-quiesce.c').read_text()
s=before[names[3]];s=replace(s,'\tu8 held_domains;','\tu8 held_domains;\n\tu8 ipe_reset_acks[2];');s=replace(s,'\n#endif','\nint camss_a5_ipe_quiesce(struct camss_a5_resources *res);\n\n#endif');after[names[3]]=s
name='camss-icp-a5-ipe.h';original=(HERE.parent/'kernel380'/name).read_text();before[name]=original
job='''
/* Sleeping synchronous bring-up transfer. Only the verified all-zero IQ
 * fixture is accepted. The core owns all DMA backing and retains it after
 * uncertain completion until A5 and both IPE engines are quiescent.
 */
struct camss_a5_ipe_job {
\tconst void *striping, *iq, *input;
\tvoid *output;
\tu32 striping_bytes, iq_bytes, input_bytes, output_bytes;
\tu32 bl_bytes, request_id, max_cores, target_time_ns;
};
int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,
\t\t     const struct camss_a5_ipe_job *job);
'''
after[name]=original.replace('\n#endif','\n'+job+'\n#endif');names.append(name)
patch='';relative=Path('drivers/media/platform/qcom/camss')
for name in names:
 (P/(name+'.before')).write_text(before[name]);(P/(name+'.proposed')).write_text(after[name])
 patch+=''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/'+str(relative/name),tofile='b/'+str(relative/name)))
(P/'camss-icp-a5-boot-test.c.proposed').write_bytes((P/'camss-icp-a5-boot-test.c.before').read_bytes())
(HERE/'ipe-transfer.patch').write_text(patch)
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=381,parent='1f0038ccbdc2efb71d97fc85c1f64452f9ce41a6',changed=names,frame_submission_candidate=True,installed=False),indent=2)+'\n')
print('Prepared owned frame transfer, 72-byte completion parsing and reset-before-DMA-release integration.')
