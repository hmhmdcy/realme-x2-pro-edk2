static int config_region_locked(struct camss_a5 *a5,
				struct camss_a5_session *session, bool map)
{
	u8 packet[56] = {};
	int ret;

	if (session->a5 != a5 || !a5->initialized || a5->session_uncertain)
		return -EIO;
	if ((map && a5->config_fw_mapped) ||
	    (!map && (!a5->config_fw_mapped || a5->config_owner != session)))
		return -EBUSY;
	ret = session_token(a5);
	if (ret)
		return ret;
	a5->session_opcode = map ? IPE_MEM_MAP : IPE_MEM_UNMAP;
	put_unaligned_le32(sizeof(packet), packet);
	put_unaligned_le32(IPE_ASYNC_DIRECT, packet + 4);
	put_unaligned_le32(a5->session_opcode, packet + 8);
	put_unaligned_le64(a5->session_cookie, packet + 12);
	put_unaligned_le64(a5->session_cookie2, packet + 20);
	put_unaligned_le32(1, packet + 28);
	put_unaligned_le32(session->handle, packet + 32);
	put_unaligned_le64(a5->session_cookie, packet + 36);
	put_unaligned_le32(1, packet + 44);
	put_unaligned_le32(a5->config.iova, packet + 48);
	put_unaligned_le32(a5->config.bytes, packet + 52);
	ret = send_packet(a5, packet, sizeof(packet), IPE_ASYNC_DIRECT_ACK);
	if (map && a5->command_queued) {
		/* A failed reply can follow a partially applied firmware mapping.
		 * Keep its backing until an acknowledged unmap or CPU quiescence.
		 */
		a5->config_fw_mapped = true;
		a5->config_owner = session;
	}
	if (ret) {
		session_command_failed(a5, ret);
		if (map && a5->command_queued)
			a5->session_uncertain = true;
		return ret;
	}
	if (map) {
		a5->config_maps++;
	} else {
		a5->config_fw_mapped = false;
		a5->config_owner = NULL;
		a5->config_unmaps++;
	}
	dev_info(a5->dev, "A5 IPE config region %s acknowledged\n", map ? "map" : "unmap");
	return 0;
}

int camss_a5_ipe_configure_nv12(struct camss_a5 *a5,
			       struct camss_a5_session *session,
			       const struct camss_a5_ipe_io *io)
{
	u8 packet[40] = {};
	int ret, unmap;

	if (!session || !io)
		return -EINVAL;
	mutex_lock(&a5->lock);
	if (session->a5 != a5 || !session->handle || !a5->initialized ||
	    !a5->cpu_enabled) {
		ret = -ENODEV;
		goto done;
	}
	if (a5->session_uncertain || a5->config_fw_mapped) {
		ret = -EBUSY;
		goto done;
	}
	if (!a5->config.cpu || a5->config.bytes < IPE_IO_CONFIG_BYTES ||
	    a5->config.mapped != a5->config.bytes) {
		ret = -EINVAL;
		goto done;
	}
	ret = encode_ipe_io(a5->config.cpu, a5->config.bytes, io);
	if (ret)
		goto done;
	dma_wmb();
	ret = config_region_locked(a5, session, true);
	if (ret)
		goto done;
	ret = session_token(a5);
	if (ret)
		goto unmap;
	a5->session_opcode = IPE_CONFIG_IO;
	put_unaligned_le32(sizeof(packet), packet);
	put_unaligned_le32(IPE_ASYNC_INDIRECT, packet + 4);
	put_unaligned_le32(IPE_CONFIG_IO, packet + 8);
	put_unaligned_le64(a5->session_cookie, packet + 12);
	put_unaligned_le64(a5->session_cookie2, packet + 20);
	put_unaligned_le32(1, packet + 28);
	put_unaligned_le32(session->handle, packet + 32);
	put_unaligned_le32(a5->config.iova, packet + 36);
	session->configured = false;
	session->scratch_bytes = 0;
	ret = send_packet(a5, packet, sizeof(packet), IPE_ASYNC_INDIRECT_ACK);
	if (ret) {
		session_command_failed(a5, ret);
	} else {
		session->scratch_bytes = a5->session_scratch_bytes;
		a5->io_configs++;
		dev_info(a5->dev, "A5 IPE CONFIG_IO acknowledged scratch=%u\n",
			 session->scratch_bytes);
	}
unmap:
	if (!a5->session_uncertain) {
		unmap = config_region_locked(a5, session, false);
		if (!ret)
			ret = unmap;
	}
	if (!ret) {
		session->io = *io;
		session->configured = true;
	}
done:
	mutex_unlock(&a5->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_configure_nv12);
