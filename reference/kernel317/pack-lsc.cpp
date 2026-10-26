/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/lens_shading.h"
#include <fstream>
#include <cstdio>
using namespace libcamera::ipa;
int main(int argc, char **argv)
{
	if (argc != 3)
		return 2;
	std::ifstream input(argv[1], std::ios::binary);
	std::ofstream output(argv[2], std::ios::binary);
	if (!input || !output)
		return 3;
	unsigned int tables = 0;
	LscMesh mesh;
	while (input.read(reinterpret_cast<char *>(&mesh), sizeof(mesh))) {
		LscPackedMesh packed;
		if (!lscPackTitan17x(mesh, &packed))
			return 4;
		output.write(reinterpret_cast<const char *>(&packed), sizeof(packed));
		if (!output)
			return 5;
		++tables;
	}
	if (!input.eof() || input.gcount() || !tables)
		return 6;
	std::printf("LSC_PACK tables=%u points=%u\n", tables, LscPoints);
	return 0;
}
