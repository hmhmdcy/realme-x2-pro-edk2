from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';out=Path('/mnt/e/edk2-samurai-out/kernel107');prev=out.parent/'kernel106'
k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out/'preparation.json').exists()
baseline=(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert baseline[0]==(prev/'runtime-boot-id-after-private.txt').read_text().strip() and '#105 SMP PREEMPT' in baseline[1] and baseline[3]=='0' and baseline.count('running')==2
old=json.loads((prev/'kernel-validation.json').read_text());assert json.loads((prev/'public-docs-validation.json').read_text())['public_audit_pass']
for n,p,key in [('Image','arch/arm64/boot/Image','image_sha256'),('dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb_sha256'),('cpio','usr/initramfs_data.cpio','cpio_sha256')]:
    assert sha(k/p)==old[key];shutil.copyfile(k/p,out/(n+'-before'))
shutil.copyfile(k/'.config',out/'config-before')
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
(out/'initramfs-before.json').write_text(json.dumps({str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()},indent=2))
(out/'untracked-before.json').write_text(json.dumps({n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()},indent=2))

def edit(n,path,fn):
    before=(k/path).read_text();(out/(n+'-before.c')).write_text(before)
    after=fn(before);assert before!=after
    (k/path).write_text(after);(ref/(n+'.after')).write_text(after)
    (ref/(n+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path)))

def core(s):
    gate='''\tmutex_lock(&node->ep_lock);
\tif (!node->hello_sent && type != QRTR_TYPE_HELLO) {
\t\tmutex_unlock(&node->ep_lock);
\t\ttrace_qrtr_endpoint_tx(READ_ONCE(node->nid), wire_node, type,
\t\t\tfrom->sq_port, to->sq_port, len, -EAGAIN);
\t\tkfree_skb(skb);
\t\treturn -EAGAIN;
\t}
\tmutex_unlock(&node->ep_lock);

'''
    assert s.count(gate)==1;s=s.replace(gate,'')
    for old in [' * @hello_sent: hello packet send successful\n','\tbool hello_sent;\n\n','\t\tif (!rc && type == QRTR_TYPE_HELLO)\n\t\t\tnode->hello_sent = true;\n','\tnode->hello_sent = false;\n']:
        assert old in s;s=s.replace(old,'')
    # Keep the existing endpoint-registration and MHI-resume initiators/API.
    s=s.replace('\tmutex_lock(&node->ep_lock);\n\tmutex_unlock(&node->ep_lock);\n\n\tschedule_delayed_work(&node->say_hello, 0);','\tschedule_delayed_work(&node->say_hello, 0);')
    assert 'hello_sent' not in s and 'void qrtr_endpoint_hello(struct qrtr_endpoint *ep)' in s
    assert 'INIT_DELAYED_WORK(&node->say_hello, qrtr_hello_work)' in s and 'cancel_delayed_work_sync(&node->say_hello)' in s
    return s

def ns(s):
    old='''static int ctrl_cmd_hello(struct sockaddr_qrtr *sq)
{
\treturn announce_servers(sq);
}'''
    assert s.count(old)==1
    # Restore the upstream NS reply-before-advertise sequence. This uses the
    # normal QRTR control socket; no node ID, transport or service is special.
    new='''static int say_hello(struct sockaddr_qrtr *dest)
{
\tstruct qrtr_ctrl_pkt pkt = { };
\tstruct msghdr msg = { };
\tstruct kvec iv;
\tint ret;

\tiv.iov_base = &pkt;
\tiv.iov_len = sizeof(pkt);
\tpkt.cmd = cpu_to_le32(QRTR_TYPE_HELLO);
\tmsg.msg_name = (struct sockaddr *)dest;
\tmsg.msg_namelen = sizeof(*dest);
\tret = kernel_sendmsg(qrtr_ns.sock, &msg, &iv, 1, sizeof(pkt));
\tif (ret < 0)
\t\tpr_err("failed to send hello msg\\n");
\treturn ret;
}

static int ctrl_cmd_hello(struct sockaddr_qrtr *sq)
{
\tint ret;

\t/* A peer HELLO must not lose the one initial service announcement. */
\tret = say_hello(sq);
\tif (ret < 0)
\t\treturn ret;

\treturn announce_servers(sq);
}'''
    return s.replace(old,new)
edit('af_qrtr.c','net/qrtr/af_qrtr.c',core);edit('ns.c','net/qrtr/ns.c',ns)
(out/'preparation.json').write_text(json.dumps(dict(stage=107,kernel_build=106,source_scope=['net/qrtr/af_qrtr.c','net/qrtr/ns.c'],config_changed=False,endpoint_and_resume_hello_initiators_preserved=True,hello_first_reply_and_announcement_sequence_restored=True,destructive_hello_gate_removed=True,nv_partition_writes=False,goal_complete=False),indent=2)+'\n')
print('QRTR_NS_REPLY_SEQUENCE_PREPARED_ENDPOINT_AND_RESUME_INITIATORS_PRESERVED')
