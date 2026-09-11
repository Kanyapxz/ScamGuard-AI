// ── Splash Screen ────────────────────────────────
(function () {
  const splash = document.getElementById("splashScreen");
  if (!splash) return;

  const landingPage = document.getElementById("landingPage");
  if (landingPage) {
    landingPage.style.visibility = "hidden";
  }

  setTimeout(() => {
    splash.classList.add("splash-hiding");

    if (landingPage) {
      landingPage.style.visibility = "";
    }

    splash.addEventListener(
      "animationend",
      () => {
        splash.classList.add("splash-hidden");
      },
      { once: true }
    );
  }, 2700);
})();

// ── Page switching ──────────────────────────────
function openChat() {
  document.getElementById("landingPage").classList.add("hidden");
  document.getElementById("detectPage").classList.add("hidden");
  document.getElementById("knowledgePage").classList.add("hidden");
  document.getElementById("chatPage").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeChatBack() {
  document.getElementById("chatPage").classList.add("hidden");
  document.getElementById("landingPage").classList.remove("hidden");
  document.body.style.overflow = "";
}

function openDetectPage() {
  document.getElementById("chatPage").classList.add("hidden");
  document.getElementById("knowledgePage").classList.add("hidden");
  document.getElementById("detectPage").classList.remove("hidden");
  closeAllTopMenus();
  document.body.style.overflow = "hidden";
}

function openKnowledgePage() {
  document.getElementById("chatPage").classList.add("hidden");
  document.getElementById("detectPage").classList.add("hidden");
  document.getElementById("knowledgePage").classList.remove("hidden");
  closeAllTopMenus();
  document.body.style.overflow = "hidden";
}

function closeDetectToLanding() {
  document.getElementById("detectPage").classList.add("hidden");
  document.getElementById("chatPage").classList.add("hidden");
  document.getElementById("landingPage").classList.remove("hidden");
  closeAllTopMenus();
  document.body.style.overflow = "";
}

function closeKnowledgeToLanding() {
  document.getElementById("knowledgePage").classList.add("hidden");
  document.getElementById("chatPage").classList.add("hidden");
  document.getElementById("landingPage").classList.remove("hidden");
  closeAllTopMenus();
  document.body.style.overflow = "";
}

// ── Mode select page ───────────────────────────
const modeButtons = document.querySelectorAll(".mode-chip");
const modePanel = document.getElementById("modePanel");
const modeToggleBtn = document.getElementById("modeToggleBtn");
const currentModeLabel = document.getElementById("currentModeLabel");

modeToggleBtn?.addEventListener("click", () => {
  modePanel?.classList.toggle("expanded");
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    modeButtons.forEach((btn) => btn.classList.remove("active"));
    button.classList.add("active");

    const mode = button.dataset.mode;
    if (currentModeLabel) {
      currentModeLabel.textContent =
        mode === "knowledge" ? "กำลังเลือกโหมดคลังความรู้" : "กำลังเลือกโหมดตรวจสอบข้อความ";
    }

    if (mode === "knowledge") {
      openKnowledgePage();
    } else {
      openDetectPage();
    }
  });
});

// ── Top-right menu on sub pages ────────────────
const detectMenuBtn = document.getElementById("detectMenuBtn");
const detectDropdown = document.getElementById("detectDropdown");
const knowledgeMenuBtn = document.getElementById("knowledgeMenuBtn");
const knowledgeDropdown = document.getElementById("knowledgeDropdown");

function closeAllTopMenus() {
  detectDropdown?.classList.add("hidden");
  knowledgeDropdown?.classList.add("hidden");
}

function toggleMenu(menuEl, otherMenuEl) {
  if (!menuEl) return;
  otherMenuEl?.classList.add("hidden");
  menuEl.classList.toggle("hidden");
}

detectMenuBtn?.addEventListener("click", (e) => {
  e.stopPropagation();
  toggleMenu(detectDropdown, knowledgeDropdown);
});

knowledgeMenuBtn?.addEventListener("click", (e) => {
  e.stopPropagation();
  toggleMenu(knowledgeDropdown, detectDropdown);
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".topbar-menu-wrap")) {
    closeAllTopMenus();
  }
});

function switchFromDetectToDetect() {
  closeAllTopMenus();
}

function switchFromKnowledgeToKnowledge() {
  closeAllTopMenus();
}

function switchFromDetectToKnowledge() {
  document.getElementById("detectPage").classList.add("hidden");
  document.getElementById("knowledgePage").classList.remove("hidden");
  closeAllTopMenus();
}

function switchFromKnowledgeToDetect() {
  document.getElementById("knowledgePage").classList.add("hidden");
  document.getElementById("detectPage").classList.remove("hidden");
  closeAllTopMenus();
}

// ── Multi-session management ──────────────────
function generateSessionId() {
  return "sess_" + Math.random().toString(36).slice(2) + "_" + Date.now();
}

const detectSessions = {};
const knowledgeSessions = {};
let activeDetectId = null;
let activeKnowledgeId = null;
let detectSidebarOpen = window.innerWidth > 900;
let knowledgeSidebarOpen = window.innerWidth > 900;

function getStore(mode) {
  return mode === "detect" ? detectSessions : knowledgeSessions;
}

function getChatArea(mode) {
  return document.getElementById(mode === "detect" ? "detectChatArea" : "knowledgeChatArea");
}

function getSidebar(mode) {
  return document.getElementById(mode === "detect" ? "detectSidebar" : "knowledgeSidebar");
}

function getSidebarOverlay(mode) {
  return document.getElementById(mode === "detect" ? "detectSidebarOverlay" : "knowledgeSidebarOverlay");
}

function getSidebarList(mode) {
  return document.getElementById(mode === "detect" ? "detectChatList" : "knowledgeChatList");
}

function createSession(mode) {
  const id = generateSessionId();
  const store = getStore(mode);
  const num = Object.keys(store).length + 1;
  store[id] = { id, title: `การสนทนา ${num}`, htmlSnapshot: "" };
  return id;
}

function saveActiveSnapshot(mode) {
  const store = getStore(mode);
  const chatArea = getChatArea(mode);
  const activeId = mode === "detect" ? activeDetectId : activeKnowledgeId;
  if (activeId && store[activeId] && chatArea) {
    store[activeId].htmlSnapshot = chatArea.innerHTML;
  }
}

function activateSession(mode, id) {
  const store = getStore(mode);
  const chatArea = getChatArea(mode);
  if (!store[id] || !chatArea) return;

  saveActiveSnapshot(mode);

  if (mode === "detect") activeDetectId = id;
  else activeKnowledgeId = id;

  if (store[id].htmlSnapshot) {
    chatArea.innerHTML = store[id].htmlSnapshot;
    scrollToBottom(chatArea);
  } else {
    renderWelcome(mode, chatArea);
  }

  // Detect mode is one-shot: if this session already has an analysis result,
  // lock the composer; otherwise keep it open for a fresh check.
  if (mode === "detect") {
    const hasAnalysis = chatArea.querySelector(
      ".bot-card-enterprise:not(.bot-card-error):not(.bot-card-nextstep)"
    );
    if (hasAnalysis) lockDetectComposer();
    else unlockDetectComposer();
  }

  renderSidebarList(mode);
  closeSidebarOnMobile(mode);
}

function renderWelcome(mode, chatArea) {
  const botImg = `<img src="/static/i-want-a-owl-reaing-a-book-with-glases.png" width="20" height="20" style="object-fit:contain;border-radius:4px" alt="bot">`;

  if (mode === "detect") {
    chatArea.innerHTML = `
      <div class="message bot welcome-card">
        <div class="avatar-bot">${botImg}</div>
        <div class="bubble bubble-bot">
          <p>สวัสดีครับ ผม ScamGuard AI ยินดีช่วยเหลือครับ วางข้อความ ลิงก์ หรือ URL ที่ต้องการตรวจสอบได้เลยครับ</p>
        </div>
      </div>`;
    return;
  }

  chatArea.innerHTML = `
    <div class="message bot welcome-card welcome-card-hero">
      <div class="avatar-bot avatar-bot-hero">${botImg}</div>
      <div class="bubble bubble-bot bubble-bot-hero">
        <p>สวัสดีครับ ผม ScamGuard AI ยินดีช่วยเหลือครับ ถามเรื่องมิจฉาชีพ วิธีป้องกัน หรือแนวทางรับมือได้เลยครับ</p>
      </div>
    </div>
    <div class="quick-prompts quick-prompts-hero" id="knowledgeQuickPrompts">
      <div class="quick-prompts-list">
        <button class="quick-prompt-btn" data-prompt="Scammer คืออะไร">Scammer คืออะไร</button>
        <button class="quick-prompt-btn" data-prompt="วิธีรับมือกับ Scammer มีอะไรบ้าง">วิธีรับมือกับ Scammer มีอะไรบ้าง</button>
        <button class="quick-prompt-btn" data-prompt="วิธีสังเกตข้อความหลอกลวงมีอะไรบ้าง">วิธีสังเกตข้อความหลอกลวงมีอะไรบ้าง</button>
        <button class="quick-prompt-btn" data-prompt="ทำไมมิจฉาชีพชอบขอ OTP">ทำไมมิจฉาชีพชอบขอ OTP</button>
        <button class="quick-prompt-btn" data-prompt="ถ้าเผลอกดลิงก์ต้องทำยังไง">ถ้าเผลอกดลิงก์ต้องทำยังไง</button>
        <button class="quick-prompt-btn" data-prompt="คอลเซ็นเตอร์หลอกลวงมีลักษณะยังไง">คอลเซ็นเตอร์หลอกลวงมีลักษณะยังไง</button>
        <button class="quick-prompt-btn" data-prompt="ทำไมมิจฉาชีพชอบขอ OTP">ทำไมมิจฉาชีพชอบขอ OTP</button>
      </div>
    </div>`;
}

function renderSidebarList(mode) {
  const store = getStore(mode);
  const listEl = getSidebarList(mode);
  const activeId = mode === "detect" ? activeDetectId : activeKnowledgeId;
  if (!listEl) return;

  listEl.innerHTML = "";
  const ids = Object.keys(store).reverse();

  ids.forEach((id) => {
    const session = store[id];
    const div = document.createElement("div");
    div.className = "sg-chat-item" + (id === activeId ? " active" : "");
    div.dataset.sessionId = id;
    div.innerHTML = `
      <div class="sg-chat-item-icon">${mode === "detect" ? "🔍" : "💡"}</div>
      <div class="sg-chat-item-text">
        <div class="sg-chat-item-title">${escSidebar(session.title)}</div>
      </div>
      <div class="sg-chat-item-actions">
        <button class="sg-action-btn" title="เปลี่ยนชื่อ" onclick="startSidebarRename('${mode}','${id}',event)">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
        </button>
        <button class="sg-action-btn sg-delete-btn" title="ลบ" onclick="deleteSession('${mode}','${id}',event)">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
        </button>
      </div>
    `;

    div.addEventListener("click", (e) => {
      if (e.target.closest(".sg-chat-item-actions")) return;
      activateSession(mode, id);
    });

    listEl.appendChild(div);
  });
}

function escSidebar(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function startSidebarRename(mode, id, e) {
  e.stopPropagation();
  const store = getStore(mode);
  const listEl = getSidebarList(mode);
  const targetItem = listEl?.querySelector(`.sg-chat-item[data-session-id="${id}"] .sg-chat-item-title`);
  if (!targetItem || !store[id]) return;

  const oldValue = store[id].title;
  const input = document.createElement("input");
  input.className = "sg-rename-input";
  input.value = oldValue;
  targetItem.replaceWith(input);
  input.focus();
  input.select();

  const finish = () => {
    store[id].title = input.value.trim() || oldValue;
    renderSidebarList(mode);
  };

  input.addEventListener("blur", finish);
  input.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") input.blur();
    if (ev.key === "Escape") {
      input.value = oldValue;
      input.blur();
    }
    ev.stopPropagation();
  });
}

function deleteSession(mode, id, e) {
  e.stopPropagation();
  const store = getStore(mode);
  delete store[id];

  const remaining = Object.keys(store);
  if (!remaining.length) {
    if (mode === "detect") createDetectChat();
    else createKnowledgeChat();
    return;
  }

  if (mode === "detect") activeDetectId = null;
  else activeKnowledgeId = null;

  activateSession(mode, remaining[remaining.length - 1]);
}

function createDetectChat() {
  const id = createSession("detect");
  activateSession("detect", id);
}

function createKnowledgeChat() {
  const id = createSession("knowledge");
  activateSession("knowledge", id);
}

function toggleChatSidebar(mode) {
  const sidebar = getSidebar(mode);
  const overlay = getSidebarOverlay(mode);
  if (!sidebar || !overlay) return;

  const isOpen = mode === "detect" ? detectSidebarOpen : knowledgeSidebarOpen;
  const nextState = !isOpen;

  if (mode === "detect") detectSidebarOpen = nextState;
  else knowledgeSidebarOpen = nextState;

  sidebar.classList.toggle("sg-sidebar-collapsed", !nextState);

  if (window.innerWidth <= 900) {
    overlay.classList.toggle("show", nextState);
  } else {
    overlay.classList.remove("show");
  }
}

function closeSidebarOnMobile(mode) {
  if (window.innerWidth > 900) return;

  const sidebar = getSidebar(mode);
  const overlay = getSidebarOverlay(mode);
  if (!sidebar || !overlay) return;

  sidebar.classList.add("sg-sidebar-collapsed");
  overlay.classList.remove("show");

  if (mode === "detect") detectSidebarOpen = false;
  else knowledgeSidebarOpen = false;
}

function resetSidebarByViewport() {
  const desktop = window.innerWidth > 900;
  const sidebars = [
    { mode: "detect", el: getSidebar("detect") },
    { mode: "knowledge", el: getSidebar("knowledge") },
  ];

  sidebars.forEach(({ mode, el }) => {
    if (!el) return;
    if (desktop) {
      el.classList.remove("sg-sidebar-collapsed");
      if (mode === "detect") detectSidebarOpen = true;
      else knowledgeSidebarOpen = true;
    } else {
      el.classList.add("sg-sidebar-collapsed");
      if (mode === "detect") detectSidebarOpen = false;
      else knowledgeSidebarOpen = false;
    }
  });

  getSidebarOverlay("detect")?.classList.remove("show");
  getSidebarOverlay("knowledge")?.classList.remove("show");
}

function getDetectSessionId() {
  return activeDetectId || "anonymous";
}

function getKnowledgeSessionId() {
  return activeKnowledgeId || "anonymous";
}

(function initSessions() {
  createDetectChat();
  createKnowledgeChat();
  resetSidebarByViewport();
})();

window.addEventListener("resize", resetSidebarByViewport);

const botAvatarHTML = `
  <div class="avatar-bot">
    <img
      src="/static/i-want-a-owl-reaing-a-book-with-glases.png"
      width="20"
      height="20"
      style="object-fit:contain;border-radius:4px"
      alt="bot avatar"
    >
  </div>
`;

// ── Detect page DOM ────────────────────────────
const detectChatArea = document.getElementById("detectChatArea");
const detectMessageInput = document.getElementById("detectMessageInput");
const detectSendBtn = document.getElementById("detectSendBtn");
const detectLoading = document.getElementById("detectLoading");
const detectComposer = document.getElementById("detectComposer");
const detectResetBtn = document.getElementById("detectResetBtn");

// Image attach (OCR) refs
const detectAttachBtn = document.getElementById("detectAttachBtn");
const detectImageInput = document.getElementById("detectImageInput");
const detectImagePreview = document.getElementById("detectImagePreview");
const detectImagePreviewImg = document.getElementById("detectImagePreviewImg");
const detectImagePreviewName = document.getElementById("detectImagePreviewName");
const detectImagePreviewStatus = document.getElementById("detectImagePreviewStatus");
const detectImagePreviewRemove = document.getElementById("detectImagePreviewRemove");

// ── Knowledge page DOM ─────────────────────────
const knowledgeChatArea = document.getElementById("knowledgeChatArea");
const knowledgeMessageInput = document.getElementById("knowledgeMessageInput");
const knowledgeSendBtn = document.getElementById("knowledgeSendBtn");
const knowledgeLoading = document.getElementById("knowledgeLoading");

// ── Helpers ────────────────────────────────────
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function renderInlineMarkdown(text) {
  let html = esc(text);
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  return html;
}

function renderFormattedText(text) {
  const raw = String(text ?? "").replace(/\r\n/g, "\n").trim();
  if (!raw) return "-";

  const lines = raw.split("\n");
  let html = "";
  let inList = false;

  const closeListIfNeeded = () => {
    if (inList) {
      html += "</ol>";
      inList = false;
    }
  };

  for (const lineRaw of lines) {
    const line = lineRaw.trim();

    if (!line) {
      closeListIfNeeded();
      html += `<div class="bot-paragraph-space"></div>`;
      continue;
    }

    const numbered = line.match(/^(\d+)\.\s+(.*)$/);

    if (numbered) {
      if (!inList) {
        html += `<ol class="bot-number-list">`;
        inList = true;
      }
      html += `<li>${renderInlineMarkdown(numbered[2])}</li>`;
      continue;
    }

    closeListIfNeeded();
    html += `<p class="bot-paragraph">${renderInlineMarkdown(line)}</p>`;
  }

  closeListIfNeeded();
  return html;
}

function scrollToBottom(chatArea) {
  if (!chatArea) return;
  chatArea.scrollTop = chatArea.scrollHeight;
}

function addUserMessage(chatArea, text) {
  chatArea.insertAdjacentHTML(
    "beforeend",
    `
      <div class="message user">
        <div class="bubble-user">${esc(text)}</div>
        <div class="avatar-user">👤</div>
      </div>
    `
  );
  scrollToBottom(chatArea);
}

function listHTML(items = []) {
  if (!items || !items.length) return "";
  return `
    <ul class="detail-list">
      ${items.map((item) => `<li>${esc(item)}</li>`).join("")}
    </ul>
  `;
}

function chipListHTML(items = []) {
  if (!items || !items.length) return "";
  return items.map((item) => `<span class="signal-chip">${esc(item)}</span>`).join("");
}

function getPriorityBadge(priority) {
  if (priority === "critical") {
    return `<span class="badge badge-danger">เร่งด่วนมาก</span>`;
  }
  if (priority === "high") {
    return `<span class="badge badge-warn">เร่งด่วน</span>`;
  }
  return `<span class="badge badge-safe">แนะนำให้ทำต่อ</span>`;
}

function hideKnowledgeQuickPrompts() {
  const qp = document.getElementById("knowledgeQuickPrompts");
  if (qp) qp.style.display = "none";
}

function renameSessionFromFirstMessage(mode, message) {
  const store = getStore(mode);
  const sid = mode === "detect" ? getDetectSessionId() : getKnowledgeSessionId();
  if (store[sid] && store[sid].title.startsWith("การสนทนา")) {
    store[sid].title = message.slice(0, 32) + (message.length > 32 ? "…" : "");
    renderSidebarList(mode);
  }
}

// ── Bot renderers ──────────────────────────────
function addBotDetect(chatArea, data) {
  const badgeClass =
    data.final_color === "SUSPICIOUS"
      ? "badge-danger"
      : data.final_color === "REVIEW"
        ? "badge-warn"
        : "badge-safe";

  const summaryText = renderFormattedText(data.reply || data.summary || data.warning || "-");

  const indicatorsBlock =
    data.indicators?.length
      ? `
          <div class="enterprise-section">
            <div class="enterprise-section-head">
              <div class="enterprise-section-title">สัญญาณที่พบ</div>
              <div class="enterprise-section-sub">จุดที่ระบบตรวจพบจากข้อความนี้</div>
            </div>
            <div class="signal-chip-wrap">
              ${chipListHTML(data.indicators)}
            </div>
          </div>
        `
      : "";

  const reasonsBlock =
    data.reasons?.length
      ? `
          <div class="enterprise-section">
            <div class="enterprise-section-head">
              <div class="enterprise-section-title">เหตุผลในการประเมิน</div>
              <div class="enterprise-section-sub">สรุปจากกฎและโครงสร้างข้อความที่พบ</div>
            </div>
            ${listHTML(data.reasons)}
          </div>
        `
      : "";

  const adviceBlock =
    data.advice?.length
      ? `
          <div class="enterprise-section">
            <div class="enterprise-section-head">
              <div class="enterprise-section-title">คำแนะนำที่ควรทำ</div>
              <div class="enterprise-section-sub">แนวทางที่แนะนำให้ทำต่อทันที</div>
            </div>
            ${listHTML(data.advice)}
          </div>
        `
      : "";

  const nextStepBlock =
    data.show_next_step_actions &&
    Array.isArray(data.next_step_situations) &&
    data.next_step_situations.length
      ? `
          <div class="enterprise-section enterprise-section-soft">
            <div class="enterprise-section-head">
              <div class="enterprise-section-title">สถานการณ์ของคุณตอนนี้</div>
              <div class="enterprise-section-sub">เลือกสิ่งที่เกิดขึ้นจริงเพื่อรับคำแนะนำต่อทันที</div>
            </div>
            <div class="next-step-actions next-step-actions-enterprise">
              ${data.next_step_situations
                .map(
                  (item) => `
                    <button
                      class="next-step-btn-enterprise"
                      onclick="requestNextStep('${String(item.key).replace(/'/g, "\\'")}')"
                    >
                      <span class="next-step-btn-label">${esc(item.label)}</span>
                      <span class="next-step-btn-arrow">↗</span>
                    </button>
                  `
                )
                .join("")}
            </div>
          </div>
        `
      : "";

  chatArea.insertAdjacentHTML(
    "beforeend",
    `
      <div class="message bot">
        ${botAvatarHTML}
        <div class="bot-card bot-card-enterprise">
          <div class="enterprise-top">
            <div class="enterprise-top-left">
              <div class="enterprise-status-row">
                <span class="enterprise-status-icon">🛡️</span>
                <span class="badge ${badgeClass}">${esc(data.final_label || "ผลการตรวจสอบ")}</span>
              </div>
              <div class="enterprise-summary-title">ผลการวิเคราะห์ข้อความ</div>
              <div class="enterprise-summary-text">${summaryText}</div>
            </div>
          </div>

          ${indicatorsBlock}
          ${reasonsBlock}
          ${adviceBlock}
          ${nextStepBlock}
        </div>
      </div>
    `
  );

  scrollToBottom(chatArea);
}

function addBotKnowledge(chatArea, data) {
  chatArea.insertAdjacentHTML(
    "beforeend",
    `
      <div class="message bot">
        ${botAvatarHTML}
        <div class="bot-card">
          <div class="bot-card-body formatted-bot-text">${renderFormattedText(data.answer || "-")}</div>
        </div>
      </div>
    `
  );
  scrollToBottom(chatArea);
}

function addBotNextStep(chatArea, data) {
  const section = (title, items) =>
    !items?.length
      ? ""
      : `
          <div class="enterprise-section">
            <div class="enterprise-section-head">
              <div class="enterprise-section-title">${esc(title)}</div>
            </div>
            ${listHTML(items)}
          </div>
        `;

  chatArea.insertAdjacentHTML(
    "beforeend",
    `
      <div class="message bot">
        ${botAvatarHTML}
        <div class="bot-card bot-card-enterprise bot-card-nextstep">
          <div class="enterprise-top">
            <div class="enterprise-top-left">
              <div class="enterprise-status-row">
                <span class="enterprise-status-icon">📌</span>
                ${getPriorityBadge(data.priority)}
              </div>
              <div class="enterprise-summary-title">${esc(data.title || "คำแนะนำเพิ่มเติม")}</div>
              <div class="enterprise-summary-text">${renderFormattedText(data.warning || "-")}</div>
            </div>
          </div>

          ${section("สิ่งที่ควรทำทันที", data.steps)}
          ${section("หมายเหตุเพิ่มเติม", data.notes)}
        </div>
      </div>
    `
  );

  scrollToBottom(chatArea);
}

function addBotError(chatArea, message) {
  chatArea.insertAdjacentHTML(
    "beforeend",
    `
      <div class="message bot">
        ${botAvatarHTML}
        <div class="bot-card bot-card-enterprise bot-card-error">
          <div class="enterprise-top">
            <div class="enterprise-top-left">
              <div class="enterprise-status-row">
                <span class="enterprise-status-icon">⚠️</span>
                <span class="badge badge-danger">เกิดข้อผิดพลาด</span>
              </div>
              <div class="enterprise-summary-title">ไม่สามารถประมวลผลได้</div>
              <div class="enterprise-summary-text text-error">${renderFormattedText(message || "ไม่สามารถเชื่อมต่อได้")}</div>
            </div>
          </div>
        </div>
      </div>
    `
  );
  scrollToBottom(chatArea);
}

// ── Detect mode: lock/unlock input after analysis ──
// Note: query DOM directly so these work even when called during initSessions(),
// which runs before the top-level `const detectComposer` etc. are assigned.
function lockDetectComposer() {
  const wrap = document.querySelector("#detectPage .composer-wrap");
  const composer = document.getElementById("detectComposer");
  const input = document.getElementById("detectMessageInput");
  const sendBtn = document.getElementById("detectSendBtn");
  const resetBtn = document.getElementById("detectResetBtn");
  const strip = document.getElementById("detectStatusStrip");

  if (wrap) wrap.classList.add("is-complete");
  if (composer) composer.classList.add("is-locked");
  if (input) {
    input.disabled = true;
    input.placeholder = "รอบนี้ตรวจเสร็จแล้ว — กดปุ่มด้านล่างเพื่อตรวจข้อความใหม่";
  }
  if (sendBtn) {
    sendBtn.disabled = true;
    sendBtn.setAttribute("title", "วิเคราะห์เสร็จสิ้น");
  }
  if (strip) strip.classList.remove("hidden");
  if (resetBtn) resetBtn.classList.remove("hidden");
}

function unlockDetectComposer() {
  const wrap = document.querySelector("#detectPage .composer-wrap");
  const composer = document.getElementById("detectComposer");
  const input = document.getElementById("detectMessageInput");
  const sendBtn = document.getElementById("detectSendBtn");
  const resetBtn = document.getElementById("detectResetBtn");
  const strip = document.getElementById("detectStatusStrip");

  if (wrap) wrap.classList.remove("is-complete");
  if (composer) composer.classList.remove("is-locked");
  if (input) {
    input.disabled = false;
    input.placeholder = "วางข้อความหรือลิงก์ที่ต้องการตรวจสอบ...";
    input.value = "";
    input.style.height = "auto";
  }
  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.setAttribute("title", "ส่งข้อความ");
  }
  if (strip) strip.classList.add("hidden");
  if (resetBtn) resetBtn.classList.add("hidden");

  // ล้าง image preview ตอนเริ่มตรวจใหม่
  clearDetectImagePreview();
}

// ── Detect mode: image attach + OCR ────────────────
// Allowed types are also enforced server-side via ocr_service.py
const OCR_ALLOWED_TYPES = new Set([
  "image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp",
]);
const OCR_MAX_BYTES = 5 * 1024 * 1024; // 5 MB — ต้องตรงกับ backend

function setDetectImagePreviewStatus(state, message) {
  // state: "loading" | "success" | "error"
  const statusEl = document.getElementById("detectImagePreviewStatus");
  if (!statusEl) return;
  statusEl.classList.remove("is-success", "is-error");
  if (state === "success") statusEl.classList.add("is-success");
  if (state === "error") statusEl.classList.add("is-error");
  statusEl.innerHTML = `
    <span class="detect-ocr-spinner"></span>
    <span>${escapeText(message)}</span>
  `;
}

function escapeText(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function showDetectImagePreview(file) {
  const previewEl = document.getElementById("detectImagePreview");
  const imgEl = document.getElementById("detectImagePreviewImg");
  const nameEl = document.getElementById("detectImagePreviewName");
  if (!previewEl || !imgEl || !nameEl) return;

  // Preview thumbnail from local file (ไม่ต้องอัปโหลด)
  const reader = new FileReader();
  reader.onload = (e) => { imgEl.src = e.target.result; };
  reader.readAsDataURL(file);

  nameEl.textContent = file.name;
  previewEl.classList.remove("hidden");
  setDetectImagePreviewStatus("loading", "กำลังอ่านข้อความจากรูป...");
}

function clearDetectImagePreview() {
  const previewEl = document.getElementById("detectImagePreview");
  const imgEl = document.getElementById("detectImagePreviewImg");
  const inputEl = document.getElementById("detectImageInput");
  if (previewEl) previewEl.classList.add("hidden");
  if (imgEl) imgEl.src = "";
  if (inputEl) inputEl.value = "";
}

async function handleDetectImageAttach(file) {
  if (!file) return;

  // Client-side validation — mirror ของ backend
  if (!OCR_ALLOWED_TYPES.has(file.type)) {
    alert("รูปแบบไฟล์ไม่รองรับ — ต้องเป็น PNG, JPG, WEBP หรือ BMP");
    return;
  }
  if (file.size > OCR_MAX_BYTES) {
    alert("ไฟล์ใหญ่เกินไป (จำกัด 5 MB)");
    return;
  }
  if (file.size === 0) {
    alert("ไฟล์ว่างเปล่า กรุณาลองใหม่");
    return;
  }

  // Block ถ้าอยู่ในสถานะ locked (ตรวจเสร็จแล้ว)
  if (document.getElementById("detectComposer")?.classList.contains("is-locked")) return;

  showDetectImagePreview(file);

  const formData = new FormData();
  formData.append("image", file);

  try {
    const response = await fetch("/api/ocr", {
      method: "POST",
      body: formData,
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok || !data.ok) {
      setDetectImagePreviewStatus("error", data.message || "ไม่สามารถอ่านข้อความได้");
      return;
    }

    // เติม text ที่อ่านได้ใน textarea — ให้ผู้ใช้แก้ก่อนส่ง (Option B)
    const inputEl = document.getElementById("detectMessageInput");
    if (inputEl) {
      const existing = inputEl.value.trim();
      inputEl.value = existing
        ? existing + "\n" + data.text
        : data.text;
      // trigger auto-resize
      inputEl.style.height = "auto";
      inputEl.style.height = Math.min(inputEl.scrollHeight, 148) + "px";
      inputEl.focus();
    }

    const count = data.char_count || (data.text ? data.text.length : 0);
    setDetectImagePreviewStatus(
      "success",
      `อ่านได้ ${count} ตัวอักษร · แก้ไขและกดส่งเพื่อตรวจสอบ`
    );
  } catch (err) {
    setDetectImagePreviewStatus("error", "เชื่อมต่อไม่ได้ กรุณาลองใหม่");
  }
}

// ── API calls ───────────────────────────────────
async function sendDetectMessage(prefilledMessage = null) {
  // Block sending while composer is locked (user must click "ตรวจข้อความใหม่")
  if (document.getElementById("detectComposer")?.classList.contains("is-locked")) return;

  const message = (prefilledMessage ?? detectMessageInput?.value ?? "").trim();
  if (!message || !detectChatArea || !detectLoading) return;

  renameSessionFromFirstMessage("detect", message);

  addUserMessage(detectChatArea, message);
  if (detectMessageInput) {
    detectMessageInput.value = "";
    detectMessageInput.style.height = "auto";
  }
  detectLoading.classList.remove("hidden");
  scrollToBottom(detectChatArea);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        mode: "detect",
        session_id: getDetectSessionId(),
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      addBotError(detectChatArea, data.message || "เกิดข้อผิดพลาด");
      // On error, keep composer usable so user can retry
      return;
    }

    addBotDetect(detectChatArea, data);
    // Lock composer after a successful analysis — detect mode is one-shot
    lockDetectComposer();
    // ซ่อน image preview หลังส่งสำเร็จ เพื่อไม่ให้รูปค้างใน locked state
    clearDetectImagePreview();
  } catch (error) {
    addBotError(detectChatArea, "เชื่อมต่อล้มเหลว ตรวจสอบอินเทอร์เน็ต");
  } finally {
    detectLoading.classList.add("hidden");
    saveActiveSnapshot("detect");
  }
}

async function sendKnowledgeMessage(prefilledMessage = null) {
  const message = (prefilledMessage ?? knowledgeMessageInput?.value ?? "").trim();
  if (!message || !knowledgeChatArea || !knowledgeLoading) return;

  renameSessionFromFirstMessage("knowledge", message);
  hideKnowledgeQuickPrompts();

  addUserMessage(knowledgeChatArea, message);
  if (knowledgeMessageInput) {
    knowledgeMessageInput.value = "";
    knowledgeMessageInput.style.height = "auto";
  }
  knowledgeLoading.classList.remove("hidden");
  scrollToBottom(knowledgeChatArea);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        mode: "knowledge",
        session_id: getKnowledgeSessionId(),
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      addBotError(knowledgeChatArea, data.message || "เกิดข้อผิดพลาด");
      return;
    }

    addBotKnowledge(knowledgeChatArea, data);
  } catch (error) {
    addBotError(knowledgeChatArea, "เชื่อมต่อล้มเหลว ตรวจสอบอินเทอร์เน็ต");
  } finally {
    knowledgeLoading.classList.add("hidden");
    saveActiveSnapshot("knowledge");
  }
}

async function requestNextStep(situationKey) {
  if (!detectLoading || !detectChatArea) return;

  detectLoading.classList.remove("hidden");
  scrollToBottom(detectChatArea);

  try {
    const response = await fetch("/api/next-step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: getDetectSessionId(),
        situation: situationKey,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.ok) {
      addBotError(detectChatArea, data.message || "ไม่สามารถสร้างคำแนะนำถัดไปได้");
      return;
    }

    addBotNextStep(detectChatArea, data);
  } catch (error) {
    addBotError(detectChatArea, "เชื่อมต่อล้มเหลวระหว่างขอคำแนะนำเพิ่มเติม");
  } finally {
    detectLoading.classList.add("hidden");
    saveActiveSnapshot("detect");
  }
}

// ── Input resize ────────────────────────────────
function bindAutoResize(textarea) {
  if (!textarea) return;
  textarea.addEventListener("input", () => {
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 148) + "px";
  });
}

bindAutoResize(detectMessageInput);
bindAutoResize(knowledgeMessageInput);

// ── Events ─────────────────────────────────────
detectSendBtn?.addEventListener("click", () => sendDetectMessage());
knowledgeSendBtn?.addEventListener("click", () => sendKnowledgeMessage());

detectResetBtn?.addEventListener("click", () => {
  unlockDetectComposer();
  saveActiveSnapshot("detect");
  detectMessageInput?.focus();
});

// Image attach (OCR) events
detectAttachBtn?.addEventListener("click", () => {
  if (detectComposer?.classList.contains("is-locked")) return;
  detectImageInput?.click();
});

detectImageInput?.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) handleDetectImageAttach(file);
});

detectImagePreviewRemove?.addEventListener("click", () => {
  clearDetectImagePreview();
  detectMessageInput?.focus();
});

detectMessageInput?.addEventListener("keydown", (event) => {
  // Respect locked state — don't send on Enter while locked
  if (document.getElementById("detectComposer")?.classList.contains("is-locked")) {
    event.preventDefault();
    return;
  }
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendDetectMessage();
  }
});

knowledgeMessageInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendKnowledgeMessage();
  }
});

knowledgeChatArea?.addEventListener("click", (e) => {
  const btn = e.target.closest(".quick-prompt-btn");
  if (!btn) return;
  const prompt = btn.dataset.prompt || "";
  if (!prompt) return;

  if (knowledgeMessageInput) {
    knowledgeMessageInput.value = prompt;
    knowledgeMessageInput.style.height = "auto";
    knowledgeMessageInput.style.height = Math.min(knowledgeMessageInput.scrollHeight, 148) + "px";
  }

  sendKnowledgeMessage(prompt);
});