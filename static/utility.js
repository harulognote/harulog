// HaruLog v2.7.0 — 공과금 직접입력 및 월별/연간 금액 통계 관리
let utilityRecords = [];
let utilityEditingId = null;
let utilityBusy = false;

const utilityEl = id => document.getElementById(id);

function switchExpenseSubTab(tab) {
    const invoiceView = utilityEl('expenseInvoiceView');
    const utilityView = utilityEl('expenseUtilityView');
    const invoiceBtn = utilityEl('subtabInvoiceBtn');
    const utilityBtn = utilityEl('subtabUtilityBtn');

    if (tab === 'utility') {
        invoiceView.style.display = 'none';
        utilityView.style.display = 'block';
        invoiceBtn.classList.remove('active');
        utilityBtn.classList.add('active');
        loadUtilityRecords();
        loadUtilityStats();
    } else {
        invoiceView.style.display = 'block';
        utilityView.style.display = 'none';
        invoiceBtn.classList.add('active');
        utilityBtn.classList.remove('active');
    }
}

function updateUtilityTotalCalc() {
    const elec = Number(utilityEl('utilityElecFee').value) || 0;
    const water = Number(utilityEl('utilityWaterFee').value) || 0;
    const gas = Number(utilityEl('utilityGasFee').value) || 0;
    const telecom = Number(utilityEl('utilityTelecomFee').value) || 0;
    const other = Number(utilityEl('utilityOtherFee').value) || 0;

    const sum = elec + water + gas + telecom + other;
    utilityEl('utilityTotalFee').value = sum > 0 ? sum.toFixed(0) : '';
    utilityEl('utilityAutoSumNotice').textContent = `항목 소계 합산: ${sum.toLocaleString('ko-KR')}원 (전기: ${elec.toLocaleString()} | 수도: ${water.toLocaleString()} | 가스: ${gas.toLocaleString()} | 통신: ${telecom.toLocaleString()} | 기타: ${other.toLocaleString()})`;
}

async function loadUtilityRecords() {
    utilityEl('utilityListStatus').textContent = '공과금 기록을 불러오는 중입니다…';
    try {
        const res = await fetch('/api/utility/records', { cache: 'no-store' });
        if (!res.ok) throw new Error('목록을 불러오지 못했습니다.');
        utilityRecords = await res.json();
        renderUtilitySummary();
        renderUtilityList();
        utilityEl('utilityListStatus').textContent = '';
    } catch (err) {
        utilityEl('utilityListStatus').textContent = err.message;
    }
}

// 첫 화면 요약: 최근 연도 합산 및 청구총액/전기/수도/가스/통신/기타 모든 항목 소계 표시
function renderUtilitySummary() {
    const container = utilityEl('utilitySummary');
    if (!utilityRecords.length) {
        container.innerHTML = `
            <div class="score-summary" style="grid-template-columns: repeat(2, minmax(0, 1fr));">
                <div><span>등록된 기록</span><strong>0건</strong></div>
                <div><span>연간 청구총액</span><strong>—</strong></div>
            </div>
        `;
        return;
    }

    // 가장 최근 기록의 연도 (예: '2026')
    const latestYear = utilityRecords[0].billing_month.slice(0, 4);
    const yearRecords = utilityRecords.filter(r => r.billing_month.startsWith(latestYear));

    let sumTotal = 0;
    let sumElec = 0;
    let sumWater = 0;
    let sumGas = 0;
    let sumTelecom = 0;
    let sumOther = 0;

    yearRecords.forEach(r => {
        sumTotal += Number(r.total_fee) || 0;
        sumElec += Number(r.electricity_fee) || 0;
        sumWater += Number(r.water_fee) || 0;
        sumGas += Number(r.gas_fee) || 0;
        sumTelecom += Number(r.telecom_fee) || 0;
        sumOther += Number(r.other_fee) || 0;
    });

    container.innerHTML = `
        <div class="input-card" style="padding:12px 14px; margin-bottom:12px; border:1.5px solid var(--border-color);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:6px;">
                <span style="font-weight:700; color:#60a5fa; font-size:0.95rem;">📅 ${latestYear}년 연간 합계 (${yearRecords.length}개월)</span>
                <span style="font-size:0.8rem; color:var(--text-muted);">총 청구 합계</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-size:0.88rem; color:#fff; font-weight:600;">청구총액 합계</span>
                <strong style="font-size:1.4rem; color:#38bdf8;">${formatMoney(sumTotal)}</strong>
            </div>
            <div class="score-summary" style="margin-bottom:0; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:6px;">
                <div style="padding:8px 10px; gap:4px;">
                    <span style="font-size:0.72rem; color:#f59e0b;">⚡ 전기세 소계</span>
                    <strong style="font-size:0.92rem;">${formatMoney(sumElec)}</strong>
                </div>
                <div style="padding:8px 10px; gap:4px;">
                    <span style="font-size:0.72rem; color:#06b6d4;">💧 수도세 소계</span>
                    <strong style="font-size:0.92rem;">${formatMoney(sumWater)}</strong>
                </div>
                <div style="padding:8px 10px; gap:4px;">
                    <span style="font-size:0.72rem; color:#f87171;">🔥 가스비 소계</span>
                    <strong style="font-size:0.92rem;">${formatMoney(sumGas)}</strong>
                </div>
                <div style="padding:8px 10px; gap:4px;">
                    <span style="font-size:0.72rem; color:#a78bfa;">📱 통신비 소계</span>
                    <strong style="font-size:0.92rem;">${formatMoney(sumTelecom)}</strong>
                </div>
                <div style="padding:8px 10px; gap:4px;">
                    <span style="font-size:0.72rem; color:#9ca3af;">🏢 기타 소계</span>
                    <strong style="font-size:0.92rem;">${formatMoney(sumOther)}</strong>
                </div>
                <div style="padding:8px 10px; gap:4px;">
                    <span style="font-size:0.72rem; color:#34d399;">📊 월평균 청구</span>
                    <strong style="font-size:0.92rem;">${formatMoney(yearRecords.length ? sumTotal / yearRecords.length : 0)}</strong>
                </div>
            </div>
        </div>
    `;
}

async function loadUtilityStats() {
    try {
        const res = await fetch('/api/utility/stats', { cache: 'no-store' });
        if (!res.ok) return;
        const stats = await res.json();
        renderUtilityCharts(stats);
    } catch (err) {
        console.warn('통계 로드 실패:', err);
    }
}

function renderUtilityCharts(stats) {
    const feeChartContainer = utilityEl('utilityFeeChart');
    if (!feeChartContainer) return;

    if (!stats.months || !stats.months.length) {
        feeChartContainer.innerHTML = '<p class="score-help" style="text-align:center;padding:20px 0;">월별 공과금을 등록하시면 금액 추이 그래프가 표시됩니다.</p>';
        return;
    }

    feeChartContainer.innerHTML = createFeeSvgChart(stats);
}

function createFeeSvgChart(stats) {
    const months = stats.months;
    const totals = stats.total_fee;
    const elecs = stats.electricity_fee;
    const waters = stats.water_fee;
    const telecoms = stats.telecom_fee;

    const maxVal = Math.max(...totals, 10000);
    const width = 420;
    const height = 180;
    const padX = 42;
    const padY = 25;
    const chartW = width - padX - 15;
    const chartH = height - padY * 2;
    const n = months.length;
    const colW = Math.max(14, Math.min(32, chartW / n - 8));

    let bars = '';
    let xLabels = '';

    for (let i = 0; i < n; i++) {
        const x = padX + (chartW / n) * i + (chartW / n - colW) / 2;
        const totalH = (totals[i] / maxVal) * chartH;
        const yTotal = height - padY - totalH;

        const elecH = (elecs[i] / maxVal) * chartH;
        const waterH = (waters[i] / maxVal) * chartH;

        bars += `
            <g class="chart-col">
                <rect x="${x}" y="${yTotal}" width="${colW}" height="${totalH}" rx="3" fill="#3b82f6" opacity="0.85" />
                <rect x="${x}" y="${height - padY - elecH}" width="${colW / 2}" height="${elecH}" fill="#f59e0b" opacity="0.95" />
                <rect x="${x + colW / 2}" y="${height - padY - waterH}" width="${colW / 2}" height="${waterH}" fill="#06b6d4" opacity="0.95" />
                <text x="${x + colW / 2}" y="${yTotal - 4}" text-anchor="middle" font-size="9" fill="#93c5fd">${Math.round(totals[i] / 1000)}k</text>
            </g>
        `;
        const shortMonth = months[i].replace(/^\d{4}-/, '');
        xLabels += `<text x="${x + colW / 2}" y="${height - 8}" text-anchor="middle" font-size="10" fill="#9ca3af">${shortMonth}월</text>`;
    }

    return `
        <div style="font-size:11.5px; margin-bottom:8px; display:flex; gap:12px; justify-content:flex-end;">
            <span style="color:#3b82f6;">■ 청구총액</span>
            <span style="color:#f59e0b;">■ 전기세</span>
            <span style="color:#06b6d4;">■ 수도세</span>
        </div>
        <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;overflow:visible;">
            <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#374151" stroke-width="1"/>
            <line x1="${padX}" y1="${height - padY}" x2="${width - 10}" y2="${height - padY}" stroke="#374151" stroke-width="1"/>
            <text x="${padX - 4}" y="${padY + 4}" text-anchor="end" font-size="9" fill="#6b7280">${Math.round(maxVal / 1000)}k</text>
            <text x="${padX - 4}" y="${height - padY}" text-anchor="end" font-size="9" fill="#6b7280">0</text>
            ${bars}
            ${xLabels}
        </svg>
    `;
}

function renderUtilityList() {
    const list = utilityEl('utilityRecordList');
    list.replaceChildren();

    if (!utilityRecords.length) {
        list.innerHTML = '<p class="score-help" style="text-align:center;padding:24px 0;">아직 직접 입력한 공과금 내역이 없습니다.<br>위 폼에서 첫 월별 공과금을 등록해 보세요.</p>';
        return;
    }

    utilityRecords.forEach(row => {
        const card = document.createElement('article');
        card.className = 'input-card invoice-card';
        card.innerHTML = `
            <div class="score-toolbar" style="margin-bottom:4px;">
                <span style="font-weight:700; font-size:15px; color:#60a5fa;">📅 ${escapeHtml(row.billing_month)}월</span>
                <div class="log-actions">
                    <button type="button" class="btn-log-action util-edit">수정</button>
                    <button type="button" class="btn-log-action btn-log-delete util-delete">삭제</button>
                </div>
            </div>
            <div class="invoice-sum" style="margin: 6px 0 8px 0;">
                <span style="font-size:0.85rem;">청구총액</span>
                <strong style="color:#38bdf8; font-size:18px;">${Number(row.total_fee).toLocaleString('ko-KR')}원</strong>
            </div>
            <div class="score-fields" style="background:rgba(255,255,255,0.03); padding:8px 10px; border-radius:6px; font-size:12.5px; border:1px solid var(--border-color); margin-bottom:6px;">
                <div><span style="color:#f59e0b;">⚡ 전기세:</span> <strong>${Number(row.electricity_fee).toLocaleString()}원</strong></div>
                <div><span style="color:#06b6d4;">💧 수도세:</span> <strong>${Number(row.water_fee).toLocaleString()}원</strong></div>
            </div>
            <div style="font-size:12px; color:#9ca3af; display:flex; gap:10px; flex-wrap:wrap;">
                <span>📱 통신비: <strong style="color:#e5e7eb;">${Number(row.telecom_fee).toLocaleString()}원</strong></span>
                ${Number(row.gas_fee) > 0 ? `<span>🔥 가스비: <strong style="color:#e5e7eb;">${Number(row.gas_fee).toLocaleString()}원</strong></span>` : ''}
                ${Number(row.other_fee) > 0 ? `<span>🏢 기타: <strong style="color:#e5e7eb;">${Number(row.other_fee).toLocaleString()}원</strong></span>` : ''}
            </div>
            ${row.memo ? `<p class="score-memo" style="margin-top:6px; font-size:12px;">${escapeHtml(row.memo)}</p>` : ''}
        `;

        card.querySelector('.util-edit').onclick = () => editUtilityRecord(row.id);
        card.querySelector('.util-delete').onclick = () => deleteUtilityRecord(row.id);
        list.append(card);
    });
}

function openUtilityForm(row) {
    utilityEditingId = row ? row.id : null;
    utilityEl('utilityFormTitle').textContent = row ? `공과금 수정 (${row.billing_month})` : '월별 공과금 직접입력';
    const now = new Date();
    const curMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

    utilityEl('utilityMonth').value = row ? row.billing_month : curMonth;
    utilityEl('utilityElecFee').value = row ? row.electricity_fee : '';
    utilityEl('utilityWaterFee').value = row ? row.water_fee : '';
    utilityEl('utilityGasFee').value = row ? row.gas_fee : '';
    utilityEl('utilityTelecomFee').value = row ? row.telecom_fee : '';
    utilityEl('utilityOtherFee').value = row ? row.other_fee : '';
    utilityEl('utilityTotalFee').value = row ? row.total_fee : '';
    utilityEl('utilityMemo').value = row ? row.memo : '';

    updateUtilityTotalCalc();
    utilityEl('utilityForm').hidden = false;
    utilityEl('utilityForm').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function newUtilityRecord() {
    openUtilityForm(null);
}

function editUtilityRecord(id) {
    const row = utilityRecords.find(r => r.id === id);
    if (row) openUtilityForm(row);
}

function cancelUtilityEdit() {
    utilityEl('utilityForm').hidden = true;
    utilityEditingId = null;
}

async function saveUtilityRecord(event) {
    event.preventDefault();
    if (utilityBusy) return;

    const data = {
        billing_month: utilityEl('utilityMonth').value.trim(),
        electricity_usage: utilityRecords.find(row => row.id === utilityEditingId)?.electricity_usage ?? '0.00',
        electricity_fee: utilityEl('utilityElecFee').value,
        water_usage: utilityRecords.find(row => row.id === utilityEditingId)?.water_usage ?? '0.00',
        water_fee: utilityEl('utilityWaterFee').value,
        gas_fee: utilityEl('utilityGasFee').value,
        telecom_fee: utilityEl('utilityTelecomFee').value,
        other_fee: utilityEl('utilityOtherFee').value,
        total_fee: utilityEl('utilityTotalFee').value,
        memo: utilityEl('utilityMemo').value.trim()
    };

    utilityBusy = true;
    utilityEl('utilitySaveBtn').disabled = true;
    utilityEl('utilityFormStatus').textContent = '저장 중입니다…';

    try {
        const url = utilityEditingId ? `/api/utility/records/${utilityEditingId}` : '/api/utility/records';
        const method = utilityEditingId ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const resJson = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(resJson.error || '저장하지 못했습니다.');

        utilityEl('utilityForm').hidden = true;
        utilityEditingId = null;
        await loadUtilityRecords();
        await loadUtilityStats();
    } catch (err) {
        utilityEl('utilityFormStatus').textContent = err.message;
    } finally {
        utilityBusy = false;
        utilityEl('utilitySaveBtn').disabled = false;
    }
}

async function deleteUtilityRecord(id) {
    if (!confirm('이 월별 공과금 기록을 삭제하시겠습니까?')) return;
    try {
        const res = await fetch(`/api/utility/records/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('삭제에 실패했습니다.');
        if (utilityEditingId === id) cancelUtilityEdit();
        await loadUtilityRecords();
        await loadUtilityStats();
    } catch (err) {
        alert(err.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const form = utilityEl('utilityForm');
    if (form) form.addEventListener('submit', saveUtilityRecord);
});
