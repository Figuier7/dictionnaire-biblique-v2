<?php
/**
 * =============================================================
 *  CHANTIER B — Homepage v3
 *  À l'ombre du figuier · alombredufiguier.org
 * =============================================================
 *
 *  Contenu de ce fichier :
 *   1. Taxonomie `pilier` (Israël · l'Église · les Nations · Science · Archéologie)
 *   2. Shortcode [homepage_v3]
 *   3. Enqueue conditionnel du CSS/JS homepage v3
 *   4. Filtre admin (restriction du panneau pilier aux articles Actualité)
 *
 *  Inclusion :
 *   Ajouter en fin de functions.php :
 *     require_once get_stylesheet_directory() . '/inc/homepage-v3.php';
 *
 *  Dépendances :
 *   - Taxonomies `serie` et `dossier` (Chantier A, déjà déployées)
 *   - Catégorie WP `Actualités` (slug : actualites)
 *   - figuier_bible_get_concept_meta() défini dans functions.php principal
 *
 *  Terminologie BYM respectée dans tous les textes statiques :
 *   Yéhoshoua ha Mashiah, Elohîm, YHWH, Mashiah, Tanakh, Rouah ha Qodesh.
 *
 * =============================================================
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* =========================================================
   1. TAXONOMIE `pilier`
   ========================================================= */
function figuier_register_pilier_taxonomy() {
	$labels = array(
		'name'              => 'Piliers',
		'singular_name'     => 'Pilier',
		'search_items'      => 'Rechercher un pilier',
		'all_items'         => 'Tous les piliers',
		'edit_item'         => 'Modifier le pilier',
		'update_item'       => 'Mettre à jour le pilier',
		'add_new_item'      => 'Ajouter un nouveau pilier',
		'new_item_name'     => 'Nouveau nom de pilier',
		'menu_name'         => 'Piliers',
		'not_found'         => 'Aucun pilier trouvé.',
	);

	$args = array(
		'labels'             => $labels,
		'hierarchical'       => false,
		'public'             => true,
		'show_ui'            => true,
		'show_admin_column'  => true,
		'show_in_menu'       => true,
		'show_in_nav_menus'  => true,
		'show_in_rest'       => true,
		'query_var'          => true,
		'rewrite'            => array(
			'slug'         => 'actualites',
			'with_front'   => false,
			'hierarchical' => false,
		),
	);

	register_taxonomy( 'pilier', array( 'post' ), $args );
}
add_action( 'init', 'figuier_register_pilier_taxonomy', 0 );

/**
 * Crée les 5 termes de la taxonomie pilier s'ils n'existent pas encore.
 * Exécuté une seule fois, après enregistrement de la taxonomie.
 */
function figuier_seed_pilier_terms() {
	if ( get_option( 'figuier_pilier_seeded_v1' ) ) {
		return;
	}
	if ( ! taxonomy_exists( 'pilier' ) ) {
		return;
	}

	$terms = array(
		'israel'      => array( 'name' => 'Israël',      'slug' => 'israel',      'desc' => "Actualités touchant l'État et le peuple d'Israël, lues à la lumière des Écritures." ),
		'eglise'      => array( 'name' => "l'Église",    'slug' => 'eglise',      'desc' => "Actualités de l'Église universelle et de ses composantes, vues dans la perspective du Tanakh et des Écritures apostoliques." ),
		'nations'     => array( 'name' => 'les Nations', 'slug' => 'nations',     'desc' => "Actualités des nations, des peuples et des mouvements géopolitiques, relues bibliquement." ),
		'science'     => array( 'name' => 'Science',     'slug' => 'science',     'desc' => "Actualités scientifiques et technologiques, discernement à la lumière des Écritures." ),
		'archeologie' => array( 'name' => 'Archéologie', 'slug' => 'archeologie', 'desc' => "Découvertes archéologiques et éclairage biblique." ),
	);

	foreach ( $terms as $t ) {
		if ( ! term_exists( $t['slug'], 'pilier' ) ) {
			wp_insert_term(
				$t['name'],
				'pilier',
				array(
					'slug'        => $t['slug'],
					'description' => $t['desc'],
				)
			);
		}
	}

	update_option( 'figuier_pilier_seeded_v1', 1 );
}
add_action( 'init', 'figuier_seed_pilier_terms', 5 );


/* =========================================================
   2. ENQUEUE CONDITIONNEL — CSS/JS homepage v3
   ========================================================= */
function figuier_homepage_v3_enqueue() {
	if ( ! is_front_page() && ! is_home() ) {
		return;
	}

	$css_path = get_stylesheet_directory() . '/css/homepage-v3.css';
	$js_path  = get_stylesheet_directory() . '/js/homepage-v3.js';

	wp_enqueue_style(
		'figuier-homepage-v3',
		get_stylesheet_directory_uri() . '/css/homepage-v3.css',
		array( 'figuier-style-globals' ),
		file_exists( $css_path ) ? filemtime( $css_path ) : '1.0'
	);

	wp_enqueue_script(
		'figuier-homepage-v3',
		get_stylesheet_directory_uri() . '/js/homepage-v3.js',
		array(),
		file_exists( $js_path ) ? filemtime( $js_path ) : '1.0',
		true
	);
}
add_action( 'wp_enqueue_scripts', 'figuier_homepage_v3_enqueue', 25 );


/* =========================================================
   3. HELPERS
   ========================================================= */

/**
 * Retourne le permalien de recherche du dictionnaire.
 */
function figuier_hpv3_dictionnaire_url() {
	return home_url( '/dictionnaire-biblique/' );
}

/**
 * Concept du jour (sélection stable par date, basée sur concept-meta.json).
 * Retourne un tableau avec les clés : label, hebrew, translit, cat, excerpt, url
 * ou null si indisponible.
 */
function figuier_hpv3_concept_du_jour() {
	if ( ! function_exists( 'figuier_bible_get_concept_meta' ) ) {
		return null;
	}
	$meta = figuier_bible_get_concept_meta();
	if ( ! is_array( $meta ) || count( $meta ) === 0 ) {
		return null;
	}
	$keys      = array_keys( $meta );
	$day_index = abs( crc32( date( 'Y-m-d' ) ) ) % count( $keys );
	$day_id    = $keys[ $day_index ];
	$day       = $meta[ $day_id ];
	$slug      = ! empty( $day['u'] ) ? $day['u'] : $day_id;

	return array(
		'label'    => ! empty( $day['p'] ) ? $day['p'] : ( ! empty( $day['l'] ) ? $day['l'] : $day_id ),
		'hebrew'   => ! empty( $day['h'] ) ? $day['h'] : '',
		'translit' => ! empty( $day['t'] ) ? $day['t'] : '',
		'cat'      => ! empty( $day['c'] ) ? ucfirst( str_replace( '_', ' ', $day['c'] ) ) : '',
		'excerpt'  => ! empty( $day['e'] ) ? $day['e'] : '',
		'url'      => home_url( '/dictionnaire-biblique/' . $slug . '/' ),
	);
}

/**
 * Récupère la liste des séries (taxonomie `serie` du Chantier A)
 * et des dossiers (taxonomie `dossier`), triés par ordre manuel.
 */
function figuier_hpv3_series_dossiers() {
	$items = array();

	if ( taxonomy_exists( 'serie' ) ) {
		$series = get_terms( array(
			'taxonomy'   => 'serie',
			'hide_empty' => true,
			'orderby'    => 'meta_value_num',
			'meta_key'   => 'order',
			'order'      => 'ASC',
		) );
		// Fallback : l'orderby meta_value_num exclut silencieusement les termes
		// sans le meta `order`. Si vide ou en erreur, on relance sans tri.
		if ( is_wp_error( $series ) || empty( $series ) ) {
			$series = get_terms( array( 'taxonomy' => 'serie', 'hide_empty' => true, 'orderby' => 'name', 'order' => 'ASC' ) );
		}
		if ( is_array( $series ) ) {
			foreach ( $series as $term ) {
				$img = function_exists( 'get_term_meta' ) ? get_term_meta( $term->term_id, 'image', true ) : '';
				$items[] = array(
					'type'        => 'serie',
					'badge'       => 'Série',
					'title'       => $term->name,
					'description' => $term->description,
					'url'         => get_term_link( $term ),
					'count'       => $term->count,
					'image'       => $img,
				);
			}
		}
	}

	if ( taxonomy_exists( 'dossier' ) ) {
		$dossiers = get_terms( array(
			'taxonomy'   => 'dossier',
			'hide_empty' => true,
			'orderby'    => 'meta_value_num',
			'meta_key'   => 'order',
			'order'      => 'ASC',
		) );
		// Fallback : même bug que pour 'serie' — si pas de meta `order`, relance sans tri.
		if ( is_wp_error( $dossiers ) || empty( $dossiers ) ) {
			$dossiers = get_terms( array( 'taxonomy' => 'dossier', 'hide_empty' => true, 'orderby' => 'name', 'order' => 'ASC' ) );
		}
		if ( is_array( $dossiers ) ) {
			foreach ( $dossiers as $term ) {
				$img = function_exists( 'get_term_meta' ) ? get_term_meta( $term->term_id, 'image', true ) : '';
				$items[] = array(
					'type'        => 'dossier',
					'badge'       => 'Dossier',
					'title'       => $term->name,
					'description' => $term->description,
					'url'         => get_term_link( $term ),
					'count'       => $term->count,
					'image'       => $img,
				);
			}
		}
	}

	return $items;
}

/**
 * Retourne l'URL de la vignette d'un article pour les cartes de la homepage.
 *
 * Ordre de repli :
 *   1. Image mise en avant (featured image) si définie ;
 *   2. Première image trouvée dans le contenu de l'article
 *      (y compris figures Gutenberg et balises <img>) ;
 *   3. Chaîne vide (la carte affichera alors son fond beige).
 *
 * Le résultat est mis en cache en meta-post pour éviter de
 * scanner le contenu à chaque affichage de la homepage.
 *
 * @param int    $post_id  ID du post.
 * @param string $size     Taille WordPress demandée pour la featured image.
 * @return string          URL absolue, ou chaîne vide.
 */
function figuier_hpv3_card_image_url( $post_id, $size = 'medium_large' ) {
	if ( has_post_thumbnail( $post_id ) ) {
		$url = get_the_post_thumbnail_url( $post_id, $size );
		if ( $url ) {
			return $url;
		}
	}

	// Cache en post meta (invalidé automatiquement à chaque save_post).
	$cached = get_post_meta( $post_id, '_figuier_hpv3_fallback_img', true );
	if ( is_string( $cached ) && $cached !== '' ) {
		return $cached;
	}

	$post = get_post( $post_id );
	if ( ! $post || empty( $post->post_content ) ) {
		return '';
	}

	$content = $post->post_content;
	$found   = '';

	// 1. Cherche un bloc Gutenberg image avec attribut src.
	if ( preg_match( '/<img[^>]+src=(["\'])(.*?)\1/i', $content, $m ) ) {
		$found = html_entity_decode( $m[2], ENT_QUOTES | ENT_HTML5, 'UTF-8' );
	}

	// 2. Fallback : une URL .jpg/.png/.webp/.gif en clair (bloc image sans <img> rendu).
	if ( ! $found && preg_match( '#https?://[^\s"\'<>]+\.(?:jpe?g|png|webp|gif)#i', $content, $m2 ) ) {
		$found = $m2[0];
	}

	if ( $found ) {
		update_post_meta( $post_id, '_figuier_hpv3_fallback_img', $found );
	}

	return $found;
}

/**
 * Invalide le cache de fallback d'image quand un post est mis à jour,
 * pour que la détection re-tourne sur le nouveau contenu.
 */
function figuier_hpv3_clear_fallback_img_cache( $post_id ) {
	if ( wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) ) {
		return;
	}
	delete_post_meta( $post_id, '_figuier_hpv3_fallback_img' );
}
add_action( 'save_post', 'figuier_hpv3_clear_fallback_img_cache' );

/**
 * Liste des catégories disponibles pour le filtre des derniers articles,
 * hors catégorie `actualites`.
 */
function figuier_hpv3_categories_for_chips() {
	$all = get_categories( array(
		'hide_empty' => true,
		'orderby'    => 'name',
	) );
	$out = array();
	foreach ( $all as $c ) {
		if ( $c->slug === 'actualites' ) {
			continue;
		}
		$out[] = $c;
	}
	return $out;
}


/* =========================================================
   4. SHORTCODE [homepage_v3]
   ========================================================= */
function figuier_homepage_v3_shortcode() {
	ob_start();

	$dict_url    = figuier_hpv3_dictionnaire_url();
	$concept     = figuier_hpv3_concept_du_jour();
	$une_items   = figuier_hpv3_series_dossiers();
	$cat_chips   = figuier_hpv3_categories_for_chips();

	// Query derniers articles (hors Actualité)
	$actualite_term = get_category_by_slug( 'actualites' );
	$exclude_cat    = $actualite_term ? array( $actualite_term->term_id ) : array();

	$recent = new WP_Query( array(
		'post_type'      => 'post',
		'posts_per_page' => 9,
		'post_status'    => 'publish',
		'category__not_in' => $exclude_cat,
	) );

	// Query signes des temps (catégorie Actualité)
	$signes = new WP_Query( array(
		'post_type'      => 'post',
		'posts_per_page' => 9,
		'post_status'    => 'publish',
		'category_name'  => 'actualites',
	) );

	?>
	<div class="hpv3">

		<?php /* ============================================================
		         BLOC 1 — DICTIONNAIRE BIBLIQUE (bande compacte)
		         ============================================================ */ ?>
		<?php
		$concept_count = 0;
		if ( function_exists( 'figuier_bible_get_concept_meta' ) ) {
			$meta = figuier_bible_get_concept_meta();
			if ( is_array( $meta ) ) {
				$concept_count = count( $meta );
			}
		}
		?>
		<section class="hpv3-section hpv3-dict" aria-labelledby="hpv3-dict-title">
			<div class="hpv3-wrap">
				<a class="hpv3-dict-band" href="<?php echo esc_url( $dict_url ); ?>">
					<span class="hpv3-dict-band-icon" aria-hidden="true">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><path d="M9 6h7"/><path d="M9 10h7"/></svg>
					</span>
					<div class="hpv3-dict-band-text">
						<h2 id="hpv3-dict-title" class="hpv3-dict-band-title">Dictionnaire biblique multi-sources</h2>
						<p class="hpv3-dict-band-stats">
							<strong><?php echo number_format_i18n( $concept_count ); ?></strong> entrées
							<span class="hpv3-dict-band-sep" aria-hidden="true">·</span>
							<span class="hpv3-dict-band-sources">BYM · Easton · Smith · ISBE</span>
							<span class="hpv3-dict-band-sep" aria-hidden="true">·</span>
							<strong>3 416</strong> racines hébraïques
						</p>
					</div>
					<span class="hpv3-dict-band-arrow" aria-hidden="true">&rarr;</span>
				</a>
			</div>
		</section>

		<?php /* ============================================================
		         BLOC 2 — CONCEPT DU JOUR
		         ============================================================ */ ?>
		<?php if ( $concept ) : ?>
		<section class="hpv3-section hpv3-concept" aria-labelledby="hpv3-concept-title">
			<div class="hpv3-wrap">
				<header class="hpv3-section-header">
					<h2 id="hpv3-concept-title">Concept du jour</h2>
					<p class="hpv3-subtitle">Une notion biblique éclairée par plusieurs sources</p>
					<div class="hpv3-rule"></div>
				</header>
				<div class="hpv3-concept-card">
					<div class="hpv3-concept-header">
						<div class="hpv3-concept-title"><?php echo esc_html( $concept['label'] ); ?></div>
						<?php if ( $concept['hebrew'] ) : ?>
							<div class="hpv3-concept-hebrew" dir="rtl"><?php echo esc_html( $concept['hebrew'] ); ?></div>
						<?php endif; ?>
						<?php if ( $concept['translit'] ) : ?>
							<div class="hpv3-concept-translit"><?php echo esc_html( $concept['translit'] ); ?></div>
						<?php endif; ?>
					</div>
					<?php if ( $concept['excerpt'] ) : ?>
						<p class="hpv3-concept-excerpt"><?php echo esc_html( mb_substr( $concept['excerpt'], 0, 260 ) ); ?>&hellip;</p>
					<?php endif; ?>
					<div class="hpv3-concept-footer">
						<a href="<?php echo esc_url( $concept['url'] ); ?>" class="hpv3-btn hpv3-btn-ghost">Voir la fiche complète &rarr;</a>
					</div>
				</div>
			</div>
		</section>
		<?php endif; ?>

		<?php /* ============================================================
		         BLOC 3 — À LA UNE (Séries & Dossiers)
		         ============================================================ */ ?>
		<?php if ( ! empty( $une_items ) ) : ?>
		<section class="hpv3-section hpv3-une" aria-labelledby="hpv3-une-title">
			<div class="hpv3-wrap">
				<header class="hpv3-section-header">
					<h2 id="hpv3-une-title">À la une</h2>
					<p class="hpv3-subtitle">Séries et dossiers en cours</p>
					<div class="hpv3-rule"></div>
				</header>
				<div class="hpv3-une-grid">
					<?php foreach ( $une_items as $item ) : ?>
						<article class="hpv3-une-card hpv3-une-<?php echo esc_attr( $item['type'] ); ?>">
							<a class="hpv3-une-link" href="<?php echo esc_url( $item['url'] ); ?>">
								<div class="hpv3-une-cover"<?php if ( ! empty( $item['image'] ) ) : ?> style="background-image:url('<?php echo esc_url( $item['image'] ); ?>')"<?php endif; ?>>
									<span class="hpv3-une-badge"><?php echo esc_html( $item['badge'] ); ?><?php if ( $item['count'] ) : ?> &middot; <?php echo (int) $item['count']; ?> épisode<?php echo $item['count'] > 1 ? 's' : ''; ?><?php endif; ?></span>
								</div>
								<div class="hpv3-une-body">
									<h3><?php echo esc_html( $item['title'] ); ?></h3>
									<?php if ( $item['description'] ) : ?>
										<p><?php echo esc_html( wp_trim_words( $item['description'], 30, '…' ) ); ?></p>
									<?php endif; ?>
									<span class="hpv3-une-meta">Explorer &rarr;</span>
								</div>
							</a>
						</article>
					<?php endforeach; ?>
				</div>
			</div>
		</section>
		<?php endif; ?>

		<?php /* ============================================================
		         BLOC 4 — DERNIERS ARTICLES (grille filtrante)
		         ============================================================ */ ?>
		<?php if ( $recent->have_posts() ) : ?>
		<section class="hpv3-section hpv3-derniers" aria-labelledby="hpv3-derniers-title">
			<div class="hpv3-wrap">
				<header class="hpv3-section-header">
					<h2 id="hpv3-derniers-title">Derniers articles</h2>
					<p class="hpv3-subtitle">Édification, étude et réflexion biblique</p>
					<div class="hpv3-rule"></div>
				</header>
				<div class="hpv3-chips" id="hpv3-chips-articles" role="tablist" aria-label="Filtrer les articles par catégorie">
					<button type="button" class="hpv3-chip hpv3-chip-active" data-filter="all">Tous</button>
					<?php foreach ( $cat_chips as $c ) : ?>
						<button type="button" class="hpv3-chip" data-filter="<?php echo esc_attr( $c->slug ); ?>"><?php echo esc_html( $c->name ); ?></button>
					<?php endforeach; ?>
				</div>
				<div class="hpv3-articles-grid" id="hpv3-articles-grid">
					<?php while ( $recent->have_posts() ) : $recent->the_post();
						$post_cats = get_the_category();
						$cat_slugs = array();
						$primary_cat = '';
						foreach ( $post_cats as $pc ) {
							if ( $pc->slug !== 'actualites' ) {
								$cat_slugs[] = $pc->slug;
								if ( ! $primary_cat ) {
									$primary_cat = $pc->name;
								}
							}
						}
						$data_cats = implode( ' ', $cat_slugs );
					?>
					<?php
						$card_img_url = figuier_hpv3_card_image_url( get_the_ID(), 'medium_large' );
						$card_img_alt = the_title_attribute( array( 'echo' => false ) );
					?>
					<article class="hpv3-article-card<?php echo $card_img_url ? '' : ' hpv3-article-card-noimg'; ?>" data-cats="<?php echo esc_attr( $data_cats ); ?>">
						<a class="hpv3-article-link" href="<?php the_permalink(); ?>">
							<div class="hpv3-article-thumb">
								<?php if ( $card_img_url ) : ?>
									<img src="<?php echo esc_url( $card_img_url ); ?>" alt="<?php echo esc_attr( $card_img_alt ); ?>" loading="lazy" decoding="async" />
								<?php endif; ?>
								<?php if ( $primary_cat ) : ?>
									<span class="hpv3-article-cat"><?php echo esc_html( $primary_cat ); ?></span>
								<?php endif; ?>
							</div>
							<div class="hpv3-article-body">
								<h3><?php the_title(); ?></h3>
								<p><?php echo esc_html( wp_trim_words( get_the_excerpt(), 22, '…' ) ); ?></p>
								<div class="hpv3-article-meta"><?php echo esc_html( $primary_cat ); ?> &middot; <?php echo get_the_date( 'j M Y' ); ?></div>
							</div>
						</a>
					</article>
					<?php endwhile; wp_reset_postdata(); ?>
				</div>
			</div>
		</section>
		<?php endif; ?>

		<?php /* ============================================================
		         BLOC 5 — ACTUALITÉS & SIGNES DES TEMPS
		         ============================================================ */ ?>
		<?php if ( $signes->have_posts() ) : ?>
		<section class="hpv3-section hpv3-signes" aria-labelledby="hpv3-signes-title">
			<div class="hpv3-wrap">
				<header class="hpv3-section-header">
					<h2 id="hpv3-signes-title">Actualités &amp; signes des temps</h2>
					<p class="hpv3-subtitle">Lire l'actualité, discerner les temps</p>
					<div class="hpv3-rule"></div>
				</header>
				<div class="hpv3-chips" id="hpv3-chips-signes" role="tablist" aria-label="Filtrer par pilier">
					<button type="button" class="hpv3-chip hpv3-chip-active" data-filter="all">Tous les piliers</button>
					<button type="button" class="hpv3-chip" data-filter="israel">Israël</button>
					<button type="button" class="hpv3-chip" data-filter="eglise">l'Église</button>
					<button type="button" class="hpv3-chip" data-filter="nations">les Nations</button>
					<button type="button" class="hpv3-chip" data-filter="science">Science</button>
					<button type="button" class="hpv3-chip" data-filter="archeologie">Archéologie</button>
				</div>
				<div class="hpv3-signes-grid" id="hpv3-signes-grid">
					<?php while ( $signes->have_posts() ) : $signes->the_post();
						$piliers = get_the_terms( get_the_ID(), 'pilier' );
						$pilier_slugs = array();
						$pilier_name  = '';
						if ( $piliers && ! is_wp_error( $piliers ) ) {
							foreach ( $piliers as $p ) {
								$pilier_slugs[] = $p->slug;
								if ( ! $pilier_name ) {
									$pilier_name = $p->name;
								}
							}
						}
						$data_piliers = implode( ' ', $pilier_slugs );
					?>
					<article class="hpv3-signe-card" data-piliers="<?php echo esc_attr( $data_piliers ); ?>"<?php if ( ! empty( $pilier_slugs ) ) : ?> data-pilier="<?php echo esc_attr( $pilier_slugs[0] ); ?>"<?php endif; ?>>
						<a class="hpv3-signe-link" href="<?php the_permalink(); ?>">
							<?php if ( $pilier_name ) : ?>
								<span class="hpv3-signe-pilier"><span class="hpv3-signe-dot"></span><?php echo esc_html( $pilier_name ); ?></span>
							<?php endif; ?>
							<h3><?php the_title(); ?></h3>
							<p><?php echo esc_html( wp_trim_words( get_the_excerpt(), 26, '…' ) ); ?></p>
							<div class="hpv3-signe-meta"><?php echo get_the_date( 'j M Y' ); ?></div>
						</a>
					</article>
					<?php endwhile; wp_reset_postdata(); ?>
				</div>
			</div>
		</section>
		<?php endif; ?>

		<?php /* ============================================================
		         BLOC 6 — OUTILS D'ÉTUDE
		         ============================================================ */ ?>
		<section class="hpv3-section hpv3-outils" aria-labelledby="hpv3-outils-title">
			<div class="hpv3-wrap">
				<header class="hpv3-section-header">
					<h2 id="hpv3-outils-title">Outils d'étude</h2>
					<p class="hpv3-subtitle">Pour approfondir une notion, un mot ou un passage</p>
					<div class="hpv3-rule"></div>
				</header>
				<div class="hpv3-outils-grid">
					<a class="hpv3-outil-card" href="<?php echo esc_url( home_url( '/dictionnaire-biblique/' ) ); ?>">
						<div class="hpv3-outil-icon">
							<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
						</div>
						<h3>Recherche concept</h3>
						<p>9 876 entrées croisées entre BYM, Easton, Smith et l'ISBE.</p>
						<span class="hpv3-outil-link">Rechercher &rarr;</span>
					</a>
					<a class="hpv3-outil-card" href="<?php echo esc_url( home_url( '/lexique-hebreu-biblique/' ) ); ?>">
						<div class="hpv3-outil-icon">
							<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/></svg>
						</div>
						<h3>Lexique hébreu biblique</h3>
						<p>8 674 entrées du lexique hébreu biblique &mdash; définitions, racines, translittérations.</p>
						<span class="hpv3-outil-link">Consulter &rarr;</span>
					</a>
					<a class="hpv3-outil-card" href="<?php echo esc_url( home_url( '/lexique-hebreu-biblique/#racine=' ) ); ?>">
						<div class="hpv3-outil-icon">
							<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3v18"/><path d="M6 8h13a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6"/><path d="M6 3h9a2 2 0 0 1 2 2v3"/></svg>
						</div>
						<h3>Arbre des racines</h3>
						<p>2 658 racines hébraïques avec leurs dérivés et occurrences bibliques.</p>
						<span class="hpv3-outil-link">Explorer &rarr;</span>
					</a>
				</div>
			</div>
		</section>

		<?php /* ============================================================
		         BLOC 7 — VISION + CARTES
		         ============================================================ */ ?>
		<section class="hpv3-section hpv3-vision" aria-labelledby="hpv3-vision-title">
			<div class="hpv3-wrap">
				<header class="hpv3-section-header">
					<h2 id="hpv3-vision-title">Notre vision</h2>
					<p class="hpv3-subtitle">Une plateforme biblique sobre, gratuite, pour l'édification de tous</p>
					<div class="hpv3-rule hpv3-rule-light"></div>
				</header>
				<div class="hpv3-vision-grid">
					<div class="hpv3-vision-card">
						<h3>Soyons comme des Béréens</h3>
						<p>« Ces Juifs étaient de sentiments plus nobles que ceux de Thessalonique ; ils reçurent la parole avec beaucoup d'empressement, et ils examinaient chaque jour les Écritures, pour voir si ce qu'on leur disait était exact. » &mdash; Actes 17:11. Notre ligne éditoriale invite le lecteur à vérifier, à discerner, et à revenir aux sources.</p>
					</div>
					<div class="hpv3-vision-card">
						<h3>Gratuité du contenu</h3>
						<p>Tous les contenus publiés sur ce site &mdash; articles, ouvrages, dictionnaires, lexiques, fiches concepts &mdash; sont diffusés gratuitement à des fins d'édification, d'instruction et d'éducation, dans une logique non commerciale. <em>Vous avez reçu gratuitement, donnez gratuitement.</em> &mdash; Matthieu 10:8.</p>
					</div>
				</div>
			</div>
		</section>

	</div><!-- /.hpv3 -->
	<?php

	return ob_get_clean();
}
add_shortcode( 'homepage_v3', 'figuier_homepage_v3_shortcode' );


/* =========================================================
   5. ADMIN — Message d'aide panneau pilier
   ========================================================= */
function figuier_pilier_admin_hint( $taxonomy ) {
	if ( $taxonomy !== 'pilier' ) {
		return;
	}
	echo '<p style="max-width:720px;padding:10px 14px;background:#fff7ec;border:1px solid #e6d9c7;border-radius:6px;color:#6B4C3B;font-size:13px;">';
	echo '<strong>Usage :</strong> les piliers sont destinés aux articles de la catégorie <em>Actualité</em> (section <em>Actualités &amp; signes des temps</em> de la page d\'accueil). ';
	echo 'Affectez <strong>un seul pilier</strong> par article : Israël, l\'Église, les Nations, Science ou Archéologie.';
	echo '</p>';
}
add_action( 'pilier_pre_add_form', 'figuier_pilier_admin_hint' );
add_action( 'pilier_pre_edit_form', 'figuier_pilier_admin_hint' );

/* Fin du Chantier B */
