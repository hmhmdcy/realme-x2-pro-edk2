from pathlib import Path
import difflib
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';out=Path('/mnt/e/edk2-samurai-out/kernel106');k=Path('/home/cy122/x2pro-linux/linux')
for n,path in [('qrtr.h','include/trace/events/qrtr.h'),('af_qrtr.c','net/qrtr/af_qrtr.c')]:
    p=k/path;s=p.read_text();assert s==(ref/(n+'.after')).read_text()
    if n=='qrtr.h':
        a=s.index('TRACE_EVENT(qrtr_endpoint_tx,');b=s.index('#endif /* _TRACE_QRTR_H */',a)
        c=s[a:b].replace('TP_PROTO(unsigned int node, int type,','TP_PROTO(unsigned int node, unsigned int wire_node, int type,').replace('TP_ARGS(node, type,','TP_ARGS(node, wire_node, type,').replace('__field(unsigned int, node)','__field(unsigned int, node)\n\t\t__field(unsigned int, wire_node)').replace('__entry->node = node; __entry->type = type;','__entry->node = node; __entry->wire_node = wire_node;\n\t\t__entry->type = type;').replace('"node=%u type=%d','"node=%u wire_node=%u type=%d').replace('__entry->node, __entry->type,','__entry->node, __entry->wire_node, __entry->type,')
        s=s[:a]+c+s[b:]
    else:
        a=s.index('static int qrtr_node_enqueue(');b=s.index('\n/* Lookup node by id.',a)
        c=s[a:b].replace('\tint rc, confirm_rx;','\tint rc, confirm_rx;\n\tu32 wire_node = READ_ONCE(node->nid);').replace('trace_qrtr_endpoint_tx(READ_ONCE(node->nid), type,','trace_qrtr_endpoint_tx(READ_ONCE(node->nid), wire_node, type,').replace('\thdr->confirm_rx = cpu_to_le32(!!confirm_rx);','\thdr->confirm_rx = cpu_to_le32(!!confirm_rx);\n\twire_node = le32_to_cpu(hdr->dst_node_id);')
        s=s[:a]+c+s[b:]
    p.write_text(s);(ref/(n+'.after')).write_text(s)
    original=(out/(n+'-before.c')).read_text()
    (ref/(n+'.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/'+path,tofile='b/'+path)))
for n in ['target-build.log','kernel-build.log','kernel-validation.json']:
    p=out/n;t=out/(n+'.before-wire-node');assert p.exists() and not t.exists();p.rename(t)
print('ACTUAL_WIRE_DESTINATION_RECORDED_BEFORE_XMIT')
