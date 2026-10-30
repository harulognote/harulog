'use strict';
let loginCsrf='',firstSetup=false,signupMode=false;
const setupStorageKey='harulog.initial-admin';
const usernameStorageKey='harulog.remembered-username';
const loginEl=id=>document.getElementById(id);
const fragmentToken=new URLSearchParams(location.hash.slice(1)).get('setup')||'';
let setupToken=fragmentToken;
try{
    if(fragmentToken)sessionStorage.setItem(setupStorageKey,fragmentToken);
    else setupToken=sessionStorage.getItem(setupStorageKey)||'';
}catch(_){/* Registration still works if browser storage is unavailable. */}
if(location.hash)history.replaceState(null,'',location.pathname);
function clearSetupToken(){
    setupToken='';loginEl('setupCode').value='';
    try{sessionStorage.removeItem(setupStorageKey);}catch(_){}
}
function restoreRememberedUsername(){
    try{const saved=localStorage.getItem(usernameStorageKey)||'';loginEl('loginUsername').value=saved;loginEl('rememberUsername').checked=Boolean(saved);}catch(_){/* Login remains available when storage is blocked. */}
}
function saveRememberedUsername(){
    try{if(loginEl('rememberUsername').checked)localStorage.setItem(usernameStorageKey,loginEl('loginUsername').value.trim());else localStorage.removeItem(usernameStorageKey);}catch(_){/* Remembering an ID is optional. */}
}
async function fetchLoginState(){
    const response=await fetch('/api/auth/status',{cache:'no-store',credentials:'same-origin'});
    const state=await response.json();if(!response.ok)throw new Error(state.error||'로그인 상태를 확인하지 못했습니다.');
    loginCsrf=state.csrf_token;
    return state;
}
function renderLoginForm(state){
    firstSetup=!state.configured;
    loginEl('signupToggle').hidden=firstSetup;
    loginEl('setupCodeLabel').hidden=!firstSetup;
    loginEl('setupCode').required=firstSetup;
    if(firstSetup&&!state.setup_allowed){
        loginEl('loginForm').hidden=true;
        loginEl('loginTitle').textContent='실행 중인 서버 버전을 확인해 주세요';
        loginEl('loginHelp').textContent='이전 서버의 등록 제한이 응답하고 있습니다. 실행 중인 HaruLog를 종료한 뒤 교체한 폴더의 Run_harulog.bat을 다시 실행해 주세요.';
        return;
    }
    if(state.configured)clearSetupToken();
    loginEl('loginForm').hidden=false;
    loginEl('loginTitle').textContent=firstSetup?'최초 관리자 등록':signupMode?'회원가입':'로그인';
    loginEl('loginHelp').textContent=firstSetup?'아이디와 8자 이상 비밀번호를 설정해 주세요. 서버 실행창의 최신 설정 코드를 입력하거나 설정 링크를 열어 주세요.':signupMode?'가입 후 관리자 승인을 받아 본인 공간을 이용합니다.':'HaruLog 로그인 계정을 입력해 주세요.';
    loginEl('loginConfirmLabel').hidden=!(firstSetup||signupMode);
    loginEl('rememberUsernameLabel').hidden=firstSetup||signupMode;
    loginEl('loginConfirm').required=firstSetup||signupMode;
    loginEl('loginPassword').minLength=firstSetup||signupMode?8:1;
    loginEl('loginPassword').autocomplete=firstSetup||signupMode?'new-password':'current-password';
    loginEl('loginSubmit').textContent=firstSetup?'관리자 등록 후 시작':signupMode?'가입 신청':'로그인';
    loginEl('signupToggle').textContent=signupMode?'로그인으로 돌아가기':'회원가입';
    if(firstSetup&&!loginEl('setupCode').value)loginEl('setupCode').value=setupToken;
    if(!firstSetup&&!signupMode&&!loginEl('loginUsername').value)restoreRememberedUsername();
}
async function readLoginState(){
    const state=await fetchLoginState();
    if(state.authenticated){clearSetupToken();location.replace('/');return;}
    renderLoginForm(state);loginEl('loginUsername').focus();
}
loginEl('loginForm').addEventListener('submit',async event=>{
    event.preventDefault();loginEl('loginSubmit').disabled=true;loginEl('loginStatus').textContent='';
    try{
        // Refresh signed-session CSRF immediately before each submission.
        let state=await fetchLoginState();
        if(state.authenticated){clearSetupToken();location.replace('/');return;}
        if(firstSetup&&state.configured){signupMode=false;renderLoginForm(state);loginEl('loginStatus').textContent='관리자가 이미 등록되어 있습니다. 같은 아이디와 비밀번호로 로그인해 주세요.';return;}
        if(firstSetup){
            setupToken=loginEl('setupCode').value.trim();
            if(!setupToken)throw new Error('서버 콘솔의 최신 설정 링크를 열거나 설정 코드를 입력해 주세요.');
            try{sessionStorage.setItem(setupStorageKey,setupToken);}catch(_){}
        }
        let response,data;
        for(let attempt=0;attempt<2;attempt++){
            response=await fetch('/api/auth/'+(firstSetup?'setup':signupMode?'signup':'login'),{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':loginCsrf},body:JSON.stringify({username:loginEl('loginUsername').value,password:loginEl('loginPassword').value,confirm_password:loginEl('loginConfirm').value,setup_token:setupToken})});
            data=await response.json();
            if(response.status===403&&data.code==='CSRF_EXPIRED'&&attempt===0){state=await fetchLoginState();continue;}
            break;
        }
        if(!response.ok){
            if(data.code==='CSRF_EXPIRED')throw new Error('인증 쿠키를 유지하지 못했습니다. 이 사이트의 쿠키 허용 여부와 서버 중복 실행을 확인한 뒤 다시 시도해 주세요.');
            throw new Error(data.error||'요청을 처리하지 못했습니다.');
        }
        if(signupMode){loginEl('loginStatus').textContent=data.message;loginEl('loginForm').reset();return;}
        if(!firstSetup)saveRememberedUsername();
        clearSetupToken();location.replace('/');
    }catch(error){loginEl('loginStatus').textContent=error.message;}
    finally{loginEl('loginSubmit').disabled=false;}
});
loginEl('signupToggle').addEventListener('click',()=>{
    signupMode=!signupMode;loginEl('loginStatus').textContent='';loginEl('loginForm').reset();
    renderLoginForm({configured:true,setup_allowed:false});
});
readLoginState().catch(error=>{loginEl('loginStatus').textContent=error.message;});
