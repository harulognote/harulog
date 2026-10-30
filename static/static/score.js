// HaruLog v1.9.0 — 기본정보 · 18홀 직접입력 · 타수 추이
let scoreRounds=[];
let scoreEditingId=null;
let scoreBusy=false;
let scorePhotoObjectUrl=null;
let scoreLegacyTotals=null;
const scoreEl=id=>document.getElementById(id);

async function loadScores(){
    scoreEl('scoreListStatus').textContent='라운드를 불러오는 중입니다…';
    try{const rows=await apiRequest('/api/golf/rounds',{cache:'no-store'});if(!Array.isArray(rows))throw new Error('라운드 목록 형식을 확인해 주세요.');scoreRounds=rows;renderScores();scoreEl('scoreListStatus').textContent='';}
    catch(error){scoreEl('scoreListStatus').textContent=error.message;}
}
function renderScores(){
    const totals=scoreRounds.map(row=>row.total_score);
    scoreEl('scoreSummary').innerHTML=[['라운드',`${totals.length}회`],['평균 타수',totals.length?(totals.reduce((a,b)=>a+b,0)/totals.length).toFixed(1):'—'],['최저 타수',totals.length?Math.min(...totals):'—']].map(([label,value])=>`<div><span>${label}</span><strong>${value}</strong></div>`).join('');
    renderScoreTrend();
    const list=scoreEl('scoreRoundList');list.replaceChildren();
    if(!scoreRounds.length){list.textContent='아직 등록된 라운드가 없습니다.';return;}
    scoreRounds.forEach(row=>{
        const card=document.createElement('article');card.className='input-card score-round';
        card.innerHTML=`<div class="score-toolbar"><span class="score-help">${escapeHtml(row.played_on)}</span><div class="log-actions"><button type="button" class="btn-log-action score-edit">수정</button><button type="button" class="btn-log-action btn-log-delete score-delete">삭제</button></div></div><h3>${escapeHtml(row.golf_club||row.course_name)}</h3><p class="score-help">${escapeHtml(row.golf_club?row.course_name:'')}</p><div class="score-result"><span>${escapeHtml(row.player_name)}${row.player_nickname?' ('+escapeHtml(row.player_nickname)+')':''}<small>전반 ${row.front_score} · 후반 ${row.back_score}</small></span><strong>${row.total_score}<small>타</small></strong></div>`;
        card.querySelector('.score-edit').onclick=()=>editScoreRound(row.id);card.querySelector('.score-delete').onclick=()=>deleteScoreRound(row.id);
        const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='홀별 점수 · 동반자 · 사진 보기';details.append(summary);
        const holes=document.createElement('p');holes.className='score-help';holes.textContent=Array.isArray(row.hole_scores)?'1~9홀: '+row.hole_scores.slice(0,9).join(' · ')+' / 10~18홀: '+row.hole_scores.slice(9).join(' · '):'기존 합계 기록 (홀별 점수 미등록)';details.append(holes);
        row.companions.forEach(person=>{const p=document.createElement('p');p.textContent=`${person.name}${person.nickname?' ('+person.nickname+')':''} · ${person.total_score}타`;details.append(p);});
        if(row.memo){const p=document.createElement('p');p.className='score-memo';p.textContent=row.memo;details.append(p);}
        if(row.photo_path){const a=document.createElement('a');a.href=row.photo_path;a.target='_blank';a.rel='noopener';a.className='score-photo-link';const img=document.createElement('img');img.src=row.photo_path;img.alt='스코어카드 원본 열기';img.loading='lazy';a.append(img);details.append(a);}
        card.append(details);list.append(card);
    });
}
function renderScoreTrend(){
    const container=scoreEl('scoreTrend');const rows=scoreRounds.slice(0,20).reverse();
    container.innerHTML='<h3>본인 총타수 추이 · 최근 20회</h3><p class="score-help">날짜순 · 낮을수록 좋은 기록입니다.</p>';
    if(!rows.length){const p=document.createElement('p');p.className='score-help';p.textContent='라운드를 등록하면 타수 그래프가 표시됩니다.';container.append(p);return;}
    const width=520,height=220,left=44,right=18,top=24,bottom=40;
    const values=rows.map(row=>row.total_score);const min=Math.max(0,Math.floor((Math.min(...values)-5)/5)*5),max=Math.ceil((Math.max(...values)+5)/5)*5;
    const x=i=>rows.length===1?(width+left-right)/2:left+i*(width-left-right)/(rows.length-1),y=value=>top+(max-value)*(height-top-bottom)/(max-min);
    let content=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="최근 라운드의 본인 총타수 추이. 아래 기록표에서 정확한 점수를 확인할 수 있습니다."><text x="6" y="14" class="trend-label">타수</text>`;
    for(let i=0;i<=4;i++){const n=min+(max-min)*i/4,py=y(n);content+=`<line x1="${left}" y1="${py}" x2="${width-right}" y2="${py}" class="trend-grid"/><text x="${left-8}" y="${py+4}" text-anchor="end" class="trend-label">${Number(n.toFixed(1))}</text>`;}
    content+=`<polyline points="${rows.map((r,i)=>x(i)+','+y(r.total_score)).join(' ')}" class="trend-line"/>`;
    rows.forEach((r,i)=>{content+=`<circle cx="${x(i)}" cy="${y(r.total_score)}" r="4" class="trend-point"><title>${escapeHtml(r.played_on+' '+(r.golf_club||r.course_name)+' '+r.total_score+'타')}</title></circle>`;if(rows.length<=8)content+=`<text x="${x(i)}" y="${y(r.total_score)-9}" text-anchor="middle" class="trend-label">${r.total_score}</text>`;if(i===0||i===rows.length-1)content+=`<text x="${x(i)}" y="${height-12}" text-anchor="${i===0?'start':'end'}" class="trend-label">${escapeHtml(r.played_on)}</text>`;});
    content+='</svg>';const graph=document.createElement('div');graph.className='score-trend-graph';graph.innerHTML=content;container.append(graph);
    const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='그래프 기록표 보기';details.append(summary);
    const table=document.createElement('table');table.className='score-trend-table';table.innerHTML='<thead><tr><th>날짜 / 골프장</th><th>전반</th><th>후반</th><th>총점</th></tr></thead>';
    const body=document.createElement('tbody');rows.forEach(row=>{const tr=document.createElement('tr');for(const value of [row.played_on+' / '+(row.golf_club||row.course_name),row.front_score,row.back_score,row.total_score]){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);});table.append(body);details.append(table);container.append(details);
}
function createScoreHoles(){
    const container=scoreEl('scoreHoleInputs');
    for(const [first,label] of [[1,'전반 1~9홀'],[10,'후반 10~18홀']]){
        const block=document.createElement('fieldset');block.className='score-hole-section';const title=document.createElement('legend');title.textContent=label;block.append(title);const grid=document.createElement('div');grid.className='score-hole-grid';
        for(let hole=first;hole<first+9;hole++){const label=document.createElement('label');label.textContent=hole+'홀';const input=document.createElement('input');input.type='number';input.id='scoreHole'+hole;input.min='1';input.max='99';input.step='1';input.inputMode='numeric';input.placeholder='타수';input.setAttribute('aria-label',hole+'홀 실제 타수');input.oninput=updateScoreTotal;label.append(input);grid.append(label);}block.append(grid);container.append(block);
    }
}
function getScoreHoles(){return Array.from({length:18},(_,i)=>scoreEl('scoreHole'+(i+1)).value);}
function updateScoreTotal(){
    const values=getScoreHoles();const allBlank=values.every(v=>v==='');
    if(allBlank&&scoreLegacyTotals){scoreEl('scoreFront').value=scoreLegacyTotals[0];scoreEl('scoreBack').value=scoreLegacyTotals[1];scoreEl('scoreTotal').textContent=scoreLegacyTotals[0]+scoreLegacyTotals[1];return;}
    const valid=value=>/^\d+$/.test(value)&&Number(value)>=1&&Number(value)<=99;
    const front=values.slice(0,9),back=values.slice(9);const sum=values=>values.reduce((n,v)=>n+Number(v),0);
    scoreEl('scoreFront').value=front.every(valid)?sum(front):'';scoreEl('scoreBack').value=back.every(valid)?sum(back):'';
    scoreEl('scoreTotal').textContent=values.every(valid)?sum(values):'—';
}
function clearScorePhotoPreview(){if(scorePhotoObjectUrl)URL.revokeObjectURL(scorePhotoObjectUrl);scorePhotoObjectUrl=null;scoreEl('scorePhotoPreview').hidden=true;scoreEl('scorePhotoPreview').removeAttribute('src');}
function openScoreForm(row){
    if(scoreBusy)return;scoreEl('scoreForm').reset();clearScorePhotoPreview();scoreEditingId=row?row.id:null;scoreLegacyTotals=row&&!Array.isArray(row.hole_scores)?[row.front_score,row.back_score]:null;
    scoreEl('scoreFormTitle').textContent=row?'라운드 수정':'라운드 등록';const now=new Date();
    scoreEl('scoreDate').value=row?row.played_on:`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    scoreEl('scorePlayer').value=row?row.player_name:basicSettings.profile.name||'본인';scoreEl('scoreNickname').value=row?row.player_nickname||'':basicSettings.profile.nickname||'';
    scoreEl('scoreClub').value=row?row.golf_club||'':'';scoreEl('scoreCourse').value=row?row.course_name:'';scoreEl('scoreMemo').value=row?row.memo:'';
    for(let i=1;i<=18;i++)scoreEl('scoreHole'+i).value=row&&Array.isArray(row.hole_scores)?row.hole_scores[i-1]:'';
    scoreEl('scoreLegacyNotice').textContent=scoreLegacyTotals?'이전 합계 기록입니다. 홀별 점수를 입력하면 새 합계로 변경됩니다. 홀별 점수 없이 저장하면 기존 합계를 유지합니다.':'';
    scoreEl('scoreCompanions').replaceChildren();(row?row.companions:[]).forEach(addScoreCompanion);populateScoreContacts();
    scoreEl('scoreRemovePhotoLabel').hidden=!(row&&row.photo_path);if(row&&row.photo_path){scoreEl('scorePhotoPreview').src=row.photo_path;scoreEl('scorePhotoPreview').hidden=false;}
    scoreEl('scoreFormStatus').textContent='';scoreEl('scoreForm').hidden=false;updateScoreTotal();scoreEl('scoreForm').scrollIntoView({block:'start',behavior:'smooth'});
}
async function newScoreRound(){
    if(scoreBusy)return;try{await loadBasicSettings();openScoreForm(null);}catch(error){openScoreForm(null);scoreEl('scoreFormStatus').textContent='기본정보를 불러오지 못했습니다. 성명·별명을 직접 확인해 주세요. '+error.message;}
}
async function editScoreRound(id){const row=scoreRounds.find(row=>row.id===id);if(!row||scoreBusy)return;try{await loadBasicSettings();}catch(error){/* 기존 라운드 정보로 편집 가능 */}openScoreForm(row);}
function cancelScoreEdit(){if(scoreBusy)return;clearScorePhotoPreview();scoreEl('scoreForm').hidden=true;scoreEditingId=null;}
function addScoreCompanion(person){
    const container=scoreEl('scoreCompanions');if(container.children.length>=20)return alert('동반자는 최대 20명입니다.');
    const row=document.createElement('div');row.className='score-companion';row.dataset.contactId=person&&person.contact_id?person.contact_id:'';
    row.innerHTML='<input type="text" class="companion-name" aria-label="동반자 성명" placeholder="성명" maxlength="100" required><input type="text" class="companion-nickname" aria-label="동반자 별명" placeholder="별명" maxlength="100"><input type="number" class="companion-total" aria-label="동반자 총점" placeholder="총점" min="1" max="400" step="1" required><button type="button" class="btn-log-action">삭제</button>';
    if(person){row.querySelector('.companion-name').value=person.name;row.querySelector('.companion-nickname').value=person.nickname||'';row.querySelector('.companion-total').value=person.total_score||'';}
    row.querySelector('button').onclick=()=>row.remove();container.append(row);
}
function onScorePhotoChange(){clearScorePhotoPreview();const file=scoreEl('scorePhoto').files[0];if(!file)return;if(file.size>12*1024*1024){scoreEl('scorePhoto').value='';return alert('사진은 12MB 이하로 선택해 주세요.');}scorePhotoObjectUrl=URL.createObjectURL(file);scoreEl('scorePhotoPreview').src=scorePhotoObjectUrl;scoreEl('scorePhotoPreview').hidden=false;scoreEl('scoreRemovePhoto').checked=false;}
async function saveScoreRound(event){
    event.preventDefault();if(scoreBusy)return;const values=getScoreHoles();const legacy=scoreLegacyTotals&&values.every(v=>v==='');
    if(!legacy&&values.some(v=>!/^\d+$/.test(v)||Number(v)<1||Number(v)>99)){scoreEl('scoreFormStatus').textContent='1~18홀의 실제 타수를 모두 입력해 주세요. 입력 전 칸을 0으로 계산하지 않습니다.';return;}
    updateScoreTotal();
    const companions=Array.from(scoreEl('scoreCompanions').children).map(row=>({name:row.querySelector('.companion-name').value.trim(),nickname:row.querySelector('.companion-nickname').value.trim(),contact_id:row.dataset.contactId?Number(row.dataset.contactId):null,total_score:row.querySelector('.companion-total').value}));
    const data={played_on:scoreEl('scoreDate').value,golf_club:scoreEl('scoreClub').value.trim(),course_name:scoreEl('scoreCourse').value.trim(),player_name:scoreEl('scorePlayer').value.trim()||'본인',player_nickname:scoreEl('scoreNickname').value.trim(),hole_scores:legacy?null:values.map(Number),front_score:scoreEl('scoreFront').value,back_score:scoreEl('scoreBack').value,companions,memo:scoreEl('scoreMemo').value};
    const form=new FormData();form.append('data',JSON.stringify(data));form.append('remove_photo',scoreEl('scoreRemovePhoto').checked?'1':'0');const file=scoreEl('scorePhoto').files[0];if(file)form.append('photo',file);
    scoreBusy=true;scoreEl('scoreSaveButton').disabled=true;scoreEl('scoreFormStatus').textContent='저장 중입니다…';
    try{await apiRequest('/api/golf/rounds'+(scoreEditingId===null?'':`/${scoreEditingId}`),{method:scoreEditingId===null?'POST':'PUT',body:form});scoreEl('scoreForm').hidden=true;clearScorePhotoPreview();scoreEditingId=null;await loadScores();}
    catch(error){scoreEl('scoreFormStatus').textContent=error.message;}finally{scoreBusy=false;scoreEl('scoreSaveButton').disabled=false;}
}
async function deleteScoreRound(id){if(scoreBusy||!confirm('이 라운드와 사진을 삭제하시겠습니까?'))return;scoreBusy=true;try{await apiRequest(`/api/golf/rounds/${id}`,{method:'DELETE'});scoreBusy=false;if(scoreEditingId===id)cancelScoreEdit();await loadScores();}catch(error){alert(error.message);}finally{scoreBusy=false;}}
document.addEventListener('DOMContentLoaded',()=>{createScoreHoles();scoreEl('scoreForm').addEventListener('submit',saveScoreRound);});
