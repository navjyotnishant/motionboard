// Session token: `mb studio start` sets MB_STUDIO_TOKEN and prints the URL with ?token=. The first visit
// trades it for an httpOnly cookie. Every API call needs the cookie; every write also needs a same origin
// Origin header. Runs in the proxy (edge-safe: no Node APIs).
export const COOKIE = "mb_session";

export function expectedToken(): string | null {
  return process.env.MB_STUDIO_TOKEN || null;
}

export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

export function tokenOk(cookie: string | undefined): boolean {
  const t = expectedToken();
  if (!t) return false;
  return !!cookie && safeEqual(cookie, t);
}

const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function originOk(method: string, origin: string | null, allowed: string[]): boolean {
  if (!MUTATING.has(method.toUpperCase())) return true;
  return !!origin && allowed.includes(origin);
}
