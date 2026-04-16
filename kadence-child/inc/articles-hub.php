<?php
/**
 * =============================================================
 *  CHANTIER ARTICLES HUB
 *  À l'ombre du figuier · alombredufiguier.org
 * =============================================================
 *
 *  Contenu de ce fichier :
 *   1. Shortcode [articles_hub] — hub éditorial filtrant pour /articles/
 *   2. REST endpoint /wp-json/figuier/v1/articles — load more + filtrage AJAX
 *   3. Enqueue conditionnel du CSS/JS sur la page Articles
 *   4. Helpers de filtrage, query, rendu de card
 *
 *  Inclusion :
 *   Ajouter en fin de functions.php :
 *     require_once get_stylesheet_directory() . '/inc/articles-hub.php';
 *
 *  Dépendances :
 *   - Taxonomies `serie` et `dossier` (Chantier A)
 *   - Catégorie `actualites` et ses 5 enfants (exclus du hub)
 *   - figuier_hpv3_card_image_url() défini dans inc/homepage-v3.php
 *
 *  Terminologie BYM respectée dans tous les textes statiques.
 *
 * =============================================================
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* =========================================================
   1. ENQUEUE CONDITIONNEL — CSS/JS articles hub
   ========================================================= */
function figuier_articles_hub_enqueue() {
	if ( ! is_page( 'articles' ) ) {
		return;
	}

	$css_path = get_stylesheet_directory() . '/css/articles-hub.css';
	$js_path  = get_stylesheet_directory() . '/js/articles-hub.js';

	wp_enqueue_style(
		'figuier-articles-hub',
		get_stylesheet_directory_uri() . '/css/articles-hub.css',
		array( 'figuier-style-globals' ),
		file_exists( $css_path ) ? filemtime( $css_path ) : '1.0'
	);

	wp_enqueue_script(
		'figuier-articles-hub',
		get_stylesheet_directory_uri() . '/js/articles-hub.js',
		array(),
		file_exists( $js_path ) ? filemtime( $js_path ) : '1.0',
		true
	);

	wp_localize_script(
		'figuier-articles-hub',
		'FiguierArticlesHub',
		array(
			'rest_url' => esc_url_raw( rest_url( 'figuier/v1/articles' ) ),
			'nonce'    => wp_create_nonce( 'wp_rest' ),
			'page_url' => esc_url_raw( home_url( '/articles/' ) ),
		)
	);
}
add_action( 'wp_enqueue_scripts', 'figuier_articles_hub_enqueue', 26 );


/* =========================================================
   2. HELPERS — Catégories, tags, séries, dossiers, queries
   ========================================================= */

/**
 * IDs des catégories à exclure systématiquement du hub :
 * Actualités + ses enfants (Israël, l'Église, Nations, Science, Archéologie).
 *
 * @return int[]
 */
function figuier_ahub_excluded_category_ids() {
	$actualites = get_category_by_slug( 'actualites' );
	if ( ! $actualites ) {
		return array();
	}
	$ids      = array( (int) $actualites->term_id );
	$children = get_term_children( $actualites->term_id, 'category' );
	if ( ! is_wp_error( $children ) && is_array( $children ) ) {
		foreach ( $children as $child_id ) {
			$ids[] = (int) $child_id;
		}
	}
	return array_unique( $ids );
}

/**
 * Catégories à afficher dans la sidebar du hub.
 * Exclut Actualités et ses enfants, ainsi que la catégorie par défaut "Uncategorized".
 *
 * @return WP_Term[]
 */
function figuier_ahub_top_categories() {
	$excluded = figuier_ahub_excluded_category_ids();
	$cats     = get_categories( array(
		'hide_empty' => true,
		'orderby'    => 'name',
		'order'      => 'ASC',
	) );
	if ( ! is_array( $cats ) ) {
		return array();
	}
	$out = array();
	foreach ( $cats as $c ) {
		if ( in_array( (int) $c->term_id, $excluded, true ) ) {
			continue;
		}
		if ( $c->slug === 'uncategorized' ) {
			continue;
		}
		$out[] = $c;
	}
	return $out;
}

/**
 * Tags les plus populaires pour la sidebar.
 *
 * @param int $limit
 * @return WP_Term[]
 */
function figuier_ahub_top_tags( $limit = 15 ) {
	$tags = get_terms( array(
		'taxonomy'   => 'post_tag',
		'hide_empty' => true,
		'orderby'    => 'count',
		'order'      => 'DESC',
		'number'     => (int) $limit,
	) );
	if ( is_wp_error( $tags ) || ! is_array( $tags ) ) {
		return array();
	}
	return $tags;
}

/**
 * Séries publiées (taxonomie `serie`).
 * Même fallback que homepage-v3 contre le bug orderby meta_value_num.
 *
 * @return WP_Term[]
 */
function figuier_ahub_series() {
	if ( ! taxonomy_exists( 'serie' ) ) {
		return array();
	}
	$terms = get_terms( array(
		'taxonomy'   => 'serie',
		'hide_empty' => true,
		'orderby'    => 'meta_value_num',
		'meta_key'   => 'order',
		'order'      => 'ASC',
	) );
	if ( is_wp_error( $terms ) || empty( $terms ) ) {
		$terms = get_terms( array(
			'taxonomy'   => 'serie',
			'hide_empty' => true,
			'orderby'    => 'name',
			'order'      => 'ASC',
		) );
	}
	if ( is_wp_error( $terms ) || ! is_array( $terms ) ) {
		return array();
	}
	return $terms;
}

/**
 * Dossiers publiés (taxonomie `dossier`).
 *
 * @return WP_Term[]
 */
function figuier_ahub_dossiers() {
	if ( ! taxonomy_exists( 'dossier' ) ) {
		return array();
	}
	$terms = get_terms( array(
		'taxonomy'   => 'dossier',
		'hide_empty' => true,
		'orderby'    => 'meta_value_num',
		'meta_key'   => 'order',
		'order'      => 'ASC',
	) );
	if ( is_wp_error( $terms ) || empty( $terms ) ) {
		$terms = get_terms( array(
			'taxonomy'   => 'dossier',
			'hide_empty' => true,
			'orderby'    => 'name',
			'order'      => 'ASC',
		) );
	}
	if ( is_wp_error( $terms ) || ! is_array( $terms ) ) {
		return array();
	}
	return $terms;
}

/**
 * Récupère les filtres actifs à partir de la requête GET ou d'un tableau d'entrée.
 *
 * @param array|null $input  Facultatif — source alternative (REST payload).
 * @return array{cat:string,tag:string,serie:string,dossier:string}
 */
function figuier_ahub_get_filters( $input = null ) {
	$source = is_array( $input ) ? $input : $_GET;
	$sanit  = function ( $key ) use ( $source ) {
		if ( ! isset( $source[ $key ] ) ) {
			return '';
		}
		$value = $source[ $key ];
		// Protection : n'accepter que des valeurs scalaires (string/int).
		// Les appels via CLI ou certains flux REST peuvent injecter des
		// objets inattendus dans les params.
		if ( ! is_scalar( $value ) ) {
			return '';
		}
		return sanitize_title( wp_unslash( (string) $value ) );
	};
	return array(
		'cat'     => $sanit( 'cat' ),
		'tag'     => $sanit( 'tag' ),
		'serie'   => $sanit( 'serie' ),
		'dossier' => $sanit( 'dossier' ),
	);
}

/**
 * Construit les arguments WP_Query à partir des filtres.
 *
 * @param array $filters  Filtres issus de figuier_ahub_get_filters().
 * @param int   $offset
 * @param int   $limit
 * @return array
 */
function figuier_ahub_build_query_args( $filters, $offset = 0, $limit = 12 ) {
	$args = array(
		'post_type'           => 'post',
		'post_status'         => 'publish',
		'posts_per_page'      => (int) $limit,
		'offset'              => (int) $offset,
		'ignore_sticky_posts' => true,
		'orderby'             => 'date',
		'order'               => 'DESC',
		'category__not_in'    => figuier_ahub_excluded_category_ids(),
	);

	$tax_query = array();

	if ( ! empty( $filters['cat'] ) ) {
		$term = get_category_by_slug( $filters['cat'] );
		if ( $term ) {
			$tax_query[] = array(
				'taxonomy' => 'category',
				'field'    => 'term_id',
				'terms'    => array( (int) $term->term_id ),
			);
		}
	}
	if ( ! empty( $filters['tag'] ) ) {
		$tax_query[] = array(
			'taxonomy' => 'post_tag',
			'field'    => 'slug',
			'terms'    => array( $filters['tag'] ),
		);
	}
	if ( ! empty( $filters['serie'] ) && taxonomy_exists( 'serie' ) ) {
		$tax_query[] = array(
			'taxonomy' => 'serie',
			'field'    => 'slug',
			'terms'    => array( $filters['serie'] ),
		);
	}
	if ( ! empty( $filters['dossier'] ) && taxonomy_exists( 'dossier' ) ) {
		$tax_query[] = array(
			'taxonomy' => 'dossier',
			'field'    => 'slug',
			'terms'    => array( $filters['dossier'] ),
		);
	}

	if ( count( $tax_query ) > 1 ) {
		$tax_query['relation'] = 'AND';
	}
	if ( ! empty( $tax_query ) ) {
		$args['tax_query'] = $tax_query;
	}

	return $args;
}

/**
 * Construit une URL /articles/ avec les filtres fournis.
 *
 * @param array $overrides  Filtres à appliquer (cat, tag, serie, dossier).
 * @return string
 */
function figuier_ahub_filter_url( $overrides = array() ) {
	$base = home_url( '/articles/' );
	$args = array();
	foreach ( array( 'cat', 'tag', 'serie', 'dossier' ) as $k ) {
		if ( isset( $overrides[ $k ] ) && $overrides[ $k ] !== '' ) {
			$args[ $k ] = $overrides[ $k ];
		}
	}
	if ( empty( $args ) ) {
		return $base;
	}
	return add_query_arg( $args, $base );
}

/**
 * Rend une carte d'article (utilisée par le rendu initial et le REST endpoint).
 *
 * @param WP_Post $post
 * @return string
 */
function figuier_ahub_render_card( $post ) {
	$post_id = (int) $post->ID;
	if ( function_exists( 'figuier_hpv3_card_image_url' ) ) {
		$img_url = figuier_hpv3_card_image_url( $post_id, 'medium_large' );
	} else {
		$img_url = get_the_post_thumbnail_url( $post_id, 'medium_large' );
		if ( ! $img_url ) {
			$img_url = '';
		}
	}

	// Catégorie primaire affichable (première hors actualités).
	$excluded_ids = figuier_ahub_excluded_category_ids();
	$primary_cat  = '';
	$primary_slug = '';
	$cat_slugs    = array();
	$cats         = get_the_category( $post_id );
	if ( is_array( $cats ) ) {
		foreach ( $cats as $c ) {
			if ( in_array( (int) $c->term_id, $excluded_ids, true ) ) {
				continue;
			}
			$cat_slugs[] = $c->slug;
			if ( ! $primary_cat ) {
				$primary_cat  = $c->name;
				$primary_slug = $c->slug;
			}
		}
	}

	// Tags pour data-attribute (utilisé par le JS pour filtrage côté client).
	$tag_slugs = array();
	$tags      = get_the_tags( $post_id );
	if ( is_array( $tags ) ) {
		foreach ( $tags as $t ) {
			$tag_slugs[] = $t->slug;
		}
	}

	$serie_slugs = array();
	if ( taxonomy_exists( 'serie' ) ) {
		$series = get_the_terms( $post_id, 'serie' );
		if ( is_array( $series ) ) {
			foreach ( $series as $s ) {
				$serie_slugs[] = $s->slug;
			}
		}
	}
	$dossier_slugs = array();
	if ( taxonomy_exists( 'dossier' ) ) {
		$dossiers = get_the_terms( $post_id, 'dossier' );
		if ( is_array( $dossiers ) ) {
			foreach ( $dossiers as $d ) {
				$dossier_slugs[] = $d->slug;
			}
		}
	}

	$title     = get_the_title( $post_id );
	$permalink = get_permalink( $post_id );
	$excerpt   = wp_trim_words( get_the_excerpt( $post_id ), 22, '…' );
	$date      = get_the_date( 'j M Y', $post_id );

	ob_start();
	?>
	<article class="ahub-card<?php echo $img_url ? '' : ' ahub-card-noimg'; ?>"
		data-cats="<?php echo esc_attr( implode( ' ', $cat_slugs ) ); ?>"
		data-tags="<?php echo esc_attr( implode( ' ', $tag_slugs ) ); ?>"
		data-serie="<?php echo esc_attr( implode( ' ', $serie_slugs ) ); ?>"
		data-dossier="<?php echo esc_attr( implode( ' ', $dossier_slugs ) ); ?>">
		<a class="ahub-card-link" href="<?php echo esc_url( $permalink ); ?>">
			<div class="ahub-card-thumb">
				<?php if ( $img_url ) : ?>
					<img src="<?php echo esc_url( $img_url ); ?>" alt="<?php echo esc_attr( $title ); ?>" loading="lazy" decoding="async" />
				<?php endif; ?>
				<?php if ( $primary_cat ) : ?>
					<span class="ahub-card-cat"><?php echo esc_html( $primary_cat ); ?></span>
				<?php endif; ?>
			</div>
			<div class="ahub-card-body">
				<h3 class="ahub-card-title"><?php echo esc_html( $title ); ?></h3>
				<?php if ( $excerpt ) : ?>
					<p class="ahub-card-excerpt"><?php echo esc_html( $excerpt ); ?></p>
				<?php endif; ?>
				<div class="ahub-card-meta">
					<?php if ( $primary_cat ) : ?>
						<span class="ahub-card-meta-cat"><?php echo esc_html( $primary_cat ); ?></span> &middot;
					<?php endif; ?>
					<span class="ahub-card-meta-date"><?php echo esc_html( $date ); ?></span>
				</div>
			</div>
		</a>
	</article>
	<?php
	return ob_get_clean();
}


/* =========================================================
   3. SHORTCODE [articles_hub]
   ========================================================= */
function figuier_articles_hub_shortcode() {
	$filters = figuier_ahub_get_filters();
	$limit   = 12;
	$args    = figuier_ahub_build_query_args( $filters, 0, $limit );
	$query   = new WP_Query( $args );

	$total     = (int) $query->found_posts;
	$has_more  = $total > $limit;

	$cats     = figuier_ahub_top_categories();
	$tags     = figuier_ahub_top_tags( 15 );
	$series   = figuier_ahub_series();
	$dossiers = figuier_ahub_dossiers();

	// Pour les chips actifs en haut de la grille.
	$active_labels = array();
	if ( $filters['cat'] ) {
		$t = get_category_by_slug( $filters['cat'] );
		if ( $t ) {
			$active_labels['cat'] = array( 'label' => $t->name, 'type' => 'Catégorie' );
		}
	}
	if ( $filters['tag'] ) {
		$t = get_term_by( 'slug', $filters['tag'], 'post_tag' );
		if ( $t ) {
			$active_labels['tag'] = array( 'label' => $t->name, 'type' => 'Tag' );
		}
	}
	if ( $filters['serie'] && taxonomy_exists( 'serie' ) ) {
		$t = get_term_by( 'slug', $filters['serie'], 'serie' );
		if ( $t ) {
			$active_labels['serie'] = array( 'label' => $t->name, 'type' => 'Série' );
		}
	}
	if ( $filters['dossier'] && taxonomy_exists( 'dossier' ) ) {
		$t = get_term_by( 'slug', $filters['dossier'], 'dossier' );
		if ( $t ) {
			$active_labels['dossier'] = array( 'label' => $t->name, 'type' => 'Dossier' );
		}
	}

	ob_start();
	?>
	<div class="ahub" data-total="<?php echo esc_attr( $total ); ?>" data-limit="<?php echo esc_attr( $limit ); ?>">
		<div class="ahub-layout">

			<?php /* =======================================================
			         SIDEBAR — filtres
			         ======================================================= */ ?>
			<aside class="ahub-sidebar" aria-label="Filtres des articles">

				<?php /* ----- CATÉGORIES ----- */ ?>
				<?php if ( ! empty( $cats ) ) : ?>
				<div class="ahub-sidebar-card">
					<h3 class="ahub-sidebar-title">Catégories</h3>
					<ul class="ahub-filter-list">
						<li>
							<a class="ahub-filter-link<?php echo empty( $filters['cat'] ) ? ' ahub-filter-link--active' : ''; ?>"
								data-filter-type="cat" data-filter-slug=""
								href="<?php echo esc_url( figuier_ahub_filter_url( array(
									'tag'     => $filters['tag'],
									'serie'   => $filters['serie'],
									'dossier' => $filters['dossier'],
								) ) ); ?>">
								Toutes
							</a>
						</li>
						<?php foreach ( $cats as $c ) : ?>
							<li>
								<a class="ahub-filter-link<?php echo ( $filters['cat'] === $c->slug ) ? ' ahub-filter-link--active' : ''; ?>"
									data-filter-type="cat" data-filter-slug="<?php echo esc_attr( $c->slug ); ?>"
									href="<?php echo esc_url( figuier_ahub_filter_url( array(
										'cat'     => $c->slug,
										'tag'     => $filters['tag'],
										'serie'   => $filters['serie'],
										'dossier' => $filters['dossier'],
									) ) ); ?>">
									<span class="ahub-filter-name"><?php echo esc_html( $c->name ); ?></span>
									<span class="ahub-filter-count"><?php echo (int) $c->count; ?></span>
								</a>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
				<?php endif; ?>

				<?php /* ----- SÉRIES ----- */ ?>
				<?php if ( ! empty( $series ) ) : ?>
				<div class="ahub-sidebar-card">
					<h3 class="ahub-sidebar-title">Séries</h3>
					<ul class="ahub-filter-list">
						<?php foreach ( $series as $s ) : ?>
							<li>
								<a class="ahub-filter-link<?php echo ( $filters['serie'] === $s->slug ) ? ' ahub-filter-link--active' : ''; ?>"
									data-filter-type="serie" data-filter-slug="<?php echo esc_attr( $s->slug ); ?>"
									href="<?php echo esc_url( figuier_ahub_filter_url( array(
										'cat'     => $filters['cat'],
										'tag'     => $filters['tag'],
										'serie'   => $s->slug,
										'dossier' => $filters['dossier'],
									) ) ); ?>">
									<span class="ahub-filter-name"><?php echo esc_html( $s->name ); ?></span>
									<span class="ahub-filter-count"><?php echo (int) $s->count; ?></span>
								</a>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
				<?php endif; ?>

				<?php /* ----- DOSSIERS ----- */ ?>
				<?php if ( ! empty( $dossiers ) ) : ?>
				<div class="ahub-sidebar-card">
					<h3 class="ahub-sidebar-title">Dossiers</h3>
					<ul class="ahub-filter-list">
						<?php foreach ( $dossiers as $d ) : ?>
							<li>
								<a class="ahub-filter-link<?php echo ( $filters['dossier'] === $d->slug ) ? ' ahub-filter-link--active' : ''; ?>"
									data-filter-type="dossier" data-filter-slug="<?php echo esc_attr( $d->slug ); ?>"
									href="<?php echo esc_url( figuier_ahub_filter_url( array(
										'cat'     => $filters['cat'],
										'tag'     => $filters['tag'],
										'serie'   => $filters['serie'],
										'dossier' => $d->slug,
									) ) ); ?>">
									<span class="ahub-filter-name"><?php echo esc_html( $d->name ); ?></span>
									<span class="ahub-filter-count"><?php echo (int) $d->count; ?></span>
								</a>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
				<?php endif; ?>

				<?php /* ----- TAGS POPULAIRES ----- */ ?>
				<?php if ( ! empty( $tags ) ) : ?>
				<div class="ahub-sidebar-card">
					<h3 class="ahub-sidebar-title">Thèmes</h3>
					<ul class="ahub-filter-list ahub-filter-list--tags">
						<?php foreach ( $tags as $t ) : ?>
							<li>
								<a class="ahub-filter-tag<?php echo ( $filters['tag'] === $t->slug ) ? ' ahub-filter-tag--active' : ''; ?>"
									data-filter-type="tag" data-filter-slug="<?php echo esc_attr( $t->slug ); ?>"
									href="<?php echo esc_url( figuier_ahub_filter_url( array(
										'cat'     => $filters['cat'],
										'tag'     => $t->slug,
										'serie'   => $filters['serie'],
										'dossier' => $filters['dossier'],
									) ) ); ?>">
									<?php echo esc_html( $t->name ); ?>
								</a>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
				<?php endif; ?>

			</aside>

			<?php /* =======================================================
			         MAIN — grille d'articles
			         ======================================================= */ ?>
			<main class="ahub-main">

				<?php /* ----- Filtres actifs (chips en haut) ----- */ ?>
				<?php if ( ! empty( $active_labels ) ) : ?>
				<div class="ahub-active-filters" role="region" aria-label="Filtres actifs">
					<span class="ahub-active-filters-label">Filtres :</span>
					<?php foreach ( $active_labels as $key => $info ) :
						$clear = $filters;
						$clear[ $key ] = '';
					?>
						<a class="ahub-active-chip" href="<?php echo esc_url( figuier_ahub_filter_url( $clear ) ); ?>" data-remove-filter="<?php echo esc_attr( $key ); ?>">
							<?php echo esc_html( $info['type'] ); ?> : <?php echo esc_html( $info['label'] ); ?>
							<span class="ahub-active-chip-x" aria-hidden="true">&times;</span>
						</a>
					<?php endforeach; ?>
					<a class="ahub-clear-all" href="<?php echo esc_url( home_url( '/articles/' ) ); ?>">Tout effacer</a>
				</div>
				<?php endif; ?>

				<?php /* ----- Compteur ----- */ ?>
				<div class="ahub-results-count">
					<?php
					if ( $total === 0 ) {
						echo 'Aucun article ne correspond à ces filtres.';
					} elseif ( $total === 1 ) {
						echo '1 article';
					} else {
						echo (int) $total . ' articles';
					}
					?>
				</div>

				<?php /* ----- Grille ----- */ ?>
				<?php if ( $query->have_posts() ) : ?>
				<div class="ahub-grid" id="ahub-grid">
					<?php
					while ( $query->have_posts() ) :
						$query->the_post();
						echo figuier_ahub_render_card( get_post() );
					endwhile;
					wp_reset_postdata();
					?>
				</div>

				<?php /* ----- Load more ----- */ ?>
				<?php if ( $has_more ) : ?>
				<div class="ahub-load-more">
					<button type="button" class="ahub-load-more-btn" id="ahub-load-more-btn" data-offset="<?php echo (int) $limit; ?>">
						Charger plus d'articles
					</button>
					<noscript>
						<a class="ahub-load-more-btn" href="<?php echo esc_url( add_query_arg( 'offset', $limit, figuier_ahub_filter_url( $filters ) ) ); ?>">
							Charger plus d'articles
						</a>
					</noscript>
				</div>
				<?php endif; ?>

				<?php else : ?>
				<div class="ahub-empty">
					<p>Aucun article à afficher pour le moment.</p>
					<?php if ( ! empty( $active_labels ) ) : ?>
						<p><a class="ahub-clear-all" href="<?php echo esc_url( home_url( '/articles/' ) ); ?>">Effacer les filtres</a></p>
					<?php endif; ?>
				</div>
				<?php endif; ?>

			</main>

		</div><!-- /.ahub-layout -->
	</div><!-- /.ahub -->
	<?php
	return ob_get_clean();
}
add_shortcode( 'articles_hub', 'figuier_articles_hub_shortcode' );


/* =========================================================
   4. REST ENDPOINT — /wp-json/figuier/v1/articles
   ========================================================= */
function figuier_ahub_register_rest_routes() {
	register_rest_route( 'figuier/v1', '/articles', array(
		'methods'             => 'GET',
		'callback'            => 'figuier_ahub_rest_articles',
		'permission_callback' => '__return_true',
		'args'                => array(
			'cat'     => array( 'type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_title' ),
			'tag'     => array( 'type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_title' ),
			'serie'   => array( 'type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_title' ),
			'dossier' => array( 'type' => 'string', 'default' => '', 'sanitize_callback' => 'sanitize_title' ),
			'offset'  => array( 'type' => 'integer', 'default' => 0 ),
			'limit'   => array( 'type' => 'integer', 'default' => 12 ),
		),
	) );
}
add_action( 'rest_api_init', 'figuier_ahub_register_rest_routes' );

/**
 * Callback REST — retourne HTML des cards + métadonnées pagination.
 *
 * @param WP_REST_Request $request
 * @return WP_REST_Response
 */
function figuier_ahub_rest_articles( $request ) {
	// Coerce vers string : certains flux REST (CLI, tests) peuvent renvoyer null.
	$get = function ( $key ) use ( $request ) {
		$v = $request->get_param( $key );
		if ( is_null( $v ) || is_object( $v ) || is_array( $v ) ) {
			return '';
		}
		return (string) $v;
	};
	$filters = figuier_ahub_get_filters( array(
		'cat'     => $get( 'cat' ),
		'tag'     => $get( 'tag' ),
		'serie'   => $get( 'serie' ),
		'dossier' => $get( 'dossier' ),
	) );
	$offset = max( 0, (int) $request->get_param( 'offset' ) );
	$limit  = max( 1, min( 50, (int) $request->get_param( 'limit' ) ) );

	$args  = figuier_ahub_build_query_args( $filters, $offset, $limit );
	$query = new WP_Query( $args );

	$html = '';
	if ( $query->have_posts() ) {
		while ( $query->have_posts() ) {
			$query->the_post();
			$html .= figuier_ahub_render_card( get_post() );
		}
		wp_reset_postdata();
	}

	$total    = (int) $query->found_posts;
	$has_more = ( $offset + $query->post_count ) < $total;

	return new WP_REST_Response( array(
		'html'     => $html,
		'has_more' => (bool) $has_more,
		'total'    => $total,
		'rendered' => (int) $query->post_count,
		'offset'   => $offset,
	), 200 );
}

/* Fin du Chantier Articles Hub */
