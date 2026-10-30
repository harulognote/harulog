// HaruLog v1.9.0 — 기본설정
let basicSettings = {profile:{name:'',nickname:''},contacts:[]};
let editingContactId = null;
let settingsSaving = false;
const settingsEl = id => document.getElementById(id);
async function loadBasicSettings() {
    const data = await apiRequest('/api/settings',{cache:'no-store'});
    if (!data.profile || !Array.isArray(data.contacts)) throw new Error('기본설정 응답을 확인해 주세요.');
    basicSettings=data;
    settingsEl('profileName').value=data.profile.name;
    settingsEl('profileNickname').value=data.profile.nickname;
    renderContacts(); populateScoreContacts(); settingsEl('settingsStatus').textContent='';
    return data;
}
function populateScoreContacts() {
    const select=scoreEl('scoreContactSelect');const previous=select.value;select.replaceChildren();
    const empty=document.createElement('option');empty.value='';empty.textContent='저장된 동반자 선택';select.append(empty);
    basicSettings.contacts.forEach(person=>{const option=document.createElement('option');option.value=person.id;option.textContent=person.name+(person.nickname?' ('+person.nickname+')':'');select.append(option);});
    select.value=previous;
}
function addSavedScoreCompanion() {
    const id=Number(scoreEl('scoreContactSelect').value);
    const person=basicSettings.contacts.find(person=>person.id===id);
    if(!person)return alert('주소록에서 동반자를 선택해 주세요.');
    if(Array.from(scoreEl('scoreCompanions').children).some(row=>Number(row.dataset.contactId)===id))return alert('이미 추가한 동반자입니다.');
    addScoreCompanion({...person,total_score:'',contact_id:person.id});
}
function renderContacts(){
    const list=settingsEl('contactList');list.replaceChildren();
    if(!basicSettings.contacts.length){list.textContent='저장된 동반자가 없습니다.';return;}
    basicSettings.contacts.forEach(person=>{
        const card=document.createElement('article');card.className='input-card contact-card';
        const toolbar=document.createElement('div');toolbar.className='score-toolbar';toolbar.style.marginBottom='2px';
        const title=document.createElement('h3');title.style.margin='0';title.style.fontSize='0.95rem';
        title.textContent=person.name+(person.nickname?' ('+person.nickname+')':'');
        const actions=document.createElement('div');actions.className='log-actions';
        const editBtn=document.createElement('button');editBtn.type='button';editBtn.className='btn-log-action';editBtn.textContent='수정';editBtn.onclick=()=>editContact(person.id);
        const delBtn=document.createElement('button');delBtn.type='button';delBtn.className='btn-log-action btn-log-delete';delBtn.textContent='삭제';delBtn.onclick=()=>deleteContact(person.id);
        actions.append(editBtn,delBtn);
        toolbar.append(title,actions);
        card.append(toolbar);
        for(const text of [person.phone,person.address,person.memo]){
            if(text){
                const p=document.createElement('p');p.className='score-help contact-text';p.style.marginTop='3px';p.textContent=text;
                card.append(p);
            }
        }
        list.append(card);
    });
}
function editContact(id=null){
    if(settingsSaving)return;
    const person=basicSettings.contacts.find(person=>person.id===id);editingContactId=person?person.id:null;
    settingsEl('contactForm').reset();
    for(const [key,field] of [['name','contactName'],['nickname','contactNickname'],['phone','contactPhone'],['address','contactAddress'],['memo','contactMemo']])settingsEl(field).value=person?person[key]:'';
    settingsEl('contactFormTitle').textContent=person?'동반자 수정':'동반자 등록';settingsEl('contactStatus').textContent='';settingsEl('contactForm').hidden=false;settingsEl('contactForm').scrollIntoView({block:'nearest'});
}
function closeContactForm(){if(!settingsSaving){settingsEl('contactForm').hidden=true;editingContactId=null;}}
async function saveProfile(event){
    event.preventDefault();if(settingsSaving)return;settingsSaving=true;settingsEl('profileSave').disabled=true;
    try{await apiRequest('/api/settings/profile',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:settingsEl('profileName').value,nickname:settingsEl('profileNickname').value})});await loadBasicSettings();settingsEl('profileStatus').textContent='본인정보를 저장했습니다. 새 라운드부터 기본값으로 불러옵니다.';}
    catch(error){settingsEl('profileStatus').textContent=error.message;}finally{settingsSaving=false;settingsEl('profileSave').disabled=false;}
}
async function saveContact(event){
    event.preventDefault();if(settingsSaving)return;settingsSaving=true;settingsEl('contactSave').disabled=true;
    const data={};for(const [key,field] of [['name','contactName'],['nickname','contactNickname'],['phone','contactPhone'],['address','contactAddress'],['memo','contactMemo']])data[key]=settingsEl(field).value;
    try{await apiRequest('/api/settings/contacts'+(editingContactId===null?'':`/${editingContactId}`),{method:editingContactId===null?'POST':'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});settingsEl('contactForm').hidden=true;editingContactId=null;await loadBasicSettings();}
    catch(error){settingsEl('contactStatus').textContent=error.message;}finally{settingsSaving=false;settingsEl('contactSave').disabled=false;}
}
async function deleteContact(id){
    if(settingsSaving||!confirm('주소록에서 이 동반자를 삭제하시겠습니까? 기존 라운드의 동반자 기록은 유지됩니다.'))return;settingsSaving=true;
    try{await apiRequest(`/api/settings/contacts/${id}`,{method:'DELETE'});if(editingContactId===id){settingsEl('contactForm').hidden=true;editingContactId=null;}await loadBasicSettings();}
    catch(error){settingsEl('settingsStatus').textContent=error.message;}finally{settingsSaving=false;}
}
document.addEventListener('DOMContentLoaded',()=>{settingsEl('profileForm').addEventListener('submit',saveProfile);settingsEl('contactForm').addEventListener('submit',saveContact);});
