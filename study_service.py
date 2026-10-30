"""HaruLog v2.7.1 — 단어 검증, 언어별 토큰 추출 및 중복 방지."""
import re
from datetime import datetime


def validate_words(words):
    if not isinstance(words, list) or not 1 <= len(words) <= 100:
        raise ValueError('단어는 1~100개씩 등록해 주세요.')
    result = []
    for item in words:
        if not isinstance(item, dict):
            raise ValueError('단어와 뜻을 확인해 주세요.')
        word, meaning = item.get('word'), item.get('meaning')
        if not isinstance(word, str) or not isinstance(meaning, str):
            raise ValueError('단어와 뜻은 문자로 입력해 주세요.')
        word, meaning = word.strip(), meaning.strip()
        if not 1 <= len(word) <= 100 or not 1 <= len(meaning) <= 255:
            raise ValueError('단어는 1~100자, 뜻은 1~255자로 입력해 주세요.')
        result.append((word, meaning))
    return result


def insert_word(cursor, video_id, word, meaning):
    cursor.execute('SELECT id FROM vocab_list WHERE video_id <=> %s AND BINARY LOWER(word)=BINARY LOWER(%s) LIMIT 1', (video_id, word))
    if cursor.fetchone() is not None:
        return False
    cursor.execute('INSERT INTO vocab_list (video_id,word,meaning,created_at) VALUES (%s,%s,%s,%s)',
                   (video_id, word, meaning, datetime.now()))
    return True


def extract_tokens(script, language):
    if language == 'JP':
        from tinysegmenter import TinySegmenter
        tokens = TinySegmenter().tokenize(script)
        return [token.strip() for token in tokens if re.search(r'[ぁ-んァ-ヶ一-龥]', token) and len(token.strip()) >= 2]
    if language == 'CN':
        import jieba
        return [token.strip() for token in jieba.cut(script) if re.search(r'[一-龥]', token) and len(token.strip()) >= 2]
    stopwords = {'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'were', 'which',
                 'there', 'their', 'about', 'would', 'could', 'yang', 'dan', 'dari', 'ini', 'itu',
                 'pada', 'untuk', 'dengan', 'ada', 'adalah', 'akan', 'atau', 'saya', 'kamu'}
    return [token for token in re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*", script)
            if len(token) >= 3 and token.lower() not in stopwords]
