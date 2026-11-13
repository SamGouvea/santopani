(function () {
  var CHAVE = "tema";
  var raiz = document.documentElement;

  function lerSalvo() {
    try { return localStorage.getItem(CHAVE); } catch (e) { return null; }
  }
  function gravar(v) {
    try { localStorage.setItem(CHAVE, v); } catch (e) {}
  }
  function doSistema() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function atual() {
    return raiz.getAttribute("data-theme") || doSistema();
  }

  // Aplica o tema salvo antes de a página aparecer (evita piscar branco)
  var salvo = lerSalvo();
  if (salvo === "dark" || salvo === "light") raiz.setAttribute("data-theme", salvo);

  document.addEventListener("DOMContentLoaded", function () {
    var btn = document.getElementById("tema-btn");
    if (!btn) return;
    var icone = btn.querySelector(".tema-icone");

    function atualizar() {
      var escuro = atual() === "dark";
      btn.setAttribute("aria-pressed", escuro ? "true" : "false");
      icone.textContent = escuro ? "🌙" : "☀️";
    }

    btn.addEventListener("click", function () {
      var novo = atual() === "dark" ? "light" : "dark";
      raiz.setAttribute("data-theme", novo);
      gravar(novo);
      atualizar();
    });
    atualizar();
  });
})();