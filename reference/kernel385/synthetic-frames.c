/* Temporary synthetic test; each submission changes luma and chroma. */
struct test_frame_observation {
	u32 input_crc, output_crc, y_different;
	u64 uv_abs_error;
};
static struct test_frame_observation frame_observations[8];
static u32 test_frames_done;

static void append_frame_results(void)
{
	u32 i, off = strlen(result);

	off += scnprintf(result + off, sizeof(result) - off,
			 ",\"test_width\":%u,\"test_height\":%u,\"test_port\":%u,"
			 "\"test_cores\":%u,\"test_uv_swap\":%s,\"test_frames\":%u,\"frame_results\":[",
			 test_width, test_height, test_port, test_cores,
			 test_uv_swap ? "true" : "false", test_frames);
	for (i = 0; i < test_frames_done; i++) {
		const struct test_frame_observation *f = &frame_observations[i];

		off += scnprintf(result + off, sizeof(result) - off,
				 "%s{\"sequence\":%u,\"non_rt\":%s,\"input_crc\":%u,"
				 "\"output_crc\":%u,\"y_different\":%u,\"uv_abs_error\":%llu}",
				 i ? "," : "", i, i & 1 ? "true" : "false",
				 f->input_crc, f->output_crc, f->y_different,
				 (unsigned long long)f->uv_abs_error);
	}
	scnprintf(result + off, sizeof(result) - off, "]}");
}

static int test_frame(struct camss_a5 *a5, struct camss_a5_session *session,
		      u32 sequence)
{
	struct test_frame_observation *observation = &frame_observations[sequence];
	struct camss_a5_ipe_job job = {};
	u32 pixels = test_width * test_height;
	u8 *input, *output;
	u32 x, y, i;
	int ret;

	test_output_bytes = test_input_crc = test_output_crc = 0;
	kvfree(test_output);
	test_output = NULL;
	input = kvzalloc(test_image_bytes, GFP_KERNEL);
	if (!input)
		return -ENOMEM;
	test_output = kvzalloc(test_image_bytes, GFP_KERNEL);
	if (!test_output) {
		ret = -ENOMEM;
		goto out;
	}
	for (y = 0; y < test_height; y++)
		for (x = 0; x < test_width; x++)
			input[y * test_width + x] = 16 + ((x / 8 + y / 8 * 3 + sequence * 5) % 28) * 8;
	for (y = 0; y < test_height / 2; y++) {
		for (x = 0; x < test_width; x += 2) {
			u8 u = 96 + ((x / 80 + sequence) % 2) * 64;
			u8 v = 64 + ((y / 60 + sequence) % 2) * 96;

			input[pixels + y * test_width + x] = test_uv_swap ? v : u;
			input[pixels + y * test_width + x + 1] = test_uv_swap ? u : v;
		}
	}
	test_input_crc = crc32_le(0, input, test_image_bytes);
	job.input = input;
	job.input_bytes = test_image_bytes;
	job.output = test_output;
	job.output_bytes = test_image_bytes;
	job.bl_bytes = 512 * 1024;
	job.request_id = sequence + 1;
	job.max_cores = test_cores;
	job.target_time_ns = 100000000;
	ret = camss_a5_ipe_run(a5, session, &job);
	if (!ret) {
		test_output_bytes = test_image_bytes;
		test_output_crc = crc32_le(0, test_output, test_image_bytes);
		observation->input_crc = test_input_crc;
		observation->output_crc = test_output_crc;
		output = test_output;
		for (i = 0; i < pixels; i++)
			observation->y_different += input[i] != output[i];
		for (i = pixels; i < test_image_bytes; i++)
			observation->uv_abs_error += abs((int)input[i] - (int)output[i]);
		test_frames_done++;
	}
out:
	kvfree(input);
	return ret;
}
