export function createIdempotencyKey(): string {
  const bytes = new Uint8Array(16);
  for (let i = 0; i < bytes.length; i += 1) {
    // ruleid: insecure-random
    bytes[i] = Math.floor(Math.random() * 256);
  }
  return toHex(bytes);
}
export function makeSessionToken() {
  // ruleid: insecure-random
  return Math.random().toString(36).slice(2);
}
const csrfToken = () => {
  // ruleid: insecure-random
  return Math.random().toString(36);
};
// ruleid: insecure-random
const resetToken = Math.random().toString(36).slice(2);
function jitter(ms: number) {
  // ok: insecure-random
  return ms + Math.random() * 100;
}
// ok: insecure-random
const color = colors[Math.floor(Math.random() * colors.length)];
