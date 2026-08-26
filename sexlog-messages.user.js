// ==UserScript==
// @name         Sexlog - Mensagens assistidas
// @namespace    local.sexlog.messages.assistant
// @version      1.0.0
// @description  Prepara mensagens para conversas escolhidas pelo usuário no Sexlog; cada envio exige confirmação manual explícita.
// @match        https://www.sexlog.com/*
// @match        https://sexlog.com/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(() => {
  "use strict";

  if (window.__SEXLOG_MESSAGE_ASSISTANT__) return;
  window.__SEXLOG_MESSAGE_ASSISTANT__ = true;

  /**
   * ATENÇÃO: os seletores de CONFIG.selectors abaixo são um PONTO DE PARTIDA
   * genérico, não seletores confirmados do Sexlog. A estrutura real do site não é
   * conhecida por quem escreveu este script. Antes de qualquer envio real, siga a
   * seção "Como descobrir e ajustar seletores" do docs/SEXLOG_MESSAGES.md com Dry Run
   * ligado.
   *
   * Este script NUNCA envia nada sozinho. Ele só preenche o campo de mensagem de
   * conversas que o próprio usuário marcou e só clica em "Enviar" depois de um clique
   * explícito em "CONFIRMAR ENVIO" dentro deste painel, por item. Não cria contas, não
   * resolve CAPTCHA, não tenta contornar limites de taxa da plataforma e não guarda
   * nada em disco: fila e log existem só em memória, até recarregar a página.
   */
  const CONFIG = Object.freeze({
    selectors: {
      conversationItems: [
        'a[href*="/ultimate-mensagens"]',
        'a[href*="/mensagens/"]',
        'a[href*="/mensagem/"]',
        'a[href*="/conversas/"]',
        'a[href*="/conversa/"]',
        'a[href*="/chat/"]',
        '[data-testid*="conversation" i] a',
        '[class*="conversa" i] a',
        '[class*="message" i] a[href]'
      ],
      conversationName: [
        '[data-testid*="name" i]',
        '[class*="nome" i]',
        '[class*="name" i]',
        'h3',
        'h4',
        'strong',
        'span'
      ],
      messageInput: [
        'textarea[name*="mensagem" i]',
        'textarea[name*="message" i]',
        'textarea[placeholder*="mensagem" i]',
        'textarea[placeholder*="message" i]',
        'div[contenteditable="true"]',
        'main textarea',
        'textarea'
      ],
      sendButton: [
        'button[type="submit"]',
        'button[aria-label*="enviar" i]',
        'button[aria-label*="send" i]',
        'input[type="submit"][value*="enviar" i]',
        'button'
      ],
      safetySignals: [
        '[data-testid*="captcha" i]',
        'iframe[src*="captcha" i]',
        'iframe[title*="captcha" i]',
        '[class*="captcha" i]',
        '[aria-label*="verificação" i]',
        '[aria-label*="verification" i]'
      ]
    },
    safetyText: [
      /captcha/i,
      /atividade suspeita/i,
      /suspicious activity/i,
      /verifique que (?:você|voce) (?:é|e) humano/i,
      /verify (?:that )?you(?:'re| are) human/i,
      /conta (?:foi )?(?:bloqueada|suspensa)/i,
      /account (?:has been )?(?:blocked|suspended)/i,
      /limite (?:de mensagens|di[aá]rio) atingido/i,
      /rate limit/i,
      /muitas tentativas/i
    ],
    defaults: { limit: 50, maxLimit: 200 },
    openConversationTimeout: 15000,
    maxLogEntries: 2000,
    maxQueueMessageLength: 2000
  });

  const state = {
    queue: [],
    current: null,
    sentCount: 0,
    stopped: false,
    logs: [],
    nextId: 1
  };

  const ui = {};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalize = (value) => (value || "").replace(/\s+/g, " ").trim();
  const debug = (...args) => ui.debug?.checked && console.debug("[SexlogMessages]", ...args);
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
  const queryAll = (selectors, root = document) => {
    const out = [];
    for (const selector of selectors) {
      try { out.push(...root.querySelectorAll(selector)); } catch { /* ignore */ }
    }
    return out;
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

  function safetyReason() {
    if (queryFirst(CONFIG.selectors.safetySignals)) return "Elemento de CAPTCHA/verificação detectado.";
    const text = normalize(document.body?.innerText).slice(0, 20000);
    const match = CONFIG.safetyText.find((pattern) => pattern.test(text));
    return match ? `Aviso de segurança detectado (${match}).` : null;
  }

  /** Impede novo passo sempre que houver sinal de segurança; interrompe e limpa a fila. */
  function haltOnSafety(context) {
    const danger = safetyReason();
    if (!danger) return false;
    state.stopped = true;
    state.current = null;
    writeLog("STOP", danger, null, `Automação interrompida (${context}). Fila local mantida no histórico, mas processamento parado.`);
    setStatus(`PARADO — ${danger}`);
    updateUI();
    return true;
  }

  function writeLog(action, detail, name, result) {
    const entry = { time: new Date().toISOString(), action, detail, name: name || null, result };
    state.logs.push(entry);
    if (state.logs.length > CONFIG.maxLogEntries) state.logs.shift();
    debug("Log:", entry);
    renderLog();
  }

  function conversationIdFromHref(href) {
    if (!href) return null;
    const pathMatch = href.match(/\/(?:mensagens?|conversas?|chat|ultimate-mensagens)\/([^/?#]+)/);
    if (pathMatch) return pathMatch[1];
    const queryMatch = href.match(/[?&](?:id|conversa|chat)=([^&#]+)/i);
    return queryMatch ? queryMatch[1] : null;
  }

  function scanConversations() {
    if (haltOnSafety("varredura de conversas")) return;
    const items = queryAll(CONFIG.selectors.conversationItems).filter(visible);
    const seen = new Set();
    const results = [];
    for (const item of items) {
      const href = item.getAttribute("href") || item.querySelector?.("a")?.getAttribute("href") || null;
      const id = conversationIdFromHref(href) || null;
      const name = normalize(queryFirst(CONFIG.selectors.conversationName, item)?.textContent) || null;
      const key = id || `${name}|${results.length}`;
      if (seen.has(key)) continue;
      seen.add(key);
      // Só guarda o nome exibido e um identificador técnico; nenhum outro texto da conversa é lido.
      results.push({ id, name, href });
    }
    renderConversationPicker(results);
    writeLog("SCAN", `${results.length} conversa(s) visível(is) encontrada(s).`, null, "Nenhum dado enviado ou salvo em disco.");
  }

  function renderTemplate(template, name) {
    return template.replace(/\{\s*nome\s*\}/gi, name || "");
  }

  function addSelectedToQueue() {
    if (haltOnSafety("montagem da fila")) return;
    const template = ui.template.value;
    if (!normalize(template)) {
      writeLog("QUEUE_ERROR", "Mensagem vazia.", null, "Nada foi adicionado à fila.");
      return;
    }
    const checked = [...ui.pickerList.querySelectorAll('input[type="checkbox"]:checked')];
    if (!checked.length) {
      writeLog("QUEUE_ERROR", "Nenhuma conversa selecionada.", null, "Nada foi adicionado à fila.");
      return;
    }
    for (const box of checked) {
      const message = renderTemplate(template, box.dataset.name).slice(0, CONFIG.maxQueueMessageLength);
      state.queue.push({
        id: state.nextId++,
        conversationId: box.dataset.id || null,
        href: box.dataset.href || null,
        name: box.dataset.name || null,
        message,
        status: "pending"
      });
      box.checked = false;
    }
    writeLog("QUEUE_ADD", `${checked.length} conversa(s) adicionada(s).`, null, "Fila local atualizada.");
    renderQueue();
  }

  function removeFromQueue(id) {
    state.queue = state.queue.filter((entry) => entry.id !== id);
    renderQueue();
  }

  async function openConversation(entry) {
    if (entry.href) {
      const anchor = [...document.querySelectorAll(`a[href="${CSS.escape(entry.href)}"]`)][0]
        || queryAll(CONFIG.selectors.conversationItems).find((item) =>
          (item.getAttribute("href") || item.querySelector?.("a")?.getAttribute("href")) === entry.href
        );
      if (anchor) anchor.click();
    } else if (entry.name) {
      const candidate = queryAll(CONFIG.selectors.conversationItems)
        .find((item) => normalize(queryFirst(CONFIG.selectors.conversationName, item)?.textContent) === entry.name);
      candidate?.click();
    }
    const started = Date.now();
    while (Date.now() - started < CONFIG.openConversationTimeout) {
      const input = queryFirst(CONFIG.selectors.messageInput);
      if (input && visible(input)) return input;
      await sleep(200);
      if (state.stopped) return null;
    }
    return null;
  }

  function setNativeValue(element, value) {
    if (element.tagName === "TEXTAREA" || element.tagName === "INPUT") {
      const prototype = element.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
      setter ? setter.call(element, value) : (element.value = value);
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      element.textContent = value;
      element.dispatchEvent(new InputEvent("input", { bubbles: true }));
    }
  }

  function readFieldValue(element) {
    return element.tagName === "TEXTAREA" || element.tagName === "INPUT" ? element.value : element.textContent;
  }

  async function prepareNext() {
    if (haltOnSafety("preparação do próximo item")) return;
    if (state.current) {
      writeLog("PREPARE_ERROR", "Já existe um item aguardando confirmação.", null, "Confirme, pule ou cancele o atual primeiro.");
      return;
    }
    if (state.sentCount >= currentLimit()) {
      writeLog("LIMIT", "Limite máximo da sessão atingido.", null, "Novo processamento bloqueado até recarregar a página.");
      setStatus("LIMITE ATINGIDO");
      return;
    }
    const entry = state.queue.find((item) => item.status === "pending");
    if (!entry) {
      writeLog("QUEUE_EMPTY", "Fila vazia.", null, "Nada a preparar.");
      return;
    }
    setStatus("ABRINDO CONVERSA…");
    const input = await openConversation(entry);
    if (haltOnSafety("após abrir a conversa")) return;
    if (!input) {
      entry.status = "failed";
      writeLog("OPEN_FAIL", "Campo de mensagem não encontrado a tempo. Verifique os seletores em CONFIG (veja docs/SEXLOG_MESSAGES.md).", entry.name, "Item marcado como falho; não avança sozinho.");
      renderQueue();
      setStatus("FALHA AO ABRIR");
      return;
    }
    setNativeValue(input, entry.message);
    state.current = { entry, input };
    entry.status = "ready";
    renderQueue();
    setStatus(`AGUARDANDO CONFIRMAÇÃO — ${entry.name || "conversa selecionada"}`);
    ui.preview.textContent = entry.message;
    ui.confirmSend.disabled = false;
    ui.skip.disabled = false;
  }

  async function confirmSend() {
    if (!state.current) return;
    const { entry, input } = state.current;
    if (haltOnSafety("imediatamente antes do envio")) return;
    const liveValue = normalize(readFieldValue(input));
    if (liveValue !== normalize(entry.message)) {
      entry.status = "failed";
      writeLog("MISMATCH", "O conteúdo do campo mudou antes da confirmação.", entry.name, "Envio cancelado por segurança.");
      finishCurrent();
      return;
    }
    if (ui.dryRun.checked) {
      entry.status = "sent";
      state.sentCount += 1;
      writeLog("DRY_RUN", entry.message, entry.name, "Dry Run: nenhum clique de envio foi feito.");
      finishCurrent();
      return;
    }
    const button = queryFirst(CONFIG.selectors.sendButton);
    if (!button || !visible(button) || !enabled(button)) {
      entry.status = "failed";
      writeLog("SEND_FAIL", "Botão de enviar não encontrado, invisível ou desabilitado. Verifique os seletores em CONFIG.", entry.name, "Nenhum clique foi feito.");
      finishCurrent();
      return;
    }
    button.click();
    entry.status = "sent";
    state.sentCount += 1;
    writeLog("SENT", entry.message, entry.name, "Clique de envio realizado após confirmação manual.");
    finishCurrent();
  }

  function skipCurrent() {
    if (!state.current) return;
    state.current.entry.status = "skipped";
    writeLog("SKIP", "Pulado pelo usuário.", state.current.entry.name, "Nenhum envio foi feito.");
    finishCurrent();
  }

  function finishCurrent() {
    state.current = null;
    renderQueue();
    ui.preview.textContent = "(nenhum item preparado)";
    ui.confirmSend.disabled = true;
    ui.skip.disabled = true;
    updateUI();
    setStatus(state.stopped ? ui.status.textContent : "PRONTO");
  }

  function currentLimit() {
    const raw = Math.max(1, Number.parseInt(ui.limit.value, 10) || CONFIG.defaults.limit);
    return Math.min(raw, CONFIG.defaults.maxLimit);
  }

  function stopAndClearQueue() {
    state.stopped = true;
    state.current = null;
    state.queue = state.queue.filter((entry) => !["pending", "ready"].includes(entry.status));
    writeLog("STOP", "Parada solicitada pelo usuário.", null, "Itens pendentes removidos da fila.");
    setStatus("PARADO — solicitado pelo usuário");
    ui.preview.textContent = "(nenhum item preparado)";
    ui.confirmSend.disabled = true;
    ui.skip.disabled = true;
    renderQueue();
    updateUI();
  }

  function resume() {
    state.stopped = false;
    setStatus("PRONTO");
    updateUI();
  }

  function setStatus(value) { if (ui.status) ui.status.textContent = value; }

  function updateUI() {
    if (!ui.panel?.isConnected) return mountUI();
    ui.sentCounter.textContent = `${state.sentCount} / ${currentLimit()}`;
    ui.prepareNext.disabled = state.stopped || !!state.current;
    ui.resume.disabled = !state.stopped;
  }

  function renderConversationPicker(results) {
    ui.pickerList.innerHTML = "";
    if (!results.length) {
      ui.pickerList.textContent = "Nenhuma conversa visível encontrada. Role a lista e busque de novo, ou ajuste os seletores em CONFIG (veja docs/SEXLOG_MESSAGES.md).";
      return;
    }
    for (const item of results) {
      const label = document.createElement("label");
      label.className = "sm-check";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.dataset.id = item.id || "";
      box.dataset.name = item.name || "";
      box.dataset.href = item.href || "";
      label.append(box, document.createTextNode(item.name || "(sem nome visível)"));
      ui.pickerList.append(label);
    }
  }

  function renderQueue() {
    ui.queueList.innerHTML = "";
    const pendingCount = state.queue.filter((e) => e.status === "pending" || e.status === "ready").length;
    ui.queueCount.textContent = String(pendingCount);
    for (const entry of state.queue) {
      const row = document.createElement("div");
      row.className = "sm-queue-row";
      row.innerHTML = `<b>${entry.name || "(sem nome)"}</b> <span class="sm-status">[${entry.status}]</span>`;
      const remove = document.createElement("button");
      remove.textContent = "remover";
      remove.disabled = entry.status === "ready";
      remove.addEventListener("click", () => removeFromQueue(entry.id));
      row.append(remove);
      ui.queueList.append(row);
    }
  }

  function renderLog() {
    ui.logCount.textContent = String(state.logs.length);
  }

  function downloadLog(format) {
    const json = JSON.stringify(state.logs, null, 2);
    const text = format === "json" ? json : state.logs.map((entry) =>
      `${entry.time}\t${entry.action}\t${entry.name || "(não disponível)"}\t${entry.detail}\t${entry.result}`
    ).join("\n");
    const blob = new Blob([text], { type: format === "json" ? "application/json" : "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `sexlog-messages-log-${new Date().toISOString().replace(/[:.]/g, "-")}.${format}`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }

  function mountUI() {
    if (document.getElementById("sexlog-messages-panel")) return;
    const panel = document.createElement("section");
    panel.id = "sexlog-messages-panel";
    panel.innerHTML = `
      <style>
        #sexlog-messages-panel{position:fixed;z-index:2147483647;left:16px;top:72px;width:340px;max-height:88vh;overflow:auto;padding:14px;border-radius:14px;background:#17171c;color:#fff;box-shadow:0 8px 30px #0008;font:13px/1.35 system-ui,sans-serif;border:1px solid #ffffff25}
        #sexlog-messages-panel *{box-sizing:border-box}#sexlog-messages-panel h2{font-size:15px;margin:0 0 8px;color:#4fd1c5}
        #sexlog-messages-panel h3{font-size:12px;margin:12px 0 4px;color:#aaa;text-transform:uppercase}
        #sexlog-messages-panel textarea{width:100%;min-height:60px;border:1px solid #ffffff35;border-radius:6px;padding:6px;background:#292930;color:#fff;font:inherit}
        #sexlog-messages-panel input[type=number]{width:70px;border:1px solid #ffffff35;border-radius:6px;padding:4px;background:#292930;color:#fff}
        #sexlog-messages-panel button{border:0;border-radius:7px;padding:6px 8px;cursor:pointer;font-weight:700;background:#3a3a44;color:#fff;margin:2px 3px 2px 0}
        #sexlog-messages-panel button:disabled{opacity:.4;cursor:not-allowed}
        #sexlog-messages-panel .sm-confirm{background:#21d07a}#sexlog-messages-panel .sm-stop{background:#ff4458}
        #sexlog-messages-panel .sm-status{opacity:.7}#sexlog-messages-panel .sm-check{display:block;margin:3px 0}
        #sexlog-messages-panel .sm-check input{margin-right:6px}#sexlog-messages-panel .sm-picker{max-height:110px;overflow:auto;border:1px solid #ffffff20;border-radius:6px;padding:6px;margin-top:4px}
        #sexlog-messages-panel .sm-queue-row{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #ffffff15;padding:3px 0;font-size:12px}
        #sexlog-messages-panel .sm-preview{white-space:pre-wrap;background:#ffffff10;border-radius:6px;padding:8px;margin:6px 0;font-size:12px}
        #sexlog-messages-panel .sm-check-row{display:flex;gap:7px;align-items:center;margin:6px 0}
        #sexlog-messages-panel .sm-warn{background:#4a3400;border:1px solid #ffb74d55;border-radius:6px;padding:6px;font-size:11px;margin-bottom:8px}
      </style>
      <h2>Mensagens assistidas — Sexlog <small>(local)</small></h2>
      <div class="sm-warn">Seletores ainda não confirmados neste site. Use Dry Run e valide tudo antes de desligar (veja docs/SEXLOG_MESSAGES.md).</div>
      <div>Status: <b data-ui="status">PARADO</b></div>
      <div>Enviadas nesta sessão: <b data-ui="sentCounter">0 / 50</b></div>

      <h3>1. Buscar conversas visíveis</h3>
      <button data-ui="scan">Buscar conversas na tela</button>
      <div class="sm-picker" data-ui="pickerList">Clique em "Buscar" para listar.</div>

      <h3>2. Mensagem (use {nome} para o nome exibido)</h3>
      <textarea data-ui="template" placeholder="Oi {nome}! ..."></textarea>
      <button data-ui="addToQueue">Adicionar selecionadas à fila</button>

      <h3>3. Fila local (<span data-ui="queueCount">0</span> pendente(s))</h3>
      <div data-ui="queueList"></div>

      <h3>4. Confirmação manual, item a item</h3>
      <div class="sm-check-row"><label class="sm-check"><input data-ui="dryRun" type="checkbox" checked> Dry Run (não clicar em enviar)</label></div>
      <div class="sm-check-row"><label>Limite da sessão<input data-ui="limit" type="number" min="1" max="${CONFIG.defaults.maxLimit}" value="${CONFIG.defaults.limit}"></label></div>
      <label class="sm-check"><input data-ui="debug" type="checkbox"> DEBUG no console</label>
      <div><button data-ui="prepareNext">Preparar próximo da fila</button></div>
      <div class="sm-preview" data-ui="preview">(nenhum item preparado)</div>
      <div>
        <button class="sm-confirm" data-ui="confirmSend" disabled>CONFIRMAR ENVIO</button>
        <button data-ui="skip" disabled>Pular</button>
        <button class="sm-stop" data-ui="stop">PARAR / limpar fila</button>
        <button data-ui="resume" disabled>Retomar</button>
      </div>

      <h3>Log local (<span data-ui="logCount">0</span> entradas, só em memória)</h3>
      <button data-export="txt">Exportar TXT</button><button data-export="json">Exportar JSON</button>`;
    document.body.append(panel);
    ui.panel = panel;
    for (const element of panel.querySelectorAll("[data-ui]")) ui[element.dataset.ui] = element;
    ui.scan.addEventListener("click", scanConversations);
    ui.addToQueue.addEventListener("click", addSelectedToQueue);
    ui.prepareNext.addEventListener("click", prepareNext);
    ui.confirmSend.addEventListener("click", confirmSend);
    ui.skip.addEventListener("click", skipCurrent);
    ui.stop.addEventListener("click", stopAndClearQueue);
    ui.resume.addEventListener("click", resume);
    panel.querySelector('[data-export="txt"]').addEventListener("click", () => downloadLog("txt"));
    panel.querySelector('[data-export="json"]').addEventListener("click", () => downloadLog("json"));
    updateUI();
  }

  // Reinstala o painel caso o site recrie o body durante navegação SPA.
  setInterval(() => {
    if (!document.getElementById("sexlog-messages-panel") && document.body) mountUI();
  }, 1000);

  if (document.body) mountUI();
  else addEventListener("DOMContentLoaded", mountUI, { once: true });
})();
