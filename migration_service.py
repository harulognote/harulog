"""Manually selected migrations. No implicit data migration at server startup."""
import startup

LANGUAGES=[('영어','US'),('인도네시아어','ID'),('일본어','JP'),('중국어','CN'),('기타','ETC')]


def description(target):
    return {
        'schema':'[schema] 없는 테이블과 소스에 정의된 누락 컬럼을 준비합니다. 기존 값 변경·자료 복사·삭제는 하지 않습니다. DDL은 자동 커밋될 수 있습니다.',
        'languages':'[languages] 과거 언어명만 코드로 변환합니다. NULL/빈 값은 ID로 변환합니다. 기존 자료값이 변경됩니다.',
        'cats-to-pets':'[cats-to-pets] pets가 비어 있을 때 cats 자료 및 부모 관계를 복사합니다. cats 원본은 보존합니다. 서버 중단 후 실행하세요.',
    }[target]


def inspect(conn,target):
    if target=='schema':
        available=startup.schema_columns(conn)
        missing=[]
        for table,columns in startup.REQUIRED_COLUMNS.items():
            if table not in available:missing.append('신규 테이블: '+table)
            else:
                absent=set(columns.split())-available[table]
                if absent:missing.append('누락 컬럼(자동 지원 여부 검토 필요): '+table+'.'+', '.join(sorted(absent)))
        return '\n'.join(missing) or '필수 테이블/컬럼 이름 기준으로 누락 없음.'
    cursor=conn.cursor()
    try:
        if target=='languages':
            cursor.execute("SELECT COUNT(*) FROM study_videos WHERE language IN (%s,%s,%s,%s,%s) OR language IS NULL OR language=''",tuple(x[0] for x in LANGUAGES))
            return '변환 대상 영상 수: '+str(cursor.fetchone()[0])
        available=startup.schema_columns(conn)
        if 'cats' not in available:return 'cats 테이블이 없습니다. 이 이관은 필요하지 않습니다.'
        cursor.execute('SELECT COUNT(*) FROM cats');cats=cursor.fetchone()[0]
        if 'pets' not in available:return f'cats {cats}건. pets가 없습니다. 신규 테이블 준비를 먼저 수행하세요.'
        cursor.execute('SELECT COUNT(*) FROM pets');pets=cursor.fetchone()[0]
        return f'cats {cats}건 / pets {pets}건. pets가 비어 있는 경우에만 복사할 수 있습니다.'
    finally:cursor.close()


def apply(target):
    if target=='schema':
        import main
        main.prepare_schema()
        conn=startup.connect_database()
        try:startup.validate_schema(startup.schema_columns(conn))
        finally:conn.close()
        return
    conn=startup.connect_database()
    cursor=None
    try:
        conn.start_transaction()
        cursor=conn.cursor()
        if target=='languages':
            for old,new in LANGUAGES:
                cursor.execute('UPDATE study_videos SET language=%s WHERE language=%s',(new,old))
            cursor.execute("UPDATE study_videos SET language='ID' WHERE language IS NULL OR language=''")
        else:
            available=startup.schema_columns(conn)
            if 'cats' not in available:raise RuntimeError('cats 테이블이 없어 이관할 자료가 없습니다.')
            if 'pets' not in available:raise RuntimeError('pets 테이블을 먼저 준비해 주세요.')
            missing=set(startup.REQUIRED_COLUMNS['pets'].split())-available['pets']
            if missing:raise RuntimeError('pets 컬럼이 부족합니다: '+', '.join(sorted(missing)))
            cursor.execute('SELECT COUNT(*) FROM pets')
            if cursor.fetchone()[0]:raise RuntimeError('pets에 기존 자료가 있습니다. 덮어쓰거나 합치지 않고 이관을 중단합니다.')
            prefix=''
            owner_values=()
            if 'owner_id' in available['pets']:
                cursor.execute("SELECT value FROM app_system WHERE name='ownership_v1'")
                marker=cursor.fetchone()
                if not marker:raise RuntimeError('ownership 마이그레이션을 먼저 완료해 주세요.')
                owner=int(marker[0])
                if owner<1:raise RuntimeError('기존 자료 소유자를 확인해 주세요.')
                prefix='owner_id,';owner_values=(owner,)
            cursor.execute('''INSERT INTO pets
                ('''+prefix+'''id,name,species,registration_no,sex,birth_date,death_date,breed,color,microchip_no,
                 sire_id,dam_id,status,notes,photo_path,created_at,updated_at)
                SELECT '''+('%s,' if prefix else '')+'''id,name,'cat',registration_no,sex,birth_date,death_date,breed,color,microchip_no,
                       NULL,NULL,status,notes,photo_path,created_at,updated_at
                FROM cats ORDER BY id''',owner_values)
            cursor.execute('''UPDATE pets p JOIN cats c ON p.id=c.id
                SET p.sire_id=c.sire_id,p.dam_id=c.dam_id''')
        conn.commit()
        print('[OK] 명시적으로 요청한 마이그레이션 완료: '+target)
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor is not None:cursor.close()
        conn.close()


def inspect_ownership(conn,owner_id):
    import ownership
    cursor=conn.cursor()
    try:
        if owner_id:
            cursor.execute("SELECT id,username FROM app_members WHERE id=%s AND status='active'",(owner_id,))
            owner=cursor.fetchone()
            if not owner:raise RuntimeError('기존 자료를 귀속할 활성 회원 ID가 없습니다.')
        else:owner=None
        rows=['[ownership] 기존 자료에 사용자 소유권을 추가합니다. 소유자: '+str(owner or '미지정 (--owner-id 필요)')]
        available=startup.schema_columns(conn)
        for table in ownership.TABLES:
            if table not in available:raise RuntimeError(table+'가 없습니다. 먼저 schema 준비 여부를 확인해 주세요.')
            suffix=' WHERE owner_id IS NULL' if 'owner_id' in available[table] else ''
            cursor.execute('SELECT COUNT(*) FROM '+table+suffix)
            rows.append(table+': 귀속 대상 '+str(cursor.fetchone()[0])+'건')
        rows.append('개인설정 PK, 공과금 청구월/펫 등록번호의 UNIQUE를 사용자별로 변경합니다. DDL은 자동 커밋될 수 있습니다.')
        return '\n'.join(rows)
    finally:cursor.close()


def apply_ownership(owner_id):
    import ownership
    if not owner_id or owner_id<1:raise RuntimeError('--owner-id에 기존 자료의 소유자 회원 ID를 지정해 주세요.')
    conn=startup.connect_database();cursor=None
    try:
        cursor=conn.cursor()
        cursor.execute("SELECT id FROM app_members WHERE id=%s AND status='active'",(owner_id,))
        if not cursor.fetchone():raise RuntimeError('귀속 대상 활성 회원이 없습니다.')
        available=startup.schema_columns(conn)
        for table in ownership.TABLES:
            if table not in available:raise RuntimeError('기존 테이블이 없습니다: '+table)
        for table in ownership.TABLES:
            if 'owner_id' not in available[table]:cursor.execute('ALTER TABLE '+table+' ADD COLUMN owner_id BIGINT NULL')
            cursor.execute('UPDATE '+table+' SET owner_id=%s WHERE owner_id IS NULL',(owner_id,))
            cursor.execute('ALTER TABLE '+table+' MODIFY COLUMN owner_id BIGINT NOT NULL')
            cursor.execute('SHOW INDEX FROM '+table+' WHERE Key_name=%s',('idx_'+table+'_owner',))
            if not cursor.fetchall():cursor.execute('ALTER TABLE '+table+' ADD INDEX idx_'+table+'_owner (owner_id)')
        def index_columns(table,key):
            c=conn.cursor(dictionary=True)
            try:
                c.execute('SHOW INDEX FROM '+table+' WHERE Key_name=%s',(key,))
                return [r['Column_name'] for r in sorted(c.fetchall(),key=lambda r:r['Seq_in_index'])]
            finally:c.close()
        if index_columns('personal_profile','PRIMARY')!=['owner_id','id']:
            cursor.execute('ALTER TABLE personal_profile DROP PRIMARY KEY, ADD PRIMARY KEY (owner_id,id)')
        for table,key,field in [('utility_records','uq_utility_month','billing_month'),('pets','uq_pets_registration_no','registration_no')]:
            columns=index_columns(table,key)
            if columns!=['owner_id',field]:
                if columns:cursor.execute('ALTER TABLE '+table+' DROP INDEX '+key)
                cursor.execute('ALTER TABLE '+table+' ADD UNIQUE KEY '+key+' (owner_id,'+field+')')
        cursor.execute("INSERT INTO app_system (name,value) VALUES ('ownership_v1',%s) ON DUPLICATE KEY UPDATE value=VALUES(value)",(str(owner_id),))
        conn.commit()
        print('[OK] 사용자별 자료 분리 완료. 기존 자료 귀속 회원 ID: '+str(owner_id))
    except Exception:
        conn.rollback();raise
    finally:
        if cursor is not None:cursor.close()
        conn.close()
