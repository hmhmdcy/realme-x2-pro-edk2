/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Minimal S5KGW1 SGBRG10_CSI2P demosaicer.
 *
 * Input:  bare 10-bit MIPI packed Bayer, 5 bytes per 4 pixels.
 * Output: P6 PPM. Convert with ImageMagick if a JPEG is needed.
 *
 * This is a bring-up tool, not an OEM-quality ISP replacement. It performs
 * bilinear demosaicing, gray-world white balance and a fixed 2.2 gamma.
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int width = 4608;
static int height = 3456;

static inline int clamp10(int v)
{
	return v < 0 ? 0 : (v > 1023 ? 1023 : v);
}

static inline int at(const uint16_t *p, int x, int y)
{
	if (x < 0)
		x = 0;
	else if (x >= width)
		x = width - 1;
	if (y < 0)
		y = 0;
	else if (y >= height)
		y = height - 1;
	return p[(size_t)y * width + x];
}

static inline int avg2(int a, int b)
{
	return (a + b + 1) / 2;
}

static inline int avg4(int a, int b, int c, int d)
{
	return (a + b + c + d + 2) / 4;
}

int main(int argc, char **argv)
{
	FILE *in, *out;
	uint8_t *packed;
	uint16_t *raw, *r, *g, *b;
	uint8_t *row;
	size_t pixels, packed_size;
	size_t i;
	int x, y;
	uint64_t sr = 0, sg = 0, sb = 0;
	double gr, gb;
	uint8_t lut_r[1024], lut_g[1024], lut_b[1024];

	if (argc != 3 && argc != 5) {
		fprintf(stderr,
			"usage: %s input.raw output.ppm [width height]\n",
			argv[0]);
		return 2;
	}
	if (argc == 5) {
		width = atoi(argv[3]);
		height = atoi(argv[4]);
		if (width <= 0 || height <= 0 || (width & 1) || (height & 1)) {
			fprintf(stderr, "invalid dimensions\n");
			return 2;
		}
	}
	pixels = (size_t)width * height;
	packed_size = pixels * 5 / 4;

	in = fopen(argv[1], "rb");
	if (!in) {
		perror(argv[1]);
		return 1;
	}
	packed = malloc(packed_size);
	raw = malloc(pixels * sizeof(*raw));
	r = calloc(pixels, sizeof(*r));
	g = calloc(pixels, sizeof(*g));
	b = calloc(pixels, sizeof(*b));
	row = malloc((size_t)width * 3);
	if (!packed || !raw || !r || !g || !b || !row) {
		fprintf(stderr, "out of memory\n");
		return 1;
	}
	if (fread(packed, 1, packed_size, in) != packed_size) {
		fprintf(stderr, "short RAW read\n");
		return 1;
	}
	fclose(in);

	for (i = 0; i < pixels / 4; i++) {
		const uint8_t *p = packed + i * 5;
		uint16_t *q = raw + i * 4;

		q[0] = ((uint16_t)p[0] << 2) | (p[4] & 3);
		q[1] = ((uint16_t)p[1] << 2) | ((p[4] >> 2) & 3);
		q[2] = ((uint16_t)p[2] << 2) | ((p[4] >> 4) & 3);
		q[3] = ((uint16_t)p[3] << 2) | ((p[4] >> 6) & 3);
	}
	free(packed);

	/* GBRG: row 0 = G B, row 1 = R G. */
	for (y = 0; y < height; y++) {
		for (x = 0; x < width; x++) {
			size_t n = (size_t)y * width + x;
			uint16_t v = raw[n];

			if (!(y & 1) && !(x & 1))
				g[n] = v;
			else if (!(y & 1))
				b[n] = v;
			else if (!(x & 1))
				r[n] = v;
			else
				g[n] = v;
		}
	}

	for (y = 0; y < height; y++) {
		for (x = 0; x < width; x++) {
			size_t n = (size_t)y * width + x;
			int even_y = !(y & 1);
			int even_x = !(x & 1);

			if (even_y && even_x) {
				r[n] = avg2(at(r, x, y - 1), at(r, x, y + 1));
				b[n] = avg2(at(b, x - 1, y), at(b, x + 1, y));
			} else if (even_y) {
				r[n] = avg4(at(r, x - 1, y - 1),
					    at(r, x + 1, y - 1),
					    at(r, x - 1, y + 1),
					    at(r, x + 1, y + 1));
			} else if (even_x) {
				b[n] = avg4(at(b, x - 1, y - 1),
					    at(b, x + 1, y - 1),
					    at(b, x - 1, y + 1),
					    at(b, x + 1, y + 1));
			} else {
				r[n] = avg2(at(r, x - 1, y), at(r, x + 1, y));
				b[n] = avg2(at(b, x, y - 1), at(b, x, y + 1));
			}

			if (!g[n])
				g[n] = avg4(at(g, x - 1, y), at(g, x + 1, y),
					    at(g, x, y - 1), at(g, x, y + 1));
		}
	}
	free(raw);

	for (i = 0; i < pixels; i++) {
		sr += r[i];
		sg += g[i];
		sb += b[i];
	}
	gr = sr ? (double)sg / sr : 1.0;
	gb = sb ? (double)sg / sb : 1.0;

	for (i = 0; i < 1024; i++) {
		double v = pow(i / 1023.0, 1.0 / 2.2) * 255.0;

		lut_g[i] = (uint8_t)(v + 0.5);
		lut_r[i] = (uint8_t)(pow(clamp10((int)(i * gr)) / 1023.0,
					 1.0 / 2.2) * 255.0 + 0.5);
		lut_b[i] = (uint8_t)(pow(clamp10((int)(i * gb)) / 1023.0,
					 1.0 / 2.2) * 255.0 + 0.5);
	}

	out = fopen(argv[2], "wb");
	if (!out) {
		perror(argv[2]);
		return 1;
	}
	fprintf(out, "P6\n%d %d\n255\n", width, height);
	for (y = 0; y < height; y++) {
		for (x = 0; x < width; x++) {
			size_t n = (size_t)y * width + x;

			row[x * 3 + 0] = lut_r[r[n]];
			row[x * 3 + 1] = lut_g[g[n]];
			row[x * 3 + 2] = lut_b[b[n]];
		}
		if (fwrite(row, 1, (size_t)width * 3, out) !=
		    (size_t)width * 3) {
			fprintf(stderr, "short PPM write\n");
			return 1;
		}
	}
	fclose(out);

	return 0;
}
