const API="https://barbearia-api-w37o.onrender.com/api";
let user=null,service=null,time="",rescheduleId=null;
const $=id=>document.getElementById(id);
const screens=[...document.querySelectorAll(".screen")];
function show(n){
  if(n!=="register"&&n!=="welcome"&&!user)n="register";
  screens.forEach(x=>x.classList.toggle("active",x.dataset.screen===n));
  if(n==="home")renderHome();
  if(n==="service")loadServices();
  if(n==="datetime")renderTimes();
  if(n==="confirm")renderSummary();
  if(n==="history")loadHistory();
  if(n==="profile")$("profileData").textContent=user?user.name+" · "+user.phone:"";
  location.hash=n;
}
async function api(path,opt={}){const r=await fetch(API+path,{credentials:"include",headers:{"Content-Type":"application/json"},...opt});const d=await r.json();if(!r.ok)throw new Error(d.error||"Erro");return d}
document.addEventListener("click",e=>{
  const g=e.target.closest("[data-go]"),n=e.target.closest("[data-next]");
  if(g){e.preventDefault();show(g.dataset.go)}
  if(n){if(n.dataset.next==="datetime"&&!service)return alert("Escolha um serviço.");if(n.dataset.next==="confirm"&&!time)return alert("Escolha um horário.");show(n.dataset.next)}
});
$("registerBtn").onclick=async()=>{
  const name=$("regName").value.trim(),phone=$("regPhone").value.trim();
  if(!name||!phone)return alert("Informe nome e telefone.");
  try{user=await api("/client/register",{method:"POST",body:JSON.stringify({name,phone})});localStorage.setItem("barbearia_cliente",JSON.stringify(user));show("home")}
  catch(e){alert(e.message)}
};
function renderHome(){ $("hello").textContent="Olá, "+user.name+"!"; $("phoneLabel").textContent=user.phone }
async function loadServices(){
  const box=$("serviceCards");box.innerHTML="";
  for(const s of await api("/services")){const l=document.createElement("label");l.className="service";l.innerHTML='<input type="radio" name="service" value="'+s.id+'"> '+s.name+' — €'+s.price+' · '+s.duration+' min';l.querySelector("input").onchange=()=>service=s;box.append(l)}
}
function renderTimes(){
  const box=$("times");box.replaceChildren();
  ["09:00","10:00","11:00","13:00","14:00","15:00","16:00","17:00","18:00"].forEach(t=>{const b=document.createElement("button");b.className="time"+(t===time?" selected":"");b.textContent=t;b.onclick=()=>{time=t;renderTimes()};box.append(b)})
}
function renderSummary(){ $("summary").textContent=(rescheduleId?"Reagendar: ":"Solicitação: ")+service.name+" · "+$("date").value+" · "+time }
$("confirmBtn").onclick=async()=>{
  try{
    if(rescheduleId){await api("/appointments/"+rescheduleId+"/cancel",{method:"POST"});rescheduleId=null}
    const a=await api("/appointments",{method:"POST",body:JSON.stringify({phone:user.phone,service_id:service.id,date:$("date").value,time})});
    $("successTitle").textContent="Solicitação enviada!";
    $("successSummary").textContent=service.name+" · "+a.date+" · "+a.time;
    $("successText").textContent="Status: PENDENTE. A barbearia ainda precisa confirmar a disponibilidade.";
    show("success");
  }catch(e){alert(e.message)}
};
async function loadHistory(){
  const box=$("list");box.innerHTML="";
  const rows=await api("/appointments?phone="+encodeURIComponent(user.phone));
  if(!rows.length){box.textContent="Nenhum agendamento.";return}
  rows.forEach(x=>{
    const d=document.createElement("div");d.className="appointment";
    d.innerHTML="<strong>"+x.service+"</strong><span>"+x.date+" · "+x.time+" · "+x.status.toUpperCase()+"</span>";
    if(["pending","confirmed"].includes(x.status)){const q=document.createElement("div");q.className="actions";const c=document.createElement("button");c.className="dark-btn";c.textContent="Cancelar";c.onclick=async()=>{await api("/appointments/"+x.id+"/cancel",{method:"POST"});loadHistory()};q.append(c);d.append(q)}
    box.append(d);
  })
}
$("date").value=new Date().toISOString().slice(0,10);$("date").min=$("date").value;
try{user=JSON.parse(localStorage.getItem("barbearia_cliente")||"null")}catch{}
show(user?"home":"welcome");
