// HaruLog v2.7.0 — 관리비 인보이스 및 그래프 관리
let invoices = [];
let invoiceEditingId = null;
let invoiceBusy = false;
let invoicePhotoUrl = null;
let invoiceOcrGeneration = 0;
let invoiceRevision = 0;
let invoiceDraft = null;
let invoiceRawText = '';
let isUserTaxManual = false; // 세금 수동 직접 입력 여부 플래그
const invoiceEl = id => document.getElementById(id);
const invoiceDefaultItems = ['전기 사용요금', '공용설비비 (Utilitas)', '전기세금 (PBJT-TL)', '행정비', '수도 사용요금', '수도 기본료'];

function invoiceCents(value) {
    const s = String(value);
    if (!/^-?\d+(?:\.\d{1,2})?$/.test(s)) return null;
    const negative = s.startsWith('-');
    const [whole, fraction = ''] = s.replace(/^-/, '').split('.');
    const cents = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
    return negative ? -cents : cents;
}
function invoiceDecimal(cents) {
    const sign = cents < 0n ? '-' : ''; const absolute = cents < 0n ? -cents : cents;
    // 소수점 표시하지 않기 위해 올림(Ceil) 처리된 정수 문자열 반환
    const roundedUnits = Math.ceil(Number(absolute) / 100);
    return `${sign}${roundedUnits}`;
}
function invoiceMoney(value) {
    const cents = typeof value === 'bigint' ? value : invoiceCents(value);
    if (cents === null) return '—';
    const absolute = cents < 0n ? -cents : cents;
    // 계산된 금액 올림(Math.ceil) 처리 및 소수점 없는 정수 표시
    const roundedUnits = Math.ceil(Number(absolute) / 100);
    return `${cents < 0n ? '-' : ''}Rp ${roundedUnits.toLocaleString('id-ID')}`;
}

// -------------------------------------------------------------------
// 수정모드/신규/OCR 시 기본 6대 항목(수도사용요금 등) 누락 없이 항상 보장
// -------------------------------------------------------------------
function prepareInvoiceItems(existingItems) {
    const defaultList = [
        { name: '전기 사용요금', match: ['전기 사용요금', '전기사용요금', 'pemakaian listrik'] },
        { name: '공용설비비 (Utilitas)', match: ['공용설비비', 'utilitas'] },
        { name: '전기세금 (PBJT-TL)', match: ['전기세금', 'pbjt', 'pbit'] },
        { name: '행정비', match: ['행정비', 'administrasi'] },
        { name: '수도 사용요금', match: ['수도 사용요금', '수도사용요금', 'pemakaian air'] },
        { name: '수도 기본료', match: ['수도 기본료', '기본료', 'abudemen', 'subscription'], defaultAmt: '30400' }
    ];
    const result = [];
    const used = new Set();
    const items = existingItems || [];

    for (const def of defaultList) {
        let found = null;
        for (let i = 0; i < items.length; i++) {
            if (used.has(i)) continue;
            const nm = (items[i].name || '').toLowerCase();
            if (def.match.some(m => nm.includes(m.toLowerCase()))) {
                found = items[i];
                used.add(i);
                break;
            }
        }
        if (found) {
            const num = Math.ceil(parseFloat(found.amount) || 0);
            result.push({ name: def.name, amount: String(num) });
        } else {
            result.push({ name: def.name, amount: def.defaultAmt || '0' });
        }
    }
    // 추가 사용자 커스텀 항목 유지
    for (let i = 0; i < items.length; i++) {
        if (!used.has(i)) {
            const num = Math.ceil(parseFloat(items[i].amount) || 0);
            result.push({ name: items[i].name, amount: String(num) });
        }
    }
    return result;
}

// -------------------------------------------------------------------
// 청구 항목 소계 (전기세 소계, 수도세 소계, 항목 총합계) 실시간 계산
// -------------------------------------------------------------------
function updateInvoiceTotal() {
    let total = 0n;
    let elecTotal = 0n;
    let waterTotal = 0n;

    const list = invoiceEl('invoiceItems');
    if (list) {
        for (const row of list.children) {
            const name = (row.querySelector('.invoice-item-name').value || '').toLowerCase();
            const val = row.querySelector('.invoice-item-amount').value;
            const c = invoiceCents(val);
            if (c !== null) {
                total += c;
                if (name.includes('전기') || name.includes('utilitas') || name.includes('공용') || name.includes('pbjt') || name.includes('세금') || name.includes('행정비') || name.includes('administrasi') || name.includes('admin')) {
                    elecTotal += c;
                } else if (name.includes('수도') || name.includes('기본료') || name.includes('air') || name.includes('abonemen')) {
                    waterTotal += c;
                }
            }
        }
    }

    if (invoiceEl('invoiceElecSubtotal')) invoiceEl('invoiceElecSubtotal').textContent = invoiceMoney(elecTotal);
    if (invoiceEl('invoiceWaterSubtotal')) invoiceEl('invoiceWaterSubtotal').textContent = invoiceMoney(waterTotal);
    if (invoiceEl('invoiceItemsTotal')) invoiceEl('invoiceItemsTotal').textContent = total === 0n ? 'Rp 0' : invoiceMoney(total);

    const billed = invoiceCents(invoiceEl('invoiceBilled').value);
    const notice = invoiceEl('invoiceDifference');
    notice.classList.remove('invoice-warning');
    if (billed === null) {
        notice.textContent = '항목 금액과 청구총액을 입력해 주세요.';
        return;
    }
    const difference = billed - total;
    notice.textContent = difference === 0n
        ? '항목 합계와 청구총액이 일치합니다.'
        : `청구총액 − 항목 합계 = ${invoiceMoney(difference)}. 원본을 확인해 주세요. 청구총액은 그대로 저장됩니다.`;
    if (difference !== 0n) notice.classList.add('invoice-warning');
}

function copyInvoiceSum() {
    let total = 0n;
    for (const row of invoiceEl('invoiceItems').children) {
        const n = invoiceCents(row.querySelector('.invoice-item-amount').value);
        if (n === null) return alert('항목 금액을 확인해 주세요.');
        total += n;
    }
    invoiceEl('invoiceBilled').value = invoiceDecimal(total);
    ++invoiceRevision;
    updateInvoiceTotal();
}

function findInvoiceItemInput(targetKeyword) {
    const list = invoiceEl('invoiceItems');
    if (!list) return null;
    const kw = targetKeyword.toLowerCase();
    for (const row of list.children) {
        const name = (row.querySelector('.invoice-item-name').value || '').toLowerCase();
        if (name.includes(kw)) {
            return row.querySelector('.invoice-item-amount');
        }
    }
    return null;
}

// 전기세금 = (전기사용요금 + 공용설비비) * 세율(기본 2.4%) 실시간 자동 계산
// 전기세금 = (전기사용요금 + 공용설비비) * 세율(기본 2.4%) 실시간 자동 계산 (올림 처리 및 수동입력 지원)
function autoCalcTax(force = false) {
    let taxInput = findInvoiceItemInput('pbjt') || findInvoiceItemInput('전기세금');
    const elecInput = findInvoiceItemInput('전기 사용요금') || findInvoiceItemInput('전기사용요금');
    const utilInput = findInvoiceItemInput('공용설비비') || findInvoiceItemInput('utilitas');
    const taxRateInput = invoiceEl('invoiceMeter_electricity_tax_rate');

    if (!taxInput) {
        addInvoiceItem({ name: '전기세금 (PBJT-TL)', amount: '0' });
        taxInput = findInvoiceItemInput('pbjt') || findInvoiceItemInput('전기세금');
    }
    if (!taxInput) return;

    // 사용자가 직접 세금을 수동 입력 중인 경우 강제 덮어쓰기 방지
    if (!force && isUserTaxManual && taxInput.value.trim() !== '') {
        return;
    }

    const elecAmt = elecInput ? parseFloat(elecInput.value) || 0 : 0;
    const utilAmt = utilInput ? parseFloat(utilInput.value) || 0 : 0;
    const taxRate = taxRateInput ? parseFloat(taxRateInput.value) || 2.4 : 2.4;

    if (elecAmt > 0 || utilAmt > 0) {
        // 계산된 세금 올림(Math.ceil) 처리 및 소수점 없는 정수 표시
        const taxVal = Math.ceil((elecAmt + utilAmt) * (taxRate / 100));
        taxInput.value = String(taxVal);
        updateInvoiceTotal();
    }
}

function autoCalcCharges(section) {
    const usage = parseFloat(invoiceEl(invoiceMeterId(section, 'usage')).value) || 0;
    const rate = parseFloat(invoiceEl(invoiceMeterId(section, 'rate')).value) || 0;

    if (section === 'electricity') {
        const elecInput = findInvoiceItemInput('전기 사용요금') || findInvoiceItemInput('전기사용요금');
        if (elecInput && usage > 0 && rate > 0) {
            elecInput.value = String(Math.ceil(usage * rate));
            autoCalcTax();
        }
    } else if (section === 'water') {
        const waterInput = findInvoiceItemInput('수도 사용요금') || findInvoiceItemInput('수도사용요금');
        if (waterInput && usage >= 0 && rate > 0) {
            waterInput.value = String(Math.ceil(usage * rate));
        }
        const subInput = findInvoiceItemInput('수도 기본료') || findInvoiceItemInput('기본료');
        const subMeterInput = invoiceEl('invoiceMeter_water_subscription');
        if (subInput && subMeterInput && (!subInput.value || subInput.value === '0')) {
            subInput.value = String(Math.ceil(parseFloat(subMeterInput.value) || 30400));
        }
        updateInvoiceTotal();
    }
}

// 청구 항목 행 추가 (삭제 버튼 제거 및 세금 직접 입력 지원)
function addInvoiceItem(item) {
    const list = invoiceEl('invoiceItems');
    if (list.children.length >= 50) return alert('항목은 최대 50개까지 추가할 수 있습니다.');
    const row = document.createElement('div');
    row.className = 'invoice-item-row';
    row.innerHTML = `
        <input type="text" class="invoice-item-name" aria-label="청구 항목명" placeholder="항목명" maxlength="150" required>
        <input type="number" class="invoice-item-amount" aria-label="항목 금액" placeholder="금액" min="-9999999999999" max="9999999999999" step="1" required>
    `;
    const nameInput = row.querySelector('.invoice-item-name');
    const amtInput = row.querySelector('.invoice-item-amount');

    nameInput.value = item ? item.name : '';
    if (item && item.amount !== undefined && item.amount !== null && item.amount !== '') {
        amtInput.value = String(Math.ceil(parseFloat(item.amount) || 0));
    } else {
        amtInput.value = '0';
    }

    amtInput.oninput = () => {
        const n = nameInput.value.toLowerCase();
        // 세금 부분을 직접 타이핑하는 경우 수동 입력 플래그 활성화
        if (n.includes('pbjt') || n.includes('전기세금') || n.includes('세금')) {
            isUserTaxManual = (amtInput.value.trim() !== '');
        } else if (n.includes('전기') || n.includes('utilitas') || n.includes('공용')) {
            autoCalcTax(false);
        }
        updateInvoiceTotal();
    };

    list.append(row);
    ++invoiceRevision;
    updateInvoiceTotal();
}

function updateInvoicePaid() {
    const disabled = invoiceEl('invoicePaid').value !== '1';
    invoiceEl('invoicePaidDate').disabled = disabled;
    if (disabled) invoiceEl('invoicePaidDate').value = '';
}

function invoiceMeterId(section, key) { return `invoiceMeter_${section}_${key}`; }

function autoCalcUsage(section) {
    const prevInput = invoiceEl(invoiceMeterId(section, 'previous'));
    const currInput = invoiceEl(invoiceMeterId(section, 'current'));
    const usageInput = invoiceEl(invoiceMeterId(section, 'usage'));
    if (!prevInput || !currInput || !usageInput) return;

    const prevStr = prevInput.value.trim();
    const currStr = currInput.value.trim();
    if (prevStr !== '' && currStr !== '') {
        const prev = parseFloat(prevStr);
        const curr = parseFloat(currStr);
        if (!isNaN(prev) && !isNaN(curr) && curr >= prev) {
            usageInput.value = (curr - prev).toFixed(2);
            autoCalcCharges(section);
        }
    }
}

// -------------------------------------------------------------------
// 검침 정보 입력 폼: 사용량 1열 3개 배치 (이전, 현재, 사용량) & 아래 단가/세율
// -------------------------------------------------------------------
function createInvoiceMeters() {
    const container = invoiceEl('invoiceMeterFields');
    container.innerHTML = `
        <!-- 전기 (kWh) -->
        <div class="invoice-meter" style="margin-bottom:12px;">
            <h4 style="margin-bottom:6px; color:#f59e0b;">⚡ 전기 (kWh)</h4>
            <!-- 1열 3개 배치: 이전 검침, 현재 검침, 사용량 -->
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px;">
                <label>이전 검침
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_electricity_previous" placeholder="월초">
                </label>
                <label>현재 검침
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_electricity_current" placeholder="월말">
                </label>
                <label>사용량
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_electricity_usage" placeholder="자동/직접">
                </label>
            </div>
            <!-- 아래 줄: 단가 (Rp) & 세율 (%) -->
            <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:6px; margin-top:6px;">
                <label>단가 (Rp)
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_electricity_rate" placeholder="kWh 단가">
                </label>
                <label>세율 (%)
                    <input type="number" min="0" max="100" step="0.1" id="invoiceMeter_electricity_tax_rate" value="2.4" placeholder="세율 (기본 2.4%)">
                </label>
            </div>
        </div>

        <!-- 수도 (m³) -->
        <div class="invoice-meter">
            <h4 style="margin-bottom:6px; color:#06b6d4;">💧 수도 (m³)</h4>
            <!-- 1열 3개 배치: 이전 검침, 현재 검침, 사용량 -->
            <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:6px;">
                <label>이전 검침
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_water_previous" placeholder="월초">
                </label>
                <label>현재 검침
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_water_current" placeholder="월말">
                </label>
                <label>사용량
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_water_usage" placeholder="자동/직접">
                </label>
            </div>
            <!-- 아래 줄: 단가 (Rp) & 기본료 (Rp) -->
            <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:6px; margin-top:6px;">
                <label>단가 (Rp)
                    <input type="number" min="0" max="9999999999999.99" step="0.01" id="invoiceMeter_water_rate" placeholder="m³ 단가">
                </label>
                <label>기본료 (Rp)
                    <input type="number" min="0" max="9999999999999.99" step="1" id="invoiceMeter_water_subscription" value="30400" placeholder="기본료 (30,400)">
                </label>
            </div>
        </div>
    `;

    // 이벤트 리스너 연결
    ['electricity', 'water'].forEach(section => {
        const prevInput = invoiceEl(invoiceMeterId(section, 'previous'));
        const currInput = invoiceEl(invoiceMeterId(section, 'current'));
        const usageInput = invoiceEl(invoiceMeterId(section, 'usage'));
        const rateInput = invoiceEl(invoiceMeterId(section, 'rate'));

        if (prevInput) prevInput.addEventListener('input', () => autoCalcUsage(section));
        if (currInput) currInput.addEventListener('input', () => autoCalcUsage(section));
        if (usageInput) usageInput.addEventListener('input', () => autoCalcCharges(section));
        if (rateInput) rateInput.addEventListener('input', () => autoCalcCharges(section));
    });

    const taxRateInput = invoiceEl('invoiceMeter_electricity_tax_rate');
    if (taxRateInput) taxRateInput.addEventListener('input', autoCalcTax);
}
function clearInvoicePreview() {
    if (invoicePhotoUrl) URL.revokeObjectURL(invoicePhotoUrl);
    invoicePhotoUrl = null;
    invoiceEl('invoicePhotoPreview').hidden = true;
    invoiceEl('invoicePhotoPreview').removeAttribute('src');
}
function openInvoiceForm(row) {
    if (invoiceBusy) return;
    ++invoiceOcrGeneration; invoiceDraft = null; invoiceRawText = row ? row.ocr_text : '';
    invoiceEl('invoiceForm').reset(); clearInvoicePreview();
    invoiceEditingId = row ? row.id : null;
    invoiceEl('invoiceFormTitle').textContent = row ? '인보이스 수정' : '인보이스 등록';
    const now = new Date();
    invoiceEl('invoiceMonth').value = row ? row.billing_month : `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    for (const [id, key] of [['invoiceNumber','invoice_number'],['invoiceProperty','property_name'],['invoiceUnit','unit_name'],['invoiceDue','due_date'],['invoiceBilled','billed_total'],['invoiceMemo','memo'],['invoicePaidDate','paid_date']]) invoiceEl(id).value = row ? row[key] : '';
    invoiceEl('invoicePaid').value = row && row.paid ? '1' : '0'; updateInvoicePaid();
    for (const [id, key] of [['invoicePeriodStart','period_start'], ['invoicePeriodEnd','period_end']]) invoiceEl(id).value = row ? row.readings[key] || '' : '';
    for (const section of ['electricity','water']) for (const key of ['previous','current','usage','rate']) invoiceEl(invoiceMeterId(section,key)).value = row ? (row.readings[section] || {})[key] || '' : '';
    
    // 전기 세율(2.4%) 및 수도 기본료(30,400) 바인딩
    if (invoiceEl('invoiceMeter_electricity_tax_rate')) {
        invoiceEl('invoiceMeter_electricity_tax_rate').value = (row && row.readings && row.readings.electricity && row.readings.electricity.tax_rate) ? row.readings.electricity.tax_rate : '2.4';
    }
    if (invoiceEl('invoiceMeter_water_subscription')) {
        invoiceEl('invoiceMeter_water_subscription').value = (row && row.readings && row.readings.water && row.readings.water.subscription) ? row.readings.water.subscription : '30400';
    }

    invoiceEl('invoiceItems').replaceChildren();
    isUserTaxManual = !!(row && row.items); // 수정 모드 시 기존 저장된 세금 우선 보존
    const itemsToRender = prepareInvoiceItems(row ? row.items : null);
    itemsToRender.forEach(addInvoiceItem);

    invoiceEl('invoiceRemovePhotoLabel').hidden = !(row && row.photo_path);
    if (row && row.photo_path) { invoiceEl('invoicePhotoPreview').src = row.photo_path; invoiceEl('invoicePhotoPreview').hidden = false; }
    invoiceEl('invoiceOcrText').textContent = invoiceRawText;
    invoiceEl('invoiceOcrWrap').hidden = !invoiceRawText;
    invoiceEl('invoiceApplyOcr').hidden = true;
    invoiceEl('invoiceAiButton').hidden = true;
    invoiceEl('invoiceAiButton').disabled = false;
    invoiceEl('invoiceOcrStatus').textContent = '';
    invoiceEl('invoiceFormStatus').textContent = '';
    invoiceEl('invoiceOcrButton').disabled = false;
    invoiceEl('invoiceForm').hidden = false;
    invoiceRevision = 0;
    if (!row) {
        autoCalcTax(true);
    }
    updateInvoiceTotal();
    invoiceEl('invoiceForm').scrollIntoView({block:'start',behavior:'smooth'});
}
function newInvoice() { openInvoiceForm(null); }
function editInvoice(id) { const row = invoices.find(row => row.id === id); if (row) openInvoiceForm(row); }
function cancelInvoiceEdit() {
    if (invoiceBusy) return;
    ++invoiceOcrGeneration; clearInvoicePreview(); invoiceEl('invoiceForm').hidden = true; invoiceEditingId = null;
}
async function onInvoicePhotoChange() {
    ++invoiceOcrGeneration; clearInvoicePreview(); invoiceDraft = null; invoiceRawText = '';
    invoiceEl('invoiceAiButton').hidden = true;
    invoiceEl('invoiceOcrText').textContent = ''; invoiceEl('invoiceOcrWrap').hidden = true; invoiceEl('invoiceApplyOcr').hidden = true;
    invoiceEl('invoiceOcrStatus').textContent = '';
    const file = invoiceEl('invoicePhoto').files[0]; if (!file) return;
    if (file.size > 12 * 1024 * 1024) { invoiceEl('invoicePhoto').value = ''; return alert('사진은 12MB 이하로 선택해 주세요.'); }
    invoicePhotoUrl = URL.createObjectURL(file); invoiceEl('invoicePhotoPreview').src = invoicePhotoUrl; invoiceEl('invoicePhotoPreview').hidden = false;
    invoiceEl('invoiceRemovePhoto').checked = false;
    if ((invoiceEditingId !== null || invoiceRevision > 0) && !confirm('선택한 사진을 읽어 기존 입력값에 반영하시겠습니까? 취소하면 사진만 첨부합니다.')) return;
    await recognizeInvoice();
}
async function recognizeInvoice(useAi = false) {
    const file = invoiceEl('invoicePhoto').files[0];
    if (!file) return alert('읽을 인보이스 사진을 선택해 주세요.');
    const generation = ++invoiceOcrGeneration; const revision = invoiceRevision;
    const form = new FormData(); form.append('photo', file);
    invoiceEl('invoiceOcrButton').disabled = true; invoiceEl('invoiceAiButton').disabled = true;
    invoiceEl('invoiceOcrStatus').textContent = useAi ? 'OCR 확인 후 AI로 보완 중입니다…' : 'OCR로 인보이스 값을 읽고 있습니다…';
    try {
        const data = await apiRequest(useAi ? '/api/expenses/ai' : '/api/expenses/ocr',{method:'POST',body:form});
        if (generation !== invoiceOcrGeneration) return;
        invoiceDraft = data.draft; invoiceRawText = data.text;
        invoiceEl('invoiceAiButton').hidden = useAi || !data.needs_review;
        invoiceEl('invoiceOcrText').textContent = data.text || '(인식된 문자가 없습니다.)'; invoiceEl('invoiceOcrWrap').hidden = false;
        if (revision === invoiceRevision) applyInvoiceOcr(false);
        else { invoiceEl('invoiceApplyOcr').hidden = false; invoiceEl('invoiceOcrStatus').textContent = '인식 중 입력내용이 변경되어 자동 반영하지 않았습니다. 인식값 적용 버튼으로 반영할 수 있습니다.'; }
    } catch (error) { if (generation === invoiceOcrGeneration) { invoiceEl('invoiceOcrStatus').textContent = error.message + ' 수동 입력으로 저장할 수 있습니다.'; if (!useAi) invoiceEl('invoiceAiButton').hidden = false; } }
    finally { if (generation === invoiceOcrGeneration) { invoiceEl('invoiceOcrButton').disabled = false; invoiceEl('invoiceAiButton').disabled = false; } }
}
function applyInvoiceOcr(confirmReplace) {
    if (!invoiceDraft || (confirmReplace && !confirm('현재 입력값에 인식값을 반영하시겠습니까?'))) return;
    const draft = invoiceDraft;
    for (const [id,key] of [['invoiceMonth','billing_month'],['invoiceNumber','invoice_number'],['invoiceProperty','property_name'],['invoiceUnit','unit_name'],['invoiceDue','due_date'],['invoiceBilled','billed_total']]) {
        if (draft[key] !== '') {
            if (id === 'invoiceBilled') {
                invoiceEl(id).value = Math.ceil(parseFloat(draft[key]) || 0);
            } else {
                invoiceEl(id).value = draft[key];
            }
        }
    }
    
    // 기본 6개 항목(수도 사용요금 포함) 무조건 구성
    const itemsToRender = prepareInvoiceItems(draft.items);
    invoiceEl('invoiceItems').replaceChildren();
    itemsToRender.forEach(addInvoiceItem);

    for (const section of ['electricity','water']) {
        for (const key of ['previous','current','usage','rate']) {
            if ((draft.readings[section] || {})[key] !== undefined) {
                invoiceEl(invoiceMeterId(section,key)).value = draft.readings[section][key];
            }
        }
    }
    if (invoiceEl('invoiceMeter_electricity_tax_rate') && (draft.readings.electricity || {}).tax_rate) {
        invoiceEl('invoiceMeter_electricity_tax_rate').value = draft.readings.electricity.tax_rate;
    }
    if (invoiceEl('invoiceMeter_water_subscription') && (draft.readings.water || {}).subscription) {
        invoiceEl('invoiceMeter_water_subscription').value = Math.ceil(parseFloat(draft.readings.water.subscription) || 30400);
    }
    for (const [id,key] of [['invoicePeriodStart','period_start'],['invoicePeriodEnd','period_end']]) if (draft.readings[key]) invoiceEl(id).value = draft.readings[key];

    isUserTaxManual = false;
    autoCalcTax(true);
    ++invoiceRevision; updateInvoiceTotal(); invoiceEl('invoiceApplyOcr').hidden = true;
    invoiceEl('invoiceOcrStatus').textContent = `인식값을 반영했습니다. ${(draft.calculated_fields || []).join(' / ')} 인보이스 번호·호수·금액을 원본과 확인한 뒤 저장해 주세요.${!draft.items.length ? ' 청구 항목을 인식하지 못해 직접 입력이 필요합니다.' : ''}`;
}
async function saveInvoice(event) {
    event.preventDefault(); if (invoiceBusy) return;
    const items = Array.from(invoiceEl('invoiceItems').children).map(row => ({name:row.querySelector('.invoice-item-name').value.trim(),amount:row.querySelector('.invoice-item-amount').value}));
    const readings = {period_start:invoiceEl('invoicePeriodStart').value,period_end:invoiceEl('invoicePeriodEnd').value};
    for (const section of ['electricity','water']) {
        readings[section]={};
        for (const key of ['previous','current','usage','rate']) readings[section][key] = invoiceEl(invoiceMeterId(section,key)).value;
    }
    readings.electricity.tax_rate = invoiceEl('invoiceMeter_electricity_tax_rate') ? invoiceEl('invoiceMeter_electricity_tax_rate').value : '2.4';
    readings.water.subscription = invoiceEl('invoiceMeter_water_subscription') ? invoiceEl('invoiceMeter_water_subscription').value : '30400';

    const data = {billing_month:invoiceEl('invoiceMonth').value, invoice_number:invoiceEl('invoiceNumber').value,property_name:invoiceEl('invoiceProperty').value,unit_name:invoiceEl('invoiceUnit').value,due_date:invoiceEl('invoiceDue').value,paid:invoiceEl('invoicePaid').value==='1',paid_date:invoiceEl('invoicePaidDate').value,items,readings,billed_total:invoiceEl('invoiceBilled').value,memo:invoiceEl('invoiceMemo').value,ocr_text:invoiceRawText};
    const form = new FormData(); form.append('data',JSON.stringify(data)); form.append('remove_photo',invoiceEl('invoiceRemovePhoto').checked?'1':'0');
    const file = invoiceEl('invoicePhoto').files[0]; if(file) form.append('photo',file);
    invoiceBusy = true; invoiceEl('invoiceSaveButton').disabled=true; invoiceEl('invoiceFormStatus').textContent='저장 중입니다…';
    try {
        await apiRequest('/api/expenses/invoices'+(invoiceEditingId===null?'':`/${invoiceEditingId}`),{method:invoiceEditingId===null?'POST':'PUT',body:form});
        ++invoiceOcrGeneration; invoiceEl('invoiceForm').hidden=true; clearInvoicePreview(); invoiceEditingId=null; await loadInvoices();
    } catch(error) { invoiceEl('invoiceFormStatus').textContent=error.message; }
    finally { invoiceBusy=false; invoiceEl('invoiceSaveButton').disabled=false; }
}
async function loadInvoices() {
    invoiceEl('invoiceListStatus').textContent='인보이스를 불러오는 중입니다…';
    try {
        invoices = await apiRequest('/api/expenses/invoices', { cache: 'no-store' });
        if (!Array.isArray(invoices)) throw new Error('목록 형식이 올바르지 않습니다.');
        renderInvoices();
        renderInvoiceCharts();
        invoiceEl('invoiceListStatus').textContent = '';
    } catch(error) {
        invoiceEl('invoiceListStatus').textContent = error.message;
    }
}
function resetInvoiceFilters(){invoiceEl('invoiceFilterMonth').value='';invoiceEl('invoiceFilterPaid').value='';renderInvoices();}

function renderInvoiceCharts() {
    const feeContainer = invoiceEl('invoiceFeeChart');
    const usageContainer = invoiceEl('invoiceUsageChart');
    if (!feeContainer || !usageContainer) return;

    if (!invoices.length) {
        feeContainer.innerHTML = '<p class="score-help" style="text-align:center;padding:12px 0;">등록된 인보이스가 없습니다.</p>';
        usageContainer.innerHTML = '<p class="score-help" style="text-align:center;padding:12px 0;">인보이스를 등록하시면 전기 및 수도 사용량 그래프가 표시됩니다.</p>';
        return;
    }

    // 월별 오름차순 정렬 (최근 최대 12건)
    const sorted = [...invoices].sort((a, b) => a.billing_month.localeCompare(b.billing_month)).slice(-12);
    const months = sorted.map(r => r.billing_month);
    const fees = sorted.map(r => parseFloat(r.billed_total) || 0);
    const elecs = sorted.map(r => parseFloat((r.readings && r.readings.electricity && r.readings.electricity.usage) || 0));
    const waters = sorted.map(r => parseFloat((r.readings && r.readings.water && r.readings.water.usage) || 0));

    // 1. 청구총액 차트
    const maxFee = Math.max(...fees, 100000);
    const width = 420, height = 140, padX = 46, padY = 20;
    const chartW = width - padX - 15, chartH = height - padY * 2;
    const n = sorted.length;
    const colW = Math.max(12, Math.min(28, chartW / n - 8));

    let feeBars = '';
    let feeXLabels = '';
    for (let i = 0; i < n; i++) {
        const x = padX + (chartW / n) * i + (chartW / n - colW) / 2;
        const barH = (fees[i] / maxFee) * chartH;
        const y = height - padY - barH;
        const feeText = fees[i] >= 1000000 ? (fees[i] / 1000000).toFixed(1) + 'M' : Math.round(fees[i] / 1000) + 'k';
        feeBars += `
            <g class="chart-col">
                <rect x="${x}" y="${y}" width="${colW}" height="${barH}" rx="3" fill="#3b82f6" opacity="0.88" />
                <text x="${x + colW / 2}" y="${y - 4}" text-anchor="middle" font-size="8.5" fill="#93c5fd">${feeText}</text>
            </g>
        `;
        const shortMonth = months[i].replace(/^\d{4}-/, '');
        feeXLabels += `<text x="${x + colW / 2}" y="${height - 5}" text-anchor="middle" font-size="9" fill="#9ca3af">${shortMonth}월</text>`;
    }

    const maxFeeText = maxFee >= 1000000 ? (maxFee / 1000000).toFixed(1) + 'M' : Math.round(maxFee / 1000) + 'k';
    feeContainer.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;overflow:visible;">
            <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#374151" stroke-width="1"/>
            <line x1="${padX}" y1="${height - padY}" x2="${width - 10}" y2="${height - padY}" stroke="#374151" stroke-width="1"/>
            <text x="${padX - 4}" y="${padY + 4}" text-anchor="end" font-size="8.5" fill="#6b7280">${maxFeeText}</text>
            <text x="${padX - 4}" y="${height - padY}" text-anchor="end" font-size="8.5" fill="#6b7280">0</text>
            ${feeBars}
            ${feeXLabels}
        </svg>
    `;

    // 2. 사용량 차트 (전기 kWh vs 수도 m³)
    const maxElec = Math.max(...elecs, 10);
    const maxWater = Math.max(...waters, 5);
    const maxUsage = Math.max(maxElec, maxWater * 2, 20);

    let usageBars = '';
    let usageXLabels = '';
    for (let i = 0; i < n; i++) {
        const x = padX + (chartW / n) * i + (chartW / n - colW) / 2;
        const eH = (elecs[i] / maxUsage) * chartH;
        const wH = (waters[i] / maxUsage) * chartH;
        const halfW = Math.max(4, colW / 2 - 1);

        usageBars += `
            <g class="chart-col">
                <rect x="${x}" y="${height - padY - eH}" width="${halfW}" height="${eH}" fill="#f59e0b" opacity="0.95" rx="2" />
                <rect x="${x + halfW + 1}" y="${height - padY - wH}" width="${halfW}" height="${wH}" fill="#06b6d4" opacity="0.95" rx="2" />
                ${elecs[i] > 0 ? `<text x="${x + halfW / 2}" y="${height - padY - eH - 3}" text-anchor="middle" font-size="8" fill="#fbbf24">${Math.round(elecs[i])}</text>` : ''}
                ${waters[i] > 0 ? `<text x="${x + halfW + 1 + halfW / 2}" y="${height - padY - wH - 3}" text-anchor="middle" font-size="8" fill="#67e8f9">${Math.round(waters[i])}</text>` : ''}
            </g>
        `;
        const shortMonth = months[i].replace(/^\d{4}-/, '');
        usageXLabels += `<text x="${x + colW / 2}" y="${height - 5}" text-anchor="middle" font-size="9" fill="#9ca3af">${shortMonth}월</text>`;
    }

    usageContainer.innerHTML = `
        <div style="font-size:11px; margin-bottom:4px; display:flex; gap:10px; justify-content:flex-end;">
            <span style="color:#f59e0b;">■ 전기 (kWh)</span>
            <span style="color:#06b6d4;">■ 수도 (m³)</span>
        </div>
        <svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;overflow:visible;">
            <line x1="${padX}" y1="${padY}" x2="${padX}" y2="${height - padY}" stroke="#374151" stroke-width="1"/>
            <line x1="${padX}" y1="${height - padY}" x2="${width - 10}" y2="${height - padY}" stroke="#374151" stroke-width="1"/>
            <text x="${padX - 4}" y="${padY + 4}" text-anchor="end" font-size="8.5" fill="#6b7280">${Math.round(maxUsage)}</text>
            <text x="${padX - 4}" y="${height - padY}" text-anchor="end" font-size="8.5" fill="#6b7280">0</text>
            ${usageBars}
            ${usageXLabels}
        </svg>
    `;
}

function renderInvoices(){
    const month=invoiceEl('invoiceFilterMonth').value,status=invoiceEl('invoiceFilterPaid').value;
    const rows=invoices.filter(row=>(!month||row.billing_month===month)&&(!status||String(Number(row.paid))===status));
    const total=rows.reduce((n,row)=>n+invoiceCents(row.billed_total),0n);
    const avgMonth = rows.length ? total / BigInt(rows.length) : 0n;
    invoiceEl('invoiceSummary').innerHTML=[['조회 인보이스',`${rows.length}건`],['청구 합계',invoiceMoney(total)],['월평균 청구액',invoiceMoney(avgMonth)]].map(([label,value])=>`<div><span>${label}</span><strong>${value}</strong></div>`).join('');
    const list=invoiceEl('invoiceList');list.replaceChildren();
    if(!rows.length){list.textContent='조회된 인보이스가 없습니다.';return;}
    rows.forEach(row=>{
        let rowElec = 0n, rowWater = 0n;
        (row.items || []).forEach(it => {
            const n = (it.name || '').toLowerCase();
            const c = invoiceCents(it.amount);
            if (c !== null) {
                if (n.includes('전기') || n.includes('utilitas') || n.includes('공용') || n.includes('pbjt') || n.includes('세금') || n.includes('행정비') || n.includes('administrasi') || n.includes('admin')) rowElec += c;
                else if (n.includes('수도') || n.includes('기본료') || n.includes('air') || n.includes('abonemen')) rowWater += c;
            }
        });

        const card=document.createElement('article');card.className='input-card invoice-card';
        card.innerHTML=`
            <div class="score-toolbar">
                <span>${escapeHtml(row.billing_month)}</span>
                <span class="invoice-paid ${row.paid?'is-paid':''}">${row.paid?'납부 완료':'미납'}</span>
                <div class="log-actions">
                    <button type="button" class="btn-log-action invoice-edit">수정</button>
                    <button type="button" class="btn-log-action btn-log-delete invoice-delete">삭제</button>
                </div>
            </div>
            <h3>${escapeHtml(row.property_name||'관리비 인보이스')} ${escapeHtml(row.unit_name)}</h3>
            <p class="score-help">번호 ${escapeHtml(row.invoice_number||'—')} · 납기 ${escapeHtml(row.due_date||'—')}</p>
            <div style="display:flex; justify-content:space-between; font-size:0.83rem; margin:6px 0; padding:6px 8px; background:rgba(255,255,255,0.03); border-radius:4px;">
                <span style="color:#fbbf24; font-weight:600;">⚡ 전기: ${invoiceMoney(rowElec)}</span>
                <span style="color:#67e8f9; font-weight:600;">💧 수도: ${invoiceMoney(rowWater)}</span>
            </div>
            <div class="invoice-sum"><span>청구총액</span><strong>${invoiceMoney(row.billed_total)}</strong></div>
        `;
        card.querySelector('.invoice-edit').onclick=()=>editInvoice(row.id);card.querySelector('.invoice-delete').onclick=()=>deleteInvoice(row.id);
        const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='항목 · 검침 · 원본 보기';details.append(summary);
        row.items.forEach(item=>{const p=document.createElement('p');p.className='invoice-detail-line';const label=document.createElement('span');label.textContent=item.name;const n=document.createElement('span');n.textContent=invoiceMoney(item.amount);p.append(label,n);details.append(p);});
        if(invoiceCents(row.difference)!==0n){const p=document.createElement('p');p.className='score-help invoice-warning';p.textContent=`청구총액과 항목 합계 차이: ${invoiceMoney(row.difference)}`;details.append(p);}
        for(const [section,label] of [['electricity','전기'],['water','수도']]){const meter=row.readings[section]||{};if(Object.keys(meter).length){const p=document.createElement('p');p.className='score-help';p.textContent=`${label}: 이전 ${meter.previous??'—'} → 현재 ${meter.current??'—'} / 사용 ${meter.usage??'—'} / 단가 ${meter.rate?invoiceMoney(meter.rate):'—'}`;details.append(p);}}
        if(row.readings.period_start||row.readings.period_end){const p=document.createElement('p');p.className='score-help';p.textContent=`사용기간: ${row.readings.period_start||'—'} ~ ${row.readings.period_end||'—'}`;details.append(p);}
        if(row.paid_date){const p=document.createElement('p');p.className='score-help';p.textContent=`납부일: ${row.paid_date}`;details.append(p);}
        if(row.memo){const p=document.createElement('p');p.className='score-memo';p.textContent=row.memo;details.append(p);}
        if(row.photo_path){const a=document.createElement('a');a.href=row.photo_path;a.target='_blank';a.rel='noopener';a.className='score-photo-link';const img=document.createElement('img');img.src=row.photo_path;img.alt='관리비 인보이스 원본 열기';img.loading='lazy';a.append(img);details.append(a);}
        if(row.ocr_text){const source=document.createElement('details'),title=document.createElement('summary'),pre=document.createElement('pre');title.textContent='인식 원문';pre.className='invoice-ocr-source';pre.textContent=row.ocr_text;source.append(title,pre);details.append(source);}
        card.append(details);list.append(card);
    });
    renderInvoiceCharts();
}
async function deleteInvoice(id){
    if(invoiceBusy||!confirm('이 인보이스와 첨부사진을 삭제하시겠습니까?'))return;
    invoiceBusy=true;
    try{await apiRequest(`/api/expenses/invoices/${id}`,{method:'DELETE'});invoiceBusy=false;if(invoiceEditingId===id)cancelInvoiceEdit();await loadInvoices();}
    catch(error){alert(error.message);}finally{invoiceBusy=false;}
}
document.addEventListener('DOMContentLoaded',()=>{
    createInvoiceMeters();
    invoiceEl('invoiceForm').addEventListener('submit',saveInvoice);
    invoiceEl('invoiceForm').addEventListener('input',event=>{if(event.target.id!=='invoicePhoto')++invoiceRevision;});
});
