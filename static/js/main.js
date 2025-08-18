document.addEventListener("DOMContentLoaded", function(){
  document.querySelectorAll(".toggle").forEach(function(btn){
    btn.addEventListener("click", function(e){
      e.preventDefault();
      const card = btn.closest(".card");
      const shortEl = card.querySelector(".abstract.short");
      const fullEl = card.querySelector(".abstract.full");
      const isOpen = fullEl.style.display !== "none";
      if(isOpen){
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
});