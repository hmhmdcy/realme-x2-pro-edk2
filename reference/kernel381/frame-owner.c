#define TEST_IMAGE_BYTES (640U * 480U * 3U / 2U)
static void *test_output;
static u32 test_output_bytes, test_input_crc, test_output_crc;
static bool enable_frame;
module_param(enable_frame, bool, 0400);

static int test_frame(struct device *dev, struct camss_a5 *a5)
{
	const struct firmware *stripe = NULL, *iq = NULL;
	struct camss_a5_ipe_job job = {};
	u8 *input;
	unsigned int x, y;
	int ret;

	test_output_bytes = test_input_crc = test_output_crc = 0;
	kvfree(test_output);
	test_output = NULL;
	input = kvzalloc(TEST_IMAGE_BYTES, GFP_KERNEL);
	if (!input)
		return -ENOMEM;
	test_output = kvzalloc(TEST_IMAGE_BYTES, GFP_KERNEL);
	if (!test_output) {
		ret = -ENOMEM;
		goto out;
	}
	ret = request_firmware_direct(&stripe, "qcom/sm8150/samurai-ipe381-stripe.bin", dev);
	if (ret)
		goto out;
	ret = request_firmware_direct(&iq, "qcom/sm8150/samurai-ipe381-iq.bin", dev);
	if (ret)
		goto out;
	for (y = 0; y < 480; y++)
		for (x = 0; x < 640; x++)
			input[y * 640 + x] = 16 + ((x / 8 + y / 8 * 3) % 28) * 8;
	for (y = 0; y < 240; y++) {
		for (x = 0; x < 640; x += 2) {
			input[640 * 480 + y * 640 + x] = 96 + (x / 80 % 2) * 64;
			input[640 * 480 + y * 640 + x + 1] = 64 + (y / 60 % 2) * 96;
		}
	}
	test_input_crc = crc32_le(0, input, TEST_IMAGE_BYTES);
	job.striping = stripe->data;
	job.striping_bytes = stripe->size;
	job.iq = iq->data;
	job.iq_bytes = iq->size;
	job.input = input;
	job.input_bytes = TEST_IMAGE_BYTES;
	job.output = test_output;
	job.output_bytes = TEST_IMAGE_BYTES;
	job.bl_bytes = 156512;
	job.request_id = 1;
	job.max_cores = 1;
	job.target_time_ns = 100000000;
	ret = camss_a5_ipe_run(a5, &session_rt, &job);
	if (!ret) {
		test_output_bytes = TEST_IMAGE_BYTES;
		test_output_crc = crc32_le(0, test_output, TEST_IMAGE_BYTES);
	}
out:
	if (iq)
		release_firmware(iq);
	if (stripe)
		release_firmware(stripe);
	kvfree(input);
	return ret;
}

static ssize_t image_read(struct file *file, struct kobject *kobj,
			  const struct bin_attribute *attr, char *buffer,
			  loff_t offset, size_t count)
{
	ssize_t ret = -ENODATA;

	mutex_lock(&test_lock);
	if (!finished || test_error || !test_output || !test_output_bytes)
		goto out;
	if (offset < 0) {
		ret = -EINVAL;
		goto out;
	}
	ret = 0;
	if (offset >= test_output_bytes)
		goto out;
	count = min_t(size_t, count, test_output_bytes - offset);
	memcpy(buffer, test_output + offset, count);
	ret = count;
out:
	mutex_unlock(&test_lock);
	return ret;
}
static const struct bin_attribute image_attribute = {
	.attr = { .name = "image", .mode = 0400 },
	.size = TEST_IMAGE_BYTES,
	.read = image_read,
};
