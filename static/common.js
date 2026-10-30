// HaruLog v2.7.1 — 공통 요청 및 HTML 이스케이프
async function apiRequest(url, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 150000);
    try {
        const response = await fetch(url, {...options, signal:controller.signal});
        const text = await response.text();
        let data;
        try { data = JSON.parse(text); }
        catch (_) { throw new Error(`서버 응답 형식 오류 (HTTP ${response.status}). 서버 재시작과 최신 소스 적용 여부를 확인해 주세요.`); }
        if (!response.ok) {
            const error = new Error(data.error || `요청 실패 (HTTP ${response.status})`);
            error.details = data; throw error;
        }
        return data;
    } catch (error) {
        if (error.name === 'AbortError') throw new Error('요청이 150초를 초과했습니다. 연결 상태와 서버 로그를 확인해 주세요. 사진과 입력값은 유지됩니다.');
        if (error instanceof TypeError) throw new Error('서버에 연결하지 못했습니다. 서버 실행 상태와 네트워크를 확인해 주세요.');
        throw error;
    } finally { clearTimeout(timer); }
}

function escapeHtml(text) {
    if (!text) return '';
    return text.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}