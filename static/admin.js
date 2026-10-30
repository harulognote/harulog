'use strict';
let adminMembers=[],adminPage=1;
async function loadMembers(page=1){
    adminPage=page;const status=document.getElementById('adminStatus');status.textContent='';
    try{
        const data=await apiRequest('/api/admin/members?page='+page+'&q='+encodeURIComponent(document.getElementById('memberSearch').value),{cache:'no-store'});
        adminMembers=data.members;const list=document.getElementById('memberList');list.replaceChildren();
        document.getElementById('memberCount').textContent=`검색 ${data.total}명 · ${data.page}페이지`;
        document.getElementById('memberPrev').disabled=page<=1;document.getElementById('memberNext').disabled=page*100>=data.total;
        for(const member of adminMembers){
            const card=document.createElement('article');card.className='input-card';
            const title=document.createElement('h3');title.textContent=`#${member.id} ${member.display_name} (${member.username})`;
            const text=document.createElement('p');text.textContent=`${member.role==='admin'?'관리자':'일반 사용자'} · ${{active:'사용 중',pending:'승인 대기',suspended:'이용 정지',deleted:'삭제 처리'}[member.status]||member.status}`;
            const edit=document.createElement('button');edit.type='button';edit.className='btn-edit-video';edit.textContent='조회·수정';edit.addEventListener('click',()=>editMember(member.id));
            card.append(title,text,edit);list.append(card);
        }
        if(!adminMembers.length)list.textContent='조회된 멤버가 없습니다.';
    }catch(error){status.textContent=error.message;}
}
function editMember(id){
    const member=adminMembers.find(item=>item.id===id);if(!member)return;
    const form=document.getElementById('memberForm');form.reset();form.hidden=false;
    form.dataset.memberId=String(id);
    for(const [field,key] of [['memberUsername','username'],['memberName','display_name'],['memberRole','role'],['memberStatus','status']])document.getElementById(field).value=member[key];
    document.getElementById('memberEditTitle').textContent=`멤버 #${id} 관리`;
    document.getElementById('memberFormStatus').textContent='';form.scrollIntoView({behavior:'smooth',block:'start'});
}
async function changeMember(event,remove=false){
    event.preventDefault();const form=document.getElementById('memberForm');const id=Number(form.dataset.memberId);
    if(!id)return;
    const formStatus=document.getElementById('memberFormStatus'),adminPassword=document.getElementById('memberAdminPassword');
    formStatus.textContent='';
    if(!adminPassword.value){formStatus.textContent='저장하려면 관리자 본인의 현재 비밀번호를 입력해 주세요.';adminPassword.focus();adminPassword.scrollIntoView({behavior:'smooth',block:'center'});return;}
    if(!document.getElementById('memberName').value.trim()){formStatus.textContent='멤버 이름을 입력해 주세요.';document.getElementById('memberName').focus();return;}
    if(remove&&!confirm('이 멤버를 삭제 처리하시겠습니까? 로그인은 차단되며 기존 자료와 작업 기록은 보존됩니다.'))return;
    const save=document.getElementById('memberSave'),del=document.getElementById('memberDelete');save.disabled=true;del.disabled=true;
    try{
        const data={};for(const [field,key] of [['memberUsername','username'],['memberName','display_name'],['memberRole','role'],['memberStatus','status'],['memberNewPassword','new_password'],['memberAdminPassword','admin_password']])data[key]=document.getElementById(field).value;
        const result=await apiRequest('/api/admin/members/'+id,{method:remove?'DELETE':'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
        form.reset();form.hidden=true;await loadMembers(adminPage);
        document.getElementById('adminStatus').textContent=(result.member?.display_name||'멤버')+' 정보를 저장했습니다. 다른 기존 로그인 세션은 다시 로그인해야 합니다.';
        document.getElementById('adminStatus').scrollIntoView({behavior:'smooth',block:'center'});
    }catch(error){formStatus.textContent=error.message;formStatus.scrollIntoView({behavior:'smooth',block:'center'});}
    finally{save.disabled=false;del.disabled=false;document.getElementById('memberAdminPassword').value='';document.getElementById('memberNewPassword').value='';}
}
async function loadAdminAudit(){
    try{const data=await apiRequest('/api/admin/audit');const list=document.getElementById('adminAudit');list.replaceChildren();for(const row of data.records){const item=document.createElement('p');item.textContent=`${row.created_at} · 관리자 #${row.actor_id} → 멤버 #${row.target_id} · ${row.action} · ${row.details}`;list.append(item);}if(!data.records.length)list.textContent='관리 작업 기록이 없습니다.';}
    catch(error){document.getElementById('adminStatus').textContent=error.message;}
}
document.addEventListener('DOMContentLoaded',()=>{
    document.getElementById('memberForm').addEventListener('submit',event=>changeMember(event));
    document.getElementById('memberDelete').addEventListener('click',event=>changeMember(event,true));
});
