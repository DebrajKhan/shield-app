// dpe-client.js — frontend <-> backend glue
(function(){
  // Use same origin for API by default, so it works locally and when deployed
  const API_BASE = (window.DPE_API_BASE || (window.location.origin + "/api"));
  const API_KEY = (window.DPE_API_KEY || "dev-key");

  function $(sel){ return document.querySelector(sel); }

  async function api(path, opts={}){
    const res = await fetch(`${API_BASE}${path}`, {
      ...opts,
      headers: {
        "Content-Type":"application/json",
        "x-api-key": API_KEY,
        ...(opts.headers||{})
      }
    });
    if(!res.ok){ throw new Error(`${path} failed: ` + await res.text()); }
    return res.json();
  }

  async function predict(payload){ return api("/predict",{method:"POST",body:JSON.stringify(payload)}); }
  async function alertSOS(data){ return api("/alert",{method:"POST",body:JSON.stringify(data||{})}); }

  // Hook Settings form
  const form = document.querySelector("form");
  if(form){
    form.addEventListener("submit", async (e)=>{
      e.preventDefault();
      const resting = parseInt($("#resting")?.value || "70", 10);
      const device = $("#device")?.value || "Unknown";
      const threshold = parseInt($("#threshold")?.value || "0", 10);

      const payload = {
        lat: 22.5726, lon: 88.3639, // Kolkata demo coords
        timestamp: new Date().toISOString(),
        heart_rate: resting + Math.max(25, threshold||0),
        resting_bpm: resting,
        motion: { shake: false, fall: false, speed_kmh: 5 },
        context: { lighting: "dark", crowd: "few" },
        user_text: "testing prediction from settings form",
        device
      };
      try{
        const res = await predict(payload);
        alert(`Risk: ${res.level.toUpperCase()} (${res.score})\nReasons: ${res.reasons.join(", ")}`);
      }catch(err){ alert("Prediction failed. Is the backend running?"); console.error(err); }
    });
  }

  // SOS button (pulsing primary)
  const sosBtn = document.querySelector(".btn.btn-primary.btn-pulse");
  if(sosBtn){
    sosBtn.addEventListener("click", async ()=>{
      try{
        const out = await alertSOS({ reason:"manual_sos", when:new Date().toISOString() });
        alert("SOS queued. Stay safe!\n" + JSON.stringify(out, null, 2));
      }catch(e){ alert("Could not send SOS."); console.error(e); }
    });
  }

  // Load Safe Zones into #map
  async function loadZones(){
    const mapDiv = $("#map"); if(!mapDiv) return;
    try{
      const { items } = await fetch(`${API_BASE.replace(/\/api$/,'')}/api/safe-zones?lat=22.5726&lon=88.3639&radius_km=5`).then(r=>r.json());
      if(window.L && typeof L.map==="function"){
        const map = L.map("map").setView([22.5726, 88.3639], 13);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
        items.forEach(z=> L.marker([z.lat, z.lon]).addTo(map).bindPopup(`<b>${z.title}</b><br>${(z.tags||[]).join(", ")}`));
      } else {
        mapDiv.innerHTML = "";
        items.forEach(z=>{
          const card = document.createElement("div");
          card.className = "safezone-card";
          card.style.cssText = "border:1px solid #2a2a2a;border-radius:12px;padding:12px;margin:8px 0;background:#111;";
          card.innerHTML = `<strong>${z.title}</strong><br><small>${(z.tags||[]).join(", ")}</small>${z.distance_km?`<br><small>${z.distance_km} km</small>`:""}`;
          mapDiv.appendChild(card);
        });
      }
    }catch(e){ console.warn("Safe zones failed", e); }
  }
  loadZones();

  // Chat -> risk
  const chatInput = $("#userInput");
  const sendBtn = $("#sendMessage");
  if(sendBtn && chatInput){
    sendBtn.addEventListener("click", async ()=>{
      const text = (chatInput.value||"").trim(); if(!text) return;
      try{
        const res = await predict({
          lat: 22.5726, lon: 88.3639,
          timestamp: new Date().toISOString(),
          heart_rate: 88, resting_bpm: 72,
          motion: { shake:false, fall:false, speed_kmh: 4 },
          context: { lighting:"dim", crowd:"few" },
          user_text: text, device: $("#device")?.value || "WebApp"
        });
        const msgList = $("#chatMessages");
        if(msgList){
          const capsule = document.createElement("div");
          capsule.className = "risk-capsule";
          capsule.style.cssText = "margin:8px 0;padding:8px;border-radius:8px;border:1px dashed #555;";
          capsule.textContent = `RISK: ${res.level.toUpperCase()} (${res.score}) → ${res.recommended_actions[0]}`;
          msgList.appendChild(capsule);
          msgList.scrollTop = msgList.scrollHeight;
        }
      }catch(e){ console.error(e); }
    });
  }

  // Expose for console debugging
  window.DPE = { predict, alertSOS };
})();