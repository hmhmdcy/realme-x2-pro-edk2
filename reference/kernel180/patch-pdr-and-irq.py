#!/usr/bin/env python3
"""Apply the PDR lifetime/epoch fix and early WCD parent-IRQ shutdown once."""
from pathlib import Path
import difflib
import hashlib
import json
import re

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel180')
out.mkdir(parents=True, exist_ok=True)
paths = {
    'drivers/soc/qcom/pdr_interface.c': 'da13d7f202fbfe201b56d2a05fe6987e818110042485332da4808751d6e8c813',
    'drivers/mfd/wcd934x.c': 'b858f4d42504f1c548706566ae0fb6ac6d04b9bb1701a8be1f72b7ac6aaa3921',
}
sources = {}
for name, digest in paths.items():
    data = (root / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, name
    backup = out / (Path(name).name + '.before-private')
    assert not backup.exists(), backup
    backup.write_bytes(data)
    sources[name] = data.decode()


def replace_function(source, name, body):
    match = re.search(r'^(?:static )?(?:int|void) ' + name + r'\(', source, re.M)
    assert match, name
    start = source.index('{', match.start())
    depth, end = 1, start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[:match.start()] + body.strip() + source[end:]


s = sources['drivers/soc/qcom/pdr_interface.c']
s = s.replace('\tbool service_connected;\n', '''\tbool service_connected;
\tbool lookup_failed;
\tu64 server_generation;
\tu64 state_sequence;
\tu64 locator_attempt;
''', 1)
s = s.replace('\tstruct list_head lookups;\n', '\tstruct list_head lookups;\n\tstruct list_head retired;\n', 1)
s = s.replace('\tbool locator_init_complete;\n', '''\tbool locator_init_complete;
\tbool stopping;
\tu64 locator_generation;
\tu64 locator_run;
''', 1)
s = s.replace('\tstruct pdr_service *pds;\n\tstruct list_head node;\n', '''\tstruct pdr_service *pds;
\tstruct sockaddr_qrtr addr;
\tu64 server_generation;
\tstruct list_head node;
''', 1)

s = replace_function(s, 'pdr_locator_new_server', r'''
static int pdr_locator_new_server(struct qmi_handle *qmi,
                                  struct qmi_service *svc)
{
	struct pdr_handle *pdr = container_of(qmi, struct pdr_handle, locator_hdl);

	mutex_lock(&pdr->lock);
	if (READ_ONCE(pdr->stopping)) {
		mutex_unlock(&pdr->lock);
		return -ESHUTDOWN;
	}
	pdr->locator_addr.sq_family = AF_QIPCRTR;
	pdr->locator_addr.sq_node = svc->node;
	pdr->locator_addr.sq_port = svc->port;
	pdr->locator_generation++;
	pdr->locator_init_complete = true;
	schedule_work(&pdr->locator_work);
	mutex_unlock(&pdr->lock);

	return 0;
}
''')
s = replace_function(s, 'pdr_locator_del_server', r'''
static void pdr_locator_del_server(struct qmi_handle *qmi,
                                   struct qmi_service *svc)
{
	struct pdr_handle *pdr = container_of(qmi, struct pdr_handle, locator_hdl);

	mutex_lock(&pdr->lock);
	if (!READ_ONCE(pdr->stopping) && pdr->locator_init_complete &&
	    pdr->locator_addr.sq_node == svc->node &&
	    pdr->locator_addr.sq_port == svc->port) {
		pdr->locator_init_complete = false;
		pdr->locator_generation++;
		pdr->locator_addr.sq_node = 0;
		pdr->locator_addr.sq_port = 0;
	}
	mutex_unlock(&pdr->lock);
}
''')
s = replace_function(s, 'pdr_register_listener', r'''
static int pdr_register_listener(struct pdr_handle *pdr, const char *service_path,
				 struct sockaddr_qrtr *addr, bool enable, int *state)
{
	struct servreg_register_listener_resp resp = { };
	struct servreg_register_listener_req req;
	struct qmi_txn txn;
	int ret;

	ret = qmi_txn_init(&pdr->notifier_hdl, &txn,
			   servreg_register_listener_resp_ei, &resp);
	if (ret < 0)
		return ret;

	req.enable = enable;
	strscpy(req.service_path, service_path, sizeof(req.service_path));
	ret = qmi_send_request(&pdr->notifier_hdl, addr, &txn,
			       SERVREG_REGISTER_LISTENER_REQ,
			       SERVREG_REGISTER_LISTENER_REQ_LEN,
			       servreg_register_listener_req_ei, &req);
	if (ret < 0) {
		qmi_txn_cancel(&txn);
		return ret;
	}

	ret = qmi_txn_wait(&txn, 5 * HZ);
	if (ret < 0) {
		pr_err("PDR: %s register listener txn wait failed: %d\n",
		       service_path, ret);
		return ret;
	}
	if (resp.resp.result != QMI_RESULT_SUCCESS_V01) {
		pr_err("PDR: %s register listener failed: 0x%x\n",
		       service_path, resp.resp.error);
		return -EREMOTEIO;
	}
	if (!resp.curr_state_valid) {
		pr_err("PDR: %s register listener response has no state\n", service_path);
		return -EPROTO;
	}
	*state = resp.curr_state;
	return 0;
}

/* status_lock orders callbacks; list_lock is never held across client code. */
static bool pdr_notify_pending_down(struct pdr_handle *pdr, struct pdr_service *pds)
{
	bool notify;

	lockdep_assert_held(&pdr->status_lock);
	mutex_lock(&pdr->list_lock);
	notify = !pdr->stopping && !pds->lookup_failed && pds->need_notifier_remove;
	if (notify) {
		pds->need_notifier_remove = false;
		pds->state = SERVREG_SERVICE_STATE_DOWN;
	}
	mutex_unlock(&pdr->list_lock);
	if (notify)
		pdr->status(SERVREG_SERVICE_STATE_DOWN, pds->service_path, pdr->priv);
	return notify;
}

static void pdr_publish_registration(struct pdr_handle *pdr, struct pdr_service *pds,
				     u64 generation, u64 sequence, int state)
{
	bool notify;

	mutex_lock(&pdr->status_lock);
	/* A coalesced DEL/NEW must release the old client's resources first. */
	while (pdr_notify_pending_down(pdr, pds))
		;
	mutex_lock(&pdr->list_lock);
	notify = !pdr->stopping && !pds->lookup_failed && pds->service_connected &&
		 pds->server_generation == generation && pds->state_sequence == sequence;
	if (notify)
		pds->state = state;
	mutex_unlock(&pdr->list_lock);
	if (notify)
		pdr->status(state, pds->service_path, pdr->priv);
	mutex_unlock(&pdr->status_lock);
}
''')
s = replace_function(s, 'pdr_notifier_work', r'''
static void pdr_notifier_work(struct work_struct *work)
{
	struct pdr_handle *pdr = container_of(work, struct pdr_handle, notifier_work);
	struct pdr_service *pds, *iter;
	struct sockaddr_qrtr addr;
	u64 generation, sequence;
	bool remove;
	int ret, state;

	for (;;) {
		pds = NULL;
		mutex_lock(&pdr->status_lock);
		mutex_lock(&pdr->list_lock);
		if (!pdr->stopping) {
			list_for_each_entry(iter, &pdr->lookups, node) {
				if (iter->need_notifier_remove ||
				    (iter->service_connected && iter->need_notifier_register)) {
					pds = iter;
					break;
				}
			}
		}
		if (!pds) {
			mutex_unlock(&pdr->list_lock);
			mutex_unlock(&pdr->status_lock);
			return;
		}
		remove = pds->need_notifier_remove;
		if (remove) {
			pds->need_notifier_remove = false;
			pds->state = SERVREG_SERVICE_STATE_DOWN;
		} else {
			pds->need_notifier_register = false;
			addr = pds->addr;
			generation = pds->server_generation;
			sequence = pds->state_sequence;
		}
		mutex_unlock(&pdr->list_lock);
		if (remove)
			pdr->status(SERVREG_SERVICE_STATE_DOWN, pds->service_path, pdr->priv);
		mutex_unlock(&pdr->status_lock);
		if (remove)
			continue;

		/* RX control/indication callbacks must run while this transaction waits. */
		ret = pdr_register_listener(pdr, pds->service_path, &addr, true, &state);
		if (ret < 0)
			state = SERVREG_SERVICE_STATE_DOWN;
		pdr_publish_registration(pdr, pds, generation, sequence, state);
	}
}
''')
s = replace_function(s, 'pdr_notifier_new_server', r'''
static int pdr_notifier_new_server(struct qmi_handle *qmi,
                                   struct qmi_service *svc)
{
	struct pdr_handle *pdr = container_of(qmi, struct pdr_handle, notifier_hdl);
	struct pdr_service *pds;

	mutex_lock(&pdr->list_lock);
	if (pdr->stopping) {
		mutex_unlock(&pdr->list_lock);
		return -ESHUTDOWN;
	}
	list_for_each_entry(pds, &pdr->lookups, node) {
		if (pds->service != svc->service || pds->instance != svc->instance)
			continue;
		if (pds->service_connected && pds->addr.sq_node == svc->node &&
		    pds->addr.sq_port == svc->port)
			continue;
		if (pds->service_connected)
			pds->need_notifier_remove = true;
		pds->server_generation++;
		pds->state_sequence++;
		pds->service_connected = true;
		pds->need_notifier_register = true;
		pds->addr.sq_family = AF_QIPCRTR;
		pds->addr.sq_node = svc->node;
		pds->addr.sq_port = svc->port;
		queue_work(pdr->notifier_wq, &pdr->notifier_work);
		if (pds->need_notifier_remove)
			queue_work(pdr->indack_wq, &pdr->indack_work);
	}
	mutex_unlock(&pdr->list_lock);
	return 0;
}
''')
s = replace_function(s, 'pdr_notifier_del_server', r'''
static void pdr_notifier_del_server(struct qmi_handle *qmi,
                                    struct qmi_service *svc)
{
	struct pdr_handle *pdr = container_of(qmi, struct pdr_handle, notifier_hdl);
	struct pdr_service *pds;

	mutex_lock(&pdr->list_lock);
	if (!pdr->stopping) {
		list_for_each_entry(pds, &pdr->lookups, node) {
			if (pds->service != svc->service || pds->instance != svc->instance ||
			    !pds->service_connected || pds->addr.sq_node != svc->node ||
			    pds->addr.sq_port != svc->port)
				continue;
			pds->server_generation++;
			pds->state_sequence++;
			pds->service_connected = false;
			pds->need_notifier_register = false;
			pds->need_notifier_remove = true;
			pds->addr.sq_node = 0;
			pds->addr.sq_port = 0;
			queue_work(pdr->notifier_wq, &pdr->notifier_work);
			queue_work(pdr->indack_wq, &pdr->indack_work);
		}
	}
	mutex_unlock(&pdr->list_lock);
}
''')
s = s.replace('static int pdr_send_indack_msg(struct pdr_handle *pdr, struct pdr_service *pds,\n\t\t\t       u16 tid)',
              'static int pdr_send_indack_msg(struct pdr_handle *pdr, struct pdr_service *pds,\n\t\t\t       struct sockaddr_qrtr *addr, u16 tid)')
# Only the acknowledgement function still used this old mutable-address call.
s = s.replace('qmi_send_request(&pdr->notifier_hdl, &pds->addr,', 'qmi_send_request(&pdr->notifier_hdl, addr,')
s = replace_function(s, 'pdr_indack_work', r'''
static void pdr_indack_work(struct work_struct *work)
{
	struct pdr_handle *pdr = container_of(work, struct pdr_handle, indack_work);
	struct pdr_list_node *ind;
	struct pdr_service *pds, *iter;
	bool notify;

	for (;;) {
		pds = NULL;
		mutex_lock(&pdr->status_lock);
		mutex_lock(&pdr->list_lock);
		if (pdr->stopping)
			goto done;
		/* Deliver server loss even while notifier_work is waiting for QMI. */
		list_for_each_entry(iter, &pdr->lookups, node) {
			if (iter->need_notifier_remove) {
				pds = iter;
				break;
			}
		}
		if (pds) {
			mutex_unlock(&pdr->list_lock);
			pdr_notify_pending_down(pdr, pds);
			mutex_unlock(&pdr->status_lock);
			continue;
		}
		if (list_empty(&pdr->indack_list))
			goto done;
		ind = list_first_entry(&pdr->indack_list, struct pdr_list_node, node);
		list_del(&ind->node);
		pds = ind->pds;
		notify = !pds->lookup_failed && pds->service_connected &&
			 pds->server_generation == ind->server_generation;
		if (notify)
			pds->state = ind->curr_state;
		mutex_unlock(&pdr->list_lock);
		if (notify)
			pdr->status(ind->curr_state, pds->service_path, pdr->priv);
		mutex_unlock(&pdr->status_lock);

		/* Ack only the original peer, after the client has released resources. */
		if (!READ_ONCE(pdr->stopping))
			pdr_send_indack_msg(pdr, pds, &ind->addr, ind->transaction_id);
		kfree(ind);
	}
done:
	mutex_unlock(&pdr->list_lock);
	mutex_unlock(&pdr->status_lock);
}
''')
s = replace_function(s, 'pdr_indication_cb', r'''
static void pdr_indication_cb(struct qmi_handle *qmi, struct sockaddr_qrtr *sq,
			      struct qmi_txn *txn, const void *data)
{
	struct pdr_handle *pdr = container_of(qmi, struct pdr_handle, notifier_hdl);
	const struct servreg_state_updated_ind *ind_msg = data;
	struct pdr_list_node *ind;
	struct pdr_service *pds;

	if (!sq || !ind_msg || !ind_msg->service_path[0] ||
	    strnlen(ind_msg->service_path, sizeof(ind_msg->service_path)) > SERVREG_NAME_LENGTH)
		return;
	ind = kzalloc_obj(*ind);
	if (!ind)
		return;

	mutex_lock(&pdr->list_lock);
	if (!pdr->stopping) {
		list_for_each_entry(pds, &pdr->lookups, node) {
			if (strcmp(pds->service_path, ind_msg->service_path) ||
			    !pds->service_connected || pds->addr.sq_node != sq->sq_node ||
			    pds->addr.sq_port != sq->sq_port)
				continue;
			pds->state_sequence++;
			ind->transaction_id = ind_msg->transaction_id;
			ind->curr_state = ind_msg->curr_state;
			ind->pds = pds;
			ind->addr = *sq;
			ind->server_generation = pds->server_generation;
			list_add_tail(&ind->node, &pdr->indack_list);
			queue_work(pdr->indack_wq, &pdr->indack_work);
			mutex_unlock(&pdr->list_lock);
			pr_info("PDR: Indication received from %s, state: 0x%x, trans-id: %d\n",
				ind_msg->service_path, ind_msg->curr_state, ind_msg->transaction_id);
			return;
		}
	}
	mutex_unlock(&pdr->list_lock);
	kfree(ind);
}
''')
s = s.replace('struct pdr_handle *pdr)\n{\n\tstruct qmi_txn txn;',
              'struct pdr_handle *pdr, struct sockaddr_qrtr *addr)\n{\n\tstruct qmi_txn txn;', 1)
s = s.replace('\tmutex_lock(&pdr->lock);\n\tret = qmi_send_request(&pdr->locator_hdl,\n\t\t\t       &pdr->locator_addr,',
              '\tret = qmi_send_request(&pdr->locator_hdl,\n\t\t\t       addr,', 1)
s = s.replace('\t\t\t       req);\n\tmutex_unlock(&pdr->lock);', '\t\t\t       req);', 1)
s = s.replace('static int pdr_locate_service(struct pdr_handle *pdr, struct pdr_service *pds)',
              'static int pdr_locate_service(struct pdr_handle *pdr, struct pdr_service *pds,\n\t\t\t      struct sockaddr_qrtr *addr)', 1)
s = s.replace('pdr_get_domain_list(&req, resp, pdr)', 'pdr_get_domain_list(&req, resp, pdr, addr)', 1)
s = replace_function(s, 'pdr_notify_lookup_failure', r'''
static void pdr_notify_lookup_failure(struct pdr_handle *pdr,
				      struct pdr_service *pds, int err)
{
	pr_err("PDR: service lookup for %s failed: %d\n", pds->service_name, err);
	if (err == -ENXIO)
		return;

	mutex_lock(&pdr->status_lock);
	mutex_lock(&pdr->list_lock);
	if (pdr->stopping || pds->lookup_failed) {
		mutex_unlock(&pdr->list_lock);
		mutex_unlock(&pdr->status_lock);
		return;
	}
	pds->lookup_failed = true;
	pds->need_locator_lookup = false;
	pds->need_notifier_register = false;
	pds->need_notifier_remove = false;
	pds->state = SERVREG_LOCATOR_ERR;
	/* Workers and queued indications retain this object until handle release. */
	list_move_tail(&pds->node, &pdr->retired);
	mutex_unlock(&pdr->list_lock);
	pdr->status(SERVREG_LOCATOR_ERR, pds->service_path, pdr->priv);
	mutex_unlock(&pdr->status_lock);
}
''')
s = replace_function(s, 'pdr_locator_work', r'''
static void pdr_locator_work(struct work_struct *work)
{
	struct pdr_handle *pdr = container_of(work, struct pdr_handle, locator_work);
	struct pdr_service snapshot, *pds, *iter;
	struct sockaddr_qrtr addr;
	u64 generation, run;
	int ret;

	mutex_lock(&pdr->list_lock);
	run = ++pdr->locator_run;
	mutex_unlock(&pdr->list_lock);
	for (;;) {
		mutex_lock(&pdr->lock);
		if (!pdr->locator_init_complete || READ_ONCE(pdr->stopping)) {
			mutex_unlock(&pdr->lock);
			return;
		}
		addr = pdr->locator_addr;
		generation = pdr->locator_generation;
		mutex_unlock(&pdr->lock);

		pds = NULL;
		mutex_lock(&pdr->list_lock);
		if (!pdr->stopping) {
			list_for_each_entry(iter, &pdr->lookups, node) {
				if (iter->need_locator_lookup && iter->locator_attempt != run) {
					pds = iter;
					pds->locator_attempt = run;
					snapshot = *pds;
					break;
				}
			}
		}
		mutex_unlock(&pdr->list_lock);
		if (!pds)
			return;

		ret = pdr_locate_service(pdr, &snapshot, &addr);
		mutex_lock(&pdr->lock);
		if (!pdr->locator_init_complete || pdr->locator_generation != generation ||
		    READ_ONCE(pdr->stopping)) {
			mutex_unlock(&pdr->lock);
			continue;
		}
		if (!ret) {
			mutex_lock(&pdr->list_lock);
			pds->service_data_valid = snapshot.service_data_valid;
			pds->service_data = snapshot.service_data;
			pds->instance = snapshot.instance;
			pds->need_locator_lookup = false;
			mutex_unlock(&pdr->list_lock);
		}
		mutex_unlock(&pdr->lock);
		if (ret < 0) {
			pdr_notify_lookup_failure(pdr, pds, ret);
			continue;
		}
		ret = qmi_add_lookup(&pdr->notifier_hdl, pds->service, 1, snapshot.instance);
		if (ret < 0)
			pdr_notify_lookup_failure(pdr, pds, ret);
	}
}
''')
# Public operations must not schedule new work during release.
marker = '\tmutex_lock(&pdr->list_lock);\n\tlist_for_each_entry(tmp, &pdr->lookups, node) {'
assert s.count(marker) == 2
s = s.replace(marker, '\tmutex_lock(&pdr->list_lock);\n\tif (pdr->stopping) {\n\t\tmutex_unlock(&pdr->list_lock);\n\t\treturn ERR_PTR(-ESHUTDOWN);\n\t}\n\tlist_for_each_entry(tmp, &pdr->lookups, node) {', 1)
s = s.replace('\tlist_add(&pds->node, &pdr->lookups);\n\tmutex_unlock(&pdr->list_lock);\n\n\tschedule_work(&pdr->locator_work);',
              '\tlist_add(&pds->node, &pdr->lookups);\n\tschedule_work(&pdr->locator_work);\n\tmutex_unlock(&pdr->list_lock);', 1)
# The second site returns an integer (restart_pd), not an error pointer.
s = s.replace(marker, '\tmutex_lock(&pdr->list_lock);\n\tif (pdr->stopping) {\n\t\tmutex_unlock(&pdr->list_lock);\n\t\treturn -ESHUTDOWN;\n\t}\n\tlist_for_each_entry(tmp, &pdr->lookups, node) {', 1)
s = s.replace('\tINIT_LIST_HEAD(&pdr->lookups);', '\tINIT_LIST_HEAD(&pdr->lookups);\n\tINIT_LIST_HEAD(&pdr->retired);', 1)
s = s.replace('release_qmi_handle:\n\tqmi_handle_release(&pdr->locator_hdl);',
              'release_qmi_handle:\n\tWRITE_ONCE(pdr->stopping, true);\n\tcancel_work_sync(&pdr->locator_work);\n\tqmi_handle_release(&pdr->locator_hdl);', 1)
s = replace_function(s, 'pdr_handle_release', r'''
void pdr_handle_release(struct pdr_handle *pdr)
{
	struct pdr_service *pds, *tmp;
	struct pdr_list_node *ind, *next;

	if (IS_ERR_OR_NULL(pdr))
		return;

	mutex_lock(&pdr->list_lock);
	WRITE_ONCE(pdr->stopping, true);
	mutex_unlock(&pdr->list_lock);
	/* Pair with locator callbacks so no callback can queue after cancellation. */
	mutex_lock(&pdr->lock);
	pdr->locator_init_complete = false;
	pdr->locator_generation++;
	mutex_unlock(&pdr->lock);

	/* Keep QMI RX alive until every in-flight transaction has finished. */
	cancel_work_sync(&pdr->locator_work);
	cancel_work_sync(&pdr->notifier_work);
	cancel_work_sync(&pdr->indack_work);
	qmi_handle_release(&pdr->locator_hdl);
	qmi_handle_release(&pdr->notifier_hdl);
	destroy_workqueue(pdr->notifier_wq);
	destroy_workqueue(pdr->indack_wq);

	list_for_each_entry_safe(ind, next, &pdr->indack_list, node) {
		list_del(&ind->node);
		kfree(ind);
	}
	list_for_each_entry_safe(pds, tmp, &pdr->lookups, node) {
		list_del(&pds->node);
		kfree(pds);
	}
	list_for_each_entry_safe(pds, tmp, &pdr->retired, node) {
		list_del(&pds->node);
		kfree(pds);
	}
	kfree(pdr);
}
''')
# Align continuation arguments to the kernel's tab/space convention.
s = s.replace('                                  struct qmi_service *svc)', '\t\t\t\t  struct qmi_service *svc)')
s = s.replace('                                   struct qmi_service *svc)', '\t\t\t\t   struct qmi_service *svc)')
s = s.replace('                                    struct qmi_service *svc)', '\t\t\t\t    struct qmi_service *svc)')

mfd = sources['drivers/mfd/wcd934x.c']
marker = '\t/* Children must release their virtual IRQs before the domain is freed. */\n'
assert mfd.count(marker) == 1
mfd = mfd.replace(marker, '''\t/* Stop and synchronize the parent thread before child teardown can sleep. */
\tdisable_irq(ddata->irq);

''' + marker)
updated = {'drivers/soc/qcom/pdr_interface.c': s, 'drivers/mfd/wcd934x.c': mfd}
diff = ''
for name, source in updated.items():
    diff += ''.join(difflib.unified_diff(sources[name].splitlines(True), source.splitlines(True),
                                      fromfile='a/' + name, tofile='b/' + name))
    (root / name).write_text(source)
(ref / 'pdr-and-parent-irq.patch').write_text(
    'Subject: [PATCH] soc: qcom: pdr: release list lock during transactions and fence peers\n\n'
    'Keep service objects alive until callbacks and workers are stopped, order old\n'
    'DOWN notifications before new states, and quiesce the WCD parent interrupt\n'
    'before child removal.\n\n---\n' + diff)
(out / 'config-before-private').write_bytes((root / '.config').read_bytes())
print(json.dumps({'stage': 180, 'changed': {name: hashlib.sha256(source.encode()).hexdigest()
                                         for name, source in updated.items()}}))
