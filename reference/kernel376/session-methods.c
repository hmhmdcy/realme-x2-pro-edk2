/* Caller holds the lifecycle/command mutex throughout a session command. */
static int session_token(struct camss_a5 *a5)
{
	if (a5->session_sequence == U64_MAX)
		return -EOVERFLOW;
	a5->session_cookie = ++a5->session_sequence;
	a5->session_cookie2 = a5->session_cookie ^ 0x3764955045413541ULL;
	a5->session_reply = false;
	a5->session_reply_handle = 0;
	return 0;
}

static void session_command_failed(struct camss_a5 *a5, int ret)
{
	/* Once enqueued, timeout or an unrecognizable response can leave an
	 * unknown live firmware handle. Do not issue another session command.
	 */
	if (a5->command_queued && (ret != -EREMOTEIO || !a5->session_reply))
		a5->session_uncertain = true;
}

int camss_a5_ipe_create(struct camss_a5 *a5, struct camss_a5_session *session,
			 u32 handle_type)
{
	struct camss_a5_session *existing;
	u8 packet[28] = {};
	int ret;

	if (!session || (handle_type != CAMSS_A5_IPE_RT &&
			 handle_type != CAMSS_A5_IPE_NON_RT))
		return -EINVAL;
	mutex_lock(&a5->lock);
	if (session->a5) {
		ret = -EBUSY;
		goto done;
	}
	if (!a5->initialized || !a5->cpu_enabled) {
		ret = -ENODEV;
		goto done;
	}
	if (a5->session_uncertain) {
		ret = -EIO;
		goto done;
	}
	ret = session_token(a5);
	if (ret)
		goto done;
	put_unaligned_le32(sizeof(packet), packet);
	put_unaligned_le32(IPE_CREATE, packet + 4);
	put_unaligned_le32(handle_type, packet + 8);
	put_unaligned_le64(a5->session_cookie, packet + 12);
	put_unaligned_le64(a5->session_cookie2, packet + 20);
	ret = send_packet(a5, packet, sizeof(packet), IPE_CREATE_ACK);
	if (ret) {
		session_command_failed(a5, ret);
		goto done;
	}
	list_for_each_entry(existing, &a5->sessions, node) {
		if (existing->handle == a5->session_reply_handle) {
			a5->session_uncertain = true;
			ret = -EPROTO;
			goto done;
		}
	}
	session->a5 = a5;
	session->type = handle_type;
	session->handle = a5->session_reply_handle;
	list_add_tail(&session->node, &a5->sessions);
	a5->session_count++;
	a5->session_creates++;
	a5->session_peak = max(a5->session_peak, a5->session_count);
	dev_info(a5->dev, "A5 IPE create acknowledged type=%u active=%u\n",
		 handle_type, a5->session_count);
done:
	mutex_unlock(&a5->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_create);

static int ipe_destroy_locked(struct camss_a5 *a5,
			      struct camss_a5_session *session)
{
	u8 packet[44] = {};
	int ret;

	if (session->a5 != a5 || !session->handle)
		return -ENOENT;
	if (!a5->initialized || !a5->cpu_enabled)
		return -ENODEV;
	if (a5->session_uncertain)
		return -EIO;
	ret = session_token(a5);
	if (ret)
		return ret;
	a5->session_opcode = IPE_DESTROY;
	put_unaligned_le32(sizeof(packet), packet);
	put_unaligned_le32(IPE_ASYNC_DIRECT, packet + 4);
	put_unaligned_le32(IPE_DESTROY, packet + 8);
	put_unaligned_le64(a5->session_cookie, packet + 12);
	put_unaligned_le64(a5->session_cookie2, packet + 20);
	put_unaligned_le32(1, packet + 28);
	put_unaligned_le32(session->handle, packet + 32);
	/* This ABI's destroy payload has no independent echoed handle. The
	 * two unique header tokens bind this reply to the submitted handle.
	 */
	put_unaligned_le64(a5->session_cookie, packet + 36);
	ret = send_packet(a5, packet, sizeof(packet), IPE_ASYNC_DIRECT_ACK);
	if (ret) {
		session_command_failed(a5, ret);
		return ret;
	}
	list_del_init(&session->node);
	session->a5 = NULL;
	session->handle = 0;
	session->type = 0;
	a5->session_count--;
	a5->session_destroys++;
	dev_info(a5->dev, "A5 IPE destroy acknowledged active=%u\n", a5->session_count);
	return 0;
}

int camss_a5_ipe_destroy(struct camss_a5 *a5, struct camss_a5_session *session)
{
	int ret;

	if (!session)
		return -EINVAL;
	mutex_lock(&a5->lock);
	ret = ipe_destroy_locked(a5, session);
	mutex_unlock(&a5->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_destroy);

static void invalidate_sessions(struct camss_a5 *a5)
{
	struct camss_a5_session *session, *next;

	list_for_each_entry_safe(session, next, &a5->sessions, node) {
		list_del_init(&session->node);
		session->a5 = NULL;
		session->handle = 0;
		session->type = 0;
	}
	a5->session_count = 0;
	a5->session_uncertain = false;
}
