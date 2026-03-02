(function () {
  if (window.__FAQ_CHATBOT_LOADED__) return;
  window.__FAQ_CHATBOT_LOADED__ = true;

  const currentScript =
    document.currentScript ||
    document.querySelector('script[src*="widget.js"]');

  const API_URL =
    (currentScript && currentScript.getAttribute("data-api")) ||
    "http://localhost:8000";

  const USER_ID =
    (currentScript && currentScript.getAttribute("data-user-id")) || null;

  function init() {
    // ---------------------------------------------------------------------
    // Host Container
    // ---------------------------------------------------------------------
    const host = document.createElement("div");
    host.id = "faq-chatbot-host";
    host.style.cssText =
      "position:fixed;bottom:24px;right:24px;z-index:2147483647;font-family:Arial,sans-serif;";
    document.body.appendChild(host);

    const shadow = host.attachShadow({ mode: 'open' });

    // -------------------------------------------------------------------------
    // Template
    // -------------------------------------------------------------------------
    shadow.innerHTML = `
      <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        #bubble {
          width: 56px; height: 56px;
          background: #4f46e5;
          border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer;
          box-shadow: 0 4px 16px rgba(79,70,229,0.4);
          transition: transform 0.2s, box-shadow 0.2s;
          user-select: none;
        }
        #bubble:hover {
          transform: scale(1.08);
          box-shadow: 0 6px 20px rgba(79,70,229,0.5);
        }
        #bubble svg { width: 26px; height: 26px; fill: white; }

        #panel {
          display: none;
          flex-direction: column;
          width: 340px;
          height: 480px;
          background: #fff;
          border-radius: 16px;
          box-shadow: 0 12px 40px rgba(0,0,0,0.18);
          overflow: hidden;
          margin-bottom: 12px;
          animation: slideUp 0.25s ease;
        }
        #panel.open { display: flex; }

        @keyframes slideUp {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        #header {
          background: #4f46e5;
          color: #fff;
          padding: 14px 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-shrink: 0;
        }

        #header-title {
          font-weight: 700;
          font-size: 15px;
        }

        #close-btn {
          background: none;
          border: none;
          color: rgba(255,255,255,0.8);
          font-size: 20px;
          cursor: pointer;
          line-height: 1;
          padding: 2px 4px;
          border-radius: 4px;
        }
        #close-btn:hover {
          background: rgba(255,255,255,0.15);
          color: #fff;
        }

        #messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 10px;
          background: #f8f8fb;
        }

        .msg {
          display: flex;
          flex-direction: column;
          max-width: 82%;
          gap: 3px;
        }

        .msg.user {
          align-self: flex-end;
          align-items: flex-end;
        }

        .msg.bot {
          align-self: flex-start;
          align-items: flex-start;
        }

        .bubble-text {
          padding: 10px 14px;
          border-radius: 18px;
          font-size: 13.5px;
          line-height: 1.5;
          word-break: break-word;
        }

        .msg.user .bubble-text {
          background: #4f46e5;
          color: #fff;
          border-bottom-right-radius: 4px;
        }

        .msg.bot .bubble-text {
          background: #fff;
          color: #1f2937;
          border-bottom-left-radius: 4px;
          box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }

        .msg-label {
          font-size: 10.5px;
          color: #9ca3af;
          padding: 0 4px;
        }

        .typing .bubble-text {
          color: #9ca3af;
          font-style: italic;
        }

        #input-row {
          display: flex;
          border-top: 1px solid #e5e7eb;
          background: #fff;
        }

        #chat-input {
          flex: 1;
          border: none;
          outline: none;
          padding: 12px 14px;
          font-size: 13.5px;
        }

        #send-btn {
          background: #4f46e5;
          border: none;
          color: #fff;
          padding: 0 16px;
          cursor: pointer;
          font-size: 18px;
        }

        #send-btn:disabled {
          background: #a5b4fc;
          cursor: not-allowed;
        }
      </style>

      <div id="panel">
        <div id="header">
          <div id="header-title">FAQ Assistant</div>
          <button id="close-btn" title="Close">&#x2715;</button>
        </div>

        <div id="messages"></div>

        <div id="input-row">
          <input id="chat-input" placeholder="Ask a question..." autocomplete="off" />
          <button id="send-btn">&#9658;</button>
        </div>
      </div>

      <div id="bubble">
        <svg viewBox="0 0 24 24">
          <path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2z"/>
        </svg>
      </div>
    `;

    const panel = shadow.getElementById("panel");
    const bubble = shadow.getElementById("bubble");
    const closeBtn = shadow.getElementById("close-btn");
    const input = shadow.getElementById("chat-input");
    const sendBtn = shadow.getElementById("send-btn");
    const messages = shadow.getElementById("messages");

    let isWaiting = false;

    function openPanel() {
      panel.classList.add("open");
      bubble.style.display = "none";
      if (!messages.children.length) {
        appendBot("Hi there! How can I help you today?");
      }
      setTimeout(() => input.focus(), 100);
    }

    function closePanel() {
      panel.classList.remove("open");
      bubble.style.display = "flex";
    }

    bubble.addEventListener("click", openPanel);
    closeBtn.addEventListener("click", closePanel);

    function appendUser(text) {
      const el = document.createElement("div");
      el.className = "msg user";
      el.innerHTML = `
        <div class="bubble-text">${escapeHTML(text)}</div>
        <span class="msg-label">You</span>
      `;
      messages.appendChild(el);
      scrollBottom();
    }

    function appendBot(text) {
      const el = document.createElement("div");
      el.className = "msg bot";
      el.innerHTML = `
        <span class="msg-label">Assistant</span>
        <div class="bubble-text">${escapeHTML(text)}</div>
      `;
      messages.appendChild(el);
      scrollBottom();
    }

    function showTyping() {
      const el = document.createElement("div");
      el.className = "msg bot typing";
      el.id = "typing-indicator";
      el.innerHTML = `
        <span class="msg-label">Assistant</span>
        <div class="bubble-text">Thinking...</div>
      `;
      messages.appendChild(el);
      scrollBottom();
    }

    function removeTyping() {
      const el = shadow.getElementById("typing-indicator");
      if (el) el.remove();
    }

    function scrollBottom() {
      messages.scrollTop = messages.scrollHeight;
    }

    function escapeHTML(str) {
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/\n/g, "<br>");
    }

    async function sendMessage() {
      const text = input.value.trim();
      if (!text || isWaiting) return;

      input.value = "";
      isWaiting = true;
      sendBtn.disabled = true;

      appendUser(text);
      showTyping();

      try {
        const res = await fetch(`${API_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, user_id: USER_ID }),
        });

        if (!res.ok) throw new Error(`Server error: ${res.status}`);

        const data = await res.json();
        removeTyping();
        appendBot(data.reply || "No response received.");
      } catch (err) {
        removeTyping();
        appendBot("Sorry, something went wrong. Please try again.");
        console.error("[FAQ Widget Error]", err);
      } finally {
        isWaiting = false;
        sendBtn.disabled = false;
        input.focus();
      }
    }

    sendBtn.addEventListener("click", sendMessage);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  if (document.body) {
    init();
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }

})();
