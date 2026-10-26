/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "libipa/tmc11_tree.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
using namespace libcamera::ipa;
struct Reader {
	const std::vector<unsigned char> &bytes;
	size_t offset = 0;
	template<typename T> T get() {
		if (offset + sizeof(T) > bytes.size()) throw std::runtime_error("truncated");
		T value; std::memcpy(&value, bytes.data() + offset, sizeof(T)); offset += sizeof(T); return value;
	}
	uint32_t count() { auto n = get<uint32_t>(); if (n > 21) throw std::runtime_error("count"); return n; }
};
int main()
{
	uint32_t size;
	while (std::fread(&size, sizeof(size), 1, stdin) == 1) {
		if (size > 2000000) return 2;
		std::vector<unsigned char> bytes(size);
		if (std::fread(bytes.data(), size, 1, stdin) != 1) return 3;
		const auto original = bytes;
		uint32_t status = 0; Tmc11RegionValues output; std::memset(&output, 0xa5, sizeof(output));
		try {
			Reader r{ bytes };
			auto ac = r.get<uint32_t>(), hc = r.get<uint32_t>();
			auto triggers = r.get<Tmc11TreeTriggers>();
			std::vector<Tmc11DrcRegion> tree(r.count());
			for (auto &drc : tree) {
				drc.trigger = r.get<std::array<float, 2>>(); drc.children.resize(r.count());
				for (auto &hdr : drc.children) {
					hdr.trigger = r.get<std::array<float, 6>>(); hdr.children.resize(r.count());
					for (auto &aec : hdr.children) aec = r.get<Tmc11AecRegion>();
				}
			}
			if (r.offset != bytes.size()) return 4;
			status = interpolateTmc11Tree(tree, ac, hc, triggers, &output);
		} catch (const std::runtime_error &) { return 5; }
		if (original != bytes) return 6;
		if (!status) for (auto b : std::vector<unsigned char>(reinterpret_cast<unsigned char *>(&output),
								 reinterpret_cast<unsigned char *>(&output) + sizeof(output)))
			if (b != 0xa5) return 7;
		if (std::fwrite(&status, sizeof(status), 1, stdout) != 1 ||
		    std::fwrite(&output, sizeof(output), 1, stdout) != 1) return 8;
	}
	return std::ferror(stdin) ? 9 : 0;
}
