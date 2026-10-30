// HaruLog v2.7.1: dependency-free frontend regression checks (Node 18+).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const nodes = new Map();
function element() {
    return {value:'',textContent:'',innerHTML:'',style:{},children:[],hidden:false,
        classList:{add(){},remove(){},toggle(){},contains(){return false}},
        appendChild(child){this.children.push(child)},append(child){this.children.push(child)},
        addEventListener(){},setAttribute(){},querySelector(){return element()}};
}
const callbacks=[];
const context = vm.createContext({console,AbortController,setTimeout,clearTimeout,URL,
    alert(){},confirm(){return true},
    document:{addEventListener(event,callback){if(event==='DOMContentLoaded')callbacks.push(callback)},
        getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},
        createElement:element,querySelectorAll(){return []}},
    fetch:async()=>{throw Error('Unexpected network request')}});
const root=path.join(__dirname,'..','static');
for(const file of ['common.js','app.js','score.js','invoice.js','settings.js','utility.js']){
    vm.runInContext(fs.readFileSync(path.join(root,file),'utf8'),context,{filename:file});
}
const run=code=>vm.runInContext(code,context);
const response=data=>({ok:true,status:200,json:async()=>data,text:async()=>JSON.stringify(data)});
(async()=>{
    let count=0;
    assert.equal(run(`escapeHtml('<"&')`),'&lt;&quot;&amp;');count++;
    // One list fetch populates both the video cards and the dropdown at startup.
    const requests=[];
    context.fetch=async url=>{requests.push(url);return response([])};
    callbacks[0]();
    await new Promise(resolve=>setTimeout(resolve,0));
    assert.equal(requests.filter(x=>x==='/api/study/videos').length,1);count++;
    // Editing fees must retain legacy electricity and water usage fields.
    run(`utilityRecords=[{id:1,electricity_usage:'123.45',water_usage:'6.78'}];utilityEditingId=1;
         loadUtilityRecords=async()=>{};loadUtilityStats=async()=>{};`);
    nodes.get('utilityMonth') || context.document.getElementById('utilityMonth');
    nodes.get('utilityMonth').value='2026-10';
    let saved;
    context.fetch=async(url,options)=>{saved=JSON.parse(options.body);return response({status:'success'})};
    await context.saveUtilityRecord({preventDefault(){}});
    assert.equal(saved.electricity_usage,'123.45');assert.equal(saved.water_usage,'6.78');count++;
    // Closing an extraction modal prevents a delayed response from replacing a later modal.
    run(`currentVideoId=1;currentVideo={id:1,title:'A'};`);
    let finish;
    context.fetch=()=>new Promise(resolve=>{finish=resolve});
    const extracting=context.openScriptVocabModal();
    context.closeScriptVocabModal();
    const list=context.document.getElementById('scriptVocabList');list.innerHTML='new session';
    finish(response({extracted_words:[{word:'makan',meaning:'먹다'}]}));
    await extracting;assert.equal(list.innerHTML,'new session');count++;
    // A preview belongs to the video captured when it was opened, even if selection changes.
    run(`scriptVocabVideoId=1;currentVideoId=2;`);
    context.document.querySelectorAll=selector=>selector.includes('.script-vocab-row')?
        [{querySelector:selector=>({value:selector.includes('word')?'makan':'먹다'})}]:[];
    let savedUrl;
    context.fetch=async url=>{savedUrl=url;return response({saved_count:0,skipped_count:1})};
    run('loadVocab=async()=>{}');
    await context.saveScriptVocabBatch();
    assert.equal(savedUrl,'/api/study/videos/1/vocab/generate');count++;
    console.log(`${count} frontend regression checks passed`);
})().catch(error=>{console.error(error);process.exitCode=1});
