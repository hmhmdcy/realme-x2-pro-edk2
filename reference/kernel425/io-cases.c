/* SPDX-License-Identifier: GPL-2.0-only */
int main(void)
{
	u32 in[5];
	u8 out[1280], saved[1280], legacy[1216];
	struct camss_a5_ipe_io io = {
		.input = {640, 480, 640, 480, false},
		.output = {640, 480, 640, 480, false}, .output_port = 8,
	}, bad;
	struct camss_a5_pd10_layout layout, before = {1, 2, 3, 4, 5}, invalid;
	unsigned rejected = 0;

	assert(camss_a5_ipe_pd10_quarter(NULL, &layout) == -EINVAL);
	assert(camss_a5_ipe_pd10_quarter(&io.input, NULL) == -EINVAL);
	for (unsigned i = 0; i < 8; i++) {
		bad = io;
		switch (i) {
		case 0: bad.input.width = 126; break;
		case 1: bad.input.width = 8194; break;
		case 2: bad.input.height = 0xffffffff; break;
		case 3: bad.input.width = 641; break;
		case 4: bad.input.stride = 639; break;
		case 5: bad.input.slice_height = 479; break;
		case 6: bad.input.height = 126; break;
		case 7: bad.input.stride = 643; break;
		}
		layout = before;
		assert(camss_a5_ipe_pd10_quarter(&bad.input, &layout) == -EINVAL &&
		       !memcmp(&layout, &before, sizeof(layout)));
		rejected++;
	}
	assert(!camss_a5_ipe_pd10_quarter(&io.input, &layout));
	for (unsigned i = 0; i < 12; i++) {
		bad = io; invalid = layout;
		unsigned capacity = sizeof(out);
		switch (i) {
		case 0: invalid.width++; break;
		case 1: invalid.height++; break;
		case 2: invalid.stride++; break;
		case 3: invalid.slice_height++; break;
		case 4: invalid.bytes++; break;
		case 5: bad.output.width = 638; break;
		case 6: bad.output.height = 478; break;
		case 7: bad.output.uv_swap = true; break;
		case 8: bad.output_port = 10; break;
		case 9: capacity = 1215; break;
		case 10: bad.output.stride = 639; break;
		case 11: bad.input.width = 0xffffffff; break;
		}
		memset(out, 0xa7, sizeof(out)); memcpy(saved, out, sizeof(out));
		assert(camss_a5_ipe_encode_io(out, capacity, &bad, &invalid) == -EINVAL &&
		       !memcmp(out, saved, sizeof(out)));
		rejected++;
	}
	assert(camss_a5_ipe_encode_io(NULL, sizeof(out), &io, &layout) == -EINVAL);
	assert(camss_a5_ipe_encode_io(out, sizeof(out), NULL, &layout) == -EINVAL);
	assert(rejected == 20);
	while (fread(in, sizeof(in), 1, stdin) == 1) {
		io = (struct camss_a5_ipe_io){
			.input = {in[0], in[1], in[0] + in[4], in[1] + in[4], in[3]},
			.output = {in[0], in[1], in[0] + 2 * in[4], in[1] + 2 * in[4], in[3]},
			.output_port = in[2],
		};
		assert(!camss_a5_ipe_pd10_quarter(&io.input, &layout));
		memset(out, 0xa7, sizeof(out));
		assert(!camss_a5_ipe_encode_io(out, sizeof(out), &io, &layout));
		for (unsigned i = 1216; i < sizeof(out); i++) assert(out[i] == 0xa7);
		assert(fwrite(&layout, sizeof(layout), 1, stdout) == 1 &&
		       fwrite(out, 1216, 1, stdout) == 1);
		assert(!old_encode_ipe_io(legacy, 1216, &io));
		assert(!camss_a5_ipe_encode_io(out, sizeof(out), &io, NULL) &&
		       !memcmp(out, legacy, sizeof(legacy)));
		assert(fwrite(out, 1216, 1, stdout) == 1);
	}
	return 0;
}
