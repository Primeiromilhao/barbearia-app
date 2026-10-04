const API="https://barbearia-api-w37o.onrender.com/api/dev";const $=id=>document.getElementById(id);
async function api(path,opt={}){const r=await fetch(API+path,{credentials:"include",headers:{"Content-Type":"application/json",...(opt.headers||{})},...opt});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||"Erro");return d}
async function check(){try{const d=await api("/me");if(d.authenticated){$("loginView").hidden=true;$("consoleView").hidden=false;loadAll()}}catch{}}
$("loginBtn").onclick=async()=>{try{await api("/login",{method:"POST",body:JSON.stringify({password:$("devPassword").value})});$("devPassword").value="";$("loginView").hidden=true;$("consoleView").hidden=false;loadAll()}catch(e){$("loginStatus").textContent=e.message}};
$("logoutBtn").onclick=async()=>{await api("/logout",{method:"POST"});location.reload()};
async function loadAll(){try{const d=await api("/dashboard");$("devContent").innerHTML="<h2>Diagnóstico</h2><pre>"+esc(JSON.stringify(d,null,2))+"</pre>"}catch(e){$("devContent").textContent=e.message}} 
async function showClients(){const d=await api("/clients");renderTable("Clientes",d,["id","name","phone","appointments"])}
async function showAppointments(){const d=await api("/appointments");renderTable("Todos os agendamentos",d,["id","client","phone","service","date","time","status"])}
async function showNotifications(){const d=await api("/notifications");renderTable("Fila de notificações",d,["id","appointment_id","channel","status","phone","message"])}
async function showServices(){const d=await api("/services");renderTable("Serviços",d,["id","name","price","duration"])}
async function showAudit(){const d=await api("/audit");renderTable("Auditoria",d,["id","actor_type","action","target_type","target_id","created_at"])}
async function showSystem(){const d=await api("/system");$("devContent").innerHTML="<h2>Sistema</h2><pre>"+esc(JSON.stringify(d,null,2))+"</pre>"}
async function resetTest(){if(!confirm("RESETAR DADOS DE TESTE? Esta ação é destrutiva."))return;try{const d=await api("/test/reset",{method:"POST",body:JSON.stringify({confirm:"RESET_TEST_ENVIRONMENT"})});$("devContent").innerHTML="<h2>Teste resetado</h2><pre>"+esc(JSON.stringify(d,null,2))+"</pre>"}catch(e){alert(e.message)}}
function renderTable(title,rows,cols){$("devContent").innerHTML="<h2>"+title+"</h2>"+(rows.length?'<div style="overflow:auto"><table><thead><tr>'+cols.map(c=>"<th>"+c+"</th>").join("")+"</tr></thead><tbody>"+rows.map(r=>"<tr>"+cols.map(c=>"<td>"+esc(r[c])+"</td>").join("")+"</tr>").join("")+"</tbody></table></div>":"<p>Nenhum registro.</p>")}
function esc(v){return String(v??"").replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]))}
check();