const fs=require('fs'),vm=require('vm'),assert=require('assert');
(async()=>{
 const calls=[],redirects=[],elements={};
 const element=id=>elements[id]||(elements[id]={value:'',textContent:'',disabled:false,addEventListener(){}});
 const context={Headers,URL,location:{href:'https://harulog.test/',origin:'https://harulog.test',replace:value=>redirects.push(value)},document:{querySelector:()=>({content:'initial-csrf'}),getElementById:element,addEventListener(){}},window:{fetch:async(input,options)=>{calls.push({input,options});if(input==='/api/auth/logout')return {status:200,ok:true,json:async()=>({authenticated:false,csrf_token:'anonymous-csrf'})};if(input==='/api/auth/status')return {status:200,ok:true,json:async()=>({authenticated:false,csrf_token:'verified-csrf'})};return {status:200,ok:true};}},apiRequest:async()=>({username:'owner',csrf_token:'rotated-csrf'}),alert:()=>{}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../static/session.js','utf8'),context);
 context.fetch=(...args)=>context.window.fetch(...args);
 await context.window.fetch('/api/logs',{method:'POST',body:'photo'});
 assert.equal(calls.at(-1).options.headers.get('X-CSRF-Token'),'initial-csrf');assert.equal(calls.at(-1).options.body,'photo');
 await context.window.fetch('/api/logs');assert.equal(calls.at(-1).options.headers.get('X-CSRF-Token'),null);
 await context.window.fetch('https://other.test/',{method:'POST'});assert.equal(calls.at(-1).options.headers,undefined);
 await context.loadLoginAccount();assert.equal(element('accountUsername').value,'owner');
 await context.window.fetch('/api/logs',{method:'DELETE'});assert.equal(calls.at(-1).options.headers.get('X-CSRF-Token'),'rotated-csrf');
 element('accountCurrentPassword').value='old';element('accountNewPassword').value='new';element('accountConfirmPassword').value='new';
 await context.saveLoginAccount({preventDefault(){}});assert.equal(element('accountCurrentPassword').value,'');assert.equal(element('accountNewPassword').value,'');
 await context.logoutHaruLog();assert.equal(redirects.at(-1),'/login?logged_out=1');assert.equal(calls.at(-1).input,'/api/auth/status');
 console.log('8 login frontend checks passed');
})().catch(error=>{console.error(error);process.exit(1);});
