from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';out=Path('/mnt/e/edk2-samurai-out/kernel106')
k=Path('/home/cy122/x2pro-linux/linux');prev=out.parent/'kernel105'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out/'preparation.json').exists()
baseline=(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert baseline[0]==(prev/'runtime-boot-id-after-private.txt').read_text().strip()
assert '#104 SMP PREEMPT' in baseline[1] and baseline[3]=='0' and baseline.count('running')==2
old=json.loads((prev/'kernel-validation.json').read_text())
for n,p,key in [('Image','arch/arm64/boot/Image','image_sha256'),('dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb_sha256'),('cpio','usr/initramfs_data.cpio','cpio_sha256')]:
    assert sha(k/p)==old[key];shutil.copyfile(k/p,out/(n+'-before'))
shutil.copyfile(k/'.config',out/'config-before')
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
init=k.parent/'initramfs'
(out/'initramfs-before.json').write_text(json.dumps({str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()},indent=2))
(out/'untracked-before.json').write_text(json.dumps({n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()},indent=2))

def edit(n,path,fn):
    before=(k/path).read_text();(out/(n+'-before.c')).write_text(before)
    after=fn(before);assert before!=after
    (k/path).write_text(after);(ref/(n+'.after')).write_text(after)
    (ref/(n+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path)))

def smd(s):
    s=s.replace('#include <linux/rpmsg.h>','#include <linux/rpmsg.h>\n#include <linux/of.h>\n#include <trace/events/samurai_diag.h>')
    s=s.replace('if (!qdev)\n\t\treturn -EAGAIN;', '''if (!qdev || !READ_ONCE(qdev->ep.node)) {
\t\tif (of_machine_is_compatible("realme,samurai"))
\t\t\ttrace_samurai_qrtr_rx_drop(len, !!qdev,
\t\t\t\tqdev && !!READ_ONCE(qdev->ep.node));
\t\treturn -EAGAIN;
\t}''')
    needle='''\trc = qrtr_endpoint_register(&qdev->ep, QRTR_EP_NID_AUTO);
\tif (rc)
\t\treturn rc;

\tdev_set_drvdata(&rpdev->dev, qdev);'''
    assert needle in s
    s=s.replace(needle,'''\t/* Registration schedules HELLO; its reply may arrive immediately. */
\tdev_set_drvdata(&rpdev->dev, qdev);
\trc = qrtr_endpoint_register(&qdev->ep, QRTR_EP_NID_AUTO);
\tif (rc) {
\t\tdev_set_drvdata(&rpdev->dev, NULL);
\t\treturn rc;
\t}''')
    return s

def core(s):
    s=s.replace('#include "q6core.h"','#include "q6core.h"\n#include <trace/events/samurai_diag.h>')
    a=s.index('\tif (of_machine_is_compatible("realme,samurai"))',s.index('static int q6core_callback('))
    b=s.index('\tswitch (hdr->opcode)',a)
    s=s[:a]+s[b:]
    needle='''\t\tif (of_machine_is_compatible("realme,samurai"))
\t\t\tdev_info_ratelimited(&adev->dev,
\t\t\t\t"samurai core basic command=%#x status=%u\\n",
\t\t\t\tcommand, result->status);
'''
    assert needle in s;s=s.replace(needle,'')
    needle='\tspin_unlock_irqrestore(&core->response_lock, flags);\n\treturn ret;\n}\n\n/* The caller'
    assert needle in s
    s=s.replace(needle,'''\tspin_unlock_irqrestore(&core->response_lock, flags);
\tif (of_machine_is_compatible("realme,samurai"))
\t\ttrace_samurai_core_transaction(1, command, hdr->token,
\t\t\thdr->opcode, data->payload_size,
\t\t\thdr->opcode == APR_BASIC_RSP_RESULT ? result->status : 0,
\t\t\tret);
\treturn ret;
}

/* The caller''')
    a=s.index('\tif (of_machine_is_compatible("realme,samurai"))',s.index('static int q6core_query('))
    b=s.index('\tif (ret >= 0)',a)
    s=s[:a]+s[b:]
    needle='\tcore->pending_command = 0;\n\tspin_unlock_irqrestore(&core->response_lock, flags);\n\treturn ret;'
    assert s.count(needle)==1
    s=s.replace(needle,'''\tcore->pending_command = 0;
\tspin_unlock_irqrestore(&core->response_lock, flags);
\tif (of_machine_is_compatible("realme,samurai"))
\t\ttrace_samurai_core_transaction(2, command, pkt.hdr.token,
\t\t\t0, 0, 0, ret);
\treturn ret;''')
    assert 'dev_info_ratelimited' not in s and '#define Q6_READY_TIMEOUT_MS 100' in s
    return s

def pdm(s):
    s=s.replace('#include "pdr_internal.h"','#include "pdr_internal.h"\n\n#define CREATE_TRACE_POINTS\n#include <trace/events/samurai_diag.h>')
    needle='\tmutex_unlock(&qcom_pdm_mutex);\n\n\tkfree(rsp);'
    assert s.count(needle)==1
    s=s.replace(needle,'''\tmutex_unlock(&qcom_pdm_mutex);
\tif (of_machine_is_compatible("realme,samurai"))
\t\ttrace_samurai_pdm_response(sq->sq_node, sq->sq_port,
\t\t\treq->service_name, offset, rsp->total_domains,
\t\t\trsp->domain_list_len, ret);
\tkfree(rsp);''')
    return s

def qrtr_header(s):
    needle='#endif /* _TRACE_QRTR_H */';assert s.count(needle)==1
    event='''TRACE_EVENT(qrtr_endpoint_tx,
\tTP_PROTO(unsigned int node, int type, unsigned int src_port,
\t\t unsigned int dst_port, unsigned int bytes, int result),
\tTP_ARGS(node, type, src_port, dst_port, bytes, result),
\tTP_STRUCT__entry(
\t\t__field(unsigned int, node)
\t\t__field(int, type)
\t\t__field(unsigned int, src_port)
\t\t__field(unsigned int, dst_port)
\t\t__field(unsigned int, bytes)
\t\t__field(int, result)
\t),
\tTP_fast_assign(
\t\t__entry->node = node; __entry->type = type;
\t\t__entry->src_port = src_port; __entry->dst_port = dst_port;
\t\t__entry->bytes = bytes; __entry->result = result;
\t),
\tTP_printk("node=%u type=%d src_port=%u dst_port=%u bytes=%u result=%d",
\t\t  __entry->node, __entry->type, __entry->src_port,
\t\t  __entry->dst_port, __entry->bytes, __entry->result)
);

'''
    return s.replace(needle,event+needle)

def qrtr_core(s):
    s=s.replace('#include "qrtr.h"','#include "qrtr.h"\n#include <trace/events/qrtr.h>')
    needle='\t\tmutex_unlock(&node->ep_lock);\n\t\tkfree_skb(skb);\n\t\treturn -EAGAIN;'
    assert s.count(needle)==1
    s=s.replace(needle,'''\t\tmutex_unlock(&node->ep_lock);
\t\ttrace_qrtr_endpoint_tx(READ_ONCE(node->nid), type,
\t\t\tfrom->sq_port, to->sq_port, len, -EAGAIN);
\t\tkfree_skb(skb);
\t\treturn -EAGAIN;''')
    needle='\tif (rc == -EAGAIN && type == QRTR_TYPE_HELLO)'
    assert s.count(needle)==1
    return s.replace(needle,'''\ttrace_qrtr_endpoint_tx(READ_ONCE(node->nid), type,
\t\tfrom->sq_port, to->sq_port, len, rc);

'''+needle)

header=k/'include/trace/events/samurai_diag.h';assert not header.exists()
shutil.copyfile(ref/'samurai-diag.h',header)
edit('smd.c','net/qrtr/smd.c',smd)
edit('q6core.c','sound/soc/qcom/qdsp6/q6core.c',core)
edit('qcom_pd_mapper.c','drivers/soc/qcom/qcom_pd_mapper.c',pdm)
edit('qrtr.h','include/trace/events/qrtr.h',qrtr_header)
edit('af_qrtr.c','net/qrtr/af_qrtr.c',qrtr_core)
display=Path('/mnt/e/edk2-samurai-out/kernel84/display-bootconfig-ready.txt').read_text()
boot=display+'''\nftrace.instance.radio {
    trace_clock = mono
    buffer_size = 1MB
    tracing_on = 1
    events = "qrtr:*", "qcom_glink:*", "samurai_diag:*"
}
'''
(ref/'bootconfig.txt').write_text(boot)
(out/'radio-bootconfig.txt').write_text(boot)
s=(k/'.config').read_text();needle='CONFIG_BOOT_CONFIG_EMBED_FILE="/mnt/e/edk2-samurai-out/kernel84/display-bootconfig-ready.txt"'
assert s.count(needle)==1
s=s.replace(needle,'CONFIG_BOOT_CONFIG_EMBED_FILE="/mnt/e/edk2-samurai-out/kernel106/radio-bootconfig.txt"')
(k/'.config').write_text(s)
(out/'preparation.json').write_text(json.dumps(dict(stage=106,kernel_build=105,source_scope=['net/qrtr/smd.c','sound/soc/qcom/qdsp6/q6core.c','drivers/soc/qcom/qcom_pd_mapper.c','include/trace/events/qrtr.h','net/qrtr/af_qrtr.c'],new_source='include/trace/events/samurai_diag.h',config_keys=['CONFIG_BOOT_CONFIG_EMBED_FILE'],dtb_mutated=False,initramfs_mutated=False,nv_mutated=False,goal_complete=False),indent=2))
print('STAGE106_QRTR_PROBE_ORDER_AND_RING_DIAGNOSTICS_PREPARED')
