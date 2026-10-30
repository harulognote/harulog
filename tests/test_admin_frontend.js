const fs=require('fs'),vm=require('vm'),assert=require('assert');
(async()=>{
 const elements={};const el=id=>elements[id]||(elements[id]={value:'',textContent:'',hidden:true,disabled:false,addEventListener(){}});
 const context={Headers,URL,location:{href:'https://app.test/',origin:'https://app.test',replace(){}},document:{querySelector:()=>({content:'csrf'}),getElementById:el,addEventListener(){}},window:{fetch:async()=>({status:200,ok:true})},alert(){},apiRequest:async()=>({username:'alice',role:'user',member_id:2,migration_required:false,csrf_token:'new'})};
 vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../static/session.js','utf8'),context);
 await context.loadLoginAccount();assert.equal(el('adminMenu').hidden,true);assert.equal(el('migrationNotice').hidden,true);
 context.apiRequest=async()=>({username:'admin',role:'admin',member_id:1,migration_required:true,csrf_token:'new'});
 await context.loadLoginAccount();assert.equal(el('adminMenu').hidden,false);assert.equal(el('migrationNotice').hidden,false);assert.ok(el('migrationNotice').textContent.includes('1'));
 const html=fs.readFileSync(__dirname+'/../static/index.html','utf8');assert.ok(/id="adminMenu"[^>]*hidden/.test(html));
 assert.ok(/id="memberForm"[^>]*novalidate/.test(html));
 assert.ok(html.includes('* 저장 필수'));
 const adminSource=fs.readFileSync(__dirname+'/../static/admin.js','utf8');
 assert.ok(adminSource.includes('저장하려면 관리자 본인의 현재 비밀번호를 입력해 주세요.'));
 assert.ok(adminSource.includes("result.member?.display_name"));
 const login=fs.readFileSync(__dirname+'/../static/login.html','utf8');assert.ok(login.includes('signupToggle'));
 console.log('11 admin visibility, member-save and signup frontend checks passed');
})().catch(error=>{console.error(error);process.exit(1)});
