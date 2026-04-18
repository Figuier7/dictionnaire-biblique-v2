(function () {
  function ensurePagination(el) {
    let pag = el.querySelector(".swiper-pagination");
    if (!pag) {
      pag = document.createElement("div");
      pag.className = "swiper-pagination";
      el.appendChild(pag);
    }
    return pag;
  }

  function toggleNav(swiper) {
    const isDesktop = window.matchMedia("(min-width: 769px)").matches;
    const nextEl = swiper.el.querySelector(".swiper-button-next");
    const prevEl = swiper.el.querySelector(".swiper-button-prev");

    if (!nextEl || !prevEl) return;

    // En desktop: nav visible. En mobile: cachée (CSS + sécurité)
    nextEl.style.display = isDesktop ? "" : "none";
    prevEl.style.display = isDesktop ? "" : "none";
  }

  function initFiguierSwipers() {
    document.querySelectorAll(".figuier-swiper").forEach((el) => {
      if (el.dataset.swiperInitialized === "1") return;
      if (!el.classList.contains("swiper")) return;
      if (typeof Swiper === "undefined") return;

      const nextEl = el.querySelector(".swiper-button-next");
      const prevEl = el.querySelector(".swiper-button-prev");
      const paginationEl = ensurePagination(el);

      const swiper = new Swiper(el, {
        slidesPerView: 1.12,
        spaceBetween: 14,
        loop: false,
        grabCursor: true,
        watchOverflow: true,

        // Pagination (mobile-friendly)
        pagination: {
          el: paginationEl,
          clickable: true,
        },

        // Nav (sera masquée en mobile)
        navigation: {
          nextEl: nextEl || null,
          prevEl: prevEl || null,
        },

        breakpoints: {
          520: { slidesPerView: 1.45, spaceBetween: 18 },
          768: { slidesPerView: 2.15, spaceBetween: 22 },
          1024: { slidesPerView: 3.0, spaceBetween: 24 },
        },

        on: {
          init: function () {
            toggleNav(this);
          },
          breakpoint: function () {
            toggleNav(this);
          },
        },
      });

      el.dataset.swiperInitialized = "1";
      el.dataset.swiperId = String(swiper?.el ? 1 : 1);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFiguierSwipers();

    // Re-scan si le DOM change (Customizer / builders)
    const obs = new MutationObserver(function () {
      initFiguierSwipers();
    });
    obs.observe(document.body, { childList: true, subtree: true });
  });

  if (window.wp && wp.customize && wp.customize.selectiveRefresh) {
    wp.customize.selectiveRefresh.bind("partial-content-rendered", function () {
      initFiguierSwipers();
    });
  }

  // Si rotation / resize mobile
  window.addEventListener("resize", function () {
    document.querySelectorAll(".figuier-swiper.swiper-initialized").forEach((el) => {
      const s = el.swiper;
      if (s) {
        s.update();
        try { s.emit("breakpoint"); } catch(e) {}
      }
    });
  });
})();
