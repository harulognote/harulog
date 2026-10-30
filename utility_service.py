"""HaruLog v2.0.0 — 공과금 직접입력 및 사용량·금액 통계 그래프 서비스."""
import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from flask import jsonify, request
from mysql.connector import Error


def init_schema(conn):
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS utility_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            billing_month CHAR(7) NOT NULL,
            electricity_usage DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            electricity_fee DECIMAL(18,2) NOT NULL DEFAULT 0.00,
            water_usage DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            water_fee DECIMAL(18,2) NOT NULL DEFAULT 0.00,
            telecom_fee DECIMAL(18,2) NOT NULL DEFAULT 0.00,
            gas_fee DECIMAL(18,2) NOT NULL DEFAULT 0.00,
            other_fee DECIMAL(18,2) NOT NULL DEFAULT 0.00,
            total_fee DECIMAL(18,2) NOT NULL DEFAULT 0.00,
            memo TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            UNIQUE KEY uq_utility_month (billing_month)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci''')
    finally:
        cursor.close()


def parse_decimal(val, default='0.00', maximum='9999999999999999.99'):
    if val is None or val == '':
        return Decimal(default)
    text = str(val).strip()
    if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?', text):
        raise ValueError('금액과 사용량은 0 이상의 숫자(소수점 최대 2자리)로 입력해 주세요.')
    try:
        value = Decimal(text.replace(',', ''))
        if not value.is_finite() or value > Decimal(maximum):
            raise ValueError('금액 또는 사용량이 허용 범위를 초과했습니다.')
        return value
    except InvalidOperation:
        raise ValueError('숫자 입력값을 확인해 주세요.') from None


def validate_utility_record(data):
    if not isinstance(data, dict):
        raise ValueError('올바른 공과금 데이터를 입력해 주세요.')

    month = str(data.get('billing_month', '')).strip()
    if not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])', month):
        raise ValueError('청구월을 YYYY-MM 형식으로 올바르게 입력해 주세요.')

    try:
        date.fromisoformat(month + '-01')
    except ValueError:
        raise ValueError('올바른 청구월을 입력해 주세요.') from None

    elec_usage = parse_decimal(data.get('electricity_usage'), maximum='99999999.99')
    elec_fee = parse_decimal(data.get('electricity_fee'))
    water_usage = parse_decimal(data.get('water_usage'), maximum='99999999.99')
    water_fee = parse_decimal(data.get('water_fee'))
    telecom_fee = parse_decimal(data.get('telecom_fee'))
    gas_fee = parse_decimal(data.get('gas_fee'))
    other_fee = parse_decimal(data.get('other_fee'))

    # 청구총액: 직접 입력값이 없으면 소계 합계로 계산
    auto_total = elec_fee + water_fee + telecom_fee + gas_fee + other_fee
    if auto_total > Decimal('9999999999999999.99'):
        raise ValueError('항목 합계가 허용 범위를 초과했습니다.')
    custom_total = data.get('total_fee')
    if custom_total is not None and str(custom_total).strip() != '':
        total_fee = parse_decimal(custom_total)
    else:
        total_fee = auto_total

    memo = str(data.get('memo', '')).strip()[:5000]

    return {
        'billing_month': month,
        'electricity_usage': format(elec_usage.quantize(Decimal('.01')), 'f'),
        'electricity_fee': format(elec_fee.quantize(Decimal('.01')), 'f'),
        'water_usage': format(water_usage.quantize(Decimal('.01')), 'f'),
        'water_fee': format(water_fee.quantize(Decimal('.01')), 'f'),
        'telecom_fee': format(telecom_fee.quantize(Decimal('.01')), 'f'),
        'gas_fee': format(gas_fee.quantize(Decimal('.01')), 'f'),
        'other_fee': format(other_fee.quantize(Decimal('.01')), 'f'),
        'total_fee': format(total_fee.quantize(Decimal('.01')), 'f'),
        'memo': memo
    }


def register_routes(app, get_conn):
    @app.route('/api/utility/records', methods=['GET'])
    def list_utility_records():
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM utility_records ORDER BY billing_month DESC, id DESC')
            rows = cursor.fetchall()
            for r in rows:
                for col in ('electricity_usage', 'electricity_fee', 'water_usage', 'water_fee',
                            'telecom_fee', 'gas_fee', 'other_fee', 'total_fee'):
                    r[col] = str(r[col])
                for col in ('created_at', 'updated_at'):
                    r[col] = r[col].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify(rows)
        except Error:
            app.logger.exception('공과금 목록 조회 실패')
            return jsonify({'error': '공과금 기록 목록을 불러오지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/utility/records', methods=['POST'])
    def add_utility_record():
        try:
            data = validate_utility_record(request.get_json(silent=True) or {})
        except ValueError as err:
            return jsonify({'error': str(err)}), 400

        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            now = datetime.now()
            cursor.execute('''INSERT INTO utility_records (
                billing_month, electricity_usage, electricity_fee, water_usage, water_fee,
                telecom_fee, gas_fee, other_fee, total_fee, memo, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['billing_month'], data['electricity_usage'], data['electricity_fee'],
                data['water_usage'], data['water_fee'], data['telecom_fee'], data['gas_fee'],
                data['other_fee'], data['total_fee'], data['memo'], now, now
            ))
            conn.commit()
            return jsonify({'status': 'success', 'billing_month': data['billing_month']}), 201
        except Error as error:
            conn.rollback()
            if error.errno == 1062:
                return jsonify({'error': '이미 등록된 청구월입니다. 기존 기록에서 수정해 주세요.'}), 409
            app.logger.exception('공과금 기록 저장 실패')
            return jsonify({'error': '공과금 기록을 저장하지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/utility/records/<int:record_id>', methods=['PUT'])
    def update_utility_record(record_id):
        try:
            data = validate_utility_record(request.get_json(silent=True) or {})
        except ValueError as err:
            return jsonify({'error': str(err)}), 400

        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT id FROM utility_records WHERE id=%s FOR UPDATE', (record_id,))
            if cursor.fetchone() is None:
                return jsonify({'error': '공과금 기록이 없습니다.'}), 404
            now = datetime.now()
            cursor.execute('''UPDATE utility_records SET
                billing_month=%s, electricity_usage=%s, electricity_fee=%s,
                water_usage=%s, water_fee=%s, telecom_fee=%s, gas_fee=%s,
                other_fee=%s, total_fee=%s, memo=%s, updated_at=%s
                WHERE id=%s
            ''', (
                data['billing_month'], data['electricity_usage'], data['electricity_fee'],
                data['water_usage'], data['water_fee'], data['telecom_fee'], data['gas_fee'],
                data['other_fee'], data['total_fee'], data['memo'], now, record_id
            ))
            conn.commit()
            return jsonify({'status': 'success'})
        except Error as error:
            conn.rollback()
            if error.errno == 1062:
                return jsonify({'error': '이미 등록된 청구월입니다. 기존 기록에서 수정해 주세요.'}), 409
            app.logger.exception('공과금 기록 수정 실패')
            return jsonify({'error': '공과금 기록 수정에 실패했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/utility/records/<int:record_id>', methods=['DELETE'])
    def delete_utility_record(record_id):
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM utility_records WHERE id=%s', (record_id,))
            conn.commit()
            return jsonify({'status': 'success'})
        except Error as error:
            conn.rollback()
            if error.errno == 1062:
                return jsonify({'error': '이미 등록된 청구월입니다. 기존 기록에서 수정해 주세요.'}), 409
            app.logger.exception('공과금 기록 삭제 실패')
            return jsonify({'error': '공과금 기록을 삭제하지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()

    @app.route('/api/utility/stats', methods=['GET'])
    def utility_stats():
        conn = get_conn()
        if conn is None:
            return jsonify({'error': 'DB 연결 실패'}), 503
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # 최근 등록된 24개 월을 선택한 다음 그래프에는 시간순으로 표시합니다.
            cursor.execute('''SELECT * FROM utility_records
                ORDER BY billing_month DESC LIMIT 24''')
            rows = cursor.fetchall()
            rows.reverse()
            months = []
            elec_fees = []
            water_fees = []
            telecom_fees = []
            total_fees = []
            elec_usages = []
            water_usages = []
            for r in rows:
                months.append(r['billing_month'])
                elec_fees.append(float(r['electricity_fee']))
                water_fees.append(float(r['water_fee']))
                telecom_fees.append(float(r['telecom_fee']))
                total_fees.append(float(r['total_fee']))
                elec_usages.append(float(r['electricity_usage']))
                water_usages.append(float(r['water_usage']))

            return jsonify({
                'months': months,
                'electricity_fee': elec_fees,
                'water_fee': water_fees,
                'telecom_fee': telecom_fees,
                'total_fee': total_fees,
                'electricity_usage': elec_usages,
                'water_usage': water_usages,
                'count': len(rows)
            })
        except Error:
            app.logger.exception('공과금 통계 조회 실패')
            return jsonify({'error': '통계 데이터를 불러오지 못했습니다.'}), 500
        finally:
            if cursor is not None:
                cursor.close()
            conn.close()
