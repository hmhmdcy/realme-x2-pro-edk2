// SPDX-License-Identifier: GPL-2.0-only
static int free_transfer_memory(struct camss_a5 *a5)
{
	struct camss_a5_fw_memory *memories[] = {
		&a5->image_output, &a5->image_input, &a5->request,
	};
	unsigned int i;
	int ret;

	if (a5->ipe_dma_pending || a5->request_fw_mapped)
		return -EBUSY;
	for (i = 0; i < ARRAY_SIZE(memories); i++) {
		ret = camss_a5_fw_memory_unmap(memories[i]);
		if (ret)
			return ret;
		ret = camss_a5_fw_memory_free(memories[i]);
		if (ret)
			return ret;
	}
	return 0;
}

static int transfer_region_locked(struct camss_a5 *a5,
				  struct camss_a5_session *session, bool map)
{
	int ret;

	if ((map && a5->request_fw_mapped) ||
	    (!map && (!a5->request_fw_mapped || a5->request_owner != session)))
		return -EBUSY;
	ret = region_packet_locked(a5, session, &a5->request, map);
	if (map && a5->command_queued) {
		a5->request_fw_mapped = true;
		a5->request_owner = session;
	}
	if (ret) {
		session_command_failed(a5, ret);
		if (map && a5->command_queued)
			a5->session_uncertain = true;
		return ret;
	}
	if (map) {
		a5->transfer_maps++;
	} else {
		a5->request_fw_mapped = false;
		a5->request_owner = NULL;
		a5->transfer_unmaps++;
	}
	return 0;
}

static int transfer_alloc(struct camss_a5 *a5,
			  struct camss_a5_fw_memory *memory, u32 iova, u32 bytes)
{
	int ret = camss_a5_iova_memory_alloc(a5->dev, memory, iova, bytes);

	return ret ?: camss_a5_fw_memory_map(memory);
}

int camss_a5_ipe_run(struct camss_a5 *a5, struct camss_a5_session *session,
		     const struct camss_a5_ipe_job *job)
{
	struct camss_a5_ipe_frame frame = {};
	u8 packet[40] = {};
	u64 input_bytes, output_bytes, parcel;
	u32 stripe_bytes, iq_offset, scratch_offset, bl_offset;
	int ret, cleanup;

	if (!a5 || !session || !job || !job->striping || !job->iq ||
	    !job->input || !job->output || job->iq_bytes != CAMSS_A5_IPE_IQ_BYTES ||
	    !job->bl_bytes || job->bl_bytes < 32 ||
	    !job->max_cores || job->max_cores > 2 || !job->target_time_ns)
		return -EINVAL;
	/* Bring-up accepts the verified disabled-module IQ fixture only.
	 * Validated module/CDM generation is a separate next step.
	 */
	if (memchr_inv(job->iq, 0, job->iq_bytes))
		return -EOPNOTSUPP;
	ret = camss_a5_ipe_striping_bytes(job->striping, job->striping_bytes,
					 &stripe_bytes);
	if (ret)
		return ret;
	mutex_lock(&a5->lock);
	if (session->a5 != a5 || !session->handle || !session->configured ||
	    !a5->initialized || !a5->cpu_enabled || !a5->engine_dma_capable) {
		ret = -ENODEV;
		goto done;
	}
	if (a5->session_uncertain || a5->ipe_dma_pending ||
	    a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu) {
		ret = -EBUSY;
		goto done;
	}
	if (!nv12_layout_valid(&session->io.input) ||
	    !nv12_layout_valid(&session->io.output)) {
		ret = -EINVAL;
		goto done;
	}
	input_bytes = (u64)session->io.input.stride * session->io.input.slice_height;
	input_bytes += input_bytes / 2;
	output_bytes = (u64)session->io.output.stride * session->io.output.slice_height;
	output_bytes += output_bytes / 2;
	if (!input_bytes || !output_bytes || input_bytes > IMAGE_WINDOW ||
	    output_bytes > IMAGE_WINDOW || job->input_bytes < input_bytes ||
	    job->output_bytes < output_bytes || session->scratch_bytes > REQUEST_MAX ||
	    job->bl_bytes > REQUEST_MAX || stripe_bytes > REQUEST_MAX) {
		ret = -EINVAL;
		goto done;
	}
	/* The stripe begins on its own page after the frame packet. */
	iq_offset = PAGE_SIZE + PAGE_ALIGN(stripe_bytes);
	scratch_offset = iq_offset + PAGE_ALIGN(CAMSS_A5_IPE_IQ_BYTES);
	bl_offset = scratch_offset + PAGE_ALIGN(session->scratch_bytes);
	parcel = PAGE_ALIGN((u64)bl_offset + job->bl_bytes);
	if (!session->scratch_bytes || parcel > REQUEST_MAX) {
		ret = -EINVAL;
		goto done;
	}
	ret = transfer_alloc(a5, &a5->request, REQUEST_IOVA, parcel);
	if (ret)
		goto release;
	ret = transfer_alloc(a5, &a5->image_input, IMAGE_INPUT_IOVA, PAGE_ALIGN(input_bytes));
	if (ret)
		goto release;
	ret = transfer_alloc(a5, &a5->image_output, IMAGE_OUTPUT_IOVA, PAGE_ALIGN(output_bytes));
	if (ret)
		goto release;
	memcpy(a5->request.cpu + PAGE_SIZE, job->striping, stripe_bytes);
	memcpy(a5->request.cpu + iq_offset, job->iq, job->iq_bytes);
	memcpy(a5->image_input.cpu, job->input, input_bytes);
	memset(a5->image_output.cpu, 0xa5, output_bytes);
	frame.striping = (struct camss_a5_ipe_buffer){ REQUEST_IOVA + PAGE_SIZE, stripe_bytes };
	frame.iq = (struct camss_a5_ipe_buffer){ REQUEST_IOVA + iq_offset, job->iq_bytes };
	frame.scratch = (struct camss_a5_ipe_buffer){ REQUEST_IOVA + scratch_offset, session->scratch_bytes };
	frame.bl = (struct camss_a5_ipe_buffer){ REQUEST_IOVA + bl_offset, job->bl_bytes };
	frame.input = (struct camss_a5_ipe_buffer){ IMAGE_INPUT_IOVA, input_bytes };
	frame.output = (struct camss_a5_ipe_buffer){ IMAGE_OUTPUT_IOVA, output_bytes };
	frame.striping_cpu = a5->request.cpu + PAGE_SIZE;
	frame.required_scratch_bytes = session->scratch_bytes;
	frame.required_bl_bytes = job->bl_bytes;
	frame.request_id = job->request_id;
	frame.max_cores = job->max_cores;
	frame.target_time_ns = job->target_time_ns;
	ret = camss_a5_ipe_encode_frame(a5->request.cpu, a5->request.bytes,
					 &session->io, &frame);
	if (ret)
		goto release;
	dma_wmb();
	ret = transfer_region_locked(a5, session, true);
	if (ret)
		goto release;
	ret = session_token(a5);
	if (ret)
		goto unmap;
	a5->session_opcode = IPE_FRAME_PROCESS;
	put_unaligned_le32(sizeof(packet), packet);
	put_unaligned_le32(IPE_ASYNC_INDIRECT, packet + 4);
	put_unaligned_le32(IPE_FRAME_PROCESS, packet + 8);
	put_unaligned_le64(a5->session_cookie, packet + 12);
	put_unaligned_le64(a5->session_cookie2, packet + 20);
	put_unaligned_le32(1, packet + 28);
	put_unaligned_le32(session->handle, packet + 32);
	put_unaligned_le32(REQUEST_IOVA, packet + 36);
	a5->ipe_dma_pending = true;
	ret = send_packet(a5, packet, sizeof(packet), IPE_ASYNC_INDIRECT_ACK);
	if (a5->command_queued)
		a5->frames_submitted++;
	if (!a5->command_queued || !ret)
		a5->ipe_dma_pending = false;
	if (ret) {
		session_command_failed(a5, ret);
		if (a5->ipe_dma_pending)
			a5->session_uncertain = true;
		dev_info(a5->dev, "A5 IPE frame failed ret=%d hfi=%u status=%u queued=%u pending=%u\n",
			 ret, a5->session_header_error, a5->session_payload_status,
			 a5->command_queued, a5->ipe_dma_pending);
	} else {
		a5->frames_completed++;
		dma_rmb();
		memcpy(job->output, a5->image_output.cpu, output_bytes);
		dev_info(a5->dev, "A5 IPE frame completed request=%u\n", job->request_id);
	}
unmap:
	if (!a5->session_uncertain && !a5->ipe_dma_pending) {
		cleanup = transfer_region_locked(a5, session, false);
		if (!ret)
			ret = cleanup;
	}
release:
	if (!a5->request_fw_mapped && !a5->ipe_dma_pending) {
		cleanup = free_transfer_memory(a5);
		if (!ret)
			ret = cleanup;
	}
done:
	mutex_unlock(&a5->lock);
	return ret;
}
EXPORT_SYMBOL_GPL(camss_a5_ipe_run);
