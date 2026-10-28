/* Presentation controls never send REAPER commands. */
(function () {
  "use strict";
  const RC = window.RC, stage = document.getElementById("stageView"), full = document.getElementById("fullView");
  function labels() {
    const fr = RC.LANG === "fr";
    stage.textContent = document.body.classList.contains("stage-view") ? (fr ? "QUITTER" : "EXIT STAGE") : (fr ? "SCÈNE" : "STAGE");
    stage.title = fr ? "Agrandir la lecture et réduire les commandes secondaires" : "Larger live display with less secondary chrome";
    full.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M8 3H3v5M16 3h5v5M21 16v5h-5M8 21H3v-5"/></svg>';
    full.setAttribute("aria-label", document.fullscreenElement ? (fr ? "Quitter le plein écran" : "Exit fullscreen") : (fr ? "Plein écran" : "Fullscreen"));
    full.title = full.getAttribute("aria-label");
    stage.setAttribute("aria-pressed", String(document.body.classList.contains("stage-view")));
    full.setAttribute("aria-pressed", String(!!document.fullscreenElement));
  }
  document.body.classList.toggle("stage-view", RC.load("reacue_stage_view") === "1");
  stage.onclick = () => {
    const on = document.body.classList.toggle("stage-view");
    RC.store("reacue_stage_view", on ? "1" : "0");
    labels(); window.dispatchEvent(new Event("resize"));
  };
  if (!document.documentElement.requestFullscreen) full.hidden = true;
  full.onclick = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch (_) { if (RC.toast) RC.toast(RC.LANG === "fr" ? "Plein écran indisponible dans ce navigateur." : "Fullscreen unavailable in this browser.", true); }
    labels();
  };
  document.addEventListener("fullscreenchange", labels);
  RC.onLang.push(labels); labels();
})();
