"""HaruLog v2.7.0 — 관리비 인보이스 및 인도네시아어 청구서 OCR."""
import json
import os
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
from pathlib import Path

from flask import jsonify, request
from mysql.connector import Error
import score_service
import recognition_service

MONTHS = {name: i for i, names in enumerate([
    ('januari', 'january'), ('februari', 'february'), ('maret', 'march'), ('april',),
    ('mei', 'may'), ('juni', 'june'), ('juli', 'july'), ('agustus', 'august'),
    ('september',), ('oktober', 'october'), ('november',), ('desember', 'december')], 1) for name in names}
ITEMS = [('electricity', '전기 사용요금'), ('utility', '공용설비비 (Utilitas)'), ('tax', '전기세금 (PBJT-TL)'),
         ('admin', '행정비'), ('water', '수도 사용요금'), ('subscription', '수도 기본료')]


def init_schema(conn):
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS expense_invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            billing_month CHAR(7) NOT NULL,
            invoice_number VARCHAR(100) NOT NULL,
            property_name VARCHAR(150) NOT NULL,
            unit_name VARCHAR(80) NOT NULL,
            due_date DATE NULL,
            paid_date DATE NULL,
            paid TINYINT NOT NULL DEFAULT 0,
            items_json LONGTEXT NOT NULL,
            readings_json TEXT NOT NULL,
            billed_total DECIMAL(18,2) NOT NULL,
            memo TEXT NOT NULL,
            photo_path VARCHAR(255) NULL,
            ocr_text LONGTEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            INDEX idx_expense_month (billing_month, id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:
        cursor.close()


def amount(value, allow_negative=False):
    # API 형식은 천 단위 구분 없는 숫자 문자열. 계산된 금액은 올림(ROUND_CEILING) 처리.
    if isinstance(value, bool) or not re.fullmatch(r'-?\d{1,13}(?:\.\d{1,2})?', str(value)):
        raise ValueError('금액은 천 단위 구분 없이 입력해 주세요.')
    number = Decimal(str(value))
    if not allow_negative and number < 0:
        raise ValueError('청구총액과 검침값은 0 이상으로 입력해 주세요.')
    # 소수점 올림 처리 후 정수 기반으로 포맷
    return format(number.quantize(Decimal('1'), rounding=ROUND_CEILING).quantize(Decimal('.01')), 'f')


def localized_number(value):
    value = re.sub(r'[^\d,.-]', '', value)
    if ',' in value and '.' in value:
        value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        parts = value.split(',')
        value = ''.join(parts) if len(parts) > 2 or len(parts[-1]) == 3 else value.replace(',', '.')
    elif '.' in value:
        parts = value.split('.')
        if len(parts) > 2 or len(parts[-1]) == 3:
            value = ''.join(parts)
    try:
        return amount(value)
    except (ValueError, InvalidOperation):
        return None


def parse_date(text):
    match = re.search(r'\b(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})\b', text)
    if match and match[2].lower() in MONTHS:
        try:
            return date(int(match[3]), MONTHS[match[2].lower()], int(match[1])).isoformat()
        except ValueError:
            pass
    return ''


def parse_invoice(text):
    result = {'billing_month': '', 'invoice_number': '', 'property_name': '', 'unit_name': '', 'due_date': '',
              'items': [], 'billed_total': '', 'readings': {'electricity': {}, 'water': {}, 'period_start': '', 'period_end': ''}}
    found = {}
    section = None
    money_pattern = r'\d[\d.,]*'
    lines = text.splitlines()

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        low = line.lower()
        if not line:
            continue

        if 'nomor' in low or re.search(r'invoice\s*(?:no|number)', low):
            match = re.search(r'(?:nomor|invoice\s*(?:no|number))\s*[:.]?\s*([\w/.-]+)', line, re.I)
            if match: result['invoice_number'] = match[1]

        if 'bulan tagih' in low:
            match = re.search(r'([A-Za-z]+)\s+(20\d{2})', line)
            if match and match[1].lower() in MONTHS:
                result['billing_month'] = f'{match[2]}-{MONTHS[match[1].lower()]:02d}'

        if 'awal catat' in low: result['readings']['period_start'] = parse_date(line)
        if 'akhir catat' in low: result['readings']['period_end'] = parse_date(line)
        if 'jatuh tempo' in low:
            result['due_date'] = parse_date(line)

        if 'unit' in low and re.search(r'unit\s*:', line, re.I):
            match = re.search(r'unit\s*:\s*([^\s]+)', line, re.I)
            if match: result['unit_name'] = match[1]
            name = re.split(r'\bunit\s*:', line, flags=re.I)[0].strip()
            if name: result['property_name'] = name[:150]

        if 'pemakaian listrik & air' in low or 'calculation consumption' in low:
            continue

        if re.match(r'^\s*(?:listrik\s*/|electricity\b)', line, re.I):
            section = 'electricity'
        elif re.match(r'^\s*(?:air\s*/|water\b)', line, re.I):
            section = 'water'
        elif re.search(r'\b(?:pembayaran|bank\s+bri|keterlambatan)\b', line, re.I):
            section = None

        if section:
            # 검침 줄 인식 (이전, 현재, 사용량)
            # 이미 검침값을 읽었다면 다시 읽지 않음
            has_meter = ('previous' in result['readings'][section] and 'current' in result['readings'][section])
            if not has_meter:
                if any(k in low for k in ['awal', 'previous', 'akhir', 'current', 'consumption']) and not any(k in low for k in ['charge', 'utilitas', 'abudemen', 'subscript']):
                    pass # 헤더 라인은 스킵
                elif re.search(r'\d', line) and not any(k in low for k in ['charge', 'utilitas', 'pbit', 'pbjt', 'administrasi', 'abudemen', 'subscription', 'consumption :', 'tagih', 'catat', 'tempo']):
                    tokens = re.findall(r'\d[\d.,]*', line)
                    if len(tokens) >= 2:
                        cleaned_nums = [t for t in tokens if t not in ('(', ')', 'e')]
                        if len(cleaned_nums) == 4 and len(cleaned_nums[1]) <= 2:
                            # 예: 7.220 2 7.234 14 -> prev: 7.220, curr: 7.234, usage: 14
                            prev_val = localized_number(cleaned_nums[0])
                            curr_val = localized_number(cleaned_nums[2])
                            use_val = localized_number(cleaned_nums[3])
                            if prev_val and curr_val:
                                result['readings'][section]['previous'] = prev_val
                                result['readings'][section]['current'] = curr_val
                                if use_val: result['readings'][section]['usage'] = use_val
                        elif len(cleaned_nums) >= 3 and ('=' in line or '-' in line or '–' in line):
                            prev_val = localized_number(cleaned_nums[0])
                            curr_val = localized_number(cleaned_nums[1])
                            use_val = localized_number(cleaned_nums[2])
                            if prev_val and curr_val:
                                result['readings'][section]['previous'] = prev_val
                                result['readings'][section]['current'] = curr_val
                                if use_val: result['readings'][section]['usage'] = use_val
                        elif len(cleaned_nums) >= 2:
                            prev_val = localized_number(cleaned_nums[0])
                            curr_val = localized_number(cleaned_nums[1])
                            if prev_val and curr_val:
                                result['readings'][section]['previous'] = prev_val
                                result['readings'][section]['current'] = curr_val
                                if len(cleaned_nums) >= 3:
                                    use_val = localized_number(cleaned_nums[2])
                                    if use_val: result['readings'][section]['usage'] = use_val

            # 사용요금 줄
            if 'usage charge' in low or re.search(r'pemakaian\s*/', low):
                if 'consumption' not in low:
                    rate = re.search(r'Rp\.?\s*(' + money_pattern + ')', line, re.I)
                    if rate:
                        result['readings'][section]['rate'] = localized_number(rate[1]) or ''
                    tail = re.search(r'(' + money_pattern + r')\s*$', line)
                    after_rate = line[rate.end():].strip() if rate else ''
                    if tail and rate and after_rate:
                        found[section] = localized_number(tail[1])
                    elif section == 'water' and (result['readings']['water'].get('usage') == '0.00' or '=0' in line.replace(' ', '')):
                        found['water'] = '0.00'

        # 공용설비비
        if re.search(r'\butilitas\b', line, re.I):
            tail = re.search(r'(' + money_pattern + r')\s*$', line)
            if tail: found['utility'] = localized_number(tail[1])

        # 세금 (PBJT-TL / PBIT-TL)
        if re.search(r'\bP[B8][IJ]T[- ]?TL\b|\bPBJT[- ]?TL\b', line, re.I):
            tax_rate_m = re.search(r'(\d+[\d.,]*)\s*%', line)
            if tax_rate_m:
                parsed_rate = tax_rate_m[1].replace(',', '.')
                result['readings']['electricity']['tax_rate'] = parsed_rate
            tail = re.search(r'(' + money_pattern + r')\s*(?:bed|[a-z]*)?$', line, re.I)
            if tail:
                val = localized_number(tail[1])
                if val: found['tax'] = val

        # 행정비
        if re.search(r'biaya\s+administrasi', line, re.I):
            tail = re.search(r'(' + money_pattern + r')\s*$', line)
            if tail: found['admin'] = localized_number(tail[1])

        # 수도 기본료 (Abudemen / Subscription Fee)
        # 중요: 'Abudemen / Subscription Fee = Rp. 30.400 331.400' 에서 'Rp. 30.400'이 진짜 기본료!
        if re.search(r'ab[ou]demen|subscription\s+fee', line, re.I):
            sub_m = re.search(r'(?:ab[ou]demen|subscription\s+fee)\s*(?:=|:)?\s*Rp\.?\s*(' + money_pattern + ')', line, re.I)
            if sub_m:
                found['subscription'] = localized_number(sub_m[1])
            else:
                tokens = re.findall(r'\d[\d.,]*', line)
                if tokens: found['subscription'] = localized_number(tokens[0])
            if found.get('subscription'):
                result['readings']['water']['subscription'] = found['subscription']

        # 총액
        if ('total utilities' in low or 'total pemakaian listrik' in low):
            tail = re.search(r'(' + money_pattern + r')\s*$', line)
            if tail: result['billed_total'] = localized_number(tail[1]) or ''

    # billed_total 미인식 시 "Pemakaian Air / Water Consumption" 아래 단독 숫자 감지
    if not result['billed_total']:
        for i, l in enumerate(lines):
            if 'water consumption' in l.lower() or 'pemakaian air' in l.lower():
                for next_l in lines[i+1:i+4]:
                    cleaned = next_l.strip()
                    if re.fullmatch(r'[\d.,]+', cleaned):
                        parsed_total = localized_number(cleaned)
                        if parsed_total:
                            result['billed_total'] = parsed_total
                            break
                break

    calculated = []
    for s in ('electricity', 'water'):
        meter = result['readings'][s]
        if 'usage' not in meter and 'previous' in meter and 'current' in meter:
            usage = Decimal(meter['current']) - Decimal(meter['previous'])
            if usage >= 0:
                meter['usage'] = format(usage, '.2f')
                calculated.append(f'{s}: 사용량 = 현재 검침 - 이전 검침')
        if s not in found and meter.get('usage') is not None and meter.get('rate'):
            found[s] = format((Decimal(meter['usage']) * Decimal(meter['rate'])).quantize(Decimal('1'), rounding=ROUND_CEILING).quantize(Decimal('.01')), 'f')
            calculated.append(f'{s}: 사용요금 = 사용량 × 단가 (올림)')

    # 전기 세율 및 세금 = (전기사용요금 + 공용설비비) * 세율 계산 (올림 처리)
    result['readings']['electricity'].setdefault('tax_rate', '2.4')
    try:
        tax_rate = Decimal(str(result['readings']['electricity'].get('tax_rate', '2.4') or '2.4'))
    except InvalidOperation:
        tax_rate = Decimal('2.4')

    elec_amt = Decimal(found.get('electricity', '0.00') or '0.00')
    util_amt = Decimal(found.get('utility', '0.00') or '0.00')
    calc_tax = ((elec_amt + util_amt) * (tax_rate / Decimal('100'))).quantize(Decimal('1'), rounding=ROUND_CEILING).quantize(Decimal('.01'))

    # tax가 없거나 OCR 오인식(예: bed) 또는 차이가 큰 경우 자동 계산값 사용
    if 'tax' not in found or not found['tax'] or found['tax'] == '0.00':
        if elec_amt > 0 or util_amt > 0:
            found['tax'] = format(calc_tax, 'f')
            calculated.append(f'전기세금 = (전기사용요금 + 공용설비비) × {tax_rate}%')
    elif abs(Decimal(found['tax']) - calc_tax) > Decimal('10.00') and (elec_amt > 0 or util_amt > 0):
        found['tax'] = format(calc_tax, 'f')
        calculated.append(f'전기세금 = (전기사용요금 + 공용설비비) × {tax_rate}% [자동보정]')

    # 수도 기본료: 내역서에서 추출한 값 우선, 없으면 30400.00
    if 'subscription' not in found or not found['subscription'] or found['subscription'] == '0.00':
        found['subscription'] = '30400.00'
    result['readings']['water'].setdefault('subscription', found['subscription'])

    # 수도 사용요금 없으면 0.00
    if 'water' not in found or not found['water']:
        found['water'] = '0.00'

    # 기본 6개 항목 모두 포함 보장
    for key, _ in ITEMS:
        if key not in found:
            found[key] = '0.00'

    result['calculated_fields'] = calculated
    result['items'] = [{'name': label, 'amount': found[key]} for key, label in ITEMS]
    result['ocr_text'] = text[:30000]
    return result


def invoice_review(draft):
    reasons=[]
    if not draft.get('billing_month'): reasons.append('청구월을 읽지 못했습니다.')
    if not draft.get('billed_total'): reasons.append('인쇄 청구총액을 읽지 못했습니다.')
    if not draft.get('items'): reasons.append('청구 항목을 읽지 못했습니다.')
    if draft.get('billed_total') and draft.get('items'):
        total=sum((Decimal(row['amount']) for row in draft['items']),Decimal('0'))
        if abs(total-Decimal(draft['billed_total']))>Decimal('1'):
            reasons.append('항목 합계와 인쇄 청구총액이 1루피아를 초과하여 다릅니다.')
    return reasons


INVOICE_PROMPT = """인도네시아 관리비 인보이스를 읽으세요. 은행계좌/전화번호는 금액이 아닙니다.
문서에 적힌 원문 숫자만 추출하세요. 계산으로 누락값을 만들거나 합계에 맞춰 금액을 변경하지 마세요.
인쇄 소계를 items에 중복 포함하지 마세요. 전기·수도 사용요금, 공용설비비, 세금, 행정비, 기본료를 구분합니다.
금액은 천 단위 구분 없는 문자열로 반환합니다. 인도네시아 표기 1.699,53 = 1699.53입니다.
날짜는 ISO 형식. 모르는 값은 빈 문자열 또는 null.
형식: {"billing_month":"YYYY-MM", "invoice_number":"", "property_name":"", "unit_name":"", "due_date":"YYYY-MM-DD",
"billed_total":"", "items":[{"name":"항목명", "amount":""}],
"readings":{"period_start":"","period_end":"", "electricity":{"previous":"","current":"","usage":"","rate":""},
"water":{"previous":"","current":"","usage":"","rate":""}}}
"""


def normalize_ai_invoice(raw):
    if not isinstance(raw.get('items',[]),list): raise ValueError('AI 청구 항목 형식을 확인해 주세요.')
    draft={key:str(raw.get(key) or '')[:limit] for key,limit in [('billing_month',7),('invoice_number',100),('property_name',150),('unit_name',80),('due_date',10)]}
    draft['items']=[]
    for item in raw.get('items',[])[:50]:
        if not isinstance(item,dict): continue
        name=str(item.get('name') or '').strip()[:150]
        try: number=amount(item.get('amount'),True)
        except ValueError: continue
        if name: draft['items'].append({'name':name,'amount':number})
    try: draft['billed_total']=amount(raw.get('billed_total'))
    except ValueError: draft['billed_total']=''
    source=raw.get('readings') if isinstance(raw.get('readings'),dict) else {}
    draft['readings']={'electricity':{},'water':{}}
    for section in ('electricity','water'):
        meter=source.get(section) if isinstance(source.get(section),dict) else {}
        for key in ('previous','current','usage','rate'):
            try: draft['readings'][section][key]=amount(meter.get(key))
            except ValueError: pass
    for key in ('period_start','period_end'):
        value=source.get(key)
        try: draft['readings'][key]=date.fromisoformat(value).isoformat() if isinstance(value,str) else ''
        except ValueError: draft['readings'][key]=''
    for key in ('due_date',):
        try: draft[key]=date.fromisoformat(draft[key]).isoformat() if draft[key] else ''
        except ValueError: draft[key]=''
    if not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])',draft['billing_month']): draft['billing_month']=''
    draft['ocr_text']='AI 보완 추출: '+json.dumps(raw,ensure_ascii=False)[:29000]
    draft['calculated_fields']=[]
    return draft


def validate(data):
    if not isinstance(data, dict): raise ValueError('올바른 인보이스 정보를 입력해 주세요.')
    def string(key, limit, default=''):
        value = data.get(key, default)
        if not isinstance(value, str) or len(value) > limit: raise ValueError(f'{key} 입력값을 확인해 주세요.')
        return value.strip()
    month = string('billing_month', 7)
    if not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', month): raise ValueError('청구월을 확인해 주세요.')
    try: date.fromisoformat(month + '-01')
    except ValueError: raise ValueError('청구월을 확인해 주세요.') from None
    result = {k: string(k, n) for k, n in [('invoice_number',100),('property_name',150),('unit_name',80),('memo',5000),('ocr_text',30000)]}
    result['billing_month'] = month
    result['paid'] = data.get('paid', False)
    if not isinstance(result['paid'], bool): raise ValueError('납부 상태를 확인해 주세요.')
    for key in ('due_date', 'paid_date'):
        value = string(key, 10)
        if value:
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError()
                date.fromisoformat(value)
            except ValueError: raise ValueError('납기일 또는 납부일을 확인해 주세요.') from None
        result[key] = value or None
    if not result['paid']: result['paid_date'] = None
    items = data.get('items', [])
    if not isinstance(items, list) or not 1 <= len(items) <= 50: raise ValueError('청구 항목을 1~50개 입력해 주세요.')
    clean = []
    for row in items:
        if not isinstance(row, dict) or not isinstance(row.get('name'), str) or not row['name'].strip() or len(row['name']) > 150:
            raise ValueError('청구 항목명을 확인해 주세요.')
        clean.append({'name': row['name'].strip(), 'amount': amount(row.get('amount'), True)})
    result['items'] = clean
    result['billed_total'] = amount(data.get('billed_total'))
    readings = data.get('readings', {})
    if not isinstance(readings, dict): raise ValueError('검침 정보를 확인해 주세요.')
    result['readings'] = {}
    for section in ('electricity', 'water'):
        values = readings.get(section, {})
        if not isinstance(values, dict): raise ValueError('검침 정보를 확인해 주세요.')
        result['readings'][section] = {key: amount(values[key]) for key in ('previous','current','usage','rate') if values.get(key) not in (None, '')}
    for key in ('period_start', 'period_end'):
        value = readings.get(key, '')
        if value:
            try:
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError()
                date.fromisoformat(value)
            except ValueError: raise ValueError('사용기간 날짜를 확인해 주세요.') from None
        result['readings'][key] = value or ''
    return result


def register_routes(app, get_conn):
    def remove_photo(path):
        if path and path.startswith('/uploads/invoice_'):
            Path(app.config['UPLOAD_FOLDER'], os.path.basename(path)).unlink(missing_ok=True)

    @app.route('/api/expenses/ocr', methods=['POST'])
    def invoice_ocr():
        try:
            image = score_service.read_photo(request.files.get('photo'))
            text = score_service.run_ocr(image)
            draft = parse_invoice(text)
            reasons = invoice_review(draft)
            return jsonify({'draft': draft, 'text': text, 'source':'OCR', 'needs_review':bool(reasons), 'review_reasons':reasons})
        except ValueError as error: return jsonify({'error': str(error)}), 400
        except RuntimeError as error: return jsonify({'error': str(error)}), 503

    @app.route('/api/expenses/ai', methods=['POST'])
    def invoice_ai():
        try:
            image = score_service.read_photo(request.files.get('photo'))
            try:
                text = score_service.run_ocr(image)
                if not invoice_review(parse_invoice(text)):
                    return jsonify({'error':'OCR에서 필수값과 합계를 확인했습니다. OCR 결과를 먼저 검토해 주세요.'}),409
            except RuntimeError:
                pass
            draft = normalize_ai_invoice(recognition_service.ai_json(image, INVOICE_PROMPT))
            reasons = invoice_review(draft)
            return jsonify({'draft':draft,'text':draft['ocr_text'],'source':'AI','needs_review':bool(reasons),'review_reasons':reasons})
        except (ValueError,InvalidOperation) as error:return jsonify({'error':str(error)}),400
        except RuntimeError as error:return jsonify({'error':str(error)}),503

    @app.route('/api/expenses/invoices', methods=['GET'])
    def list_invoices():
        conn = get_conn()
        if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM expense_invoices ORDER BY billing_month DESC, id DESC')
            rows = cursor.fetchall()
            for row in rows:
                row['items'] = json.loads(row.pop('items_json'))
                row['readings'] = json.loads(row.pop('readings_json'))
                row['billed_total'] = str(row['billed_total'])
                row['items_total'] = str(sum((Decimal(x['amount']) for x in row['items']), Decimal('0.00')))
                row['difference'] = str(Decimal(row['billed_total']) - Decimal(row['items_total']))
                row['paid'] = bool(row['paid'])
                for key in ('due_date', 'paid_date'): row[key] = row[key].isoformat() if row[key] else ''
                for key in ('created_at','updated_at'): row[key] = row[key].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(rows)
        except (Error, ValueError, InvalidOperation):
            app.logger.exception('인보이스 목록 조회 실패')
            return jsonify({'error': '인보이스 목록을 불러오지 못했습니다.'}), 500
        finally:
            if cursor is not None: cursor.close()
            conn.close()

    @app.route('/api/expenses/invoices', methods=['POST'])
    @app.route('/api/expenses/invoices/<int:invoice_id>', methods=['PUT'])
    def save_invoice(invoice_id=None):
        try:
            source = request.get_json(silent=True) if request.is_json else json.loads(request.form.get('data',''))
            data = validate(source)
            file = request.files.get('photo')
            image = score_service.read_photo(file) if file and file.filename else None
        except (ValueError, InvalidOperation) as error: return jsonify({'error': str(error)}), 400
        conn = get_conn()
        if conn is None: return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        new_photo = old_photo = None
        committed = False
        try:
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            if invoice_id is not None:
                cursor.execute('SELECT photo_path FROM expense_invoices WHERE id=%s FOR UPDATE',(invoice_id,))
                row = cursor.fetchone()
                if row is None: return jsonify({'error': '인보이스가 없습니다.'}), 404
                old_photo = row['photo_path']
            if image:
                filename = 'invoice_' + uuid.uuid4().hex + '.jpg'
                new_photo = '/uploads/' + filename
                image.save(Path(app.config['UPLOAD_FOLDER']) / filename, format='JPEG', quality=92)
            stored_photo = new_photo or (None if request.form.get('remove_photo') == '1' else old_photo)
            values = (data['billing_month'],data['invoice_number'],data['property_name'],data['unit_name'],data['due_date'],
                      data['paid_date'],int(data['paid']),json.dumps(data['items'],ensure_ascii=False),json.dumps(data['readings']),
                      data['billed_total'],data['memo'],stored_photo,data['ocr_text'],datetime.now())
            if invoice_id is None:
                cursor.execute('''INSERT INTO expense_invoices (billing_month,invoice_number,property_name,unit_name,due_date,
                    paid_date,paid,items_json,readings_json,billed_total,memo,photo_path,ocr_text,updated_at,created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',values+(datetime.now(),))
                invoice_id = cursor.lastrowid
            else:
                cursor.execute('''UPDATE expense_invoices SET billing_month=%s,invoice_number=%s,property_name=%s,unit_name=%s,
                    due_date=%s,paid_date=%s,paid=%s,items_json=%s,readings_json=%s,billed_total=%s,memo=%s,photo_path=%s,
                    ocr_text=%s,updated_at=%s WHERE id=%s''',values+(invoice_id,))
            conn.commit(); committed = True
            if old_photo and old_photo != stored_photo:
                try: remove_photo(old_photo)
                except OSError: app.logger.warning('이전 인보이스 사진 정리 실패')
            return jsonify({'status':'success','id':invoice_id}), 201 if request.method=='POST' else 200
        except (Error,OSError):
            conn.rollback(); app.logger.exception('인보이스 저장 실패')
            return jsonify({'error':'인보이스를 저장하지 못했습니다.'}),500
        finally:
            if new_photo and not committed:
                try: remove_photo(new_photo)
                except OSError: app.logger.warning('미저장 인보이스 사진 정리 실패')
            if cursor is not None: cursor.close()
            conn.close()

    @app.route('/api/expenses/invoices/<int:invoice_id>', methods=['DELETE'])
    def delete_invoice(invoice_id):
        conn = get_conn()
        if conn is None: return jsonify({'error':'DB 연결 실패'}),503
        cursor = None
        try:
            conn.start_transaction();cursor=conn.cursor(dictionary=True)
            cursor.execute('SELECT photo_path FROM expense_invoices WHERE id=%s FOR UPDATE',(invoice_id,))
            row=cursor.fetchone()
            if row is None: return jsonify({'error':'인보이스가 없습니다.'}),404
            cursor.execute('DELETE FROM expense_invoices WHERE id=%s',(invoice_id,));conn.commit()
            try: remove_photo(row['photo_path'])
            except OSError: app.logger.warning('삭제한 인보이스 사진 정리 실패')
            return jsonify({'status':'success'})
        except Error:
            conn.rollback();app.logger.exception('인보이스 삭제 실패')
            return jsonify({'error':'인보이스를 삭제하지 못했습니다.'}),500
        finally:
            if cursor is not None:cursor.close()
            conn.close()
