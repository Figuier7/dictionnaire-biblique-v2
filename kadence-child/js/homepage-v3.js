/* ============================================================
   À L'OMBRE DU FIGUIER — HOMEPAGE V3
   Filtres à chips (catégories d'articles / piliers signes des temps)
   ES5 strict (pas de const/let/arrow/template literals) pour
   compatibilité maximale avec l'écosystème WordPress.
   ============================================================ */
(function () {
	'use strict';

	/**
	 * Active le filtrage d'une grille par chips.
	 *
	 * @param {string} chipsContainerId  ID du conteneur des chips.
	 * @param {string} gridId            ID du conteneur de la grille filtrée.
	 * @param {string} dataAttr          Nom de l'attribut data- des cartes (ex: "cats" pour data-cats).
	 */
	function setupChipFilter(chipsContainerId, gridId, dataAttr) {
		var chipsContainer = document.getElementById(chipsContainerId);
		var grid = document.getElementById(gridId);
		if (!chipsContainer || !grid) {
			return;
		}

		var chips = chipsContainer.querySelectorAll('.hpv3-chip');
		var cards = grid.querySelectorAll('[data-' + dataAttr + ']');

		function applyFilter(filterValue) {
			var i, j;
			for (i = 0; i < cards.length; i++) {
				var card = cards[i];
				var raw = card.getAttribute('data-' + dataAttr) || '';
				var tokens = raw.split(' ');
				var show = false;
				if (filterValue === 'all') {
					show = true;
				} else {
					for (j = 0; j < tokens.length; j++) {
						if (tokens[j] === filterValue) {
							show = true;
							break;
						}
					}
				}
				if (show) {
					card.removeAttribute('hidden');
				} else {
					card.setAttribute('hidden', 'hidden');
				}
			}
		}

		function setActive(chip) {
			var i;
			for (i = 0; i < chips.length; i++) {
				chips[i].classList.remove('hpv3-chip-active');
				chips[i].setAttribute('aria-pressed', 'false');
			}
			chip.classList.add('hpv3-chip-active');
			chip.setAttribute('aria-pressed', 'true');
		}

		function onChipClick(e) {
			var chip = e.currentTarget;
			var filterValue = chip.getAttribute('data-filter') || 'all';
			setActive(chip);
			applyFilter(filterValue);
		}

		var k;
		for (k = 0; k < chips.length; k++) {
			chips[k].setAttribute('aria-pressed', k === 0 ? 'true' : 'false');
			if (chips[k].addEventListener) {
				chips[k].addEventListener('click', onChipClick, false);
			}
		}

		// État initial : tout affiché.
		applyFilter('all');
	}

	function init() {
		setupChipFilter('hpv3-chips-articles', 'hpv3-articles-grid', 'cats');
		setupChipFilter('hpv3-chips-signes', 'hpv3-signes-grid', 'piliers');
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init, false);
	} else {
		init();
	}
})();
