import { NextRequest } from "next/server";

// Hosted preview gateways may consume Authorization for their own authentication.
// Accept the app-specific header and translate it only on the server-to-API hop.
const API_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";
export const dynamic = "force-dynamic";

async function proxy(request: NextRequest) {
  const url = new URL(request.nextUrl.pathname + request.nextUrl.search, API_TARGET);
  const headers = new Headers();
  const token = request.headers.get("x-studyflow-token");
  const authorization = token ? `Bearer ${token}` : request.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  try {
    const upstream = await fetch(url, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
    const responseHeaders = new Headers({ "Cache-Control": "no-store" });
    for (const name of ["content-type", "www-authenticate"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ detail: "The API is temporarily unavailable. Please try again." }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as PATCH, proxy as DELETE };
