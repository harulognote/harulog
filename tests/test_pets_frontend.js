const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(require('path').join(__dirname,'../static/pets.js'),'utf8');
assert(source.includes('현재 상태'),'pet cards must identify the stored status');
assert(source.includes('정보·상태 수정'),'status changes must use the edit flow');
assert(!source.includes('>비활성화</button>'),'pet cards must not show a misleading fixed inactive button');
assert(!/renderPets\(\);if\([^\n]+loadPetPedigree\(\)/.test(source),'loading pets must not automatically load pedigree');
assert(!/if\(pedigree\)loadPetPedigree\(\)/.test(source),'opening pedigree tab must not query pedigree');
assert(source.includes('clearPetPedigreeResult'),'changing species must clear the old result');
const html=fs.readFileSync(require('path').join(__dirname,'../static/index.html'),'utf8');
assert(html.includes('onchange="clearPetPedigreeResult()"'),'species selection must not query automatically');
assert(html.includes('onclick="loadPetPedigree()">족보 조회</button>'),'only the pedigree query button starts the query');
const context={console,URL,URLSearchParams,Headers,FormData,confirm:()=>true,alert(){},requestAnimationFrame(){},encodeURI,encodeURIComponent,
 window:{addEventListener(){}},document:{getElementById(){return {style:{},value:'',textContent:'',files:[],reset(){}}},querySelector(){return null}}};
vm.createContext(context);vm.runInContext(source,context);
(async()=>{
 context.fetch=async()=>({ok:false,status:404,headers:{get:()=> 'text/html'},text:async()=> '<!doctype html><title>404</title>'});
 await assert.rejects(vm.runInContext("petRequest('/api/pets/lineage')",context),/이전 버전/);
 context.fetch=async()=>({ok:true,status:200,headers:{get:()=> 'application/json'},text:async()=> JSON.stringify({version:'2.9.5'})});
 await assert.rejects(vm.runInContext('ensurePetServerVersion()',context),/화면은 v2.9.12.*서버는 v2.9.5/);
 const layout=JSON.parse(vm.runInContext(`JSON.stringify((()=>{const rows=[
  {id:1,name:'부1',sex:'male',generation_no:1,sire_id:null,dam_id:null},
  {id:2,name:'모',sex:'female',generation_no:1,sire_id:null,dam_id:null},
  {id:3,name:'부2',sex:'male',generation_no:1,sire_id:null,dam_id:null},
  {id:4,name:'자녀',sex:'female',generation_no:2,sire_id:1,dam_id:2},
  {id:5,name:'자녀2',sex:'male',generation_no:2,sire_id:3,dam_id:2}];const value=calculateLineageLayout(rows);return {p1:value.positions.get(1),dam:value.positions.get(2),p2:value.positions.get(3),child:value.positions.get(4)};})())`,context));
 assert(layout.p1.x<layout.dam.x&&layout.dam.x<layout.p2.x,'shared dam must be centered between sires');
 assert(layout.child.y>layout.dam.y,'child generation must be below parents');
 console.log('12 pet manual-query, status, server-version and lineage-layout frontend checks passed');
})().catch(error=>{console.error(error);process.exit(1)});
