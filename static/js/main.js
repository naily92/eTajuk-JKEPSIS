document.addEventListener("DOMContentLoaded", function () {
  // Fungsi toggle untuk abstrak
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

  // Fungsi untuk hide card semasa print
  document.querySelectorAll(".hide-print-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const card = btn.closest(".card");
      if (card) {
        card.classList.add("no-print"); // class ini kita style dlm CSS
        btn.textContent = "Hidden from Print";
        btn.disabled = true;
      }
    });
  });
});
