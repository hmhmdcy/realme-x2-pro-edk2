from pathlib import Path
import difflib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['hal-io','firmware-io']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
names=['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c'];before={n:(P/(n+'.before')).read_text() for n in names};after=dict(before)
s=after[names[0]]
s=s.replace('#define IPE_DESTROY 8U','#define IPE_DESTROY 8U\n#define IPE_CONFIG_IO 5U\n#define IPE_MEM_MAP 14U\n#define IPE_MEM_UNMAP 15U\n#define IPE_ASYNC_INDIRECT 0x101000eU\n#define IPE_ASYNC_INDIRECT_ACK 0x102000eU\n#define IPE_IO_CONFIG_BYTES 1216U\n#define CONFIG_IOVA (SHARED_IOVA + 0x20000U)\n#define CONFIG_BYTES 4096U')
old='''\tcase IPE_ASYNC_DIRECT_ACK:
\t\t/* Actual A5 firmware emits 32-byte header plus 16-byte payload,
\t\t * not sizeof(the downstream packed 12-byte payload declaration).
\t\t */
\t\tif (bytes != 48)
\t\t\tgoto malformed;'''
new='''\tcase IPE_ASYNC_DIRECT_ACK:
\tcase IPE_ASYNC_INDIRECT_ACK:
\t\t/* Sizes come from the actual A5 dispatch/callbacks, which differ
\t\t * from the old downstream packed payload declarations.
\t\t */
\t\tif (a5->session_opcode != IPE_DESTROY &&
\t\t    a5->session_opcode != IPE_MEM_MAP &&
\t\t    a5->session_opcode != IPE_MEM_UNMAP &&
\t\t    a5->session_opcode != IPE_CONFIG_IO)
\t\t\tgoto malformed;
\t\tif ((a5->session_opcode == IPE_DESTROY && bytes != 48) ||
\t\t    ((a5->session_opcode == IPE_MEM_MAP ||
\t\t      a5->session_opcode == IPE_MEM_UNMAP) && bytes != 44) ||
\t\t    (a5->session_opcode == IPE_CONFIG_IO && bytes != 56))
\t\t\tgoto malformed;'''
assert s.count(old)==1;s=s.replace(old,new)
anchor='\t\ta5->session_reply = true;\n\t\tbreak;\n\tcase PING_ACK:';assert s.count(anchor)==1
s=s.replace(anchor,'\t\tif (!error && a5->session_opcode == IPE_CONFIG_IO)\n\t\t\ta5->session_scratch_bytes = get_unaligned_le32(a5->message + 36);\n'+anchor)
s=s.replace('\ta5->session_reply_handle = 0;','\ta5->session_reply_handle = 0;\n\ta5->session_scratch_bytes = 0;')
anchor='int camss_a5_ipe_create(';assert s.count(anchor)==1;s=s.replace(anchor,(HERE/'io-encode.c').read_text()+'\n'+(HERE/'io-methods.c').read_text()+'\n'+anchor)
anchor='\ta5->session_opcode = IPE_DESTROY;';assert s.count(anchor)==1
# Unmap before generating the destroy token: it must not be changed by an
# intervening command after the destroy packet's token fields are prepared.
needle='\tret = session_token(a5);\n\tif (ret)\n\t\treturn ret;\n'+anchor
assert s.count(needle)==1
s=s.replace(needle,'\tif (a5->config_fw_mapped && a5->config_owner == session) {\n\t\tret = config_region_locked(a5, session, false);\n\t\tif (ret)\n\t\t\treturn ret;\n\t}\n'+needle)
s=s.replace('\tsession->type = 0;','\tsession->type = 0;\n\tsession->configured = false;\n\tsession->scratch_bytes = 0;')
s=s.replace('\t\tsession->type = 0;\n\tsession->configured = false;\n\tsession->scratch_bytes = 0;', '\t\tsession->type = 0;\n\t\tsession->configured = false;\n\t\tsession->scratch_bytes = 0;')
anchor='\ta5->session_count = 0;\n\ta5->session_uncertain = false;';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\ta5->config_fw_mapped = false;\n\ta5->config_owner = NULL;')
anchor='return a5->firmware.cpu || a5->shared.cpu || a5->heap.cpu;';assert s.count(anchor)==1;s=s.replace(anchor,'return a5->firmware.cpu || a5->shared.cpu || a5->heap.cpu || a5->config.cpu;')
s=s.replace('{ &a5->heap, &a5->shared, &a5->firmware }','{ &a5->config, &a5->heap, &a5->shared, &a5->firmware }')
anchor='\ta5->table = a5->shared.cpu;';assert s.count(anchor)==1
s=s.replace(anchor,'\tret = camss_a5_iova_memory_alloc(a5->dev, &a5->config, CONFIG_IOVA, CONFIG_BYTES);\n\tif (ret)\n\t\treturn ret;\n'+anchor)
anchor='\treturn camss_a5_fw_memory_map(&a5->heap);';assert s.count(anchor)==1
s=s.replace(anchor,'\tret = camss_a5_fw_memory_map(&a5->heap);\n\tif (ret)\n\t\treturn ret;\n\treturn camss_a5_fw_memory_map(&a5->config);')
anchor='\ta5->session_creates = a5->session_destroys = a5->session_peak = 0;';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\ta5->io_configs = a5->config_maps = a5->config_unmaps = 0;')
after[names[0]]=s
s=after[names[1]]
anchor='struct camss_a5_session {'
assert s.count(anchor)==1;s=s.replace(anchor,'''struct camss_a5_nv12_layout {
\tu32 width, height, stride, slice_height;
\tbool uv_swap;
};

struct camss_a5_ipe_io {
\tstruct camss_a5_nv12_layout input, output;
\tu32 output_port; /* 8: display, 9: video */
};

'''+anchor)
s=s.replace('\tu32 handle, type;','\tu32 handle, type;\n\tstruct camss_a5_ipe_io io;\n\tu32 scratch_bytes;\n\tbool configured;')
s=s.replace('firmware, shared, heap;','firmware, shared, heap, config;')
anchor='\tbool command_queued, session_reply, session_uncertain;';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n\tstruct camss_a5_session *config_owner;\n\tbool config_fw_mapped;\n\tu32 session_scratch_bytes, io_configs, config_maps, config_unmaps;')
anchor='int camss_a5_ipe_destroy(struct camss_a5 *a5, struct camss_a5_session *session);';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'\n/* Configure linear NV12/NV21 without submitting any image DMA or frame. */\nint camss_a5_ipe_configure_nv12(struct camss_a5 *a5,\n\t\t\t       struct camss_a5_session *session,\n\t\t\t       const struct camss_a5_ipe_io *io);')
after[names[1]]=s
s=after[names[2]]
anchor='static struct camss_a5_session session_rt, session_non_rt;';assert s.count(anchor)==1
s=s.replace(anchor,anchor+'''\nstatic u32 scratch_observed[2];
static const struct camss_a5_ipe_io test_io = {
\t.input = { .width = 640, .height = 480, .stride = 640, .slice_height = 480 },
\t.output = { .width = 640, .height = 480, .stride = 640, .slice_height = 480 },
\t.output_port = 8,
};''')
s=s.replace('\\"image_frames\\":0}', '\\"io_configs\\":%u,\\"config_maps\\":%u,\\"config_unmaps\\":%u,\\"config_fw_mapped\\":%s,\\"scratch_bytes\\":[%u,%u],\\"image_frames\\":0}')
s=s.replace('a5->firmware.mapped + a5->shared.mapped + a5->heap.mapped,','a5->firmware.mapped + a5->shared.mapped + a5->heap.mapped + a5->config.mapped,')
anchor='\t\t  a5->session_uncertain ? "true" : "false");';assert s.count(anchor)==1
s=s.replace(anchor,'\t\t  a5->session_uncertain ? "true" : "false", a5->io_configs, a5->config_maps, a5->config_unmaps,\n\t\t  a5->config_fw_mapped ? "true" : "false", scratch_observed[0], scratch_observed[1]);')
for instance,phase,nextphase in [('session_rt','configure-ipe-rt','create-ipe-non-rt'),('session_non_rt','configure-ipe-non-rt','destroy-ipe-non-rt')]:
 anchor='\tphase = "'+nextphase+'";';assert s.count(anchor)==1
 s=s.replace(anchor,'\tphase = "'+phase+'";\n\tret = camss_a5_ipe_configure_nv12(a5, &'+instance+', &test_io);\n\tif (ret)\n\t\tgoto done;\n\tscratch_observed['+str(int(instance=='session_non_rt'))+'] = '+instance+'.scratch_bytes;\n'+anchor)
after[names[2]]=s;(HERE/names[2]).write_text(s)
patch=''
for name in names:
 (P/(name+'.proposed')).write_text(after[name]);patch+=''.join(difflib.unified_diff(before[name].splitlines(True),after[name].splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/'+name,tofile='b/drivers/media/platform/qcom/camss/'+name))
(HERE/'ipe-io-config.patch').write_text(patch)
parent=json.loads((HERE/'source-before.json').read_text())['parent'];(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=377,parent=parent,changed=names,installed=False),indent=2)+'\n')
print('Prepared actual A5 1216-byte NV12 IO config with owned DMA alias and firmware MAP/CONFIG/UNMAP lifecycle.')
