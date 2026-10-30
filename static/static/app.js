// HaruLog v2.8.1
let currentVideoScript = "";
let currentVideoId = null;
let currentVideo = null;
let dictationLoadSequence = 0;
let studyLanguageFilter = "ALL";
let videoListSequence = 0;
let scriptVocabVideoId = null;
let scriptVocabSequence = 0;
let scriptVocabSaving = false;
let vocabListSequence = 0;

function formatLangBadge(lang) {
    if (!lang) return 'ID';
    const s = String(lang).toUpperCase().trim();
    if (s === 'ID' || s.includes('인도네시아')) return 'ID';
    if (s === 'US' || s.includes('영어') || s === 'EN') return 'US';
    if (s === 'JP' || s.includes('일본') || s === 'JA') return 'JP';
    if (s === 'CN' || s.includes('중국') || s === 'ZH') return 'CN';
    return 'ETC';
}

// 오늘기록 첨부 파일 상태
let selectedLogFile = null;
let currentEditingLogId = null;
let cachedLogs = [];

document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/auth/status', { cache: 'no-store' })
        .then(r => r.json())
        .then(auth => {
            if (!auth || !auth.authenticated) {
                if (location.pathname !== '/login') {
                    location.replace('/login');
                }
                return;
            }
            loadLogs();
            loadVideos().then(videos => populateAllVocabVideoSelect(videos)).catch(error => {
                if (error && error.message && !error.message.includes('로그인')) {
                    alert(error.message);
                }
            });
            loadVocab();
        })
        .catch(() => {
            if (location.pathname !== '/login') {
                location.replace('/login');
            }
        });
});

function toggleMainMenu(forceOpen) {
    const menu = document.getElementById('mainMenu');
    const open = typeof forceOpen === 'boolean' ? forceOpen : menu.hidden;
    menu.hidden = !open;
    document.getElementById('menuToggle').setAttribute('aria-expanded', String(open));
}

function switchTab(tabId, btn) {
    const target = document.getElementById(tabId);
    if (!target || !btn) return;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('active');
        el.removeAttribute('aria-current');
    });
    target.classList.add('active');
    btn.classList.add('active');
    btn.setAttribute('aria-current', 'page');
    const title = document.getElementById('currentPageTitle');
    title.textContent = btn.lastChild.textContent.trim();
    document.title = `${title.textContent} - Harulog`;
    toggleMainMenu(false);
    document.getElementById('mainContent').scrollTop = 0;
    title.focus({preventScroll: true});
    if (tabId === 'admin-tab' && typeof loadMembers === 'function') loadMembers(1);
    if (tabId === 'score-tab' && typeof loadScores === 'function') loadScores();
    if (tabId === 'settings-tab' && typeof loadBasicSettings === 'function') loadBasicSettings().catch(error => { document.getElementById('settingsStatus').textContent = error.message; });
    if (tabId === 'expense-tab') {
        if (typeof loadInvoices === 'function') loadInvoices();
        if (typeof loadUtilityRecords === 'function') loadUtilityRecords();
        if (typeof loadUtilityStats === 'function') loadUtilityStats();
    }
    if (tabId === 'pets-tab' && typeof loadPets === 'function') loadPets();
}

document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !document.getElementById('mainMenu').hidden) {
        toggleMainMenu(false);
        document.getElementById('menuToggle').focus();
    }
});

// -------------------------------------------------------------------
// 1. 오늘기록 (Daily Logs) - 파일 첨부, 조회, 수정, 삭제
// -------------------------------------------------------------------

// 파일 선택 시 미리보기
function handleLogFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    selectedLogFile = file;
    const previewWrap = document.getElementById('filePreviewWrap');
    const previewImg = document.getElementById('filePreviewImage');
    const previewIcon = document.getElementById('filePreviewIcon');
    const previewName = document.getElementById('filePreviewName');

    previewName.innerText = file.name;
    previewWrap.style.display = 'flex';

    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewImg.style.display = 'block';
            previewIcon.style.display = 'none';
        };
        reader.readAsDataURL(file);
    } else {
        previewImg.style.display = 'none';
        previewIcon.style.display = 'inline';
    }
}

// 첨부 파일 선택 취소
function clearSelectedLogFile() {
    selectedLogFile = null;
    const input = document.getElementById('logFileInput');
    if (input) input.value = '';
    const previewWrap = document.getElementById('filePreviewWrap');
    if (previewWrap) previewWrap.style.display = 'none';
}

// 오늘기록 등록
async function saveLog() {
    const content = document.getElementById('logInput').value.trim();
    if (!content && !selectedLogFile) {
        return alert('내용 또는 첨부할 사진/파일을 입력해 주세요.');
    }

    const formData = new FormData();
    formData.append('content', content);
    if (selectedLogFile) {
        formData.append('file', selectedLogFile);
    }

    try {
        const res = await fetch('/api/logs', {
            method: 'POST',
            body: formData
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '기록 저장에 실패했습니다.');

        document.getElementById('logInput').value = '';
        clearSelectedLogFile();
        loadLogs();
    } catch (err) {
        alert(err.message || '서버 연결 실패');
    }
}

// 오늘기록 본문 줄바꿈 및 특수문자 안전 변환
function formatLogContent(content) {
    if (!content) return '';
    const clean = content.replace(/\\r\\n/g, '\n').replace(/\\r/g, '').replace(/\\n/g, '\n');
    return escapeHtml(clean);
}

// 오늘기록 목록 조회
async function loadLogs() {
    try {
        const res = await fetch('/api/logs');
        if (!res.ok) return;
        const logs = await res.json();
        cachedLogs = logs;

        const countBadge = document.getElementById('logCountBadge');
        if (countBadge) countBadge.innerText = logs.length;

        const container = document.getElementById('timelineContainer');
        container.innerHTML = logs.length === 0 
            ? '<div style="text-align:center;color:var(--text-muted);padding:30px 10px;background:var(--bg-card);border-radius:12px;border:1px dashed var(--border-color);">작성된 기록이 없습니다.<br>오늘의 순간을 첫 번째로 기록해 보세요!</div>' 
            : '';

        logs.forEach(log => {
            const item = document.createElement('div');
            item.className = 'log-item';

            // 미디어(사진/파일) 렌더링
            let mediaHtml = '';
            if (log.file_path) {
                const isImage = /\.(png|jpe?g|gif|webp)$/i.test(log.file_path);
                const fileName = log.file_path.split('/').pop();
                if (isImage) {
                    mediaHtml = `
                        <div class="log-media-box">
                            <div class="log-image-wrap" onclick="openImageLightbox('${log.file_path}')" title="클릭하여 확대 보기">
                                <img src="${log.file_path}" alt="기록 사진" loading="lazy">
                            </div>
                        </div>
                    `;
                } else {
                    mediaHtml = `
                        <div class="log-media-box">
                            <a href="${log.file_path}" class="log-file-link" target="_blank" download>
                                <span>📎 ${escapeHtml(fileName)}</span>
                            </a>
                        </div>
                    `;
                }
            }

            item.innerHTML = `
                <div class="log-header">
                    <div class="log-time">📅 ${log.created_at}</div>
                    <div class="log-actions">
                        <button type="button" class="btn-log-action btn-log-edit" onclick="openEditLogModal(${log.id})">✏️ 수정</button>
                        <button type="button" class="btn-log-action btn-log-delete" onclick="deleteLog(${log.id})">🗑️ 삭제</button>
                    </div>
                </div>
                <div class="log-content">${formatLogContent(log.content)}</div>
                ${mediaHtml}
            `;
            container.appendChild(item);
        });
    } catch (err) {
        console.error('기록 로드 실패:', err);
    }
}

// 오늘기록 수정 모달 열기
function openEditLogModal(logId) {
    const log = cachedLogs.find(l => l.id === logId);
    if (!log) return;

    currentEditingLogId = log.id;
    document.getElementById('editLogContent').value = (log.content || '').replace(/\\r\\n/g, '\n').replace(/\\r/g, '').replace(/\\n/g, '\n');

    const existingFileBox = document.getElementById('editExistingFileBox');
    const existingFileName = document.getElementById('editExistingFileName');
    const removeCheckbox = document.getElementById('editRemoveFileCheckbox');
    const fileInput = document.getElementById('editLogFileInput');

    fileInput.value = '';
    removeCheckbox.checked = false;

    if (log.file_path) {
        existingFileBox.style.display = 'block';
        existingFileName.innerText = log.file_path.split('/').pop();
    } else {
        existingFileBox.style.display = 'none';
        existingFileName.innerText = '';
    }

    document.getElementById('editLogModal').style.display = 'flex';
}

function closeEditLogModal() {
    document.getElementById('editLogModal').style.display = 'none';
    currentEditingLogId = null;
}

function handleLogModalOverlayClick(e) {
    if (e.target && e.target.id === 'editLogModal') {
        closeEditLogModal();
    }
}

// 오늘기록 수정 저장
async function saveEditedLog() {
    if (!currentEditingLogId) return;

    const content = document.getElementById('editLogContent').value.trim();
    const removeFile = document.getElementById('editRemoveFileCheckbox').checked;
    const fileInput = document.getElementById('editLogFileInput');
    const file = fileInput.files[0];

    const formData = new FormData();
    formData.append('content', content);
    if (removeFile) {
        formData.append('remove_file', 'true');
    }
    if (file) {
        formData.append('file', file);
    }

    try {
        const res = await fetch(`/api/logs/${currentEditingLogId}`, {
            method: 'PUT',
            body: formData
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '기록 수정에 실패했습니다.');

        closeEditLogModal();
        loadLogs();
    } catch (err) {
        alert(err.message || '서버 통신 실패');
    }
}

// 오늘기록 삭제
async function deleteLog(logId) {
    if (!confirm('정말로 이 기록을 삭제하시겠습니까?\n첨부된 파일도 함께 삭제됩니다.')) {
        return;
    }

    try {
        const res = await fetch(`/api/logs/${logId}`, {
            method: 'DELETE'
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '삭제에 실패했습니다.');

        loadLogs();
    } catch (err) {
        alert(err.message || '서버 통신 실패');
    }
}

// 이미지 라이트박스 확대 보기
function openImageLightbox(src) {
    const lightbox = document.getElementById('imageLightboxModal');
    const img = document.getElementById('lightboxImage');
    if (lightbox && img) {
        img.src = src;
        lightbox.style.display = 'flex';
    }
}

function closeImageLightbox() {
    const lightbox = document.getElementById('imageLightboxModal');
    if (lightbox) lightbox.style.display = 'none';
}

// -------------------------------------------------------------------
// 2. Haru스터디 (Videos & Dictation & Vocab)
// -------------------------------------------------------------------

function filterStudyVideos(lang, btn) {
    studyLanguageFilter = (lang === 'ALL' || lang === '전체') ? 'ALL' : lang;
    document.querySelectorAll('.lang-pill, .lang-filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    loadVideos().catch(error => alert(error.message));
}

async function loadVideos(selectedId = null) {
    const listSequence = ++videoListSequence;
    const isAll = (!studyLanguageFilter || studyLanguageFilter === 'ALL' || studyLanguageFilter === '전체');
    const url = isAll
        ? '/api/study/videos'
        : `/api/study/videos?language=${encodeURIComponent(studyLanguageFilter)}`;
    const res = await fetch(url);
    const videos = await res.json();
    if (!res.ok || !Array.isArray(videos)) throw new Error(videos.error || '영상 목록을 불러오지 못했습니다.');
    
    if (listSequence !== videoListSequence) return;
    // 개수 배지 업데이트
    const countBadge = document.getElementById('videoCountBadge');
    if (countBadge) countBadge.innerText = videos.length;

    // 더보기 버튼 표시 여부 제어 (4개 초과 시 노출)
    const toggleBtn = document.getElementById('btnToggleVideoList');
    if (toggleBtn) {
        toggleBtn.style.display = videos.length > 4 ? 'inline-block' : 'none';
    }

    const badgeContainer = document.getElementById('videoBadgeContainer');
    badgeContainer.innerHTML = '';
    
    if (videos.length === 0) {
        badgeContainer.innerHTML = `<div class="video-empty-notice">${!isAll ? `[${studyLanguageFilter}] 언어로 등록된 학습 영상이 없습니다.` : '등록된 학습 영상이 없습니다. 위에서 새 영상을 등록해 보세요!'}</div>`;
        return videos;
    }

    videos.forEach((vid) => {
        const item = document.createElement('div');
        item.className = 'video-card-item';
        const isActive = (selectedId !== null && vid.id === selectedId);
        if (isActive) {
            item.classList.add('active');
        }

        const langBadge = formatLangBadge(vid.language);
        item.innerHTML = `
            <span class="card-icon">${isActive ? '▶' : '🎬'}</span>
            <span class="card-title" title="${escapeHtml(vid.title)}">${escapeHtml(vid.title)}</span>
            <span class="card-lang-tag lang-${langBadge}">${langBadge}</span>
        `;

        item.onclick = () => selectVideo(vid, item);
        badgeContainer.appendChild(item);
    });
    return videos;
}

function toggleVideoListExpand() {
    const container = document.getElementById('videoBadgeContainer');
    const btn = document.getElementById('btnToggleVideoList');
    if (!container || !btn) return;

    container.classList.toggle('expanded');
    btn.innerText = container.classList.contains('expanded') ? '접기 ▴' : '전체보기 ▾';
}

async function selectVideo(vid, badgeElement) {
    const sequence = ++dictationLoadSequence;
    currentVideoId = vid.id;
    currentVideo = vid;

    document.querySelectorAll('.video-card-item').forEach(el => {
        el.classList.remove('active');
        const icon = el.querySelector('.card-icon');
        if (icon) icon.innerText = '🎬';
    });
    if (badgeElement) {
        badgeElement.classList.add('active');
        const icon = badgeElement.querySelector('.card-icon');
        if (icon) icon.innerText = '▶';
    }

    // 상단 바 표시 및 제목 반영
    const selectedBar = document.getElementById('selectedVideoBar');
    if (selectedBar) {
        selectedBar.style.display = 'flex';
        document.getElementById('selectedVideoTitle').innerText = `${vid.title} (${vid.language || '영어'})`;
    }

    document.getElementById('playerWrapper').innerHTML =
        `<iframe src="https://www.youtube.com/embed/${encodeURIComponent(vid.youtube_id)}" allowfullscreen></iframe>`;

    currentVideoScript = vid.script;
    document.getElementById('scriptContent').innerText = vid.script;
    document.getElementById('dictationResult').innerHTML = '';
    document.getElementById('studyWorkspace').style.display = 'block';

    const input = document.getElementById('dictationInput');
    const button = document.getElementById('saveDictationButton');
    input.value = '';
    input.disabled = true;
    button.disabled = true;

    try {
        const res = await fetch(`/api/study/videos/${vid.id}/dictation`, {
            cache: 'no-store'
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '받아쓰기를 불러오지 못했습니다.');
        if (sequence !== dictationLoadSequence) return;

        input.value = data.content;
        input.disabled = false;
        button.disabled = false;
        loadVocab(); // 선택된 영상과 관계된 단어 목록 로드
    } catch (error) {
        if (sequence !== dictationLoadSequence) return;
        alert(`${error.message}\n영상을 다시 선택해 주세요.`);
    }
}

let videoDeleting = false;

async function deleteSelectedVideo() {
    if (videoDeleting || videoUpdating || !currentVideo) return;
    const video = currentVideo;
    if (!confirm(`“${video.title}” 영상을 삭제하시겠습니까?\n이 영상의 단어장과 받아쓰기 기록도 함께 삭제되며 복구할 수 없습니다.`)) return;
    const button = document.getElementById('deleteVideoButton');
    videoDeleting = true;
    button.disabled = true;
    let deleted = false;
    try {
        await apiRequest(`/api/study/videos/${video.id}`, {method:'DELETE'});
        deleted = true;
        if (currentVideoId === video.id) {
            ++dictationLoadSequence;
            currentVideoId = null;
            currentVideo = null;
            currentVideoScript = '';
            closeEditVideoModal();
            document.getElementById('selectedVideoBar').style.display = 'none';
            document.getElementById('studyWorkspace').style.display = 'none';
            document.getElementById('playerWrapper').innerHTML = '<div class="video-empty-notice">위 목록에서 영상을 선택해 주세요.</div>';
            document.getElementById('dictationInput').value = '';
            document.getElementById('scriptContent').textContent = '';
            document.getElementById('dictationResult').innerHTML = '';
        }
        await loadVideos(currentVideoId);
        await populateAllVocabVideoSelect();
        if (typeof loadAllVocabList === 'function') await loadAllVocabList();
    } catch (error) {
        alert(deleted ? '영상은 삭제되었으나 목록 갱신에 실패했습니다. 새로고침해 주세요.' : error.message);
    } finally {
        videoDeleting = false;
        button.disabled = false;
    }
}

function openEditVideoModal() {
    if (!currentVideo) {
        return alert('수정할 영상을 먼저 선택해 주세요.');
    }
    document.getElementById('editVideoTitle').value = currentVideo.title;
    document.getElementById('editVideoUrl').value = `https://www.youtube.com/watch?v=${currentVideo.youtube_id}`;
    document.getElementById('editVideoLanguage').value = formatLangBadge(currentVideo.language);
    document.getElementById('editVideoScript').value = currentVideo.script;
    document.getElementById('editVideoModal').style.display = 'flex';
}

function closeEditVideoModal() {
    document.getElementById('editVideoModal').style.display = 'none';
}

function handleModalOverlayClick(e) {
    if (e.target && e.target.id === 'editVideoModal') {
        closeEditVideoModal();
    }
}

let videoUpdating = false;

async function saveEditedVideo() {
    if (videoUpdating || videoDeleting || !currentVideoId) return;

    const title = document.getElementById('editVideoTitle').value.trim();
    const url = document.getElementById('editVideoUrl').value.trim();
    const language = document.getElementById('editVideoLanguage').value.trim();
    const script = document.getElementById('editVideoScript').value.trim();

    if (!title || !url || !script) return alert('모든 항목을 입력하세요.');

    videoUpdating = true;
    try {
        const res = await fetch(`/api/study/videos/${currentVideoId}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, url, script, language})
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '영상 정보 수정에 실패했습니다.');

        currentVideo = data.video || { id: currentVideoId, title, youtube_id: currentVideo.youtube_id, script, language };
        currentVideoScript = currentVideo.script;

        document.getElementById('selectedVideoTitle').innerText = `${currentVideo.title} (${currentVideo.language || '영어'})`;
        document.getElementById('scriptContent').innerText = currentVideo.script;
        document.getElementById('playerWrapper').innerHTML =
            `<iframe src="https://www.youtube.com/embed/${encodeURIComponent(currentVideo.youtube_id)}" allowfullscreen></iframe>`;

        closeEditVideoModal();
        await loadVideos(currentVideo.id);
        await populateAllVocabVideoSelect();
        alert('영상 정보가 성공적으로 수정되었습니다!');
    } catch (error) {
        alert(error.message || '서버 통신 중 오류가 발생했습니다.');
    } finally {
        videoUpdating = false;
    }
}

let videoSaving = false;

async function saveVideo() {
    if (videoSaving) return;
    const title = document.getElementById('videoTitle').value.trim();
    const url = document.getElementById('videoUrl').value.trim();
    const language = document.getElementById('videoLanguage').value.trim();
    const script = document.getElementById('videoScript').value.trim();
    if (!title || !url || !script) return alert('모든 항목을 입력하세요.');
    videoSaving = true;
    try {
        const res = await fetch('/api/study/videos', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, url, script, language})
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '영상 등록에 실패했습니다. 서버 상태를 확인해 주세요.');
        document.getElementById('videoTitle').value = '';
        document.getElementById('videoUrl').value = '';
        document.getElementById('videoScript').value = '';
        try {
            const videos = await loadVideos();
            await populateAllVocabVideoSelect(studyLanguageFilter === 'ALL' ? videos : null);
            alert('영상이 등록되었습니다!');
        } catch (error) {
            alert('영상은 등록되었으나 목록을 불러오지 못했습니다. 새로고침해 주세요.');
        }
    } catch (error) {
        alert(error.message || '서버에 연결하지 못했습니다.');
    } finally {
        videoSaving = false;
    }
}

// -------------------------------------------------------------------
// Haru스터디 서브 탭 전환 (영상 학습 vs 전체 단어장)
// -------------------------------------------------------------------
function switchStudySubTab(tab) {
    const videoView = document.getElementById('studyVideoView');
    const vocabView = document.getElementById('studyVocabView');
    const videoBtn = document.getElementById('subtabStudyVideoBtn');
    const vocabBtn = document.getElementById('subtabStudyVocabBtn');

    if (tab === 'vocab') {
        videoView.style.display = 'none';
        vocabView.style.display = 'block';
        videoBtn.classList.remove('active');
        vocabBtn.classList.add('active');
        loadAllVocabList();
        populateAllVocabVideoSelect();
    } else {
        videoView.style.display = 'block';
        vocabView.style.display = 'none';
        videoBtn.classList.add('active');
        vocabBtn.classList.remove('active');
        if (currentVideoId) loadVocab();
    }
}

// -------------------------------------------------------------------
// 받아쓰기 정답 매칭 고도화 (LCS 및 시각적 Diff 분석)
// -------------------------------------------------------------------
function checkDictation() {
    if (!currentVideoScript) {
        return alert('선택된 영상의 정답 스크립트가 없습니다.');
    }
    const inputRaw = document.getElementById('dictationInput').value;
    if (!inputRaw || !inputRaw.trim()) {
        return alert('받아쓰기 칸에 내용을 입력해 주세요.');
    }

    // 시간 관련 부분(타임스탬프, 자막 시간대 등) 매칭 제외
    const removeTimeTokens = (text) => {
        return (text || "")
            // 자막 타임코드 구간: 00:00:00,000 --> 00:00:00,000 또는 00:01 - 00:05
            .replace(/\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\s*(?:-->|~|-)\s*\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?/gi, " ")
            // 괄호로 감싸진 시간: [00:15], (01:23), [0:05]
            .replace(/[\[\(]\s*\d{1,2}:\d{2}(?::\d{2})?\s*[\]\)]/gi, " ")
            // 일반 타임스탬프: 00:00:00, 01:23, 0:05
            .replace(/\b\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\b/g, " ")
            // 분/초 한글 시간 표기 (예: 1분 30초, 20초)
            .replace(/\b\d{1,3}\s*(?:시간|분|초)\b/gi, " ")
            // 자막 순번 숫자 단독 라인
            .replace(/^\s*\d+\s*$/gm, " ");
    };

    // 정규화 함수: 시간 제거, 문장부호 제거, 소문자화, 연속 공백 정리 후 단어 분리
    const cleanWords = (text) => {
        const withoutTime = removeTimeTokens(text);
        return withoutTime.toLowerCase()
            .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"'“”‘’—–[\]]/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .split(' ')
            .filter(w => w.length > 0);
    };

    const targetWords = cleanWords(currentVideoScript);
    const inputWords = cleanWords(inputRaw);

    if (targetWords.length === 0) {
        return alert('정답 스크립트에서 비교할 단어를 찾을 수 없습니다.');
    }

    // 1. LCS (최장 공통 부분 수열) DP 테이블 구성
    const m = targetWords.length;
    const n = inputWords.length;
    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (targetWords[i - 1] === inputWords[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    const matchedCount = dp[m][n];
    const baseLen = Math.max(m, n);
    const accuracy = Math.round((matchedCount / baseLen) * 100);

    // 2. 백트래킹을 통한 정답 대비 상세 Diff 분석
    let i = m, j = n;
    const diff = [];
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && targetWords[i - 1] === inputWords[j - 1]) {
            diff.unshift({ type: 'match', word: targetWords[i - 1] });
            i--;
            j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            diff.unshift({ type: 'extra', word: inputWords[j - 1] });
            j--;
        } else {
            diff.unshift({ type: 'missing', word: targetWords[i - 1] });
            i--;
        }
    }

    // 3. UI 렌더링
    const resultBox = document.getElementById('dictationResult');
    let diffHtml = diff.map(item => {
        if (item.type === 'match') {
            return `<span style="background:rgba(34,197,94,0.2); color:#4ade80; padding:2px 6px; border-radius:4px; font-weight:600;" title="일치">${escapeHtml(item.word)}</span>`;
        } else if (item.type === 'extra') {
            return `<span style="background:rgba(239,68,68,0.2); color:#f87171; text-decoration:line-through; padding:2px 6px; border-radius:4px;" title="오답/불필요 단어">${escapeHtml(item.word)}</span>`;
        } else {
            return `<span style="background:rgba(245,158,11,0.2); color:#fbbf24; border-bottom:1.5px dashed #f59e0b; padding:2px 6px; border-radius:4px;" title="누락된 단어">${escapeHtml(item.word)}</span>`;
        }
    }).join(' ');

    const missingCount = m - matchedCount;
    const extraCount = n - matchedCount;

    resultBox.innerHTML = `
        <div style="background:rgba(255,255,255,0.04); border:1px solid var(--border-color); border-radius:8px; padding:12px; margin-top:10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:6px;">
                <span style="font-size:1.05rem; font-weight:700; color:${accuracy >= 80 ? '#4ade80' : accuracy >= 50 ? '#fbbf24' : '#f87171'};">
                    🎯 정답 매칭 정확도: ${accuracy}%
                </span>
                <span style="font-size:0.8rem; color:var(--text-muted);">
                    정답: ${m}단어 | 입력: ${n}단어
                </span>
            </div>
            <div style="display:flex; gap:12px; font-size:0.8rem; margin-bottom:10px;">
                <span style="color:#4ade80;">✔ 일치: ${matchedCount}</span>
                <span style="color:#fbbf24;">⚠ 누락: ${missingCount}</span>
                <span style="color:#f87171;">✕ 오답/추가: ${extraCount}</span>
            </div>
            <div style="font-size:0.82rem; color:var(--text-muted); margin-bottom:6px;">단어별 매칭 비교 (초록: 일치, 노랑: 정답 누락, 빨강: 작성 오답):</div>
            <div style="display:flex; flex-wrap:wrap; gap:5px; line-height:1.7; padding:8px; background:rgba(0,0,0,0.3); border-radius:6px; font-size:0.9rem;">
                ${diffHtml}
            </div>
        </div>
    `;
}

async function saveDictation() {
    const button = document.getElementById('saveDictationButton');
    if (currentVideoId === null || button.disabled) return;

    const videoId = currentVideoId;
    const sequence = dictationLoadSequence;
    const content = document.getElementById('dictationInput').value;
    button.disabled = true;

    try {
        const res = await fetch(`/api/study/videos/${videoId}/dictation`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content})
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.error || '받아쓰기 저장에 실패했습니다.');

        alert('받아쓰기를 저장했습니다.');
    } catch (error) {
        alert(error.message || '서버에 연결하지 못했습니다.');
    } finally {
        if (sequence === dictationLoadSequence) {
            button.disabled = false;
        }
    }
}

function toggleScript() {
    const content = document.getElementById('scriptContent');
    const icon = document.getElementById('toggleIcon');
    if(content.style.display === 'none') {
        content.style.display = 'block';
        icon.innerText = '▲';
    } else {
        content.style.display = 'none';
        icon.innerText = '▼';
    }
}

// -------------------------------------------------------------------
// 영상별 관계 단어장 (선택된 영상에 등록된 단어만 표시)
// -------------------------------------------------------------------
async function loadVocab() {
    const sequence = ++vocabListSequence;
    const videoId = currentVideoId;
    const container = document.getElementById('vocabContainer');
    const titleEl = document.getElementById('videoVocabTitle');
    const noticeEl = document.getElementById('videoVocabNotice');
    if (!container) return;

    if (!currentVideoId) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:13px;padding:12px 0;text-align:center;">학습할 영상을 먼저 선택하시면 해당 영상에 등록된 단어장이 표시됩니다.</div>';
        if (titleEl) titleEl.textContent = '🔑 영상 관계 단어장';
        if (noticeEl) noticeEl.textContent = '영상을 선택하면 관계된 단어만 표시됩니다.';
        return;
    }

    if (titleEl && currentVideo) titleEl.textContent = `🔑 [${currentVideo.title}] 관계 단어장`;
    if (noticeEl && currentVideo) noticeEl.textContent = `[${currentVideo.title}] 영상과 관계된 단어 목록입니다. (A-Z 알파벳순)`;

    try {
        const res = await fetch(`/api/study/vocab?video_id=${videoId}`);
        const vocabs = await res.json();
        if (sequence !== vocabListSequence || videoId !== currentVideoId) return;
        if (!res.ok || !Array.isArray(vocabs)) throw new Error(vocabs.error || '단어장을 불러오지 못했습니다.');
        container.innerHTML = '';
        if (!Array.isArray(vocabs) || vocabs.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted);font-size:13px;padding:10px 0;text-align:center;">이 영상에 등록된 단어가 아직 없습니다.<br>위 버튼으로 스크립트에서 자동 생성하거나 직접 추가해 보세요!</div>';
            return;
        }
        vocabs.forEach(v => {
            const item = document.createElement('div');
            item.className = 'vocab-item';
            item.innerHTML = `
                <div style="display:flex;align-items:center;gap:8px;flex:1;">
                    <strong class="word" style="color:#60a5fa; font-size:0.95rem;">${escapeHtml(v.word)}</strong>
                    <span class="meaning" style="color:#e5e7eb; font-size:0.9rem;">${escapeHtml(v.meaning)}</span>
                </div>
                <button type="button" class="btn-del-vocab" onclick="deleteVocab(${v.id})" title="단어 삭제">✕</button>
            `;
            container.appendChild(item);
        });
    } catch (err) {
        if (sequence !== vocabListSequence) return;
        container.textContent = err.message;
    }
}

async function saveVocab() {
    const wordEl = document.getElementById('vocabWord');
    const meaningEl = document.getElementById('vocabMeaning');
    const word = wordEl.value.trim();
    const meaning = meaningEl.value.trim();
    if (!word || !meaning) return alert('단어와 한국어 뜻을 채워주세요.');
    if (!currentVideoId) return alert('단어를 등록할 학습 영상을 먼저 선택해 주세요.');
    
    try {
        const res = await fetch('/api/study/vocab', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ word, meaning, video_id: currentVideoId })
        });
        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.error || '단어 저장에 실패했습니다.');
        }
        wordEl.value = '';
        meaningEl.value = '';
        loadVocab();
    } catch (err) {
        alert(err.message);
    }
}

async function deleteVocab(vocabId, reloadAll = false) {
    if (!confirm('이 단어를 단어장에서 삭제하시겠습니까?')) return;
    try {
        const res = await fetch(`/api/study/vocab/${vocabId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('단어 삭제에 실패했습니다.');
        if (reloadAll) {
            const q = document.getElementById('allVocabSearchInput') ? document.getElementById('allVocabSearchInput').value : '';
            loadAllVocabList(q);
        } else {
            loadVocab();
        }
    } catch (err) {
        alert(err.message);
    }
}

// -------------------------------------------------------------------
// 전체 단어장 별도 조회 및 검색 (A-Z 알파벳순)
// -------------------------------------------------------------------
let searchAllVocabTimer = null;

function onSearchAllVocabInput() {
    clearTimeout(searchAllVocabTimer);
    searchAllVocabTimer = setTimeout(() => {
        const q = document.getElementById('allVocabSearchInput').value;
        loadAllVocabList(q);
    }, 250);
}

async function loadAllVocabList(searchQuery = '') {
    const container = document.getElementById('allVocabListContainer');
    const badge = document.getElementById('allVocabCountBadge');
    if (!container) return;

    container.innerHTML = '<div style="color:var(--text-muted);font-size:13px;padding:16px 0;text-align:center;">단어장을 불러오는 중입니다…</div>';

    try {
        const q = searchQuery.trim();
        const url = q ? `/api/study/vocab?q=${encodeURIComponent(q)}` : '/api/study/vocab';
        const res = await fetch(url);
        const vocabs = await res.json();
        if (!res.ok || !Array.isArray(vocabs)) throw new Error('단어 목록을 불러오지 못했습니다.');

        if (badge) badge.textContent = `${vocabs.length}단어`;

        container.innerHTML = '';
        if (vocabs.length === 0) {
            container.innerHTML = `<div style="color:var(--text-muted);font-size:13px;padding:24px 0;text-align:center;">${q ? '검색 결과와 일치하는 단어가 없습니다.' : '등록된 단어가 없습니다. 위에서 새 단어를 추가해 보세요!'}</div>`;
            return;
        }

        // A-Z 알파벳 그룹화 표시
        let currentInitial = '';
        vocabs.forEach(v => {
            const word = v.word.trim();
            const firstChar = word.charAt(0).toUpperCase();
            const initial = /^[A-Z]$/.test(firstChar) ? firstChar : '#';

            if (initial !== currentInitial) {
                currentInitial = initial;
                const groupHeader = document.createElement('div');
                groupHeader.style = 'background:rgba(255,255,255,0.06); padding:4px 10px; border-radius:4px; font-weight:700; color:#38bdf8; font-size:0.85rem; margin-top:8px; margin-bottom:4px;';
                groupHeader.textContent = `[ ${currentInitial} ]`;
                container.appendChild(groupHeader);
            }

            const item = document.createElement('div');
            item.className = 'vocab-item';
            const videoTag = v.video_title ? `<span class="vocab-video-badge" title="${escapeHtml(v.video_title)}">🎬 ${escapeHtml(v.video_title)}</span>` : '<span style="font-size:10px; color:var(--text-muted); padding:2px 6px; background:rgba(255,255,255,0.05); border-radius:3px;">일반</span>';
            item.innerHTML = `
                <div style="display:flex;align-items:center;gap:8px;flex:1;flex-wrap:wrap;">
                    <strong class="word" style="color:#60a5fa; font-size:0.95rem;">${escapeHtml(v.word)}</strong>
                    <span class="meaning" style="color:#e5e7eb; font-size:0.9rem;">${escapeHtml(v.meaning)}</span>
                    ${videoTag}
                </div>
                <button type="button" class="btn-del-vocab" onclick="deleteVocab(${v.id}, true)" title="단어 삭제">✕</button>
            `;
            container.appendChild(item);
        });
    } catch (err) {
        container.innerHTML = `<div style="color:#ef4444;padding:12px;">오류: ${escapeHtml(err.message)}</div>`;
    }
}

async function populateAllVocabVideoSelect(videos = null) {
    const select = document.getElementById('allVocabVideoSelect');
    if (!select) return;
    try {
        if (!videos) videos = await apiRequest('/api/study/videos');
        if (Array.isArray(videos)) {
            select.innerHTML = '<option value="">(연결 영상 없음 / 일반 단어)</option>';
            videos.forEach(vid => {
                const opt = document.createElement('option');
                opt.value = vid.id;
                opt.textContent = `🎬 ${vid.title}`;
                if (currentVideoId && vid.id === currentVideoId) opt.selected = true;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.warn('영상 드롭다운 로드 실패:', e);
    }
}

async function saveAllVocabDirect() {
    const wordEl = document.getElementById('allVocabWordInput');
    const meaningEl = document.getElementById('allVocabMeaningInput');
    const videoSelect = document.getElementById('allVocabVideoSelect');
    const word = wordEl.value.trim();
    const meaning = meaningEl.value.trim();
    const video_id = videoSelect.value ? parseInt(videoSelect.value, 10) : null;

    if (!word || !meaning) return alert('단어와 한국어 뜻을 입력해 주세요.');

    try {
        const res = await fetch('/api/study/vocab', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ word, meaning, video_id })
        });
        if (!res.ok) {
            const error = await res.json().catch(() => ({}));
            throw new Error(error.error || '단어 저장에 실패했습니다.');
        }
        wordEl.value = '';
        meaningEl.value = '';
        const searchInput = document.getElementById('allVocabSearchInput');
        loadAllVocabList(searchInput ? searchInput.value : '');
    } catch (err) {
        alert(err.message);
    }
}

// 스크립트 기반 단어장 생성 모달
async function openScriptVocabModal() {
    if (!currentVideoId || !currentVideo) {
        return alert('단어장을 생성할 학습 영상을 먼저 선택해 주세요.');
    }
    const sequence = ++scriptVocabSequence;
    scriptVocabVideoId = currentVideoId;
    const videoId = scriptVocabVideoId;
    const modal = document.getElementById('scriptVocabModal');
    const list = document.getElementById('scriptVocabList');
    const desc = document.getElementById('scriptVocabDesc');
    list.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center;">스크립트에서 단어를 분석하는 중입니다…</div>';
    desc.textContent = `[${currentVideo.title}] 스크립트에서 추출된 단어 목록입니다. 한국어 뜻을 확인/수정 후 일괄 등록하세요.`;
    modal.style.display = 'flex';

    try {
        const res = await fetch(`/api/study/videos/${videoId}/vocab/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '단어 추출에 실패했습니다.');

        if (sequence !== scriptVocabSequence) return;
        list.innerHTML = '';
        const words = data.extracted_words || [];
        if (words.length === 0) {
            list.innerHTML = '<div style="color:var(--text-muted);padding:12px;text-align:center;">스크립트에서 추출할 수 있는 단어가 없습니다. 아래에서 직접 단어를 추가해 보세요.</div>';
        } else {
            words.forEach(w => addScriptVocabRow(w.word, w.meaning));
        }
    } catch (err) {
        if (sequence !== scriptVocabSequence) return;
        list.innerHTML = `<div style="color:#ef4444;padding:12px;">오류: ${escapeHtml(err.message)}</div>`;
    }
}

function closeScriptVocabModal() {
    if (scriptVocabSaving) return;
    ++scriptVocabSequence;
    scriptVocabVideoId = null;
    document.getElementById('scriptVocabModal').style.display = 'none';
}

function handleScriptVocabModalClick(e) {
    if (e.target && e.target.id === 'scriptVocabModal') {
        closeScriptVocabModal();
    }
}

function addScriptVocabRow(word = '', meaning = '') {
    const list = document.getElementById('scriptVocabList');
    const row = document.createElement('div');
    row.className = 'script-vocab-row';
    row.style = 'display:flex; gap:6px; align-items:center;';
    row.innerHTML = `
        <input type="text" class="script-v-word" value="${escapeHtml(word)}" placeholder="단어" style="flex:1;">
        <input type="text" class="script-v-meaning" value="${escapeHtml(meaning)}" placeholder="한국어 뜻" style="flex:1;">
        <button type="button" class="btn-log-action btn-log-delete" style="padding:6px 10px;" onclick="this.parentElement.remove()" title="행 삭제">✕</button>
    `;
    list.appendChild(row);
}

async function saveScriptVocabBatch() {
    if (!scriptVocabVideoId || scriptVocabSaving) return;
    const videoId = scriptVocabVideoId;
    const rows = document.querySelectorAll('#scriptVocabList .script-vocab-row');
    const words = [];
    rows.forEach(r => {
        const w = r.querySelector('.script-v-word').value.trim();
        const m = r.querySelector('.script-v-meaning').value.trim();
        if (w && m) {
            words.push({ word: w, meaning: m });
        }
    });

    if (words.length === 0) {
        return alert('저장할 유효한 단어(단어 및 한국어 뜻)를 1개 이상 입력해 주세요.');
    }

    scriptVocabSaving = true;
    try {
        const res = await fetch(`/api/study/videos/${videoId}/vocab/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ words })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '단어 저장에 실패했습니다.');

        scriptVocabSaving = false;
        alert(`등록 ${data.saved_count ?? 0}개 · 중복 제외 ${data.skipped_count ?? 0}개`);
        closeScriptVocabModal();
        loadVocab();
    } catch (err) {
        alert(err.message);
    } finally {
        scriptVocabSaving = false;
    }
}

