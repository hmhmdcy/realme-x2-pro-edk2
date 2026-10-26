/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "gamma_interpolation.h"
#include <cassert>
#include <cstdio>

int main(int argc, char **argv)
{
 assert(argc == 3);
 FILE *input = fopen(argv[1], "rb"), *output = fopen(argv[2], "wb");
 assert(input && output);
 float weight;
 while (fread(&weight, sizeof(weight), 1, input) == 1) {
  libcamera::ipa::GammaSamples<256> first, second, result;
  assert(fread(first.data(), sizeof(float), first.size(), input) == first.size());
  assert(fread(second.data(), sizeof(float), second.size(), input) == second.size());
  result.fill(-99.0f);
  uint32_t valid = libcamera::ipa::interpolateGammaSamples<256>(first, second, weight, &result);
  if (!valid)
   for (float value : result) assert(value == -99.0f);
  assert(fwrite(&valid, sizeof(valid), 1, output) == 1);
  assert(fwrite(result.data(), sizeof(float), result.size(), output) == result.size());
 }
 int fail = ferror(input);
 fclose(input);
 return fclose(output) || fail ? 3 : 0;
}
