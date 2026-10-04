const API="https://barbearia-api-w37o.onrender.com/api";
const $=id=>document.getElementById(id);
async function api(path,opt={}){
  const r=await fetch(API+path,{...opt,credentials:"include",headers:{"Content-Type":"application/json",...(opt.headers||{})}});
  const d=await r.json();
  if(!r.ok)throw new Error(d.error||"Erro");
  return d;
}
$("ownerEnter").onclick=async()=>{
  const password=$("ownerPassword").value;
  if(!password)return $("ownerStatus").textContent="Informe a senha.";
  try{
    await api("/owner/login",{method:"POST",body:JSON.stringify({password})});
    $("ownerArea").hidden=false;
    $("ownerStatus").textContent="Área do proprietário ativa.";
    await render();
  }catch(e){$("ownerStatus").textContent=e.message;}
};
async function render(){
  const p=await api("/owner/appointments?status=pending");
  const c=await api("/owner/appointments?status=confirmed");
  const all=await api("/owner/appointments");
  const users=await api("/owner/clients");
  $("pending").innerHTML=p.length?p.map(x=>card(x,true)).join(""):"Nenhuma solicitação pendente.";
  $("confirmed").innerHTML=c.length?c.map(x=>card(x,false)).join(""):"Nenhum horário confirmado.";
  $("clients").innerHTML=users.length?users.map(x=>'<div class="appointment"><strong>'+x.name+'</strong><span>'+x.phone+' · '+x.appointments+' agendamento(s)</span></div>').join(""):"Nenhum cliente.";
  $("historyOwner").innerHTML=all.filter(x=>!["pending","confirmed"].includes(x.status)).map(x=>'<div class="appointment"><strong>'+x.client+' — '+x.service+'</strong><span>'+x.date+' · '+x.time+' · '+x.status.toUpperCase()+'</span></div>').join("")||"Sem histórico.";
}
function card(x,pending){
  let b='<div class="appointment"><strong>'+x.client+' — '+x.service+'</strong><span>'+x.date+' · '+x.time+' · '+x.phone+'</span>';
  if(pending)b+='<div class="actions"><button class="gold" onclick="confirmA('+x.id+')">CONFIRMAR</button><button class="dark-btn" onclick="rejectA('+x.id+')">RECUSAR</button></div>';
  return b+"</div>";
}
async function confirmA(id){try{await api("/owner/appointments/"+id+"/confirm",{method:"POST"});await render()}catch(e){alert(e.message)}}
async function rejectA(id){try{await api("/owner/appointments/"+id+"/reject",{method:"POST"});await render()}catch(e){alert(e.message)}}
