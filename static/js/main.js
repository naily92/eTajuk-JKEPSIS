document.addEventListener("DOMContentLoaded", function () {
  // Toggle abstrak (short <-> full)
  document.querySelectorAll(".toggle").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const card = btn.closest(".card");
      const shortEl = card.querySelector(".abstract.short");
      const fullEl = card.querySelector(".abstract.full");
      const isOpen = fullEl.style.display !== "none";
      if (isOpen) {
        fullEl.style.display = "none";
        shortEl.style.display = "";
        btn.textContent = "Read more";
      } else {
        fullEl.style.display = "";
        shortEl.style.display = "none";
        btn.textContent = "Show less";
      }
    });
  });

  // Hide card semasa print sahaja
  document.querySelectorAll(".hide-print-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const card = btn.closest(".card");
      if (card) {
        card.classList.add("no-print");
        btn.textContent = "Hidden from Print";
        btn.disabled = true;
      }
    });
  });

  // Butang cetak
  const printBtn = document.getElementById("print-btn");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      window.print();
    });
  }

  // (Bonus) Auto expand semua abstrak masa print
  function expandAll() {
    document.querySelectorAll(".card").forEach(card => {
      const shortEl = card.querySelector(".abstract.short");
      const fullEl = card.querySelector(".abstract.full");
      const toggle = card.querySelector(".toggle");
      if (shortEl && fullEl && toggle) {
        shortEl.dataset._display = shortEl.style.display || "";
        fullEl.dataset._display = fullEl.style.display || "";
        shortEl.style.display = "none";
        fullEl.style.display = "";
        toggle.dataset._text = toggle.textContent;
        //toggle.textContent = "Show less";
      }
    });
  }
  function collapseAll() {
    document.querySelectorAll(".card").forEach(card => {
      const shortEl = card.querySelector(".abstract.short");
      const fullEl = card.querySelector(".abstract.full");
      const toggle = card.querySelector(".toggle");
      if (shortEl && fullEl && toggle) {
        shortEl.style.display = shortEl.dataset._display || "";
        fullEl.style.display = fullEl.dataset._display || "none";
        if (toggle.dataset._text) toggle.textContent = toggle.dataset._text;
      }
    });
  }

  // Hook sebelum/selepas print (disokong major browser)
  if ("matchMedia" in window) {
    const mediaQueryList = window.matchMedia("print");
    mediaQueryList.addEventListener
      ? mediaQueryList.addEventListener("change", (e) => e.matches ? expandAll() : collapseAll())
      : mediaQueryList.addListener((e) => e.matches ? expandAll() : collapseAll()); // fallback lama
  }
  window.addEventListener("beforeprint", expandAll);
  window.addEventListener("afterprint", collapseAll);
});
