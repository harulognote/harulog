export async function onRequest(context) {
  const url = new URL(context.request.url);
  const backendBase = (context.env && context.env.BACKEND_URL) 
    ? context.env.BACKEND_URL.replace(/\/+$/, '') 
    : 'https://harulognote.pythonanywhere.com';

  const targetUrl = new URL(url.pathname + url.search, backendBase);
  const headers = new Headers(context.request.headers);
  headers.set('Host', targetUrl.host);

  try {
    const response = await fetch(targetUrl.toString(), {
      method: context.request.method,
      headers: headers,
      redirect: 'follow'
    });

    const newHeaders = new Headers(response.headers);
    newHeaders.set('Access-Control-Allow-Origin', url.origin);
    newHeaders.set('Cache-Control', 'public, max-age=86400');

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    });
  } catch (err) {
    return new Response('File not found or backend unreachable', { status: 404 });
  }
}
