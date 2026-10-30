const assert=require('assert'),fs=require('fs'),vm=require('vm');
const script=fs.readFileSync(__dirname+'/../static/login.js','utf8');
const settle=()=>new Promise(resolve=>setImmediate(resolve));
function browser(storage=new Map(),fragment='#setup=console-token',failures=0,configured=false,remembered=new Map()){
 const elements={},listeners={},posts=[],redirects=[];let serial=0,remaining=failures;
 const el=id=>elements[id]||(elements[id]={value:'',hidden:true,disabled:false,required:false,textContent:'',focus(){},reset(){},addEventListener(type,fn){listeners[id+':'+type]=fn;}});
 const context={URLSearchParams,sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},localStorage:{getItem:k=>remembered.get(k)||null,setItem:(k,v)=>remembered.set(k,v),removeItem:k=>remembered.delete(k)},location:{hash:fragment,pathname:'/login',replace:v=>redirects.push(v)},history:{replaceState(){}},document:{getElementById:el},fetch:async(url,options={})=>{
  if(options.method==='POST'){
   posts.push({url,options,data:JSON.parse(options.body)});
   if(remaining-->0)return {ok:false,status:403,json:async()=>({code:'CSRF_EXPIRED',error:'expired'})};
   return {ok:true,status:200,json:async()=>({ok:true})};
  }
  serial++;return {ok:true,status:200,json:async()=>({configured,authenticated:false,setup_allowed:true,csrf_token:'csrf-'+serial})};
 }};
 vm.createContext(context);vm.runInContext(script,context);
 return {context,el,listeners,posts,redirects,storage,remembered};
}
(async()=>{
 let b=browser();await settle();
 assert.equal(b.el('setupCode').value,'console-token');assert.equal(b.el('loginPassword').minLength,8);
 b=browser(b.storage,'');await settle();assert.equal(b.el('setupCode').value,'console-token');assert.equal(b.el('loginForm').hidden,false);
 b.el('loginUsername').value='owner';b.el('loginPassword').value='abcd1234';b.el('loginConfirm').value='abcd1234';
 await b.listeners['loginForm:submit']({preventDefault(){}});
 assert.equal(b.posts[0].options.headers['X-CSRF-Token'],'csrf-2');assert.equal(b.redirects.at(-1),'/');assert.equal(b.storage.size,0);
 b=browser(new Map(),'#setup=console-token',1);await settle();b.el('loginPassword').value='abcd1234';
 await b.listeners['loginForm:submit']({preventDefault(){}});
 assert.equal(b.posts.length,2);assert.equal(b.posts[1].options.headers['X-CSRF-Token'],'csrf-3');assert.equal(b.posts[1].data.password,'abcd1234');
 b=browser(new Map(),'#setup=console-token',4);await settle();b.el('loginPassword').value='abcd1234';
 await b.listeners['loginForm:submit']({preventDefault(){}});
 assert.equal(b.posts.length,2);assert.ok(b.el('loginStatus').textContent.includes('쿠키'));assert.equal(b.el('loginPassword').value,'abcd1234');assert.equal(b.storage.get('harulog.initial-admin'),'console-token');
 b=browser(new Map(),'');await settle();assert.equal(b.el('loginForm').hidden,false);assert.equal(b.el('setupCode').required,true);
 const remembered=new Map([['harulog.remembered-username','saved-user']]);b=browser(new Map(),' ',0,true,remembered);await settle();
 assert.equal(b.el('loginUsername').value,'saved-user');assert.equal(b.el('rememberUsername').checked,true);assert.equal(b.el('rememberUsernameLabel').hidden,false);
 b.el('loginUsername').value='new-user';b.el('loginPassword').value='password';await b.listeners['loginForm:submit']({preventDefault(){}});assert.equal(remembered.get('harulog.remembered-username'),'new-user');
 console.log('16 login expiry, recovery and remembered-ID checks passed');
})().catch(error=>{console.error(error);process.exit(1);});
