// ✅ Interface unifiée du dictionnaire avec correspondances inter-dictionnaires et affichage fiable

console.log("✅ Interface unifiée du dictionnaire chargée avec correspondance inter-dictionnaires");

const sources = {
  BYM: "/wp-content/uploads/dictionnaires/lexique-bym.json",
  Easton: "/wp-content/uploads/dictionnaires/eastons.json"
};

let allData = {};
let currentDict = "BYM";
let currentLetter = "A";
let currentPage = 1;
const itemsPerPage = 30;

function normalizeInput(str) {
  return (str || "").normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toUpperCase();
}

function initDictionaryApp() {
  const alpha = document.getElementById("alphabet-selector");
  const list = document.getElementById("word-list");
  const content = document.getElementById("dictionary-content");
  const descriptionContainer = document.getElementById("dictionary-description");
  const search = document.getElementById("dictionary-search");

  const descriptions = {
    BYM: "<p><strong>Dictionnaire biblique de la BYM :</strong> Lexique original publié par la Bible de Yéhoshoua ha Mashiah (BYM). Contenu entièrement restauré dans une optique d’exactitude sémantique et spirituelle. Domaine public sous la licence interne BYM.</p>",
    Easton: "<p><strong>Easton's Bible Dictionary (1897)</strong> – Auteur : M. G. Easton. Dictionnaire classique en anglais, domaine public. <strong>En cours de traduction</strong> par les Éditions À l’ombre du figuier.</p>",
    Smith: "<p><strong>Smith's Bible Dictionary</strong> – Auteur : William Smith. Dictionnaire biblique du XIXe siècle, domaine public. <strong>En cours de traduction</strong> par les Éditions À l’ombre du figuier.</p>",
    Watson: "<p><strong>Watson's Biblical & Theological Dictionary</strong> – Auteur : Richard Watson. Ouvrage théologique du XIXe siècle, domaine public. <strong>En cours de traduction</strong> par les Éditions À l’ombre du figuier.</p>"
  };

  function resetView() {
    list.style.display = "block";
    content.innerHTML = "";
    search.value = "";
  }

  function activateTab(dictKey, callback) {
    const tab = document.querySelector(`.dict-tab[data-dict="${dictKey}"]`);
    if (!tab) return;
    document.querySelectorAll(".dict-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");

    currentDict = dictKey;
    currentPage = 1;
    currentLetter = "A";
    resetView();

    if (descriptions[dictKey]) {
      descriptionContainer.innerHTML = descriptions[dictKey];
    }

    if (dictKey === "Smith" || dictKey === "Watson") {
      list.innerHTML = "";
      alpha.innerHTML = "";
      content.innerHTML = `<div style="text-align: center; padding: 3em 1em;"><p style="font-size: 1.3rem; font-weight: bold; color: #6B4C3B;">Ce dictionnaire est en cours de traduction.</p></div>`;
      return;
    }

    buildAlphabet(currentDict);
    listWords(currentDict, currentLetter, currentPage);

    if (typeof callback === "function") callback();
  }

  document.querySelectorAll(".dict-tab").forEach(tab => {
    tab.addEventListener("click", () => activateTab(tab.dataset.dict));
  });

  function buildAlphabet(dict) {
    if (window.innerWidth <= 640) {
      alpha.innerHTML = "";
      return;
    }
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
    alpha.innerHTML = "";
    letters.forEach(letter => {
      const btn = document.createElement("button");
      btn.textContent = letter;
      btn.addEventListener("click", () => {
        currentLetter = letter;
        currentPage = 1;
        listWords(dict, letter, currentPage);
      });
      alpha.appendChild(btn);
    });
  }

  function listWords(dict, letter, page = 1) {
    const cleanLetter = normalizeInput(letter);
    const data = allData[dict].filter(e => normalizeInput(e.mot).startsWith(cleanLetter));
    const total = Math.ceil(data.length / itemsPerPage);
    const start = (page - 1) * itemsPerPage;
    const shown = data.slice(start, start + itemsPerPage);
    const html = shown.map(e => `<a href="#${dict}/${e.mot}">${e.mot}</a>`).join("");
    const nav = total > 1 ? `<div class='pagination'>${Array.from({ length: total }, (_, i) => `<button class="page-btn" data-page="${i + 1}">${i + 1}</button>`).join("")}</div>` : "";
    list.innerHTML = html + nav;
    list.style.display = "block";
    document.querySelectorAll(".page-btn").forEach(b => {
      b.addEventListener("click", () => {
        currentPage = parseInt(b.dataset.page);
        listWords(currentDict, currentLetter, currentPage);
      });
    });
  }

  function findCorrespondingEntry(dict, term) {
    const altDict = dict === "BYM" ? "Easton" : "BYM";
    const all = allData[altDict];
    const termNormalized = normalizeInput(term);
    return all.find(e => normalizeInput(e.mot) === termNormalized);
  }

  function displayDefinition(dict, mot) {
    const found = allData[dict].find(e => normalizeInput(e.mot) === normalizeInput(mot));
    if (!found) {
      content.innerHTML = "<p>Mot introuvable.</p>";
      return;
    }
    list.style.display = "none";
    const dictName = dict === "BYM" ? "Dictionnaire biblique de la BYM" : dict === "Easton" ? "Easton's Bible Dictionary" : dict;
    let html = `
      <p><a href="#" id="back">← Retour à la liste</a></p>
      <h2>${found.mot} — ${dictName}</h2>
      ${marked.parse(found.definition)}
    `;

    const alt = findCorrespondingEntry(dict, mot);
    if (alt) {
      const altDict = dict === "BYM" ? "Easton" : "BYM";
      const altLabel = dict === "BYM" ? "Voir aussi dans Easton" : "Voir aussi dans le dictionnaire BYM";
      const altLink = `https://alombredufiguier.org/dictionnaires/#${altDict}/${alt.mot}`;
      html += `
        <div style="margin-top: 2em; padding-top: 1em; border-top: 1px solid #ccc;">
          <p style="font-size: 0.95rem;">
            🔁 <a href="${altLink}" style="color: #6B4C3B; text-decoration: underline;">${altLabel}</a>
          </p>
        </div>
      `;
    }

    content.innerHTML = html;
    document.getElementById("back").onclick = e => {
      e.preventDefault();
      list.style.display = "block";
      content.innerHTML = "";
    };
  }

  function handleHash() {
    const hash = decodeURIComponent(location.hash.slice(1));
    if (!hash.includes("/")) return;
    const [dict, mot] = hash.split("/");
    if (sources[dict]) {
      activateTab(dict, () => displayDefinition(dict, mot));
    }
  }

  function handleSearch() {
    const val = normalizeInput(this.value.trim());
    if (val.length < 2) return;

    const results = allData[currentDict]
      .map(e => ({ mot: e.mot, score: normalizeInput(e.mot).includes(val) ? 0 : 1 }))
      .sort((a, b) => a.score - b.score)
      .slice(0, 50);

    list.innerHTML = results.map(e => `<a href="#${currentDict}/${e.mot}">${e.mot}</a>`).join("");
    content.innerHTML = "";
    list.style.display = "block";
  }

  Promise.all(Object.entries(sources).map(async ([key, url]) => {
    const res = await fetch(url);
    const data = await res.json();
    allData[key] = Array.isArray(data)
      ? data.map(e => ({ mot: e.mot || e.term || "", definition: e.definition || "" }))
      : Object.entries(data).map(([mot, def]) => ({ mot, definition: def }));
  })).then(() => {
    buildAlphabet(currentDict);
    listWords(currentDict, currentLetter, currentPage);
    handleHash();
    search.addEventListener("input", handleSearch);
    window.addEventListener("hashchange", handleHash);
  });
}

document.addEventListener("DOMContentLoaded", initDictionaryApp);
