(function () {
  const config = window.HOSPITAL_CHAT_CONFIG || { getHospitalIds: () => [] };
  let history = [];

  const btn = document.createElement("button");
  btn.id = "hc-widget-btn";
  btn.innerText = "Ask AI";
  document.body.appendChild(btn);

  const panel = document.createElement("div");
  panel.id = "hc-widget-panel";
  panel.innerHTML = `
    <div id="hc-widget-header">Ask about this hospital</div>
    <div id="hc-widget-messages"></div>
    <div id="hc-widget-input-row">
      <input id="hc-widget-input" type="text" placeholder="Ask a question..." />
      <button id="hc-widget-send">Send</button>
    </div>`;
  document.body.appendChild(panel);

  const messagesEl = panel.querySelector("#hc-widget-messages");
  const inputEl = panel.querySelector("#hc-widget-input");
  const sendBtn = panel.querySelector("#hc-widget-send");

  btn.addEventListener("click", () => panel.classList.toggle("open"));

  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = "hc-msg " + role;
    div.innerText = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function sendMessage() {
    const message = inputEl.value.trim();
    if (!message) return;
    const hospitalIds = config.getHospitalIds();
    if (!hospitalIds || hospitalIds.length === 0) {
      addMessage("model", "Please select a hospital first.");
      return;
    }

    addMessage("user", message);
    history.push({ role: "user", text: message });
    inputEl.value = "";
    sendBtn.disabled = true;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hospital_ids: hospitalIds, message, history })
      });
      const data = await res.json();
      if (data.error) {
        addMessage("model", data.error);
      } else {
        addMessage("model", data.reply);
        history.push({ role: "model", text: data.reply });
      }
    } catch (err) {
      addMessage("model", "Something went wrong. Please try again.");
    } finally {
      sendBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => { if (e.key === "Enter") sendMessage(); });
})();
