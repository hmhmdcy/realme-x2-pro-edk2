#include "gamma_segments.h"
#include <cstdio>
#include <cstdint>
using namespace libcamera::ipa;
template<std::size_t Segments> int run(FILE *in, FILE *out)
{
 GammaSamples<Segments> samples;
 while (fread(samples.data(), sizeof(float), samples.size(), in) == samples.size()) {
  GammaSegments<Segments> result{};
  uint32_t valid = encodeGammaSegments<Segments>(samples, &result);
  if (fwrite(&valid, sizeof(valid), 1, out) != 1 ||
      fwrite(result.data(), sizeof(uint32_t), result.size(), out) != result.size())
   return 3;
 }
 return ferror(in) ? 3 : 0;
}
int main(int argc, char **argv)
{
 if (argc != 4)
  return 2;
 FILE *in = fopen(argv[2], "rb"), *out = fopen(argv[3], "wb");
 if (!in || !out)
  return 2;
 int count = 0;
 if (sscanf(argv[1], "%d", &count) != 1)
  return 2;
 int result = count == 64 ? run<64>(in, out) : count == 256 ? run<256>(in, out) : 2;
 fclose(in);
 return fclose(out) ? 3 : result;
}
