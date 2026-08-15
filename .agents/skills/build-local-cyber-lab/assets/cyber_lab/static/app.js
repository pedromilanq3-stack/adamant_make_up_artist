const result = document.querySelector("#result");

document.querySelectorAll("button[data-scenario]").forEach((button) => {
  button.addEventListener("click", async () => {
    const response = await fetch(`/api/scenario/${button.dataset.scenario}`, { method: "POST" });
    const data = await response.json();
    document.querySelector("#result-title").textContent = data.scenario;
    document.querySelector("#vulnerable").textContent = data.vulnerable;
    document.querySelector("#fixed").textContent = data.fixed;
    document.querySelector("#event").textContent = `[DETECTADO] ${data.timestamp}\n${data.event}\nEscopo: ${data.scope}`;
    result.hidden = false;
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

