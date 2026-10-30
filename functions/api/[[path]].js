export async function onRequest(context) {
  const url = new URL(context.request.url);
  // 환경변수 BACKEND_URL이 설정되어 있으면 사용하고, 없으면 기본 PythonAnywhere URL 사용
  const backendBase = (context.env && context.env.BACKEND_URL) 
    ? context.env.BACKEND_URL.replace(/\/+$/, '') 
    : 'https://harulog.pythonanywhere.com';

  const targetUrl = new URL(url.pathname + url.search, backendBase);
  const targetHost = targetUrl.host;

  const headers = new Headers(context.request.headers);
  headers.set('Host', targetHost);
  headers.set('X-Forwarded-Host', url.hostname);
  headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));
  headers.set('X-Forwarded-For', context.request.headers.get('CF-Connecting-IP') || context.request.headers.get('X-Forwarded-For') || '');

  // OPTIONS 사전 요청(Preflight) 처리
  if (context.request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': url.origin,
        'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token',
        'Access-Control-Allow-Credentials': 'true',
        'Access-Control-Max-Age': '86400',
      }
    });
  }

  try {
    const response = await fetch(targetUrl.toString(), {
      method: context.request.method,
      headers: headers,
      body: context.request.body,
      redirect: 'follow'
    });

    // Cloudflare Pages 도메인과의 원활한 통신을 위한 응답 헤더 보정
    const newHeaders = new Headers(response.headers);
    newHeaders.set('Access-Control-Allow-Origin', url.origin);
    newHeaders.set('Access-Control-Allow-Credentials', 'true');
    newHeaders.set('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
    newHeaders.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token');

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: newHeaders
    });
  } catch (err) {
    return new Response(JSON.stringify({ 
      error: '백엔드 서버에 연결할 수 없습니다. 서버 상태 및 BACKEND_URL 설정을 확인해 주세요.',
      details: err.message 
    }), {
      status: 502,
      headers: { 'Content-Type': 'application/json; charset=utf-8' }
    });
  }
}
