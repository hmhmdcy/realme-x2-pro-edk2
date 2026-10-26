from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel105'
out = Path('/mnt/e/edk2-samurai-out/kernel105')
k = Path('/home/cy122/x2pro-linux/linux')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out / 'preparation.json').exists()
prev = out.parent / 'kernel104'
baseline = (out / 'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert baseline[0] == (prev / 'runtime-boot-id-after-private.txt').read_text().strip()
assert '#103 SMP PREEMPT' in baseline[1] and baseline[3] == '0'
assert baseline.count('running') == 2
old = json.loads((prev / 'kernel-validation.json').read_text())
for n, path, key in [('Image', 'arch/arm64/boot/Image', 'image_sha256'),
                     ('dtb', 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', 'dtb_sha256'),
                     ('cpio', 'usr/initramfs_data.cpio', 'cpio_sha256')]:
    assert sha(k / path) == old[key]
    shutil.copyfile(k / path, out / (n + '-before'))
shutil.copyfile(k / '.config', out / 'config-before')
(out / 'kernel-source-before.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=k))
init = k.parent / 'initramfs'
(out / 'initramfs-before.json').write_text(json.dumps({str(p.relative_to(init)): sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}, indent=2))
(out / 'untracked-before.json').write_text(json.dumps({n: sha(k / n) for n in subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=k, text=True).splitlines() if (k / n).is_file()}, indent=2))

def edit(name, path, transform):
    before = (k / path).read_text()
    (out / (name + '-before.c')).write_text(before)
    after = transform(before)
    assert after != before
    (k / path).write_text(after)
    (ref / (name + '.c.after')).write_text(after)
    (ref / (name + '.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='a/' + path, tofile='b/' + path)))

def apr(s):
    s = s.replace('#include <linux/rpmsg.h>', '#include <linux/rpmsg.h>\n#include <linux/srcu.h>')
    s = s.replace('\tstruct idr svcs_idr;', '\tstruct idr svcs_idr;\n\tstruct srcu_struct apr_srcu;')
    s = s.replace('struct apr_device *adev;\n\tstruct apr_driver *adrv = NULL;', 'struct apr_device *adev = NULL;\n\tstruct apr_driver *adrv = NULL;')
    start = s.index('static int apr_do_rx_callback(')
    end = s.index('\nstatic int gpr_do_rx_callback(', start)
    c = s[start:end].replace('int len = abuf->len;', 'int len = abuf->len;\n\tint idx;')
    c = c.replace('hdr->pkt_size < APR_HDR_SIZE || hdr->pkt_size != len', 'hdr->pkt_size < hdr_size || hdr->pkt_size != len')
    c = c.replace('\tsvc_id = hdr->dest_svc;', '\tidx = srcu_read_lock(&apr->apr_srcu);\n\tsvc_id = hdr->dest_svc;')
    c = c.replace('if (svc && svc->dev->driver)', 'if (svc && svc_to_apr_device(svc)->dev.driver)')
    c = c.replace('\t\treturn -EINVAL;\n\t}\n\n\tresp.hdr', '\t\tsrcu_read_unlock(&apr->apr_srcu, idx);\n\t\treturn -EINVAL;\n\t}\n\n\tresp.hdr')
    c = c.replace('\tadrv->callback(adev, &resp);', '\tif (adrv->callback)\n\t\tadrv->callback(adev, &resp);\n\tsrcu_read_unlock(&apr->apr_srcu, idx);')
    c = c.replace('struct apr_resp_pkt resp;', 'struct apr_resp_pkt resp = {};')
    s = s[:start] + c + s[end:]
    start = s.index('static int apr_device_probe(')
    end = s.index('\nstatic int apr_uevent(', start)
    s = s[:start] + '''/* Device creation and driver binding have separate lifetimes. */
static int apr_register_service(struct apr_device *adev)
{
\tstruct packet_router *apr = dev_get_drvdata(adev->dev.parent);
\tstruct pkt_router_svc *old;
\tunsigned long flags;
\tint ret = 0;

\tspin_lock_irqsave(&apr->svcs_lock, flags);
\told = idr_find(&apr->svcs_idr, adev->svc.id);
\tif (old && old != &adev->svc)
\t\tret = -EEXIST;
\telse if (!old)
\t\tret = idr_alloc(&apr->svcs_idr, &adev->svc, adev->svc.id,
\t\t\t\tadev->svc.id + 1, GFP_ATOMIC);
\tspin_unlock_irqrestore(&apr->svcs_lock, flags);
\treturn ret < 0 ? ret : 0;
}

static void apr_unregister_service(struct apr_device *adev)
{
\tstruct packet_router *apr = dev_get_drvdata(adev->dev.parent);
\tunsigned long flags;

\tspin_lock_irqsave(&apr->svcs_lock, flags);
\tif (idr_find(&apr->svcs_idr, adev->svc.id) == &adev->svc)
\t\tidr_remove(&apr->svcs_idr, adev->svc.id);
\tspin_unlock_irqrestore(&apr->svcs_lock, flags);
\t/* APR callbacks execute in a workqueue and may sleep. */
\tif (apr->type == PR_TYPE_APR)
\t\tsynchronize_srcu(&apr->apr_srcu);
}

static int apr_device_probe(struct device *dev)
{
\tstruct apr_device *adev = to_apr_device(dev);
\tstruct apr_driver *adrv = to_apr_driver(dev->driver);
\tint ret;

\tret = apr_register_service(adev);
\tif (ret)
\t\treturn ret;
\tret = adrv->probe(adev);
\tif (ret) {
\t\tapr_unregister_service(adev);
\t\treturn ret;
\t}
\tadev->svc.callback = adrv->gpr_callback;
\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_info(dev, "samurai APR service registered id=%u domain=%u\\n",
\t\t\t adev->svc.id, adev->domain_id);
\treturn 0;
}

static void apr_device_remove(struct device *dev)
{
\tstruct apr_device *adev = to_apr_device(dev);
\tstruct apr_driver *adrv = to_apr_driver(dev->driver);

\t/* Remove the dispatch entry and drain existing APR callbacks first. */
\tapr_unregister_service(adev);
\tadev->svc.callback = NULL;
\tif (adrv->remove)
\t\tadrv->remove(adev);
}
''' + s[end:]
    # A service points at the child device, not its router's driver.
    s = s.replace('\tsvc->dev = dev;\n\tspin_lock_init(&svc->lock);\n\n\tadev->domain_id', '\tsvc->dev = &adev->dev;\n\tspin_lock_init(&svc->lock);\n\n\tadev->domain_id')
    # Register at driver probe, rather than once at device creation.
    a = s.index('\tspin_lock(&apr->svcs_lock);', s.index('static int apr_add_device('))
    b = s.index('\n\t/* Protection domain', a)
    s = s[:a] + s[b:]
    s = s.replace('\tINIT_LIST_HEAD(&apr->rx_list);', '\tret = init_srcu_struct(&apr->apr_srcu);\n\tif (ret)\n\t\tgoto handle_release;\n\n\tINIT_LIST_HEAD(&apr->rx_list);')
    s = s.replace('if (ret)\n\t\tgoto handle_release;\n\n\tof_register_apr_devices', 'if (ret)\n\t\tgoto cleanup_srcu;\n\n\tof_register_apr_devices')
    s = s.replace('\nhandle_release:\n', '\ncleanup_srcu:\n\tcleanup_srcu_struct(&apr->apr_srcu);\nhandle_release:\n')
    s = s.replace('\tdestroy_workqueue(apr->rxwq);\n}\n\n/*', '\tdestroy_workqueue(apr->rxwq);\n\tcleanup_srcu_struct(&apr->apr_srcu);\n\tidr_destroy(&apr->svcs_idr);\n}\n\n/*')
    # Property failures occur before device_register: reclaim their service.
    needle = 'dev_err(dev, "Failed to read second value of qcom,protection-domain\\n");\n\t\tgoto out;'
    assert needle in s
    s = s.replace(needle, 'dev_err(dev, "Failed to read second value of qcom,protection-domain\\n");\n\t\tkfree_const(adev->dev.kobj.name);\n\t\tkfree(adev);\n\t\tgoto out;')
    return s

def core(s):
    s = s.replace('#include <linux/wait.h>', '#include <linux/wait.h>\n#include <linux/completion.h>\n#include <linux/delay.h>')
    s = s.replace('\tbool resp_received;', '\tstruct completion response;\n\tspinlock_t response_lock;\n\tu32 pending_command;\n\tu32 token;\n\tint response_error;')
    start = s.index('static int q6core_callback(')
    end = s.index('\n/**\n * q6core_get_svc_api_info', start)
    s = s[:start] + '''/* Only the matching transaction may complete a synchronous query. */
static int q6core_callback(struct apr_device *adev, const struct apr_resp_pkt *data)
{
\tstruct q6core *core = dev_get_drvdata(&adev->dev);
\tconst struct apr_hdr *hdr = &data->hdr;
\tconst struct aprv2_ibasic_rsp_result_t *result = data->payload;
\tunsigned long flags;
\tu32 command;
\tint ret = 0;

\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_info_ratelimited(&adev->dev,
\t\t\t"samurai core reply opcode=%#x bytes=%d token=%#x domain=%u/%u service=%u/%u ports=%u/%u\\n",
\t\t\thdr->opcode, data->payload_size, hdr->token,
\t\t\thdr->src_domain, hdr->dest_domain, hdr->src_svc,
\t\t\thdr->dest_svc, hdr->src_port, hdr->dest_port);
\tswitch (hdr->opcode) {
\tcase APR_BASIC_RSP_RESULT:
\t\tif (data->payload_size < sizeof(*result))
\t\t\treturn -EINVAL;
\t\tcommand = result->opcode;
\t\tif (of_machine_is_compatible("realme,samurai"))
\t\t\tdev_info_ratelimited(&adev->dev,
\t\t\t\t"samurai core basic command=%#x status=%u\\n",
\t\t\t\tcommand, result->status);
\t\tbreak;
\tcase AVCS_CMDRSP_GET_FWK_VERSION:
\t\tcommand = AVCS_CMD_GET_FWK_VERSION;
\t\tbreak;
\tcase AVCS_GET_VERSIONS_RSP:
\t\tcommand = AVCS_GET_VERSIONS;
\t\tbreak;
\tcase AVCS_CMDRSP_ADSP_EVENT_GET_STATE:
\t\tcommand = AVCS_CMD_ADSP_EVENT_GET_STATE;
\t\tbreak;
\tdefault:
\t\treturn -EINVAL;
\t}

\tspin_lock_irqsave(&core->response_lock, flags);
\tif (command != core->pending_command || hdr->token != core->token) {
\t\tspin_unlock_irqrestore(&core->response_lock, flags);
\t\treturn -EINVAL;
\t}
\tswitch (hdr->opcode) {
\tcase APR_BASIC_RSP_RESULT:
\t\t/* A successful basic acknowledgement is not a version/state reply. */
\t\tif (result->status == ADSP_EOK) {
\t\t\tspin_unlock_irqrestore(&core->response_lock, flags);
\t\t\treturn 0;
\t\t}
\t\tret = result->status == ADSP_EUNSUPPORTED ? -ENOTSUPP : -EIO;
\t\tbreak;
\tcase AVCS_CMDRSP_GET_FWK_VERSION: {
\t\tconst struct avcs_cmdrsp_get_fwk_version *v = data->payload;
\t\tstruct avcs_cmdrsp_get_fwk_version *copy;

\t\tif (data->payload_size < sizeof(*v) || !v->num_services ||
\t\t    v->num_services > (data->payload_size - sizeof(*v)) /
\t\t\t\t      sizeof(v->svc_api_info[0])) {
\t\t\tret = -EBADMSG;
\t\t\tbreak;
\t\t}
\t\tcopy = kmemdup(v, struct_size(v, svc_api_info, v->num_services),
\t\t\t       GFP_ATOMIC);
\t\tif (!copy) {
\t\t\tret = -ENOMEM;
\t\t\tbreak;
\t\t}
\t\tkfree(core->fwk_version);
\t\tcore->fwk_version = copy;
\t\tcore->fwk_version_supported = true;
\t\tbreak;
\t}
\tcase AVCS_GET_VERSIONS_RSP: {
\t\tconst struct avcs_cmdrsp_get_version *v = data->payload;
\t\tstruct avcs_cmdrsp_get_version *copy;

\t\tif (data->payload_size < sizeof(*v) || !v->num_services ||
\t\t    v->num_services > (data->payload_size - sizeof(*v)) /
\t\t\t\t      sizeof(v->svc_api_info[0])) {
\t\t\tret = -EBADMSG;
\t\t\tbreak;
\t\t}
\t\tcopy = kmemdup(v, struct_size(v, svc_api_info, v->num_services),
\t\t\t       GFP_ATOMIC);
\t\tif (!copy) {
\t\t\tret = -ENOMEM;
\t\t\tbreak;
\t\t}
\t\tkfree(core->svc_version);
\t\tcore->svc_version = copy;
\t\tcore->get_version_supported = true;
\t\tbreak;
\t}
\tcase AVCS_CMDRSP_ADSP_EVENT_GET_STATE:
\t\tif (data->payload_size < sizeof(u32)) {
\t\t\tret = -EBADMSG;
\t\t\tbreak;
\t\t}
\t\tcore->get_state_supported = true;
\t\tcore->avcs_state = *(const u32 *)data->payload;
\t\tbreak;
\t}
\tcore->response_error = ret;
\tcore->pending_command = 0;
\tcomplete(&core->response);
\tspin_unlock_irqrestore(&core->response_lock, flags);
\treturn ret;
}

/* The caller holds core->lock. Tokens separate late and new replies. */
static int q6core_query(struct q6core *core, u32 command)
{
\tstruct apr_device *adev = core->adev;
\tstruct apr_pkt pkt = {};
\tunsigned long flags;
\tint ret;

\tspin_lock_irqsave(&core->response_lock, flags);
\treinit_completion(&core->response);
\tcore->pending_command = command;
\tcore->response_error = -ETIMEDOUT;
\tif (!++core->token)
\t\t++core->token;
\tpkt.hdr.token = core->token;
\tspin_unlock_irqrestore(&core->response_lock, flags);
\tpkt.hdr.hdr_field = APR_HDR_FIELD(APR_MSG_TYPE_SEQ_CMD,
\t\t\t\t      APR_HDR_LEN(APR_HDR_SIZE), APR_PKT_VER);
\tpkt.hdr.pkt_size = APR_HDR_SIZE;
\tpkt.hdr.opcode = command;
\tret = apr_send_pkt(adev, &pkt);
\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_info_ratelimited(&adev->dev,
\t\t\t"samurai core send opcode=%#x rc=%d token=%#x\\n",
\t\t\tcommand, ret, pkt.hdr.token);
\tif (ret >= 0) {
\t\tif (wait_for_completion_timeout(&core->response,
\t\t\t\tmsecs_to_jiffies(Q6_READY_TIMEOUT_MS)))
\t\t\tret = READ_ONCE(core->response_error);
\t\telse
\t\t\tret = -ETIMEDOUT;
\t}
\tspin_lock_irqsave(&core->response_lock, flags);
\tcore->pending_command = 0;
\tspin_unlock_irqrestore(&core->response_lock, flags);
\treturn ret;
}

static int q6core_get_fwk_versions(struct q6core *core)
{
\treturn q6core_query(core, AVCS_CMD_GET_FWK_VERSION);
}

static int q6core_get_svc_versions(struct q6core *core)
{
\treturn q6core_query(core, AVCS_GET_VERSIONS);
}

static bool __q6core_is_adsp_ready(struct q6core *core)
{
\tint ret = q6core_query(core, AVCS_CMD_ADSP_EVENT_GET_STATE);

\t/* Only an explicit unsupported response permits the legacy assumption. */
\treturn ret == -ENOTSUPP || (!ret && core->avcs_state);
}
''' + s[end:]
    s = s.replace('if (!g_core || !ainfo)\n\t\treturn 0;', 'if (!ainfo)\n\t\treturn -EINVAL;\n\tif (!g_core)\n\t\treturn -EPROBE_DEFER;')
    old = '''\t\tif (q6core_get_fwk_versions(g_core) == -ENOTSUPP)
\t\t\tq6core_get_svc_versions(g_core);
\t\tg_core->is_version_requested = true;'''
    assert old in s
    s = s.replace(old, '''\t\tret = q6core_get_fwk_versions(g_core);
\t\tif (ret == -ENOTSUPP)
\t\t\tret = q6core_get_svc_versions(g_core);
\t\tif (ret) {
\t\t\tmutex_unlock(&g_core->lock);
\t\t\treturn ret;
\t\t}
\t\tg_core->is_version_requested = true;''')
    # Valid version replies may omit a requested service.
    s = s.replace('\n\tif (g_core->fwk_version_supported) {', '\n\tret = -ENOTSUPP;\n\tif (g_core->fwk_version_supported) {', 1)
    s = s.replace('\t\tif (!time_after(timeout, jiffies)) {', '\t\tmsleep(20);\n\t\tif (!time_after(timeout, jiffies)) {')
    s = s.replace('\tinit_waitqueue_head(&g_core->wait);', '\tinit_waitqueue_head(&g_core->wait);\n\tinit_completion(&g_core->response);\n\tspin_lock_init(&g_core->response_lock);')
    return s

def q6v5(s):
    s = s.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/of.h>')
    start = s.index('static irqreturn_t q6v5_wdog_interrupt(')
    helper = '''/* Read-only diagnostics at a real IRQ; never request a DSP crash. */
static void q6v5_report_reason(struct qcom_q6v5 *q6v5, const char *event)
{
\tsize_t len = 0, text_len = 0;
\tconst char *msg;

\tmsg = qcom_smem_get(QCOM_SMEM_HOST_ANY, q6v5->crash_reason, &len);
\tif (!IS_ERR(msg) && len)
\t\ttext_len = strnlen(msg, min_t(size_t, len, 4096));
\tif (of_machine_is_compatible("realme,samurai"))
\t\tdev_err(q6v5->dev,
\t\t\t"samurai crash SMEM event=%s item=%d error=%ld bytes=%zu first=%u text=%zu running=%u handover=%u\\n",
\t\t\tevent, q6v5->crash_reason, IS_ERR(msg) ? PTR_ERR(msg) : 0,
\t\t\tlen, !IS_ERR(msg) && len ? (unsigned char)msg[0] : 0,
\t\t\ttext_len, q6v5->running, q6v5->handover_issued);
\tif (text_len)
\t\tdev_err(q6v5->dev, "%s received: %.*s\\n", event,
\t\t\t(int)text_len, msg);
\telse
\t\tdev_err(q6v5->dev, "%s without message\\n", event);
}

'''
    s = s[:start] + helper + s[start:]
    for event, fun in [('watchdog', 'wdog'), ('fatal error', 'fatal')]:
        start = s.index('static irqreturn_t q6v5_' + fun + '_interrupt(')
        end = s.index('\nstatic irqreturn_t ', start + 10)
        c = s[start:end].replace('\tsize_t len;\n\tchar *msg;\n', '')
        a = c.index('\tmsg = qcom_smem_get(')
        b = c.index('\n\tq6v5->running = false;', a)
        c = c[:a] + '\tq6v5_report_reason(q6v5, "' + event + '");\n' + c[b:]
        s = s[:start] + c + s[end:]
    for fun, tag in [('ready', 'ready'), ('handover', 'handover')]:
        start = s.index('static irqreturn_t q6v5_' + fun + '_interrupt(')
        end = s.index('\n}', start)
        c = s[start:end]
        needle = '\tstruct qcom_q6v5 *q6v5 = data;'
        assert needle in c
        c = c.replace(needle, needle + '\n\n\tif (of_machine_is_compatible("realme,samurai"))\n\t\tdev_info(q6v5->dev, "samurai Q6 ' + tag + ' item=%d running=%u\\n",\n\t\t\t q6v5->crash_reason, q6v5->running);')
        s = s[:start] + c + s[end:]
    return s

edit('apr', 'drivers/soc/qcom/apr.c', apr)
edit('q6v5', 'drivers/remoteproc/qcom_q6v5.c', q6v5)
edit('q6core', 'sound/soc/qcom/qdsp6/q6core.c', core)
(out / 'preparation.json').write_text(json.dumps(dict(stage=105, kernel_build=104, source_prepared=True, source_scope=['drivers/soc/qcom/apr.c', 'drivers/remoteproc/qcom_q6v5.c', 'sound/soc/qcom/qdsp6/q6core.c'], dtb_mutated=False, initramfs_mutated=False, nv_mutated=False, goal_complete=False), indent=2))
print('STAGE105_APR_LIFECYCLE_AND_READONLY_CRASH_DIAGNOSTICS_PREPARED')
