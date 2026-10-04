const KEY="barbearia_agendamentos";
const form=document.querySelector("#booking-form");
const status=document.querySelector("#booking-status");
const list=document.querySelector("#appointment-list");
function loadAppointments(){
  const a=JSON.parse(localStorage.getItem(KEY)||"[]");
  list.replaceChildren();
  if(!a.length){const p=document.createElement("p");p.textContent="Nenhum agendamento ainda.";list.appendChild(p);return;}
  a.forEach(function(x){
    const article=document.createElement("article");
    const strong=document.createElement("strong");
    strong.textContent=x.service||"Serviço";
    article.appendChild(strong);article.appendChild(document.createElement("br"));
    article.appendChild(document.createTextNode((x.date||"")+" às "+(x.time||"")));
    article.appendChild(document.createElement("br"));
    article.appendChild(document.createTextNode(x.client||""));
    list.appendChild(article);
  });
}
form?.addEventListener("submit",function(e){
  e.preventDefault();
  const d=new FormData(form);const item=Object.fromEntries(d.entries());
  const a=JSON.parse(localStorage.getItem(KEY)||"[]");
  if(a.some(function(x){return x.date===item.date&&x.time===item.time;})){status.textContent="Este horário já está ocupado. Escolha outro.";return;}
  a.push(item);localStorage.setItem(KEY,JSON.stringify(a));
  status.textContent="Agendamento confirmado para "+item.date+" às "+item.time+".";
  form.reset();loadAppointments();
});
loadAppointments();