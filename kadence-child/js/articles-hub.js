/* ============================================================
   À L'OMBRE DU FIGUIER — ARTICLES HUB
   Progressive enhancement pour le shortcode [articles_hub]
   - Filtrage hybride : URL params + AJAX sans reload si JS actif
   - Load more via REST endpoint
   - Back/forward navigateur (popstate)
   - Sidebar accordéon sur mobile
   ES5 strict pour compatibilité WordPress.
   ============================================================ */
(function () {
	'use strict';

	var CONFIG = window.FiguierArticlesHub || {};
	var REST_URL = CONFIG.rest_url || '';
	var NONCE = CONFIG.nonce || '';
	var PAGE_URL = CONFIG.page_url || '';

	var hub, grid, loadMoreBtn, sidebar, activeFiltersContainer, resultsCountEl;

	var state = {
		cat: '',
		tag: '',
		serie: '',
		dossier: '',
		offset: 0,
		limit: 12,
		total: 0
	};

	/* ========================================================
	   UTILS
	   ======================================================== */

	function $(selector, scope) {
		return (scope || document).querySelector(selector);
	}
	function $$(selector, scope) {
		return (scope || document).querySelectorAll(selector);
	}

	function parseUrlFilters(url) {
		var params = {};
		try {
			var u = new URL(url, window.location.origin);
			params.cat = u.searchParams.get('cat') || '';
			params.tag = u.searchParams.get('tag') || '';
			params.serie = u.searchParams.get('serie') || '';
			params.dossier = u.searchParams.get('dossier') || '';
		} catch (e) {
			params.cat = params.tag = params.serie = params.dossier = '';
		}
		return params;
	}

	function buildUrl(filters) {
		var base = PAGE_URL || (window.location.origin + window.location.pathname);
		var parts = [];
		var keys = ['cat', 'tag', 'serie', 'dossier'];
		for (var i = 0; i < keys.length; i++) {
			var k = keys[i];
			if (filters[k]) {
				parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(filters[k]));
			}
		}
		return parts.length ? (base + '?' + parts.join('&')) : base;
	}

	function buildRestUrl(filters, offset, limit) {
		if (!REST_URL) {
			return '';
		}
		var parts = [];
		var keys = ['cat', 'tag', 'serie', 'dossier'];
		for (var i = 0; i < keys.length; i++) {
			var k = keys[i];
			if (filters[k]) {
				parts.push(k + '=' + encodeURIComponent(filters[k]));
			}
		}
		parts.push('offset=' + (offset || 0));
		parts.push('limit=' + (limit || 12));
		var sep = REST_URL.indexOf('?') === -1 ? '?' : '&';
		return REST_URL + sep + parts.join('&');
	}

	function fetchJson(url, callback) {
		var xhr = new XMLHttpRequest();
		xhr.open('GET', url, true);
		xhr.setRequestHeader('Accept', 'application/json');
		if (NONCE) {
			xhr.setRequestHeader('X-WP-Nonce', NONCE);
		}
		xhr.onreadystatechange = function () {
			if (xhr.readyState !== 4) {
				return;
			}
			if (xhr.status >= 200 && xhr.status < 300) {
				try {
					var data = JSON.parse(xhr.responseText);
					callback(null, data);
				} catch (e) {
					callback(e);
				}
			} else {
				callback(new Error('HTTP ' + xhr.status));
			}
		};
		xhr.onerror = function () {
			callback(new Error('Network error'));
		};
		xhr.send();
	}

	/* ========================================================
	   RENDU
	   ======================================================== */

	function setCardsHtml(html) {
		if (!grid) {
			return;
		}
		grid.innerHTML = html;
	}

	function appendCardsHtml(html) {
		if (!grid) {
			return;
		}
		var temp = document.createElement('div');
		temp.innerHTML = html;
		while (temp.firstChild) {
			grid.appendChild(temp.firstChild);
		}
	}

	function updateActiveFilterLinks() {
		// Sidebar : ajoute/retire .ahub-filter-link--active selon l'état
		var links = $$('.ahub-filter-link, .ahub-filter-tag', sidebar);
		for (var i = 0; i < links.length; i++) {
			var link = links[i];
			var type = link.getAttribute('data-filter-type');
			var slug = link.getAttribute('data-filter-slug') || '';
			var cls = link.classList.contains('ahub-filter-tag') ? 'ahub-filter-tag--active' : 'ahub-filter-link--active';
			var isActive = false;
			if (type === 'cat' && slug === '' && !state.cat) {
				isActive = true;
			} else if (type && slug !== '' && state[type] === slug) {
				isActive = true;
			}
			if (isActive) {
				link.classList.add(cls);
			} else {
				link.classList.remove(cls);
			}
		}
	}

	function updateResultsCount(total) {
		if (!resultsCountEl) {
			return;
		}
		if (total === 0) {
			resultsCountEl.textContent = 'Aucun article ne correspond à ces filtres.';
		} else if (total === 1) {
			resultsCountEl.textContent = '1 article';
		} else {
			resultsCountEl.textContent = total + ' articles';
		}
	}

	function showLoadMore(show) {
		if (!loadMoreBtn) {
			return;
		}
		var wrapper = loadMoreBtn.parentNode;
		if (wrapper) {
			wrapper.style.display = show ? '' : 'none';
		}
	}

	function setLoadMoreLoading(loading) {
		if (!loadMoreBtn) {
			return;
		}
		if (loading) {
			loadMoreBtn.classList.add('is-loading');
			loadMoreBtn.disabled = true;
			loadMoreBtn.setAttribute('data-original-text', loadMoreBtn.textContent);
			loadMoreBtn.textContent = 'Chargement…';
		} else {
			loadMoreBtn.classList.remove('is-loading');
			loadMoreBtn.disabled = false;
			var original = loadMoreBtn.getAttribute('data-original-text');
			if (original) {
				loadMoreBtn.textContent = original;
			}
		}
	}

	/* ========================================================
	   ACTIONS
	   ======================================================== */

	function applyFilters(newFilters, pushHistory) {
		state.cat = newFilters.cat || '';
		state.tag = newFilters.tag || '';
		state.serie = newFilters.serie || '';
		state.dossier = newFilters.dossier || '';
		state.offset = 0;

		var url = buildUrl(state);
		if (pushHistory) {
			try {
				window.history.pushState({ ahub: true, filters: newFilters }, '', url);
			} catch (e) {
				// fallback silencieux
			}
		}

		updateActiveFilterLinks();

		var restUrl = buildRestUrl(state, 0, state.limit);
		if (!restUrl) {
			return;
		}
		if (grid) {
			grid.setAttribute('aria-busy', 'true');
		}
		fetchJson(restUrl, function (err, data) {
			if (grid) {
				grid.removeAttribute('aria-busy');
			}
			if (err) {
				// Dégradation : laisse le navigateur recharger si besoin.
				window.location.href = url;
				return;
			}
			setCardsHtml(data.html || '');
			state.total = data.total || 0;
			state.offset = data.rendered || 0;
			updateResultsCount(state.total);
			showLoadMore(!!data.has_more);
			if (loadMoreBtn) {
				loadMoreBtn.setAttribute('data-offset', state.offset);
			}
			// Scroll doux vers le haut de la grille
			if (grid && grid.scrollIntoView) {
				grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		});
	}

	function loadMore() {
		if (!loadMoreBtn) {
			return;
		}
		var offset = parseInt(loadMoreBtn.getAttribute('data-offset') || state.offset || 0, 10);
		if (isNaN(offset)) {
			offset = state.offset;
		}
		var restUrl = buildRestUrl(state, offset, state.limit);
		if (!restUrl) {
			return;
		}
		setLoadMoreLoading(true);
		fetchJson(restUrl, function (err, data) {
			setLoadMoreLoading(false);
			if (err) {
				return;
			}
			appendCardsHtml(data.html || '');
			var rendered = data.rendered || 0;
			state.offset = offset + rendered;
			if (loadMoreBtn) {
				loadMoreBtn.setAttribute('data-offset', state.offset);
			}
			if (!data.has_more) {
				showLoadMore(false);
			}
		});
	}

	/* ========================================================
	   EVENT HANDLERS
	   ======================================================== */

	function onFilterClick(e) {
		// Ne pas intercepter si modificateur pressé (ouverture onglet)
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
			return;
		}
		var target = e.currentTarget;
		var href = target.getAttribute('href');
		if (!href) {
			return;
		}
		e.preventDefault();
		var filters = parseUrlFilters(href);
		applyFilters(filters, true);
	}

	function onActiveChipClick(e) {
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
			return;
		}
		var target = e.currentTarget;
		var href = target.getAttribute('href');
		if (!href) {
			return;
		}
		e.preventDefault();
		var filters = parseUrlFilters(href);
		applyFilters(filters, true);
	}

	function onClearAllClick(e) {
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
			return;
		}
		e.preventDefault();
		applyFilters({ cat: '', tag: '', serie: '', dossier: '' }, true);
	}

	function onLoadMoreClick(e) {
		e.preventDefault();
		loadMore();
	}

	function onPopState() {
		var filters = parseUrlFilters(window.location.href);
		applyFilters(filters, false);
	}

	/* ========================================================
	   MOBILE ACCORDÉON
	   ======================================================== */

	function setupMobileAccordion() {
		if (!sidebar) {
			return;
		}
		var cards = $$('.ahub-sidebar-card', sidebar);
		for (var i = 0; i < cards.length; i++) {
			var card = cards[i];
			// Ouvre par défaut la première carte (Catégories)
			if (i === 0) {
				card.classList.add('is-open');
			}
			var title = $('.ahub-sidebar-title', card);
			if (!title) {
				continue;
			}
			(function (c) {
				title.addEventListener('click', function (e) {
					// Seulement en mode mobile
					if (window.innerWidth > 640) {
						return;
					}
					c.classList.toggle('is-open');
				}, false);
			})(card);
		}
	}

	/* ========================================================
	   INIT
	   ======================================================== */

	function init() {
		hub = $('.ahub');
		if (!hub) {
			return;
		}
		grid = $('#ahub-grid', hub);
		loadMoreBtn = $('#ahub-load-more-btn', hub);
		sidebar = $('.ahub-sidebar', hub);
		activeFiltersContainer = $('.ahub-active-filters', hub);
		resultsCountEl = $('.ahub-results-count', hub);

		// Lecture de l'état initial depuis l'URL
		var initial = parseUrlFilters(window.location.href);
		state.cat = initial.cat;
		state.tag = initial.tag;
		state.serie = initial.serie;
		state.dossier = initial.dossier;
		state.total = parseInt(hub.getAttribute('data-total') || '0', 10) || 0;
		state.limit = parseInt(hub.getAttribute('data-limit') || '12', 10) || 12;
		state.offset = grid ? grid.childElementCount : 0;

		// Bind filter links (sidebar)
		var filterLinks = $$('.ahub-filter-link, .ahub-filter-tag', sidebar);
		for (var i = 0; i < filterLinks.length; i++) {
			filterLinks[i].addEventListener('click', onFilterClick, false);
		}

		// Bind active filter chips (en haut de la grille)
		if (activeFiltersContainer) {
			var chips = $$('.ahub-active-chip', activeFiltersContainer);
			for (var j = 0; j < chips.length; j++) {
				chips[j].addEventListener('click', onActiveChipClick, false);
			}
			var clearAll = $('.ahub-clear-all', activeFiltersContainer);
			if (clearAll) {
				clearAll.addEventListener('click', onClearAllClick, false);
			}
		}
		// Également le clear-all du bloc empty
		var emptyClear = $('.ahub-empty .ahub-clear-all');
		if (emptyClear) {
			emptyClear.addEventListener('click', onClearAllClick, false);
		}

		// Bind load more
		if (loadMoreBtn) {
			loadMoreBtn.addEventListener('click', onLoadMoreClick, false);
		}

		// Bind popstate
		window.addEventListener('popstate', onPopState, false);

		// Mobile accordéon
		setupMobileAccordion();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init, false);
	} else {
		init();
	}
})();
