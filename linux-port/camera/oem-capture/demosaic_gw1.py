#!/usr/bin/env python3
"""Demosaic a bare S5KGW1 4608x3456 SGBRG10_CSI2P frame."""

import sys

import numpy as np
from PIL import Image


def shift(a, dy, dx):
	h, w = a.shape
	p = np.pad(a, ((1, 1), (1, 1)), mode="reflect")
	return p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]


def main(path, out_path, pattern="GBRG"):
	width, height = 4608, 3456
	data = np.fromfile(path, dtype=np.uint8)
	if data.size != width * height * 5 // 4:
		raise SystemExit(f"unexpected RAW size: {data.size}")

	packed = data.reshape(-1, 5).astype(np.uint16)
	pixels = np.empty((packed.shape[0], 4), dtype=np.uint16)
	for i in range(4):
		pixels[:, i] = (packed[:, i] << 2) | ((packed[:, 4] >> (2 * i)) & 3)
	raw = pixels.reshape(height, width).astype(np.float32)

	black = np.percentile(raw, 0.1)
	raw = np.clip(raw - black, 0, 1023 - black) / (1023 - black)

	masks = {
		"GBRG": ((1, 0), (0, 1), ((0, 0), (1, 1))),
		"BGGR": ((0, 1), (1, 0), ((0, 0), (1, 1))),
		"RGGB": ((0, 0), (1, 1), ((0, 1), (1, 0))),
		"GRBG": ((1, 1), (0, 0), ((0, 1), (1, 0))),
	}
	r_pos, b_pos, g_pos = masks[pattern]

	def put(pos):
		a = np.zeros_like(raw)
		a[pos[0] :: 2, pos[1] :: 2] = raw[pos[0] :: 2, pos[1] :: 2]
		return a

	r = put(r_pos)
	b = put(b_pos)
	g = put(g_pos[0]) + put(g_pos[1])
	yy, xx = np.indices(r.shape)
	even_sum = (yy + xx) % 2 == 0
	odd_odd = (yy % 2 == 1) & (xx % 2 == 1)

	r_even_even = (shift(r, 1, 0) + shift(r, -1, 0)) / 2
	r_even_odd = (
		shift(r, 1, 1) + shift(r, 1, -1) + shift(r, -1, 1) + shift(r, -1, -1)
	) / 4
	r_odd_odd = (shift(r, 0, 1) + shift(r, 0, -1)) / 2
	r = np.where(r > 0, r, np.where(even_sum, r_even_even, r_even_odd))
	r = np.where(r > 0, r, np.where(odd_odd, r_odd_odd, r))

	b_even_even = (shift(b, 0, 1) + shift(b, 0, -1)) / 2
	b_odd_even = (
		shift(b, 1, 1) + shift(b, 1, -1) + shift(b, -1, 1) + shift(b, -1, -1)
	) / 4
	b_odd_odd = (shift(b, 1, 0) + shift(b, -1, 0)) / 2
	b = np.where(b > 0, b, np.where(even_sum, b_even_even, b_odd_even))
	b = np.where(b > 0, b, np.where(odd_odd, b_odd_odd, b))

	g_fill = (
		shift(g, 1, 0) + shift(g, -1, 0) + shift(g, 0, 1) + shift(g, 0, -1)
	) / 4
	g = np.where(g > 0, g, g_fill)

	img = np.stack([r, g, b], axis=-1)
	means = img.reshape(-1, 3).mean(axis=0)
	img *= means[1] / means
	img = np.clip(img, 0, 1) ** (1 / 2.2)

	out = (img * 255).astype(np.uint8)
	Image.fromarray(out).save(out_path, quality=92)
	Image.fromarray(out).resize((1600, 1200), Image.LANCZOS).save(
		out_path.replace(".jpg", "-1600.jpg"), quality=88
	)
	print(out_path, out.shape)


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "GBRG")
