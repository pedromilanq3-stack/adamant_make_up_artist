// ==UserScript==
// @name         Tinder Web - Assistente de decisões
// @namespace    local.tinder.assistant
// @version      1.0.0
// @description  Automatiza decisões no Tinder Web sem analisar imagens.
// @match        https://tinder.com/*
// @match        https://www.tinder.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(() => {
  "use strict";

  if (window.__TINDER_DECISION_ASSISTANT__) return;
  window.__TINDER_DECISION_ASSISTANT__ = true;

  /** Todos os seletores e termos dependentes da interface ficam neste objeto. */
  const CONFIG = Object.freeze({
    selectors: {
      profileCards: [
        'main [data-testid="profile-card"]',
        'main [data-testid*="card"]',
        'main [role="group"]',
        'main article'
      ],
      profileName: [
        '[data-testid="profile-name"]',
        'h1',
        'h2'
      ],
      likeButtons: [
        'button[data-testid="gamepadLike"]',
        '[role="button"][data-testid="gamepadLike"]',
        'button[aria-label="Like"]',
        'button[aria-label="Curtir"]',
        'button[title="Like"]',
        'button[title="Curtir"]'
      ],
      rejectButtons: [
        'button[data-testid="gamepadDislike"]',
        '[role="button"][data-testid="gamepadDislike"]',
        'button[aria-label="Nope"]',
        'button[aria-label="Não"]',
        'button[title="Nope"]',
        'button[title="Não"]'
      ],
      safetySignals: [
        '[data-testid*="captcha" i]',
        'iframe[src*="captcha" i]',
        'iframe[title*="captcha" i]',
        '[aria-label*="verificação" i]',
        '[aria-label*="verification" i]'
      ]
    },
    semanticLabels: {
      like: ["like", "curtir"],
      reject: ["nope", "dislike", "não", "rejeitar"]
    },
    safetyText: [
      /captcha/i,
      /atividade suspeita/i,
      /suspicious activity/i,
      /verifique que (?:você|voce) (?:é|e) humano/i,
      /verify (?:that )?you(?:'re| are) human/i,
      /conta (?:foi )?bloqueada/i,
      /account (?:has been )?blocked/i
    ],
    explicitGender: {
      woman: [
        /(?:^|[\n|•])\s*g[êe]nero\s*:\s*(?:mulher|feminino)\b/i,
        /(?:^|[\n|•])\s*gender\s*:\s*(?:woman|female)\b/i,
        /\b(?:eu sou|sou uma)\s+(?:mulher|mulher trans)\b/i,
        /\bi(?:'m| am)\s+(?:a\s+)?(?:woman|trans woman)\b/i
      ],
      man: [
        /(?:^|[\n|•])\s*g[êe]nero\s*:\s*(?:homem|masculino)\b/i,
        /(?:^|[\n|•])\s*gender\s*:\s*(?:man|male)\b/i,
        /\b(?:eu sou|sou um)\s+(?:homem|homem trans)\b/i,
        /\bi(?:'m| am)\s+(?:a\s+)?(?:man|trans man)\b/i
      ]
    },
    defaults: { limit: 50, minDelay: 1800, maxDelay: 3500 },
    nextProfileTimeout: 20000,
    debounceMs: 350,
    maxLogEntries: 5000
  });

  const state = {
    running: false,
    processing: false,
    stopRequested: false,
    observer: null,
    routeTimer: null,
    wakeTimer: null,
    currentFingerprint: null,
    lastHandledFingerprint: null,
    likes: 0,
    rejects: 0,
    indeterminate: 0,
    total: 0,
    logs: []
  };

  const ui = {};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();
  const debug = (...args) => ui.debug?.checked && console.debug("[TinderBot]", ...args);
  const queryFirst = (selectors, root = document) => {
    for (const selector of selectors) {
      try {
        const found = root.querySelector(selector);
        if (found) return found;
      } catch (error) {
        debug("Seletor inválido ignorado:", selector, error);
      }
    }
    return null;
  };

  function visible(element) {
    if (!(element instanceof Element)) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" &&
      Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
  }

  function enabled(element) {
    return !element.matches(':disabled, [disabled], [aria-disabled="true"]');
  }

  function hash(text) {
    let value = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      value ^= text.charCodeAt(index);
      value = Math.imul(value, 16777619);
    }
    return (value >>> 0).toString(36);
  }

  function getCurrentProfile() {
    const candidates = CONFIG.selectors.profileCards
      .flatMap((selector) => {
        try { return [...document.querySelectorAll(selector)]; } catch { return []; }
      })
      .filter(visible);
    const card = candidates.find((candidate) =>
      findLikeButton(candidate) || findRejectButton(candidate)
    ) || candidates[0];
    if (!card) return null;

    const text = normalize(card.innerText);
    const name = normalize(queryFirst(CONFIG.selectors.profileName, card)?.textContent);
    const semanticId = card.getAttribute("data-testid") || card.getAttribute("aria-label") || "card";
    // Nunca inclui src de imagem: a impressão usa somente texto/atributos do contêiner.
    const fingerprint = hash(`${semanticId}|${name}|${text.slice(0, 1200)}`);
    return { element: card, name: name || null, text, fingerprint };
  }

  function getExplicitGender(profile) {
    if (!profile?.text) return { gender: "unknown", evidence: null };
    for (const [gender, patterns] of Object.entries(CONFIG.explicitGender)) {
      const match = patterns.map((pattern) => profile.text.match(pattern)).find(Boolean);
      if (match) return { gender, evidence: normalize(match[0]) };
    }
    return { gender: "unknown", evidence: null };
  }

  function semanticButtonFallback(kind, root = document) {
    const labels = CONFIG.semanticLabels[kind];
    return [...root.querySelectorAll('button, [role="button"]')].find((element) => {
      const value = normalize([
        element.getAttribute("aria-label"), element.getAttribute("title"),
        element.getAttribute("data-testid")
      ].filter(Boolean).join(" ")).toLocaleLowerCase("pt-BR");
      return labels.some((label) => value === label || value.includes(label));
    }) || null;
  }

  function findActionButton(kind, profileRoot) {
    const selectors = kind === "like" ? CONFIG.selectors.likeButtons : CONFIG.selectors.rejectButtons;
    return queryFirst(selectors, profileRoot || document) || queryFirst(selectors) ||
      semanticButtonFallback(kind, profileRoot || document) || semanticButtonFallback(kind);
  }

  function findLikeButton(profileRoot) { return findActionButton("like", profileRoot); }
  function findRejectButton(profileRoot) { return findActionButton("reject", profileRoot); }

  function decideAction(profile) {
    if (ui.mode.value === "filter") {
      return { action: "LIKE", confidence: "filter-mode", reason: "Perfil aceito pelos filtros configurados pelo usuário no Tinder." };
    }
    const explicit = getExplicitGender(profile);
    if (explicit.gender === "woman") {
      return { action: "LIKE", confidence: "explicit", reason: `Texto explícito indica mulher: “${explicit.evidence}”.` };
    }
    if (explicit.gender === "man") {
      return { action: "REJECT", confidence: "explicit", reason: `Texto explícito indica homem: “${explicit.evidence}”.` };
    }
    return { action: "SKIP", confidence: "explicit", reason: "Nenhuma informação textual explícita e confiável de gênero foi encontrada." };
  }

  function safetyReason() {
    if (queryFirst(CONFIG.selectors.safetySignals)) return "Elemento de CAPTCHA/verificação detectado.";
    const text = normalize(document.body?.innerText).slice(0, 20000);
    const match = CONFIG.safetyText.find((pattern) => pattern.test(text));
    return match ? `Aviso de segurança detectado (${match}).` : null;
  }

  function writeLog(action, reason, profile, result) {
    const entry = {
      time: new Date().toISOString(), action, reason,
      profile: profile?.name || null, fingerprint: profile?.fingerprint || null, result
    };
    state.logs.push(entry);
    if (state.logs.length > CONFIG.maxLogEntries) state.logs.shift();
    debug("Log:", entry);
    updateUI();
  }

  function readSettings() {
    const limit = Math.max(1, Number.parseInt(ui.limit.value, 10) || CONFIG.defaults.limit);
    let minDelay = Math.max(500, Number.parseInt(ui.minDelay.value, 10) || CONFIG.defaults.minDelay);
    let maxDelay = Math.max(500, Number.parseInt(ui.maxDelay.value, 10) || CONFIG.defaults.maxDelay);
    if (minDelay > maxDelay) [minDelay, maxDelay] = [maxDelay, minDelay];
    return { limit, minDelay, maxDelay };
  }

  async function performAction(decision, profile) {
    if (decision.action === "SKIP") return { ok: false, result: "Sem clique: perfil indeterminado." };
    if (ui.dryRun.checked) return { ok: true, result: "Dry Run: clique não executado." };
    const button = decision.action === "LIKE" ? findLikeButton(profile.element) : findRejectButton(profile.element);
    if (!button) return { ok: false, result: "Botão não encontrado." };
    if (!visible(button)) return { ok: false, result: "Botão encontrado, mas não está visível." };
    if (!enabled(button)) return { ok: false, result: "Botão encontrado, mas está desabilitado." };
    const fresh = getCurrentProfile();
    if (!fresh || fresh.fingerprint !== profile.fingerprint) {
      return { ok: false, result: "Perfil mudou antes do clique; ação cancelada." };
    }
    debug("Botão encontrado");
    button.click();
    debug("Clique realizado");
    return { ok: true, result: "Clique enviado." };
  }

  function waitForNextProfile(previousFingerprint, timeout = CONFIG.nextProfileTimeout) {
    debug("Aguardando próximo perfil");
    return new Promise((resolve) => {
      const started = Date.now();
      const check = () => {
        if (!state.running || state.stopRequested) return resolve(null);
        const profile = getCurrentProfile();
        if (profile && profile.fingerprint !== previousFingerprint) return resolve(profile);
        if (Date.now() - started >= timeout) return resolve(null);
        state.wakeTimer = setTimeout(check, 250);
      };
      check();
    });
  }

  async function processProfile() {
    if (!state.running || state.processing || state.stopRequested) return;
    const danger = safetyReason();
    if (danger) {
      writeLog("STOP", danger, null, "Automação parada imediatamente.");
      stopAutomation(danger);
      return;
    }
    const profile = getCurrentProfile();
    if (!profile || profile.fingerprint === state.lastHandledFingerprint) return;
    state.processing = true;
    state.currentFingerprint = profile.fingerprint;
    setStatus("PROCESSANDO");
    debug("Perfil detectado", profile.name || profile.fingerprint);
    try {
      const decision = decideAction(profile);
      debug(`Decisão: ${decision.action}`);
      const { minDelay, maxDelay } = readSettings();
      const delay = Math.round(minDelay + Math.random() * (maxDelay - minDelay));
      await sleep(delay);
      if (!state.running || state.stopRequested) return;
      const fresh = getCurrentProfile();
      if (!fresh || fresh.fingerprint !== profile.fingerprint) {
        writeLog("CANCEL", decision.reason, profile, "Perfil mudou durante o atraso.");
        return;
      }
      const outcome = await performAction(decision, profile);
      state.lastHandledFingerprint = profile.fingerprint;
      state.total += 1;
      if (decision.action === "LIKE") state.likes += 1;
      else if (decision.action === "REJECT") state.rejects += 1;
      else state.indeterminate += 1;
      writeLog(decision.action, decision.reason, profile, outcome.result);

      if (state.total >= readSettings().limit) {
        stopAutomation("Limite máximo atingido.");
        return;
      }
      if (decision.action === "SKIP" || ui.dryRun.checked || !outcome.ok) {
        setStatus(decision.action === "SKIP" ? "INDETERMINADO — avance manualmente" : "AGUARDANDO mudança manual");
        return;
      }
      const next = await waitForNextProfile(profile.fingerprint);
      if (!next && state.running) {
        writeLog("WAIT_TIMEOUT", "O perfil não mudou no prazo esperado.", profile, "Nenhum novo clique foi feito.");
        setStatus("AGUARDANDO novo perfil");
      }
    } catch (error) {
      console.error("[TinderBot] Erro:", error);
      writeLog("ERROR", error.message || String(error), profile, "Nenhum clique adicional será tentado neste perfil.");
      state.lastHandledFingerprint = profile.fingerprint;
    } finally {
      state.processing = false;
      if (state.running && ui.status.textContent === "PROCESSANDO") setStatus("ATIVO");
      updateUI();
    }
  }

  function scheduleProcessing() {
    if (!state.running || state.processing) return;
    clearTimeout(state.wakeTimer);
    state.wakeTimer = setTimeout(processProfile, CONFIG.debounceMs);
  }

  function installObserver() {
    state.observer?.disconnect();
    state.observer = new MutationObserver(scheduleProcessing);
    state.observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["aria-label", "aria-disabled", "data-testid"] });
  }

  function startAutomation() {
    if (state.running) return;
    state.running = true;
    state.stopRequested = false;
    state.lastHandledFingerprint = null;
    installObserver();
    setStatus("ATIVO");
    writeLog("START", `Modo ${ui.mode.value}; Dry Run ${ui.dryRun.checked ? "ativado" : "desativado"}.`, null, "Automação iniciada.");
    scheduleProcessing();
  }

  function stopAutomation(reason = "Parada solicitada pelo usuário.") {
    state.stopRequested = true;
    state.running = false;
    state.processing = false;
    clearTimeout(state.wakeTimer);
    state.observer?.disconnect();
    setStatus(`PARADO — ${reason}`);
    updateUI();
  }

  function setStatus(value) { if (ui.status) ui.status.textContent = value; }

  function updateUI() {
    if (!ui.panel?.isConnected) return mountUI();
    ui.likes.textContent = String(state.likes);
    ui.rejects.textContent = String(state.rejects);
    ui.indeterminate.textContent = String(state.indeterminate);
    ui.total.textContent = String(state.total);
    ui.start.disabled = state.running;
    ui.stop.disabled = !state.running;
  }

  function downloadLog(format) {
    const json = JSON.stringify(state.logs, null, 2);
    const text = format === "json" ? json : state.logs.map((entry) =>
      `${entry.time}\t${entry.action}\t${entry.profile || "(não disponível)"}\t${entry.reason}\t${entry.result}`
    ).join("\n");
    const blob = new Blob([text], { type: format === "json" ? "application/json" : "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `tinder-bot-log-${new Date().toISOString().replace(/[:.]/g, "-")}.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  function mountUI() {
    if (document.getElementById("tinder-bot-panel")) return;
    const panel = document.createElement("section");
    panel.id = "tinder-bot-panel";
    panel.innerHTML = `
      <style>
        #tinder-bot-panel{position:fixed;z-index:2147483647;right:16px;top:72px;width:300px;padding:14px;border-radius:14px;background:#17171c;color:#fff;box-shadow:0 8px 30px #0008;font:13px/1.35 system-ui,sans-serif;border:1px solid #ffffff25}
        #tinder-bot-panel *{box-sizing:border-box}#tinder-bot-panel h2{font-size:16px;margin:0 0 10px;color:#ff4458}#tinder-bot-panel label{display:block;margin:7px 0}
        #tinder-bot-panel input,#tinder-bot-panel select{width:100%;margin-top:3px;border:1px solid #ffffff35;border-radius:6px;padding:6px;background:#292930;color:#fff}
        #tinder-bot-panel .tb-row{display:grid;grid-template-columns:1fr 1fr;gap:7px}#tinder-bot-panel button{border:0;border-radius:7px;padding:7px;cursor:pointer;font-weight:700}
        #tinder-bot-panel button:disabled{opacity:.45;cursor:not-allowed}#tinder-bot-panel .tb-start{background:#21d07a}#tinder-bot-panel .tb-stop{background:#ff4458;color:#fff}
        #tinder-bot-panel .tb-status{padding:7px;background:#ffffff12;border-radius:7px;margin:8px 0;overflow-wrap:anywhere}#tinder-bot-panel .tb-counts{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin:8px 0}
        #tinder-bot-panel .tb-check{display:flex;gap:7px;align-items:center}#tinder-bot-panel .tb-check input{width:auto;margin:0}#tinder-bot-panel .tb-export button{font-size:11px}
      </style>
      <h2>TinderBot <small>(local)</small></h2>
      <div class="tb-status">Status: <b data-ui="status">PARADO</b></div>
      <label>Modo<select data-ui="mode"><option value="filter">Perfis já filtrados pelo Tinder</option><option value="text">Regra por texto explícito</option></select></label>
      <label class="tb-check"><input data-ui="dryRun" type="checkbox" checked> Dry Run (não clicar)</label>
      <label class="tb-check"><input data-ui="debug" type="checkbox"> DEBUG no console</label>
      <label>Limite máximo<input data-ui="limit" type="number" min="1" max="5000" value="${CONFIG.defaults.limit}"></label>
      <div class="tb-row"><label>Atraso mín. (ms)<input data-ui="minDelay" type="number" min="500" value="${CONFIG.defaults.minDelay}"></label><label>Atraso máx. (ms)<input data-ui="maxDelay" type="number" min="500" value="${CONFIG.defaults.maxDelay}"></label></div>
      <div class="tb-counts"><span>❤️ <b data-ui="likes">0</b></span><span>✕ <b data-ui="rejects">0</b></span><span>?</span><b data-ui="indeterminate">0</b><span>Total</span><b data-ui="total">0</b></div>
      <div class="tb-row"><button class="tb-start" data-ui="start">INICIAR</button><button class="tb-stop" data-ui="stop" disabled>PARAR / EMERGÊNCIA</button></div>
      <div class="tb-row tb-export"><button data-export="txt">Exportar TXT</button><button data-export="json">Exportar JSON</button></div>`;
    document.body.append(panel);
    ui.panel = panel;
    for (const element of panel.querySelectorAll("[data-ui]")) ui[element.dataset.ui] = element;
    ui.start.addEventListener("click", startAutomation);
    ui.stop.addEventListener("click", () => { writeLog("STOP", "Parada solicitada pelo usuário.", getCurrentProfile(), "Automação parada."); stopAutomation(); });
    panel.querySelector('[data-export="txt"]').addEventListener("click", () => downloadLog("txt"));
    panel.querySelector('[data-export="json"]').addEventListener("click", () => downloadLog("json"));
    updateUI();
  }

  // Sobrevive a navegação SPA e recriação do body/painel.
  let lastUrl = location.href;
  state.routeTimer = setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      debug("Rota alterada:", lastUrl);
      state.lastHandledFingerprint = null;
      if (state.running) installObserver();
    }
    if (!document.getElementById("tinder-bot-panel") && document.body) mountUI();
    if (state.running) scheduleProcessing();
  }, 1000);

  if (document.body) mountUI();
  else addEventListener("DOMContentLoaded", mountUI, { once: true });
})();
