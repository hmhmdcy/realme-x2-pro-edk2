/* Called with hw_lock held, after the core returned or stop was attempted. */
static bool image_transfer_owned(const struct camss_a5 *a5)
{
	return a5->ipe_dma_pending || a5->request_fw_mapped ||
		a5->request.cpu || a5->image_input.cpu || a5->image_output.cpu ||
		a5->dma_input.buffer || a5->dma_output.buffer;
}
