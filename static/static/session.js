'use strict';
// All existing same-origin fetch calls, including photo uploads, share session CSRF handling.
let harulogCsrf=document.querySelector('meta[name="harulog-csrf"]').content;
const harulogFetch=window.fetch.bind(window);
window.fetch=async function(input,options={}){
    const url=new URL(typeof input==='string'?input:input.url,location.href);
    const method=(options.method||(typeof input==='object'&&input.method)||'GET').toUpperCase();
    if(url.origin===location.origin){
        const headers=new Headers(options.headers||(typeof input==='object'?input.headers:undefined));
        if(!['GET','HEAD','OPTIONS'].includes(method))headers.set('X-CSRF-Token',harulogCsrf);
        options={...options,headers};
    }
    const response=await harulogFetch(input,options);
    if(url.origin===location.origin&&response.status===401)location.replace('/login');
    return response;
};
async function logoutHaruLog(){
    try{
        const response=await fetch('/api/auth/logout',{method:'POST',credentials:'same-origin',cache:'no-store'}),result=await response.json();
        if(!response.ok||result.authenticated!==false)throw new Error(result.error||'로그아웃하지 못했습니다.');
        harulogCsrf=result.csrf_token||harulogCsrf;
        const check=await fetch('/api/auth/status',{credentials:'same-origin',cache:'no-store'}),state=await check.json();
        if(!check.ok||state.authenticated)throw new Error('로그아웃 상태를 확인하지 못했습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.');
        harulogCsrf=state.csrf_token||harulogCsrf;location.replace('/login?logged_out=1');
    }
    catch(error){alert(error.message);}
}
async function loadLoginAccount(){
    const data=await apiRequest('/api/auth/status',{cache:'no-store'});
    harulogCsrf=data.csrf_token;
    document.getElementById('accountUsername').value=data.username;
    document.getElementById('adminMenu').hidden=data.role!=='admin';
    document.getElementById('adminBadge').hidden=data.role!=='admin';
    const notice=document.getElementById('migrationNotice');notice.hidden=!data.migration_required;
    notice.textContent=data.migration_required?'사용자별 자료 분리 준비가 필요합니다. README의 ownership 마이그레이션을 관리자에게 요청해 주세요. 내 회원 ID: '+data.member_id:'';
}
async function saveLoginAccount(event){
    event.preventDefault();const button=document.getElementById('accountSave');button.disabled=true;
    const status=document.getElementById('accountStatus');status.textContent='';
    try{
        const data=await apiRequest('/api/settings/account',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('accountUsername').value,current_password:document.getElementById('accountCurrentPassword').value,password:document.getElementById('accountNewPassword').value,confirm_password:document.getElementById('accountConfirmPassword').value})});
        harulogCsrf=data.csrf_token;
        ['accountCurrentPassword','accountNewPassword','accountConfirmPassword'].forEach(id=>{document.getElementById(id).value='';});
        status.textContent='로그인 정보를 변경했습니다. 다른 기기의 기존 로그인은 해제됩니다.';
    }catch(error){status.textContent=error.message;}
    finally{button.disabled=false;}
}
document.addEventListener('DOMContentLoaded',()=>{
    document.getElementById('accountForm').addEventListener('submit',saveLoginAccount);
    loadLoginAccount().catch(error=>{document.getElementById('accountStatus').textContent=error.message;});
});
