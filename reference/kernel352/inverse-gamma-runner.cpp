/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "ltm_inverse_gamma.h"
#include <cassert>
#include <cstdio>

int main(int argc, char **argv)
{
 assert(argc == 3);
 FILE *input = fopen(argv[1], "rb"), *output = fopen(argv[2], "wb");
 assert(input && output);
 libcamera::ipa::IfeGammaBaseNodes nodes;
 while (fread(nodes.data(), sizeof(uint16_t), nodes.size(), input) == nodes.size()) {
  libcamera::ipa::Ltm13InverseGammaTable table;
  table.segments.fill(0xa5a5a5a5);
  uint32_t valid = libcamera::ipa::encodeLtm13InverseGamma(nodes, &table);
  if (!valid)
   for (uint32_t word : table.segments) assert(word == 0xa5a5a5a5);
  assert(fwrite(&valid, sizeof(valid), 1, output) == 1);
  assert(fwrite(table.segments.data(), sizeof(uint32_t), table.segments.size(), output) == table.segments.size());
 }
 assert(!libcamera::ipa::encodeLtm13InverseGamma(nodes, nullptr));
 int fail = ferror(input);
 fclose(input);
 return fclose(output) || fail ? 3 : 0;
}
