"""Fail-closed SQL scoping for the application's fixed set of business tables."""
import re
TABLES=('daily_logs','study_videos','vocab_list','study_dictations','golf_rounds','expense_invoices','personal_profile','golf_contacts','utility_records','pets','pet_records','pet_lineage')
TABLE_PATTERN='(?:'+'|'.join(TABLES)+')'
STOP={'where','left','right','inner','outer','join','order','group','having','limit','for','union','on','set'}


def scoped_sql(sql,user_id):
    owner=int(user_id)
    if owner<1:raise ValueError('로그인 소유자가 없습니다.')
    text=sql.strip().rstrip(';')
    if re.match(r'^INSERT\s+(?:IGNORE\s+)?INTO\s+',text,re.I):
        pattern=r'^(INSERT\s+(?:IGNORE\s+)?INTO\s+('+TABLE_PATTERN+r')\s*\()([^)]*)(\)\s*VALUES\s*\()'
        match=re.search(pattern,text,re.I|re.S)
        if not match:raise ValueError('지원하지 않는 개인자료 INSERT입니다.')
        if re.search(r'\bowner_id\b',match[3],re.I):raise ValueError('소유자는 서버에서만 지정합니다.')
        return text[:match.start()]+match[1]+'owner_id,'+match[3]+match[4]+str(owner)+','+text[match.end():]
    if re.match(r'^SELECT\b',text,re.I):
        match=re.search(r'\bFROM\s+('+TABLE_PATTERN+r')\b(?:\s+([A-Za-z_]\w*))?',text,re.I)
        if not match:raise ValueError('지원하지 않는 개인자료 SELECT입니다.')
        alias=match[2] if match[2] and match[2].lower() not in STOP else match[1]
        # Scope joined videos in the ON clause, retaining LEFT JOIN semantics for free vocabulary.
        text=re.sub(r'\bJOIN\s+('+TABLE_PATTERN+r')\s+([A-Za-z_]\w*)\s+ON\s+',
                    lambda m:m[0]+m[2]+'.owner_id='+str(owner)+' AND ',text,flags=re.I)
        condition=alias+'.owner_id='+str(owner)
    elif re.match(r'^(UPDATE|DELETE)\b',text,re.I):
        match=re.match(r'^(?:UPDATE\s+|DELETE\s+FROM\s+)('+TABLE_PATTERN+r')\b',text,re.I)
        if not match:raise ValueError('지원하지 않는 개인자료 변경입니다.')
        if re.search(r'\bSET\s+owner_id\b',text,re.I):raise ValueError('소유자를 변경할 수 없습니다.')
        condition=match[1]+'.owner_id='+str(owner)
    else:raise ValueError('일반 자료 연결에서는 구조 변경을 실행할 수 없습니다.')
    # All runtime queries are single SELECT/UPDATE/DELETE statements with no subqueries/unions.
    if re.search(r'\bUNION\b|;|\bSELECT\b.+\bSELECT\b',text,re.I|re.S):raise ValueError('지원하지 않는 복합 SQL입니다.')
    where=re.search(r'\bWHERE\b',text,re.I)
    if where:return text[:where.end()]+' '+condition+' AND ('+_where_body(text[where.end():])[0]+')'+_where_body(text[where.end():])[1]
    boundary=re.search(r'\b(?:ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|FOR\s+UPDATE)\b',text,re.I)
    if boundary:return text[:boundary.start()]+' WHERE '+condition+' '+text[boundary.start():]
    return text+' WHERE '+condition


def _where_body(text):
    boundary=re.search(r'\b(?:ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|FOR\s+UPDATE)\b',text,re.I)
    return (text[:boundary.start()].strip(),' '+text[boundary.start():]) if boundary else (text.strip(),'')


class Cursor:
    def __init__(self,cursor,user_id):self._cursor=cursor;self._owner=user_id
    def execute(self,sql,params=()):return self._cursor.execute(scoped_sql(sql,self._owner),params)
    def executemany(self,*args,**kwargs):raise ValueError('지원하지 않는 일괄 SQL입니다.')
    def __getattr__(self,name):return getattr(self._cursor,name)


class Connection:
    def __init__(self,conn,user_id):self._conn=conn;self._owner=user_id
    def cursor(self,*args,**kwargs):return Cursor(self._conn.cursor(*args,**kwargs),self._owner)
    def __getattr__(self,name):return getattr(self._conn,name)
