'use strict';
// Builtin-only, bounded decode of one new host file. No source path is baked in.
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const crypto = require('node:crypto');
const { Transform } = require('node:stream');
const { pipeline } = require('node:stream/promises');
const zlib = require('node:zlib');

async function main() {
  const [input, output, expectedInputText, expectedOutputText, expectedSha] = process.argv.slice(2);
  const expectedInput = Number(expectedInputText), expectedOutput = Number(expectedOutputText);
  if (!input || !output || !Number.isSafeInteger(expectedInput) || expectedInput <= 0 ||
      !Number.isSafeInteger(expectedOutput) || expectedOutput <= 0 || !/^[0-9a-f]{64}$/.test(expectedSha || ''))
    throw new Error('input output positive-input-bytes positive-output-bytes input-sha256 required');
  const result = { passed: false, node: process.version, brotli: process.versions.brotli,
    input_bytes: 0, output_forwarded_bytes: 0, engine_bytes_written: null, input_complete: false };
  const inputHash = crypto.createHash('sha256'), outputHash = crypto.createHash('sha256');
  const decoder = zlib.createBrotliDecompress();
  const inCount = new Transform({ transform(chunk, encoding, done) {
    result.input_bytes += chunk.length; inputHash.update(chunk);
    if (result.input_bytes > expectedInput) return done(new Error('compressed input exceeds bound'));
    done(null, chunk);
  }});
  const outCount = new Transform({ transform(chunk, encoding, done) {
    if (result.output_forwarded_bytes + chunk.length > expectedOutput)
      return done(new Error('decoded output exceeds bound'));
    result.output_forwarded_bytes += chunk.length; outputHash.update(chunk); done(null, chunk);
  }});
  try {
    await pipeline(fs.createReadStream(input, { highWaterMark: 1024 * 1024 }), inCount,
      decoder, outCount, fs.createWriteStream(output, { flags: 'wx', mode: 0o600 }));
    result.engine_bytes_written = decoder.bytesWritten;
    result.input_sha256 = inputHash.digest('hex');
    result.output_sha256 = outputHash.digest('hex');
    if (result.input_bytes !== expectedInput || result.input_sha256 !== expectedSha)
      throw new Error('compressed input length or digest mismatch');
    if (!Number.isSafeInteger(decoder.bytesWritten) || decoder.bytesWritten !== expectedInput)
      throw new Error('Brotli engine did not consume exact compressed stream');
    if (result.output_forwarded_bytes !== expectedOutput) throw new Error('decoded output short');
    const handle = await fsp.open(output, 'r+');
    try { await handle.sync(); } finally { await handle.close(); }
    result.input_complete = true; result.passed = true;
  } catch (error) {
    result.engine_bytes_written = decoder.bytesWritten;
    result.error = String(error && error.stack || error); process.exitCode = 1;
  }
  try { result.output_file_bytes = (await fsp.stat(output)).size; }
  catch (error) { result.output_stat_error = String(error); result.passed = false; process.exitCode = 1; }
  process.stdout.write(JSON.stringify(result) + '\n');
}
main().catch(error => { process.stderr.write(String(error.stack || error) + '\n'); process.exitCode = 1; });
