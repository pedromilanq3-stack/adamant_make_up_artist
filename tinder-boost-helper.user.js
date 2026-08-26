// ==UserScript==
// @name         Tinder Web - Boost Helper (fluxo oficial)
// @namespace    local.tinder.boost.helper
// @version      1.3.0
// @description  Ativa Boost disponível e avisa quando o Tinder o liberar oficialmente.
// @match        https://tinder.com/*
// @match        https://www.tinder.com/*
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// @grant        GM_registerMenuCommand
// @grant        GM_notification
// @run-at       document-idle
// @noframes
// ==/UserScript==

(() => {
  "use strict";
  const INSTANCE = "__TINDER_BOOST_HELPER__";
  window[INSTANCE]?.destroy?.();

  const CONFIG = Object.freeze({
    boostSelectors: [
      'button[data-testid*="boost" i]', '[role="button"][data-testid*="boost" i]',
      'button[aria-label*="boost" i]', '[role="button"][aria-label*="boost" i]',
      'button[title*="boost" i]', '[role="button"][title*="boost" i]'
    ],
    safetySelectors: [
      '[data-testid*="captcha" i]', 'iframe[src*="captcha" i]',
      'iframe[title*="captcha" i]', '[aria-label*="verificação" i]',
      '[aria-label*="verification" i]'
    ],
    active: [/\bboost(?:ing)?\s+(?:active|ativo|ativa)\b/i, /\bboost\s+em\s+andamento\b/i,
      /\btempo\s+restante\b/i, /\bremaining\b.*\bboost\b/i],
    available: [/\b(?:1|um)\s+boost\b.*\b(?:gr[aá]tis|free|dispon[ií]vel|available)\b/i,
      /\bboost\b.*\b(?:gr[aá]tis|free|dispon[ií]vel|available)\b/i],
    purchase: [/\b(?:comprar|compre|buy|purchase|get)\b.*\bboosts?\b/i,
      /\bboosts?\b.*(?:R\$|US\$|\$|€|£)\s*\d/i, /\b(?:assinar|upgrade|subscribe)\b/i],
    activation: [/^(?:ativar|usar|iniciar)\s+(?:meu\s+)?boost$/i,
      /^(?:activate|use|start)\s+(?:my\s+)?boost$/i, /^boost\s+(?:agora|now)$/i],
    safety: [/captcha/i, /atividade suspeita/i, /suspicious activity/i,
      /verifique que (?:você|voce) (?:é|e) humano/i, /verify (?:that )?you(?:'re| are) human/i,
      /conta (?:foi )?bloqueada/i, /account (?:has been )?blocked/i],
    verifyDelayMs: 900,
    finalDelayMs: 1300,
    storageKey: "tinderBoostHelper.lastBoostUsedAt",
    monitorKey: "tinderBoostHelper.monitorEnabled",
    monitorIntervalMs: 60 * 1000
  });
  const state = { busy: false, observer: null, renderTimer: null, monitorTimer: null,
    lastMonitorStatus: "unknown" };
  const ui = {};
  const normalize = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const hasAny = (patterns, text) => patterns.some((pattern) => pattern.test(text));
  const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

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
  function labelOf(element) {
    return normalize([element?.getAttribute?.("aria-label"), element?.getAttribute?.("title"),
      element?.getAttribute?.("data-testid"), element?.textContent].filter(Boolean).join(" "));
  }
  function pageText() {
    return normalize((document.querySelector("main") || document.body)?.innerText).slice(0, 30000);
  }
  function classify(text, hasButton = false) {
    const value = normalize(text);
    if (hasAny(CONFIG.active, value)) return "active";
    if (hasAny(CONFIG.purchase, value)) return "purchase";
    if (hasAny(CONFIG.available, value)) return "available";
    return hasButton ? "button-only" : "unknown";
  }
  function boostCandidates() {
    const found = new Set();
    for (const selector of CONFIG.boostSelectors) {
      try { document.querySelectorAll(selector).forEach((element) => found.add(element)); } catch { /* UI changed */ }
    }
    document.querySelectorAll('button, [role="button"]').forEach((element) => {
      if (/\bboost\b/i.test(labelOf(element))) found.add(element);
    });
    return [...found].filter((element) => {
      const label = labelOf(element);
      return visible(element) && enabled(element) && /\bboost\b/i.test(label) &&
        !/super\s*like/i.test(label) && !hasAny(CONFIG.purchase, label);
    });
  }
  function uniqueBoostEntry() {
    const candidates = boostCandidates();
    return candidates.length === 1 ? candidates[0] : null;
  }
  function safeConfirmation() {
    const candidates = [...document.querySelectorAll('button, [role="button"]')]
      .filter((element) => visible(element) && enabled(element))
      .filter((element) => {
        const label = labelOf(element);
        return !hasAny(CONFIG.purchase, label) && hasAny(CONFIG.activation, label);
      });
    return candidates.length === 1 ? candidates[0] : null;
  }
  function safetyReason() {
    for (const selector of CONFIG.safetySelectors) {
      try { if (document.querySelector(selector)) return "CAPTCHA/verificação detectado"; } catch { /* UI changed */ }
    }
    return hasAny(CONFIG.safety, normalize(document.body?.innerText).slice(0, 20000))
      ? "Aviso de segurança detectado" : null;
  }
  function detectStatus() { return classify(pageText(), Boolean(uniqueBoostEntry())); }
  function setMessage(message) { if (ui.message) ui.message.textContent = message; }
  function estimateText() {
    const last = Number(GM_getValue(CONFIG.storageKey, 0) || 0);
    if (!last) return "Sem histórico local de ativação.";
    const estimate = new Date(last + 30 * 24 * 60 * 60 * 1000);
    return `Estimativa local de 30 dias: ${estimate.toLocaleString("pt-BR")}`;
  }
  function render() {
    const status = detectStatus();
    const labels = { active: "ATIVO", available: "DISPONÍVEL", purchase: "TELA DE COMPRA",
      "button-only": "BOTÃO DETECTADO", unknown: "NÃO DETECTADO" };
    if (ui.status) ui.status.textContent = labels[status] || status;
    if (ui.estimate) ui.estimate.textContent = estimateText();
    if (ui.activate) ui.activate.disabled = state.busy || ["active", "purchase"].includes(status);
    if (ui.refresh) ui.refresh.disabled = state.busy;
    if (ui.reset) ui.reset.disabled = state.busy || !GM_getValue(CONFIG.storageKey, 0);
  }
  function resetLocalHistory() {
    GM_deleteValue(CONFIG.storageKey);
    setMessage("Histórico local apagado. O saldo e o prazo do Tinder não foram alterados.");
    render();
  }
  function monitorEnabled() { return Boolean(GM_getValue(CONFIG.monitorKey, false)); }
  function checkAvailability({ notify = true } = {}) {
    const status = detectStatus();
    if (notify && monitorEnabled() && status === "available" && state.lastMonitorStatus !== "available") {
      GM_notification({ title: "Tinder Boost disponível", text: "O Tinder indica um Boost disponível. Abra a página para conferir e ativar pelo fluxo oficial.", timeout: 10000 });
    }
    state.lastMonitorStatus = status;
    render();
  }
  function restartMonitor() {
    clearInterval(state.monitorTimer);
    state.monitorTimer = null;
    if (monitorEnabled()) {
      state.lastMonitorStatus = detectStatus();
      state.monitorTimer = setInterval(checkAvailability, CONFIG.monitorIntervalMs);
    }
    if (ui.monitor) ui.monitor.textContent = monitorEnabled() ? "DESATIVAR AVISO" : "AVISAR QUANDO LIBERAR";
  }
  function toggleMonitor() {
    const enabled = !monitorEnabled();
    GM_setValue(CONFIG.monitorKey, enabled);
    setMessage(enabled
      ? "Aviso ativado. Enquanto esta aba estiver aberta, verificarei a disponibilidade a cada minuto."
      : "Aviso de disponibilidade desativado.");
    restartMonitor();
  }
  function reloadOfficialState() {
    if (state.busy) return;
    setMessage("Recarregando a conta para consultar novamente o estado oficial do Boost...");
    setTimeout(() => window.location.reload(), 300);
  }

  async function activateBoost() {
    if (state.busy) return;
    const danger = safetyReason();
    if (danger) return setMessage(`${danger}. Nenhuma ação executada.`);
    state.busy = true;
    render();
    try {
      let status = detectStatus();
      if (status === "active") return setMessage("O Tinder já indica Boost ativo.");
      if (status === "purchase") return setMessage("A interface indica compra. Nenhum pagamento será clicado.");
      const entry = uniqueBoostEntry();
      if (!entry) return setMessage("Não encontrei um único botão Boost confiável. Nenhum clique feito.");
      entry.click();
      setMessage("Fluxo oficial aberto. Verificando disponibilidade...");
      await sleep(CONFIG.verifyDelayMs);
      const openedText = pageText();
      status = classify(openedText, Boolean(uniqueBoostEntry()));
      if (status === "purchase" || hasAny(CONFIG.purchase, openedText)) {
        return setMessage("O Tinder abriu uma oferta de compra. Parei sem comprar nada.");
      }
      if (status === "active") {
        GM_setValue(CONFIG.storageKey, Date.now());
        return setMessage("Boost ativado pelo fluxo oficial.");
      }
      const confirmation = safeConfirmation();
      if (!confirmation) return setMessage("Não há confirmação segura identificável. Confirme manualmente.");
      confirmation.click();
      setMessage("Confirmação enviada. Verificando...");
      await sleep(CONFIG.finalDelayMs);
      const finalText = pageText();
      status = classify(finalText, Boolean(uniqueBoostEntry()));
      if (status === "active" || /\bboost\b.*\b(?:ativo|active|remaining|restante)\b/i.test(finalText)) {
        GM_setValue(CONFIG.storageKey, Date.now());
        setMessage("Boost ativado pelo fluxo oficial.");
      } else if (status === "purchase") {
        setMessage("A tela mudou para compra. Nenhuma compra foi executada.");
      } else setMessage("Não consegui confirmar a ativação. Verifique a tela do Tinder.");
    } finally {
      state.busy = false;
      render();
    }
  }

  function mount() {
    if (document.getElementById("tinder-boost-helper-panel")) return;
    const panel = document.createElement("section");
    panel.id = "tinder-boost-helper-panel";
    panel.innerHTML = `
      <style>
        #tinder-boost-helper-panel{position:fixed;z-index:2147483647;left:16px;top:72px;width:300px;padding:12px;border-radius:12px;background:#17171c;color:#fff;box-shadow:0 8px 30px #0008;font:13px/1.4 system-ui,sans-serif;border:1px solid #ffffff25}
        #tinder-boost-helper-panel *{box-sizing:border-box} #tinder-boost-helper-panel h3{margin:0 0 8px;color:#a78bfa;font-size:15px}
        #tinder-boost-helper-panel .status{padding:7px;background:#ffffff12;border-radius:7px;margin:7px 0}
        #tinder-boost-helper-panel .actions{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px}
        #tinder-boost-helper-panel button{border:0;border-radius:7px;padding:8px;cursor:pointer;font-weight:700}
        #tinder-boost-helper-panel button:disabled{opacity:.45;cursor:not-allowed}
        #tinder-boost-helper-panel .activate{background:#8b5cf6;color:#fff}
        #tinder-boost-helper-panel .reset{grid-column:1/-1;background:#34343d;color:#fff}
        #tinder-boost-helper-panel .monitor{grid-column:1/-1;background:#2563eb;color:#fff}
        #tinder-boost-helper-panel .reload{grid-column:1/-1;background:#065f46;color:#fff}
        #tinder-boost-helper-panel small{display:block;color:#bbb;margin-top:7px}
      </style>
      <h3>⚡ Tinder Boost Helper</h3><div class="status">Boost: <b data-ui="status">VERIFICANDO</b></div>
      <div data-ui="message">Só usa Boost já liberado na conta.</div><small data-ui="estimate"></small>
      <div class="actions"><button data-ui="refresh" type="button">VERIFICAR</button>
      <button class="activate" data-ui="activate" type="button">ATIVAR BOOST</button>
      <button class="monitor" data-ui="monitor" type="button">AVISAR QUANDO LIBERAR</button>
      <button class="reload" data-ui="reload" type="button">RECARREGAR ESTADO OFICIAL</button>
      <button class="reset" data-ui="reset" type="button">APAGAR HISTÓRICO LOCAL</button></div>
      <small>Alternativa segura: o aviso monitora somente a interface oficial. Nenhuma função reinicia saldo, assinatura ou prazo no Tinder.</small>`;
    document.documentElement.append(panel);
    panel.querySelectorAll("[data-ui]").forEach((element) => { ui[element.dataset.ui] = element; });
    ui.refresh.addEventListener("click", render);
    ui.monitor.addEventListener("click", toggleMonitor);
    ui.reload.addEventListener("click", reloadOfficialState);
    ui.reset.addEventListener("click", resetLocalHistory);
    ui.activate.addEventListener("click", () => activateBoost().catch((error) => setMessage(`Erro: ${error.message || error}`)));
    render();
    restartMonitor();
  }
  function scheduleRender() {
    clearTimeout(state.renderTimer);
    state.renderTimer = setTimeout(() => {
      if (!document.getElementById("tinder-boost-helper-panel")) mount();
      else if (!state.busy) render();
    }, 250);
  }
  function destroy() {
    state.observer?.disconnect();
    clearTimeout(state.renderTimer);
    clearInterval(state.monitorTimer);
    document.getElementById("tinder-boost-helper-panel")?.remove();
  }
  GM_registerMenuCommand("⚡ Verificar Boost", () => { mount(); render(); });
  GM_registerMenuCommand("⚡ Ativar Boost disponível", () => { mount(); activateBoost(); });
  GM_registerMenuCommand("🧹 Apagar histórico local", () => { mount(); resetLocalHistory(); });
  GM_registerMenuCommand("🔔 Alternar aviso de disponibilidade", () => { mount(); toggleMonitor(); });
  GM_registerMenuCommand("↻ Recarregar estado oficial", reloadOfficialState);
  state.observer = new MutationObserver(scheduleRender);
  state.observer.observe(document.documentElement, { childList: true, subtree: true });
  window[INSTANCE] = { destroy, render, activateBoost, resetLocalHistory, checkAvailability,
    toggleMonitor, reloadOfficialState };
  mount();
})();
