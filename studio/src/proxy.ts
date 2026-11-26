// Guards every route: token cookie for pages and APIs, same origin for writes. Localhost only by design.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { COOKIE, expectedToken, originOk, safeEqual, tokenOk } from "./lib/token";

const PORT = Number(process.env.PORT || 4317);
const ORIGINS = [`http://127.0.0.1:${PORT}`, `http://localhost:${PORT}`];

export function proxy(req: NextRequest) {
  const url = req.nextUrl;
  // ?session= is what mb studio start prints (the engine's report scrubber hides anything called "token").
  const given = url.searchParams.get("session") ?? url.searchParams.get("token");
  const expected = expectedToken();
  if (given && expected && safeEqual(given, expected)) {
    url.searchParams.delete("session");
    url.searchParams.delete("token");
    const res = NextResponse.redirect(url);
    res.cookies.set(COOKIE, given, { httpOnly: true, sameSite: "strict", path: "/" });
    return res;
  }
  if (!tokenOk(req.cookies.get(COOKIE)?.value)) {
    if (url.pathname.startsWith("/api/")) return NextResponse.json({ error: "FORBIDDEN" }, { status: 403 });
    return new NextResponse(
      "Motionboard Studio: this session has expired or the link is missing its token. Run `mb studio open` for a fresh link.",
      { status: 403, headers: { "content-type": "text/plain" } },
    );
  }
  if (!originOk(req.method, req.headers.get("origin"), ORIGINS)) {
    return NextResponse.json({ error: "BAD_ORIGIN" }, { status: 403 });
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
