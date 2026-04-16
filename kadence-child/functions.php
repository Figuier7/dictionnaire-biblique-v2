<?php
/**
 * Kadence Child — À l'ombre du figuier
 * - Styles globaux dans /css/style-globals.css
 * - Grilles/Carrousels/Swiper dans /css/figuier-grilles-carrousels.css
 * - Init Swiper dans /js/swiper-init.js
 *
 * Notes importantes :
 * - Le rognage des images venait du hard-crop (add_image_size(..., true)).
 *   Ici, on passe le crop à false + on sert une taille non-cropée côté frontend.
 * - Après changement de tailles d’images, il faut régénérer les miniatures WP.
 */

/* =========================================================
   ENQUEUE ASSETS (CSS/JS)
   ========================================================= */
function figuier_enqueue_assets() {

	// Parent + child (Kadence)
	if ( ! wp_style_is( 'kadence-parent-style', 'enqueued' ) ) {
		wp_enqueue_style( 'kadence-parent-style', get_template_directory_uri() . '/style.css' );
	}

	if ( ! wp_style_is( 'kadence-child-style', 'enqueued' ) ) {
		wp_enqueue_style( 'kadence-child-style', get_stylesheet_uri(), array( 'kadence-parent-style' ) );
	}

	// CSS globals (variables + styles généraux)
	$globals_path = get_stylesheet_directory() . '/css/style-globals.css';
	wp_enqueue_style(
		'figuier-style-globals',
		get_stylesheet_directory_uri() . '/css/style-globals.css',
		array( 'kadence-child-style' ),
		file_exists( $globals_path ) ? filemtime( $globals_path ) : '1.0'
	);

	// Swiper CSS (CDN) — version fixée pour stabilité cache
	wp_enqueue_style(
		'swiper-css',
		'https://cdn.jsdelivr.net/npm/swiper@9/swiper-bundle.min.css',
		array(),
		'9.4.1'
	);

	// CSS grilles/carrousels (doit dépendre des globals + swiper)
	$carrousels_path = get_stylesheet_directory() . '/css/figuier-grilles-carrousels.css';
	wp_enqueue_style(
		'figuier-grilles-carrousels',
		get_stylesheet_directory_uri() . '/css/figuier-grilles-carrousels.css',
		array( 'figuier-style-globals', 'swiper-css' ),
		file_exists( $carrousels_path ) ? filemtime( $carrousels_path ) : '1.0'
	);

	// Swiper JS (CDN) — version fixée
	wp_enqueue_script(
		'swiper-js',
		'https://cdn.jsdelivr.net/npm/swiper@9/swiper-bundle.min.js',
		array(),
		'9.4.1',
		true
	);

	// Init Swiper (local) — dépend de swiper-js
	$swiper_init_path = get_stylesheet_directory() . '/js/swiper-init.js';
	wp_enqueue_script(
		'figuier-swiper-init',
		get_stylesheet_directory_uri() . '/js/swiper-init.js',
		array( 'swiper-js' ),
		file_exists( $swiper_init_path ) ? filemtime( $swiper_init_path ) : '1.0',
		true
	);
}
add_action( 'wp_enqueue_scripts', 'figuier_enqueue_assets', 20 );


/* =========================================================
   GOOGLE FONTS
   ========================================================= */
function figuier_enqueue_google_fonts() {
	wp_enqueue_style(
		'figuier-google-fonts',
		'https://fonts.googleapis.com/css2?family=EB+Garamond&family=Inter:wght@400;500;600&display=swap',
		array(),
		null
	);
}
add_action( 'wp_enqueue_scripts', 'figuier_enqueue_google_fonts', 21 );


/* =========================================================
   THEME SUPPORT + IMAGE SIZES
   ========================================================= */
add_action( 'after_setup_theme', function () {
	add_theme_support( 'post-thumbnails' );

	/**
	 * ✅ vignette homepage 16:9 SANS rognage
	 * IMPORTANT : après ce changement, régénérer les miniatures WP
	 */
	add_image_size( 'figuier_thumb_16_9', 800, 450, false );
} );


/* =========================================================
   HELPERS
   ========================================================= */

/**
 * Retourne une URL d'image NON rognée (priorité à large).
 * On évite volontairement de servir en priorité un format custom potentiellement ancien/cropé.
 */
function figuier_get_image() {
	if ( has_post_thumbnail() ) {

		// Priorité : tailles WP non-cropées (selon thème/config)
		$img = get_the_post_thumbnail_url( get_the_ID(), 'large' );
		if ( $img ) return $img;

		$img = get_the_post_thumbnail_url( get_the_ID(), 'medium_large' );
		if ( $img ) return $img;

		// Dernier recours : full
		$img = get_the_post_thumbnail_url( get_the_ID(), 'full' );
		if ( $img ) return $img;
	}

	return '';
}


/* =========================================================
   SECTION RENDER (GRILLE ou SWIPER)
   ========================================================= */
function figuier_render_section( $args, $titre, $lien_voir_tout, $style = 'grille' ) {

	$query = new WP_Query( $args );
	if ( ! $query->have_posts() ) {
		return '';
	}

	ob_start();

	// ✅ Un SEUL wrapper de section
	echo '<section class="homepage-latest figuier-section">';
	echo '<h2>' . esc_html( $titre ) . '</h2>';

	if ( $style === 'carrousel' ) {
		// ✅ HTML Swiper (structure correcte)
		echo '<div class="swiper figuier-swiper" aria-label="' . esc_attr( $titre ) . '">';
		echo '<div class="swiper-wrapper">';
	} else {
		echo '<div class="figuier-latest-items">';
	}

	while ( $query->have_posts() ) : $query->the_post();

		$post_id    = get_the_ID();
		$image_url  = figuier_get_image();
		$permalink  = get_permalink();
		$post_title = get_the_title();

		$item_class = ( $style === 'carrousel' ) ? 'swiper-slide figuier-card' : 'figuier-item';
		?>
		<article class="<?php echo esc_attr( $item_class ); ?>">

			<?php if ( $image_url ) : ?>
				<div class="figuier-thumb">
					<a href="<?php echo esc_url( $permalink ); ?>">
						<img
							src="<?php echo esc_url( $image_url ); ?>"
							alt="<?php echo esc_attr( $post_title ); ?>"
							loading="lazy"
							decoding="async"
						/>
					</a>
				</div>
			<?php endif; ?>

			<h3>
				<a href="<?php echo esc_url( $permalink ); ?>">
					<?php echo esc_html( $post_title ); ?>
				</a>
			</h3>

			<?php
				// ✅ Temps de lecture (badge unique, cohérent avec style-globals.css)
				echo '<div class="figuier-meta-row figuier-meta-row--card">' . figuier_reading_time_markup( $post_id ) . '</div>';
			?>

			<p class="excerpt">
				<?php echo esc_html( wp_trim_words( get_the_excerpt(), 20, '...' ) ); ?>
			</p>

		</article>
		<?php
	endwhile;

	// Fermetures + navigation Swiper
	if ( $style === 'carrousel' ) {
		echo '</div>'; // .swiper-wrapper
		echo '<div class="swiper-button-prev" aria-label="Précédent"></div>';
		echo '<div class="swiper-button-next" aria-label="Suivant"></div>';
		echo '<div class="swiper-pagination" aria-hidden="true"></div>'; // ✅ utile mobile
		echo '</div>'; // .swiper
	} else {
		echo '</div>'; // .figuier-latest-items
	}

	// Bouton Voir tout
	echo '<div class="voir-tout-container">';
	echo '<a class="btn-voir-tout" href="' . esc_url( $lien_voir_tout ) . '">Voir tout</a>';
	echo '</div>';

	echo '</section>';

	wp_reset_postdata();

	return ob_get_clean();
}


/* =========================================================
   SHORTCODE HOMEPAGE
   ========================================================= */
function figuier_homepage_custom_shortcode() {
	ob_start();

	// ✅ Bloc Outils — PAS de figuier-section ici (évite double padding)
	echo '<section class="tools-block" aria-labelledby="tools-block-title">';
	echo '  <h2 id="tools-block-title">' . esc_html( "Outils d’étude biblique" ) . '</h2>';
	echo '  <p>' . esc_html( "Explorez nos dictionnaires, encyclopédies, cartes et illustrations bibliques pour enrichir votre compréhension des Écritures." ) . '</p>';
	echo '  <div class="voir-tout-container tools-cta">';
	echo '    <a class="btn-voir-tout" href="' . esc_url( home_url( '/ressources-bibliques/' ) ) . '">Découvrir les outils</a>';
	echo '  </div>';
	echo '</section>';

	// Études bibliques
	echo figuier_render_section(
		array( 'post_type' => 'post', 'posts_per_page' => 6, 'category_name' => 'etude-biblique' ),
		'Études bibliques',
		esc_url( home_url( '/category/etude-biblique' ) ),
		'carrousel'
	);

	// Méditations
	echo figuier_render_section(
		array( 'post_type' => 'post', 'posts_per_page' => 6, 'category_name' => 'meditation' ),
		'Méditations & Exhortations',
		esc_url( home_url( '/category/meditation' ) ),
		'carrousel'
	);

	// Société & culture
	echo figuier_render_section(
		array( 'post_type' => 'post', 'posts_per_page' => 6, 'category_name' => 'societe-culture' ),
		'Société & culture',
		esc_url( home_url( '/category/societe-culture' ) ),
		'carrousel'
	);

	// Histoire & contextes
	echo figuier_render_section(
		array( 'post_type' => 'post', 'posts_per_page' => 6, 'category_name' => 'histoire' ),
		'Histoire & contextes',
		esc_url( home_url( '/category/histoire' ) ),
		'carrousel'
	);

	// Témoignages & Réveils
	echo figuier_render_section(
		array( 'post_type' => 'post', 'posts_per_page' => 6, 'category_name' => 'temoignages-reveils' ),
		'Témoignages & Réveils',
		esc_url( home_url( '/category/temoignages-reveils' ) ),
		'carrousel'
	);

	// Dernières actualités
	echo figuier_render_section(
		array( 'post_type' => 'post', 'posts_per_page' => 6, 'category_name' => 'actualites' ),
		'Dernières actualités',
		esc_url( home_url( '/category/actualites' ) ),
		'carrousel'
	);

	// Podcasts
	echo figuier_render_section(
		array( 'post_type' => 'podcast', 'posts_per_page' => 6 ),
		'Podcasts récents',
		esc_url( home_url( '/podcasts' ) ),
		'carrousel'
	);

	return ob_get_clean();
}
add_shortcode( 'homepage_custom', 'figuier_homepage_custom_shortcode' );


/* =========================================================
   HOMEPAGE V2 — Layout 2 colonnes (main + sidebar)
   ========================================================= */
function figuier_homepage_v2_shortcode() {
	ob_start();
	$meta = figuier_bible_get_concept_meta();
	$concept_count = is_array( $meta ) ? count( $meta ) : 9876;
	?>

	<!-- Layout 2 colonnes -->
	<div class="hp-layout">

		<!-- Colonne principale -->
		<div class="hp-main">

			<!-- Outils -->
			<section class="hp-tools" aria-label="Outils">
				<h2 class="hp-section-title">Outils d'&eacute;tude biblique</h2>
				<div class="hp-tools__grid">
					<a href="<?php echo esc_url( home_url( '/dictionnaire-biblique/' ) ); ?>" class="hp-tool-card">
						<span class="hp-tool-card__num"><?php echo number_format_i18n( $concept_count ); ?> <small>concepts</small></span>
						<span class="hp-tool-card__title">Dictionnaire biblique</span>
						<span class="hp-tool-card__desc">Explorez les personnages, lieux, doctrines et termes bibliques.</span>
					</a>
					<a href="<?php echo esc_url( home_url( '/lexique-hebreu-biblique/' ) ); ?>" class="hp-tool-card">
						<span class="hp-tool-card__num">8 674 <small>mots h&eacute;breux</small></span>
						<span class="hp-tool-card__title">Lexique h&eacute;breu biblique</span>
						<span class="hp-tool-card__desc">D&eacute;finitions, racines et occurrences dans le texte h&eacute;breu des &Eacute;critures.</span>
					</a>
				</div>
			</section>

			<?php
			// Concept du jour
			if ( is_array( $meta ) && count( $meta ) > 0 ) {
				$keys = array_keys( $meta );
				$day_index = crc32( date( 'Y-m-d' ) ) % count( $keys );
				$day_id = $keys[ abs( $day_index ) ];
				$day = $meta[ $day_id ];
				$day_label = ! empty( $day['p'] ) ? $day['p'] : $day['l'];
				$day_cat = ucfirst( str_replace( '_', ' ', $day['c'] ) );
				$day_excerpt = ! empty( $day['e'] ) ? $day['e'] : '';
				$day_slug = ! empty( $day['u'] ) ? $day['u'] : $day_id;
				?>
				<section class="hp-concept-day" aria-label="Concept du jour">
					<h2 class="hp-section-title">Concept du jour</h2>
					<div class="hp-concept-day__card">
						<span class="hp-concept-day__cat"><?php echo esc_html( $day_cat ); ?></span>
						<h3 class="hp-concept-day__title"><?php echo esc_html( $day_label ); ?></h3>
						<?php if ( $day_excerpt ) : ?>
							<p class="hp-concept-day__excerpt"><?php echo esc_html( mb_substr( $day_excerpt, 0, 180 ) ); ?>&hellip;</p>
						<?php endif; ?>
						<a href="<?php echo esc_url( home_url( '/dictionnaire-biblique/' . $day_slug . '/' ) ); ?>" class="hp-concept-day__link">Explorer &rarr;</a>
					</div>
				</section>
			<?php } ?>

			<?php
			// Derniers articles
			$recent = new WP_Query( array( 'post_type' => 'post', 'posts_per_page' => 6, 'post_status' => 'publish' ) );
			if ( $recent->have_posts() ) : ?>
			<section class="hp-articles" aria-label="Derniers articles">
				<h2 class="hp-section-title">Derniers articles</h2>
				<div class="hp-articles__grid">
					<?php while ( $recent->have_posts() ) : $recent->the_post(); ?>
						<a href="<?php the_permalink(); ?>" class="hp-article-card">
							<?php if ( has_post_thumbnail() ) : ?>
								<div class="hp-article-card__img"><?php the_post_thumbnail( 'medium' ); ?></div>
							<?php endif; ?>
							<span class="hp-article-card__cat"><?php $cats = get_the_category(); if ( $cats ) echo esc_html( $cats[0]->name ); ?></span>
							<h3 class="hp-article-card__title"><?php the_title(); ?></h3>
						</a>
					<?php endwhile; ?>
				</div>
			</section>
			<?php wp_reset_postdata(); endif; ?>

			<!-- Vision -->
			<section class="hp-vision" aria-label="Notre vision">
				<h2 class="hp-section-title">Notre vision</h2>
				<p>Diffuser gratuitement des ressources bibliques et th&eacute;ologiques utiles &agrave; l'&eacute;dification, &agrave; l'&eacute;tude et &agrave; la compr&eacute;hension des &Eacute;critures.</p>
				<a href="<?php echo esc_url( home_url( '/vision/' ) ); ?>" class="hp-vision__link">D&eacute;couvrir notre vision &rarr;</a>
			</section>

		</div><!-- .hp-main -->

		<!-- Sidebar droite -->
		<aside class="hp-sidebar">

			<!-- Arbre des racines (lien rapide) -->
			<div class="hp-sidebar-card">
				<h3>Arbre des racines</h3>
				<p>D&eacute;couvrez les 2 658 familles s&eacute;mantiques h&eacute;bra&iuml;ques et leurs d&eacute;riv&eacute;s.</p>
				<a href="<?php echo esc_url( home_url( '/lexique-hebreu-biblique/#racine=' ) ); ?>">Explorer l'arbre &rarr;</a>
			</div>

			<!-- Bible BYM -->
			<div class="hp-sidebar-card">
				<h3>Bible de Yehoshoua</h3>
				<p>Lisez les &Eacute;critures dans la version BYM avec les noms restaur&eacute;s.</p>
				<a href="https://www.bibledeyehoshouahamashiah.org/lire.html" target="_blank" rel="noopener">Lire la BYM &rarr;</a>
			</div>

			<?php
			// Articles aleatoires
			$random_posts = new WP_Query( array( 'post_type' => 'post', 'posts_per_page' => 4, 'orderby' => 'rand', 'post_status' => 'publish' ) );
			if ( $random_posts->have_posts() ) : ?>
			<div class="hp-sidebar-card hp-sidebar-card--articles">
				<h3>Articles &agrave; d&eacute;couvrir</h3>
				<?php while ( $random_posts->have_posts() ) : $random_posts->the_post(); ?>
					<a href="<?php the_permalink(); ?>" class="hp-sidebar-article">
						<span class="hp-sidebar-article__cat"><?php $cats = get_the_category(); if ( $cats ) echo esc_html( $cats[0]->name ); ?></span>
						<span class="hp-sidebar-article__title"><?php the_title(); ?></span>
					</a>
				<?php endwhile; ?>
			</div>
			<?php wp_reset_postdata(); endif; ?>

			<!-- Editeur BYM -->
			<div class="hp-sidebar-card">
				<h3>&Eacute;diteur biblique BYM</h3>
				<p>Ins&eacute;rez des versets BYM dans vos documents Google Docs.</p>
				<a href="<?php echo esc_url( home_url( '/editeur-biblique-bym/' ) ); ?>">En savoir plus &rarr;</a>
			</div>

		</aside><!-- .hp-sidebar -->

	</div><!-- .hp-layout -->
	<?php
	return ob_get_clean();
}
add_shortcode( 'homepage_v2', 'figuier_homepage_v2_shortcode' );


/* =========================================================
   UPLOAD JSON (Media Library)
   ========================================================= */
function autoriser_json_upload( $mimes ) {
	$mimes['json'] = 'application/json';
	return $mimes;
}
add_filter( 'upload_mimes', 'autoriser_json_upload' );


/* =========================================================
   DICTIONNAIRE — enqueue uniquement si shortcode présent
   ========================================================= */
function dictionnaire_enqueue_assets() {
	global $post;

	if ( isset( $post->post_content ) && has_shortcode( $post->post_content, 'dictionnaire_interactif' ) ) {

		$dict_css_path = get_stylesheet_directory() . '/css/dictionnaire-style-unifiee.css';
		wp_enqueue_style(
			'dictionnaire-style-unifiee',
			get_stylesheet_directory_uri() . '/css/dictionnaire-style-unifiee.css',
			array(),
			file_exists( $dict_css_path ) ? filemtime( $dict_css_path ) : '1.0',
			'all'
		);

		wp_enqueue_script(
			'marked-js',
			'https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js',
			array(),
			null,
			true
		);

		$dict_js_path = get_stylesheet_directory() . '/js/interface-unifiee.js';
		wp_enqueue_script(
			'interface-unifiee',
			get_stylesheet_directory_uri() . '/js/interface-unifiee.js',
			array( 'marked-js' ),
			file_exists( $dict_js_path ) ? filemtime( $dict_js_path ) : '1.0',
			true
		);
	}
}
add_action( 'wp_enqueue_scripts', 'dictionnaire_enqueue_assets' );


/* =========================================================
   SHORTCODE [dictionnaire_interactif]
   ========================================================= */
function afficher_dictionnaire_interactif() {
	ob_start();
	?>
	<div id="dictionnaire-app" class="figuier-dict-ui">

		<nav id="dictionary-tabs" class="dict-tabs">
			<button data-dict="BYM" class="dict-tab active">BYM</button>
			<button data-dict="Easton" class="dict-tab">Easton</button>
			<button data-dict="Smith" class="dict-tab">Smith</button>
			<button data-dict="Watson" class="dict-tab">Watson</button>
		</nav>

		<div id="dictionary-description" class="dictionary-note">
			<p><strong>Dictionnaire biblique de la BYM :</strong> Lexique original publié par la Bible de Yéhoshoua ha Mashiah (BYM). Domaine public sous licence interne BYM.</p>
		</div>

		<div class="dict-interface">
			<aside class="dict-panel-left">
				<input type="text" id="dictionary-search" placeholder="🔍 Rechercher un mot..." />
				<div id="alphabet-selector" class="alphabet-buttons"></div>
				<div id="word-list" class="word-list"></div>
			</aside>

			<main id="dictionary-content" class="dict-definition"></main>
		</div>
	</div>
	<?php
	return ob_get_clean();
}
add_shortcode( 'dictionnaire_interactif', 'afficher_dictionnaire_interactif' );


/* =========================================================
   SHORTCODE [encyclopedie_biblique]
   ========================================================= */
function figuier_encyclopedie_enqueue() {
	global $post;
	if ( ! isset( $post->post_content ) || ! has_shortcode( $post->post_content, 'encyclopedie_biblique' ) ) {
		return;
	}
	$css_path = get_stylesheet_directory() . '/css/encyclopedie-style.css';
	wp_enqueue_style(
		'figuier-encyclopedie-style',
		get_stylesheet_directory_uri() . '/css/encyclopedie-style.css',
		array( 'figuier-style-globals' ),
		file_exists( $css_path ) ? filemtime( $css_path ) : '1.0'
	);

	$js_path = get_stylesheet_directory() . '/js/encyclopedie-app.js';
	wp_enqueue_script(
		'figuier-encyclopedie-app',
		get_stylesheet_directory_uri() . '/js/encyclopedie-app.js',
		array(),
		file_exists( $js_path ) ? filemtime( $js_path ) : '1.0',
		true
	);

	wp_localize_script( 'figuier-encyclopedie-app', 'figuierEncycConfig', array(
		'manifestUrl' => content_url( 'uploads/dictionnaires/source-manifest.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/source-manifest.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/source-manifest.json' ) : '1' ),
		'dictBaseUrl'  => home_url( '/dictionnaire-biblique/' ),
		'slugsUrl'     => content_url( 'uploads/dictionnaires/concept-url-slugs.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/concept-url-slugs.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/concept-url-slugs.json' ) : '1' ),
	));
}
add_action( 'wp_enqueue_scripts', 'figuier_encyclopedie_enqueue' );

function afficher_encyclopedie_biblique() {
	ob_start();
	?>
	<div id="encyclopedie-app" class="figuier-encyc-ui">
		<noscript>
			<p>L'encyclopédie biblique nécessite JavaScript pour fonctionner.</p>
			<p><a href="<?php echo esc_url( home_url( '/dictionnaire-biblique/' ) ); ?>">Accéder au dictionnaire biblique</a></p>
		</noscript>
	</div>
	<?php
	return ob_get_clean();
}
add_shortcode( 'encyclopedie_biblique', 'afficher_encyclopedie_biblique' );


/* =========================================================
   SHORTCODE [lexique_strong_bdb]
   ========================================================= */
function figuier_lexique_strong_enqueue() {
	global $post;
	if ( ! isset( $post->post_content ) || ! has_shortcode( $post->post_content, 'lexique_strong_bdb' ) ) {
		return;
	}
	$css_path = get_stylesheet_directory() . '/css/lexique-strong-style.css';
	wp_enqueue_style(
		'figuier-lexique-strong-style',
		get_stylesheet_directory_uri() . '/css/lexique-strong-style.css',
		array( 'figuier-style-globals' ),
		file_exists( $css_path ) ? filemtime( $css_path ) : '1.0'
	);

	// CSS V3 interface (pour les .fb-verse-bubble stylees)
	$v3_css_path = get_stylesheet_directory() . '/css/bible-v3-interface.css';
	wp_enqueue_style(
		'figuier-bible-v3-style',
		get_stylesheet_directory_uri() . '/css/bible-v3-interface.css',
		array( 'figuier-style-globals' ),
		file_exists( $v3_css_path ) ? filemtime( $v3_css_path ) : '1.0'
	);
	wp_enqueue_style(
		'figuier-hebrew-font',
		'https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@400;700&display=swap',
		array(),
		null
	);

	// Stack V3 pour que les verse bubbles fonctionnent aussi sur la page lexique
	wp_enqueue_script( 'marked-js', 'https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js', array(), null, true );
	$v2_js_path = get_stylesheet_directory() . '/js/bible-v2-app.js';
	wp_enqueue_script( 'figuier-bible-v2-app', get_stylesheet_directory_uri() . '/js/bible-v2-app.js', array( 'marked-js' ),
		file_exists( $v2_js_path ) ? filemtime( $v2_js_path ) : '1.0', true );
	$v3_js_path = get_stylesheet_directory() . '/js/bible-v3-patch.js';
	wp_enqueue_script( 'figuier-bible-v3-patch', get_stylesheet_directory_uri() . '/js/bible-v3-patch.js', array( 'figuier-bible-v2-app' ),
		file_exists( $v3_js_path ) ? filemtime( $v3_js_path ) : '1.0', true );

	// Config minimale pour que showVerseBubble fetch correctement les versets BYM
	// bymProxyUrl = admin-ajax.php (hook WP AJAX `figuier_bym_proxy`), comme pour v2-app
	wp_localize_script( 'figuier-bible-v2-app', 'FIGUIER_BIBLE_V2_CONFIG', array(
		'bymSourceBase'    => 'https://gitlab.com/anjc/bjc-source/-/raw/master',
		'bymProxyUrl'      => admin_url( 'admin-ajax.php' ),
		'bymReaderBase'    => 'https://www.bibledeyehoshouahamashiah.org/lire.html',
		'mobileBreakpoint' => 900,
	));

	$js_path = get_stylesheet_directory() . '/js/lexique-strong-app.js';
	wp_enqueue_script(
		'figuier-lexique-strong-app',
		get_stylesheet_directory_uri() . '/js/lexique-strong-app.js',
		array( 'figuier-bible-v3-patch' ),
		file_exists( $js_path ) ? filemtime( $js_path ) : '1.0',
		true
	);

	wp_localize_script( 'figuier-lexique-strong-app', 'figuierLexiqueConfig', array(
		'lexiconUrl'   => content_url( 'uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json' ),
		'dictBaseUrl'  => home_url( '/dictionnaire-biblique/' ),
		'slugsUrl'     => content_url( 'uploads/dictionnaires/concept-url-slugs.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/concept-url-slugs.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/concept-url-slugs.json' ) : '1' ),
		'manifestUrl'  => content_url( 'uploads/dictionnaires/source-manifest.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/source-manifest.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/source-manifest.json' ) : '1' ),
		'concordanceUrl' => content_url( 'uploads/dictionnaires/strong-concordance-oshb.json' ),
	));
}
add_action( 'wp_enqueue_scripts', 'figuier_lexique_strong_enqueue' );


/* =========================================================
   CRON QUOTIDIEN — purge cache pour rafraîchir le concept du jour
   (calculé via crc32(date('Y-m-d')) sur homepage-v3.php + functions.php)
   Sans cette purge, la homepage cachée par LiteSpeed peut garder la
   même entrée "concept du jour" pendant plusieurs jours.
   ========================================================= */
function figuier_daily_purge_hook() {
	// Purge LiteSpeed (toutes pages + assets optimisés)
	if ( defined( 'LSCWP_V' ) || class_exists( '\LiteSpeed\Purge' ) ) {
		do_action( 'litespeed_purge_all' );
	}
	// Purge cache objet WP (transients, etc.)
	if ( function_exists( 'wp_cache_flush' ) ) {
		wp_cache_flush();
	}
}
add_action( 'figuier_daily_purge', 'figuier_daily_purge_hook' );

function figuier_daily_purge_schedule() {
	if ( ! wp_next_scheduled( 'figuier_daily_purge' ) ) {
		// 1ère execution : demain à 03h00 (heure serveur UTC → ~04h/05h locale FR)
		wp_schedule_event( strtotime( 'tomorrow 03:00:00' ), 'daily', 'figuier_daily_purge' );
	}
}
add_action( 'init', 'figuier_daily_purge_schedule' );

// Nettoyage si plugin desactive (best-effort, ne plante pas si deja absent)
register_deactivation_hook( __FILE__, function () {
	$ts = wp_next_scheduled( 'figuier_daily_purge' );
	if ( $ts ) wp_unschedule_event( $ts, 'figuier_daily_purge' );
});

function afficher_lexique_strong_bdb() {
	ob_start();
	?>
	<div id="lexique-strong-app" class="figuier-lexique-ui">
		<noscript>
			<p>Le lexique hébreu biblique nécessite JavaScript pour fonctionner.</p>
			<p><a href="<?php echo esc_url( home_url( '/dictionnaire-biblique/' ) ); ?>">Accéder au dictionnaire biblique</a></p>
		</noscript>
	</div>
	<p class="fig-lexique-sources">
		<strong>Sources&nbsp;:</strong>
		Brown-Driver-Briggs (BDB) · Open Scriptures Hebrew Bible (OSHB) · Numérotation Strong ·
		<a href="<?php echo esc_url( home_url( '/a-propos-du-lexique-hebreu-biblique/' ) ); ?>">En savoir plus</a>
	</p>
	<?php
	return ob_get_clean();
}
add_shortcode( 'lexique_strong_bdb', 'afficher_lexique_strong_bdb' );


/* =========================================================
   PROXY BYM — fichier separe pour isoler les erreurs
   ========================================================= */
require_once get_stylesheet_directory() . '/bym-proxy.php';


/* =========================================================
   BIBLE INTERFACE V2 — enqueue uniquement si shortcode present
   ========================================================= */
function figuier_bible_v2_should_enqueue() {
	global $post;

	return isset( $post->post_content ) && has_shortcode( $post->post_content, 'bible_interface_v2' );
}

function figuier_bible_v2_enqueue_assets() {
	if ( ! figuier_bible_v2_should_enqueue() ) {
		return;
	}

	$v3_css_path = get_stylesheet_directory() . '/css/bible-v3-interface.css';
	wp_enqueue_style(
		'figuier-bible-v3-style',
		get_stylesheet_directory_uri() . '/css/bible-v3-interface.css',
		array( 'figuier-style-globals' ),
		file_exists( $v3_css_path ) ? filemtime( $v3_css_path ) : '1.0',
		'all'
	);
	wp_enqueue_style(
		'figuier-hebrew-font',
		'https://fonts.googleapis.com/css2?family=Noto+Sans+Hebrew:wght@400;700&display=swap',
		array(),
		null
	);

	wp_enqueue_script(
		'marked-js',
		'https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js',
		array(),
		null,
		true
	);

	$v2_js_path = get_stylesheet_directory() . '/js/bible-v2-app.js';
	wp_enqueue_script(
		'figuier-bible-v2-app',
		get_stylesheet_directory_uri() . '/js/bible-v2-app.js',
		array( 'marked-js' ),
		file_exists( $v2_js_path ) ? filemtime( $v2_js_path ) : '1.0',
		true
	);

	// V3 DOM patch — layout restructuring
	$v3_js_path = get_stylesheet_directory() . '/js/bible-v3-patch.js';
	wp_enqueue_script(
		'figuier-bible-v3-patch',
		get_stylesheet_directory_uri() . '/js/bible-v3-patch.js',
		array( 'figuier-bible-v2-app' ),
		file_exists( $v3_js_path ) ? filemtime( $v3_js_path ) : '1.0',
		true
	);

	// V3 hotfix — Hebrew sidebar label-based lookup + VerseBubble URL fix
	$v3_hotfix_path = get_stylesheet_directory() . '/js/bible-v3-hotfix.js';
	wp_enqueue_script(
		'figuier-bible-v3-hotfix',
		get_stylesheet_directory_uri() . '/js/bible-v3-hotfix.js',
		array( 'figuier-bible-v3-patch' ),
		file_exists( $v3_hotfix_path ) ? filemtime( $v3_hotfix_path ) : '1.0',
		true
	);

	$bible_config = array(
			'manifestUrl' => content_url( 'uploads/dictionnaires/source-manifest.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/source-manifest.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/source-manifest.json' ) : '1' ),
			'workerUrl'   => get_stylesheet_directory_uri() . '/js/bible-v2-search-worker.js',
			'hebrewLexiconUrl' => content_url( 'uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/hebrew/hebrew-lexicon-fr-compact.json' ) : '1' ),
			'bymSourceBase'    => 'https://gitlab.com/anjc/bjc-source/-/raw/master',
			'bymProxyUrl'      => admin_url( 'admin-ajax.php' ),
			'bymReaderBase'    => 'https://www.bibledeyehoshouahamashiah.org/lire.html',
			'heroImageUrl' => 'https://alombredufiguier.org/wp-content/uploads/2026/03/Etude-matinale-sous-un-figuier.png',
			'hashPrefix'  => 'concept',
			'seoBaseUrl'  => home_url( '/dictionnaire-biblique/' ),
			'urlSlugsUrl' => content_url( 'uploads/dictionnaires/concept-url-slugs.json' ) . '?v=' . ( file_exists( WP_CONTENT_DIR . '/uploads/dictionnaires/concept-url-slugs.json' ) ? filemtime( WP_CONTENT_DIR . '/uploads/dictionnaires/concept-url-slugs.json' ) : '1' ),
			'mobileBreakpoint' => 900,
			'browse' => array(
				'homeLetterPreviewSize'      => 4,
				'homeCategoryPreviewSize'    => 4,
				'letterPageSize'             => 12,
				'categoryDirectoryPageSize'  => 6,
				'categoryConceptPageSize'    => 12,
			),
			'labels'      => array(
				'search_placeholder' => 'Chercher un concept, un nom ou une autre forme...',
				'loading'            => 'Chargement de l\'interface biblique...',
				'search_loading'     => 'Préparation de la recherche...',
				'search_empty'       => 'Utilisez la recherche ou l\'index alphabétique pour ouvrir un concept biblique.',
				'search_no_results'  => 'Aucun concept correspondant.',
				'search_error'       => 'La recherche n\'a pas pu être initialisée.',
				'concept_error'      => 'Le concept demandé est introuvable.',
				'quick_gloss'        => 'Notice lexicale',
				'main_definition'    => 'Définition principale',
				'secondary_definition' => 'Lecture complémentaire',
				'detailed_reference' => 'Référence détaillée',
				'deep_read'          => 'Approfondissement',
				'home_kicker'        => 'Dictionnaire biblique interactif',
				'other_forms'        => 'Autres formes',
				'other_form'         => 'Forme d\'origine',
				'english_forms'      => 'Formes anglaises',
				'category'           => 'Catégorie',
				'aliases'            => 'Autres appellations',
				'sources'            => 'Sources disponibles',
				'related'            => 'Concepts liés',
				'related_placeholder' => 'Les concepts liés seront ajoutés dans une étape ultérieure.',
				'back'               => 'Retour',
				'page_prev'          => 'Précédent',
				'page_next'          => 'Suivant',
				'page_indicator'     => 'Page {current} sur {total}',
				'search_open'        => 'Recherche',
				'search_close'       => 'Fermer la recherche',
				'reading_open'       => 'Lire la suite',
				'reading_close'      => 'Fermer la lecture',
				'open_concept'       => 'Ouvrir ce concept',
				'search_prompt'      => 'Saisissez au moins deux caractères pour rechercher un concept biblique.',
				'reading_loading'    => 'Chargement de la lecture...',
				'home_title'         => 'Dictionnaire biblique interactif',
				'home_title_note'    => 'Un espace pour rechercher, explorer et approfondir les termes bibliques',
				'home_positioning'   => 'Près de 9 000 références déjà traduites en français, issues de dictionnaires bibliques de référence du XIXᵉ siècle. Une interface fluide pour la recherche et la lecture, avec des repères pour mieux comprendre le contexte historique, culturel et biblique. Une nouvelle étape pour approfondir l\'étude des Écritures.',
				'home_image_alt'     => 'Étude matinale sous un figuier',
				'home_browse_letter' => 'Parcourir les concepts',
				'home_browse_categories' => 'Explorer les catégories',
				'browse_title'       => 'Parcourir par lettre',
				'browse_copy'        => 'L\'index alphabétique ouvre la même page conceptuelle que la recherche.',
				'browse_letter_open' => 'Ouvrir la vue alphabétique',
				'browse_letter_kicker' => 'Vue alphabétique',
				'browse_letter_title' => 'Lettre',
				'browse_letter_count' => '{count} concepts pour cette lettre.',
				'browse_empty'       => 'Aucun concept disponible pour cette lettre.',
				'categories_title'   => 'Explorer par catégorie',
				'categories_copy'    => 'Première couche de repérage conceptuel pour orienter l\'exploration.',
				'categories_kicker'  => 'Parcours thématique',
				'categories_directory_copy' => 'Choisissez une catégorie pour entrer dans une vue dédiée et paginée.',
				'categories_open_all' => 'Voir le répertoire des catégories',
				'categories_back'    => 'Retour aux catégories',
				'category_view_kicker' => 'Vue par catégorie',
				'category_view_count' => '{count} concepts dans cette catégorie.',
				'category_empty'     => 'Aucun concept disponible pour cette catégorie.',
				'open_category'      => 'Ouvrir la catégorie',
				'redirect_intro'     => 'Dans le lexique BYM, cette forme renvoie à ce concept.',
				'redirect_open'      => 'Ouvrir le concept cible',
			),
	);

	// Inject initialConceptId if URL-based concept route (résout le slug français)
	$raw_slug = get_query_var( 'bible_concept' );
	if ( $raw_slug ) {
		$resolved_id = figuier_bible_resolve_slug( $raw_slug );
		if ( $resolved_id ) {
			$bible_config['initialConceptId'] = sanitize_text_field( $resolved_id );
		}
	}

	wp_localize_script(
		'figuier-bible-v2-app',
		'FIGUIER_BIBLE_V2_CONFIG',
		$bible_config
	);
}
add_action( 'wp_enqueue_scripts', 'figuier_bible_v2_enqueue_assets', 31 );


/* =========================================================
   SHORTCODE [bible_interface_v2]
   ========================================================= */
function figuier_render_bible_interface_v2() {
	ob_start();
	?>
	<section class="figuier-bible-app" data-app="bible-v2" data-version="2" data-view="idle">
		<header class="fb-topbar">
			<div class="fb-topbar-row">
				<button class="fb-nav-back" type="button" hidden>Retour</button>
				<div class="fb-search-trigger-row">
					<label class="screen-reader-text" for="fb-search-input">Rechercher un concept biblique</label>
					<input
						id="fb-search-input"
						class="fb-search-input"
						type="search"
						placeholder="Chercher un concept, un nom ou une autre forme..."
						autocomplete="off"
						spellcheck="false"
					/>
					<button class="fb-search-clear" type="button" hidden>Effacer</button>
				</div>
			</div>
			<div class="fb-search-status" aria-live="polite">Chargement de l'interface biblique...</div>
		</header>

		<section class="fb-search-panel" hidden></section>

		<main class="fb-content">
			<section class="fb-concept-slot" aria-live="polite">
				<div class="fb-empty-state">
					<h2>Interface biblique</h2>
					<p>Chargement de l\'accueil de l\'interface biblique.</p>
				</div>
			</section>
		</main>

		<section class="fb-reading-panel" hidden></section>
	</section>
	<?php
	return ob_get_clean();
}
add_shortcode( 'bible_interface_v2', 'figuier_render_bible_interface_v2' );


/* =========================================================
   FOOTNOTES TOOLTIP (final)
   ========================================================= */
function figuier_footnote_tooltips_final() { ?>
<script>
/* Footnotes tooltip – A l'ombre du figuier (final) */
(function(){
  let openTip = null, currentSup = null;
  const hasHover = window.matchMedia('(hover:hover)').matches && window.matchMedia('(pointer:fine)').matches;

  function getNoteHTML(sup){
    const a = sup.querySelector('a[href^="#"]');
    if(!a) return null;
    const id = a.getAttribute('href').slice(1);
    const noteEl = document.getElementById(id);
    if(!noteEl) return null;
    const clone = noteEl.cloneNode(true);
    clone.querySelectorAll('a[href^="#"]').forEach(el => el.remove());
    return clone.innerHTML.trim();
  }

  function positionTip(tip, sup){
    const rect = sup.getBoundingClientRect();
    const w = Math.min(320, window.innerWidth - 20);
    tip.style.width = w + 'px';

    let left = rect.left + window.scrollX - (w/2) + (rect.width/2);
    const minL = 10, maxL = window.scrollX + window.innerWidth - w - 10;
    if (left < minL) left = minL;
    if (left > maxL) left = maxL;

    const top = rect.bottom + window.scrollY + 10;
    tip.style.left = left + 'px';
    tip.style.top  = top  + 'px';
  }

  function closeTip(){
    if (openTip) { openTip.remove(); openTip = null; currentSup = null; }
  }

  function showTip(sup){
    closeTip();
    const html = getNoteHTML(sup);
    if(!html) return;
    const tip = document.createElement('div');
    tip.className = 'footnote-tooltip';
    tip.setAttribute('role', 'tooltip');
    tip.innerHTML = html + '<button class="footnote-close" aria-label="Fermer">×</button>';
    document.body.appendChild(tip);
    positionTip(tip, sup);
    openTip = tip; currentSup = sup;
  }

  document.addEventListener('click', function(e){
    const sup = e.target.closest('sup.fn');
    if (sup) { e.preventDefault(); showTip(sup); return; }
    if (openTip && !e.target.closest('.footnote-tooltip')) closeTip();
  }, true);

  if (hasHover) {
    document.addEventListener('pointerenter', function(e){
      const sup = e.target.closest && e.target.closest('sup.fn');
      if (sup) showTip(sup);
    }, true);
    document.addEventListener('pointerleave', function(e){
      if (e.target.closest && e.target.closest('sup.fn')) {
        setTimeout(() => {
          if (!document.querySelector('sup.fn:hover') && openTip) closeTip();
        }, 100);
      }
    }, true);
  }

  window.addEventListener('scroll', ()=>{ if(openTip && currentSup) positionTip(openTip, currentSup); }, {passive:true});
  window.addEventListener('resize', ()=>{ if(openTip && currentSup) positionTip(openTip, currentSup); });

  document.addEventListener('click', (e)=>{ if (e.target.matches('.footnote-close')) closeTip(); });
})();
</script>
<?php }
add_action( 'wp_footer', 'figuier_footnote_tooltips_final', 99 );


/* =========================================================
   TEMPS DE LECTURE — FIGUIER (Homepage + Single + Archives)
   ========================================================= */

/**
 * Calcule le temps de lecture (minutes) à partir d'un contenu.
 */
function figuier_reading_time_minutes_from_content( $content, $wpm = 220 ) {
	$content = strip_shortcodes( (string) $content );
	$content = wp_strip_all_tags( $content );
	$content = preg_replace( '/s+/u', ' ', $content ); // ✅ correction: s+

	$words = str_word_count( $content );
	$wpm   = max( 120, (int) apply_filters( 'figuier_reading_time_wpm', $wpm ) );

	$minutes = (int) ceil( max( 1, $words ) / $wpm );
	return max( 1, $minutes );
}

/**
 * Retourne le HTML “pill” (sans emoji) pour un post.
 */
function figuier_reading_time_markup( $post_id = 0 ) {
	$post_id = $post_id ? (int) $post_id : (int) get_the_ID();
	if ( ! $post_id ) return '';

	// Limiter aux articles uniquement (comme tu le faisais)
	if ( get_post_type( $post_id ) !== 'post' ) return '';

	$content = get_post_field( 'post_content', $post_id );
	if ( ! $content ) return '';

	$minutes = figuier_reading_time_minutes_from_content( $content );
	$txt     = sprintf( '%s min', number_format_i18n( $minutes ) );

	$svg = '<svg class="figuier-rt-ico" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
		<path d="M12 8v5l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
		<path d="M21 12a9 9 0 1 1-9-9 9 9 0 0 1 9 9Z" fill="none" stroke="currentColor" stroke-width="2"/>
	</svg>';

	return '<span class="figuier-readingtime" aria-label="Temps de lecture">'
		. $svg
		. '<span class="figuier-rt-txt">' . esc_html( $txt ) . '</span>'
	. '</span>';
}

/**
 * SINGLE (Kadence) : juste sous le titre.
 */
function figuier_kadence_single_reading_time() {
	if ( ! is_singular( 'post' ) ) return;

	echo '<div class="figuier-meta-row figuier-meta-row--single">'
		. figuier_reading_time_markup( get_the_ID() )
	. '</div>';
}
add_action( 'kadence_single_after_entry_title', 'figuier_kadence_single_reading_time', 12 );

/**
 * ARCHIVES / CATEGORIES / BLOG (Kadence loop) : au début de la ligne meta.
 */
function figuier_kadence_loop_reading_time() {
	if ( is_singular() ) return; // évite doublon sur single
	if ( get_post_type() !== 'post' ) return;

	echo '<span class="figuier-meta-inline">'
		. figuier_reading_time_markup( get_the_ID() )
	. '</span>';
}
add_action( 'kadence_before_loop_entry_meta', 'figuier_kadence_loop_reading_time', 5 );


/* ===========================================================
   OPTIMISATION IMAGES — REMPLACEMENT OPTIMOLE
   =========================================================== */
add_filter( 'wp_get_attachment_image_attributes', function( $attr, $attachment ) {
    static $count = 0;
    $count++;
    if ( $count <= 2 ) {
        $attr['fetchpriority'] = 'high';
        unset( $attr['loading'] );
    }
    $attr['decoding'] = 'async';
    return $attr;
}, 10, 2 );

add_filter( 'wp_omit_loading_attr_threshold', function() {
    return 2;
});

/* ===========================================================
   ANCRES AUTOMATIQUES SUR LES TITRES H2/H3
   Priorite 15 = apres do_blocks (9)
   =========================================================== */
add_filter( 'the_content', function( $content ) {
    if ( ! is_single() && ! is_page() ) {
        return $content;
    }
    return preg_replace_callback(
        '/<h([23])([^>]*)>(.*?)<\/h\\1>/i',
        function( $matches ) {
            if ( strpos( $matches[2], 'id=' ) !== false ) {
                return $matches[0];
            }
            $slug = sanitize_title( wp_strip_all_tags( $matches[3] ) );
            return '<h' . $matches[1] . $matches[2] . ' id="' . esc_attr( $slug ) . '">'
                   . $matches[3] . '</h' . $matches[1] . '>';
        },
        $content
    );
}, 15 );

/* ===========================================================
   SOMMAIRE AUTOMATIQUE POUR ARTICLES LONGS
   Priorite 20 = apres ancres auto (15)
   =========================================================== */
add_filter( 'the_content', function( $content ) {
    if ( ! is_single() ) {
        return $content;
    }
    $word_count = str_word_count( wp_strip_all_tags( $content ) );
    if ( $word_count < 1500 ) {
        return $content;
    }
    preg_match_all(
        '/<h([23])[^>]*id="([^"]+)"[^>]*>(.*?)<\/h\\1>/i',
        $content,
        $matches,
        PREG_SET_ORDER
    );
    if ( count( $matches ) < 3 ) {
        return $content;
    }
    $toc  = '<nav class="figuier-toc" aria-label="Sommaire">';
    $toc .= '<p class="toc-title">Sommaire</p><ul>';
    foreach ( $matches as $m ) {
        $level_class = ( $m[1] === '3' ) ? ' class="toc-sub"' : '';
        $clean_title = wp_strip_all_tags( $m[3] );
        $toc .= '<li' . $level_class . '><a href="#' . esc_attr( $m[2] ) . '">'
                . esc_html( $clean_title ) . '</a></li>';
    }
    $toc .= '</ul></nav>';
    return $toc . $content;
}, 20 );


/* ===========================================================
   SEO DICTIONNAIRE BIBLIQUE — URLs réelles, SSR, JSON-LD, Sitemap
   =========================================================== */

/**
 * Charge et met en cache le fichier concept-meta.json (index léger).
 * Utilise un transient WordPress (cache 24h) pour éviter de parser 1.2MB à chaque requête.
 */
function figuier_bible_get_concept_meta( $concept_id = null ) {
    $cache_key = 'figuier_concept_meta_v2';
    $meta = get_transient( $cache_key );

    if ( false === $meta ) {
        $file = WP_CONTENT_DIR . '/uploads/dictionnaires/concept-meta.json';
        if ( ! file_exists( $file ) ) {
            return $concept_id ? null : array();
        }
        $raw = file_get_contents( $file );
        $meta = json_decode( $raw, true );
        if ( ! is_array( $meta ) ) {
            return $concept_id ? null : array();
        }
        set_transient( $cache_key, $meta, DAY_IN_SECONDS );
    }

    if ( $concept_id ) {
        return isset( $meta[ $concept_id ] ) ? $meta[ $concept_id ] : null;
    }
    return $meta;
}

/**
 * Charge et met en cache slug-map.json (slug français → concept_id).
 */
function figuier_bible_get_slug_map() {
    $cache_key = 'figuier_slug_map_v1';
    $map = get_transient( $cache_key );

    if ( false === $map ) {
        $file = WP_CONTENT_DIR . '/uploads/dictionnaires/slug-map.json';
        if ( ! file_exists( $file ) ) {
            return array();
        }
        $raw = file_get_contents( $file );
        $map = json_decode( $raw, true );
        if ( ! is_array( $map ) ) {
            return array();
        }
        set_transient( $cache_key, $map, DAY_IN_SECONDS );
    }
    return $map;
}

/**
 * Résout un slug d'URL en concept_id.
 * Accepte un slug français (paul → paulos) ou un concept_id direct.
 */
function figuier_bible_resolve_slug( $slug ) {
    if ( ! $slug ) {
        return null;
    }
    $slug = urldecode( $slug );

    // 1) Essayer comme concept_id direct
    $meta = figuier_bible_get_concept_meta( $slug );
    if ( $meta ) {
        return $slug;
    }

    // 2) Chercher dans le slug-map (slug français → concept_id)
    $map = figuier_bible_get_slug_map();
    if ( isset( $map[ $slug ] ) ) {
        return $map[ $slug ];
    }

    return null;
}

/**
 * Retourne le slug d'URL français pour un concept_id donné.
 * Si le concept a un slug français ('u'), on l'utilise ; sinon le concept_id.
 */
function figuier_bible_get_url_slug( $concept_id ) {
    $meta = figuier_bible_get_concept_meta( $concept_id );
    if ( $meta && ! empty( $meta['u'] ) ) {
        return $meta['u'];
    }
    return $concept_id;
}

/**
 * Invalide les caches concept-meta et slug-map.
 * Appeler manuellement ou via WP-CLI :
 *   wp transient delete figuier_concept_meta_v2
 *   wp transient delete figuier_slug_map_v1
 */
function figuier_bible_flush_concept_cache() {
    delete_transient( 'figuier_concept_meta_v2' );
    delete_transient( 'figuier_slug_map_v1' );
}

/**
 * 0b. REDIRECT — /dictionnaire-biblique/racines/ → Lexique onglet Arbre
 *     Cette URL intuitive n'est pas un concept ; on redirige vers l'app lexique.
 */
add_action( 'template_redirect', function () {
    $concept = get_query_var( 'bible_concept', '' );
    if ( $concept === 'racines' ) {
        wp_redirect( home_url( '/lexique-hebreu-biblique/#racine=' ), 301 );
        exit;
    }
} );

/**
 * 1. REWRITE RULES — /dictionnaire-biblique/{slug}/
 *    Accepte les slugs français avec accents (encodés en URL : %C3%A9 pour é, etc.)
 */
add_action( 'init', function () {
    add_rewrite_rule(
        '^dictionnaire-biblique/sitemap\.xml$',
        'index.php?figuier_bible_sitemap=1',
        'top'
    );
    add_rewrite_rule(
        '^dictionnaire-biblique/sitemap-([A-Z])\.xml$',
        'index.php?figuier_bible_sitemap_letter=$matches[1]',
        'top'
    );
    add_rewrite_rule(
        '^dictionnaire-biblique/([^/]+)/?$',
        'index.php?pagename=dictionnaire-biblique&bible_concept=$matches[1]',
        'top'
    );
} );

/* Flush conditionnel — s'exécute UNE SEULE FOIS après mise à jour */
add_action( 'init', function () {
    if ( get_option( 'figuier_rewrite_v3' ) !== '1' ) {
        flush_rewrite_rules( false );
        update_option( 'figuier_rewrite_v3', '1', true );
    }
}, 99 );

add_filter( 'query_vars', function ( $vars ) {
    $vars[] = 'bible_concept';
    $vars[] = 'figuier_bible_sitemap';
    $vars[] = 'figuier_bible_sitemap_letter';
    return $vars;
} );

/**
 * 2. META TAGS DYNAMIQUES — <title>, description, og:tags, canonical, JSON-LD
 *    Résout le slug français → concept_id avant de chercher les métadonnées.
 */
add_action( 'wp_head', function () {
    $raw_slug = get_query_var( 'bible_concept' );
    if ( ! $raw_slug ) {
        return;
    }

    $concept_id = figuier_bible_resolve_slug( $raw_slug );
    if ( ! $concept_id ) {
        return;
    }

    $concept = figuier_bible_get_concept_meta( $concept_id );
    if ( ! $concept ) {
        return;
    }

    // Slug français canonique pour l'URL
    $url_slug  = figuier_bible_get_url_slug( $concept_id );

    $primary   = ! empty( $concept['p'] ) ? $concept['p'] : $concept['l'];
    $secondary = ! empty( $concept['s'] ) ? $concept['s'] : '';
    $category  = ! empty( $concept['c'] ) ? $concept['c'] : '';
    $excerpt   = ! empty( $concept['e'] ) ? $concept['e'] : '';

    // Title
    $title_parts = array( $primary );
    if ( $secondary && $secondary !== $primary ) {
        $title_parts[] = $secondary;
    }
    $page_title = implode( ' — ', $title_parts ) . ' | Dictionnaire Biblique';

    // Description
    $cat_label = str_replace( '_', ' ', $category );
    $cat_label = function_exists( 'mb_ucfirst' ) ? mb_ucfirst( $cat_label ) : ucfirst( $cat_label );
    $description = $excerpt ? $excerpt : sprintf( 'Définition de %s dans le dictionnaire biblique interactif.', $primary );

    $url = home_url( '/dictionnaire-biblique/' . rawurlencode( $url_slug ) . '/' );

    // Override WordPress <title>
    add_filter( 'pre_get_document_title', function () use ( $page_title ) {
        return $page_title;
    } );

    // Meta tags
    echo "\n<!-- Figuier Bible SEO -->\n";
    echo '<meta name="description" content="' . esc_attr( $description ) . '" />' . "\n";
    echo '<link rel="canonical" href="' . esc_url( $url ) . '" />' . "\n";
    echo '<meta property="og:title" content="' . esc_attr( $page_title ) . '" />' . "\n";
    echo '<meta property="og:description" content="' . esc_attr( $description ) . '" />' . "\n";
    echo '<meta property="og:url" content="' . esc_url( $url ) . '" />' . "\n";
    echo '<meta property="og:type" content="article" />' . "\n";
    echo '<meta property="og:site_name" content="À l\'ombre du figuier" />' . "\n";

    // JSON-LD DefinedTerm
    $jsonld = array(
        '@context'         => 'https://schema.org',
        '@type'            => 'DefinedTerm',
        'name'             => $primary . ( $secondary && $secondary !== $primary ? ' (' . $secondary . ')' : '' ),
        'description'      => $description,
        'url'              => $url,
        'inDefinedTermSet' => array(
            '@type' => 'DefinedTermSet',
            'name'  => 'Dictionnaire Biblique — À l\'ombre du figuier',
            'url'   => home_url( '/dictionnaire-biblique/' ),
        ),
    );
    echo '<script type="application/ld+json">' . wp_json_encode( $jsonld, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . '</script>' . "\n";
    echo "<!-- /Figuier Bible SEO -->\n";
}, 1 );

/**
 * 3. SSR — Contenu visible pour les crawlers (noscript + section cachée)
 */
add_filter( 'the_content', function ( $content ) {
    $raw_slug = get_query_var( 'bible_concept' );
    if ( ! $raw_slug ) {
        return $content;
    }

    $concept_id = figuier_bible_resolve_slug( $raw_slug );
    if ( ! $concept_id ) {
        return $content;
    }

    $concept = figuier_bible_get_concept_meta( $concept_id );
    if ( ! $concept ) {
        return $content;
    }

    $primary   = ! empty( $concept['p'] ) ? $concept['p'] : $concept['l'];
    $secondary = ! empty( $concept['s'] ) ? $concept['s'] : '';
    $category  = ! empty( $concept['c'] ) ? $concept['c'] : '';
    $excerpt   = ! empty( $concept['e'] ) ? $concept['e'] : '';
    $cat_label = ucfirst( str_replace( '_', ' ', $category ) );

    $definition_preview = ! empty( $concept['d'] ) ? $concept['d'] : '';

    $ssr_html  = '<div class="figuier-bible-ssr" style="display:none" aria-hidden="true">';
    $ssr_html .= '<h1>' . esc_html( $primary );
    if ( $secondary && $secondary !== $primary ) {
        $ssr_html .= ' <span>(' . esc_html( $secondary ) . ')</span>';
    }
    $ssr_html .= '</h1>';
    if ( $cat_label ) {
        $ssr_html .= '<h2>Catégorie : ' . esc_html( $cat_label ) . '</h2>';
    }
    if ( $excerpt ) {
        $ssr_html .= '<p><em>' . esc_html( $excerpt ) . '</em></p>';
    }
    if ( $definition_preview ) {
        $ssr_html .= '<div class="figuier-bible-ssr-definition"><p>' . esc_html( $definition_preview ) . '</p></div>';
    }
    $ssr_html .= '<p><a href="' . esc_url( home_url( '/dictionnaire-biblique/' ) ) . '">Retour au dictionnaire biblique</a></p>';
    $ssr_html .= '</div>';

    $noscript  = '<noscript>';
    $noscript .= '<article class="figuier-bible-ssr-noscript">';
    $noscript .= '<h1>' . esc_html( $primary );
    if ( $secondary && $secondary !== $primary ) {
        $noscript .= ' (' . esc_html( $secondary ) . ')';
    }
    $noscript .= '</h1>';
    if ( $cat_label ) {
        $noscript .= '<h2>Catégorie : ' . esc_html( $cat_label ) . '</h2>';
    }
    if ( $excerpt ) {
        $noscript .= '<p><em>' . esc_html( $excerpt ) . '</em></p>';
    }
    if ( $definition_preview ) {
        $noscript .= '<p>' . esc_html( $definition_preview ) . '</p>';
    }
    $noscript .= '<p><a href="' . esc_url( home_url( '/dictionnaire-biblique/' ) ) . '">Voir le dictionnaire biblique complet</a></p>';
    $noscript .= '</article>';
    $noscript .= '</noscript>';

    return $ssr_html . $noscript . $content;
}, 5 );

/**
 * 4. CONCEPT_ID est passé au JS directement via wp_localize_script
 *    (voir figuier_bible_v2_enqueue_assets ci-dessus)
 */

/**
 * 5a. Prevent trailing slash redirect on sitemap URLs
 */
add_filter( 'redirect_canonical', function ( $redirect_url, $requested_url ) {
    if ( get_query_var( 'figuier_bible_sitemap' ) || get_query_var( 'figuier_bible_sitemap_letter' ) ) {
        return false;
    }
    return $redirect_url;
}, 10, 2 );

/**
 * 5b. SITEMAP XML — /dictionnaire-biblique/sitemap.xml
 */
add_action( 'template_redirect', function () {
    $is_index  = get_query_var( 'figuier_bible_sitemap' );
    $letter    = get_query_var( 'figuier_bible_sitemap_letter' );

    if ( ! $is_index && ! $letter ) {
        return;
    }

    $meta = figuier_bible_get_concept_meta();
    if ( empty( $meta ) ) {
        status_header( 503 );
        echo '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>';
        exit;
    }

    $base = home_url( '/dictionnaire-biblique/' );
    $mod  = date( 'Y-m-d' );

    header( 'Content-Type: application/xml; charset=UTF-8' );

    if ( $letter ) {
        // Single-letter sitemap
        $letter = strtoupper( $letter );
        echo '<?xml version="1.0" encoding="UTF-8"?>';
        echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
        foreach ( $meta as $id => $c ) {
            $label = isset( $c['p'] ) ? $c['p'] : ( isset( $c['l'] ) ? $c['l'] : $id );
            if ( strtoupper( mb_substr( $label, 0, 1, 'UTF-8' ) ) !== $letter ) {
                continue;
            }
            $slug = figuier_bible_get_url_slug( $id );
            echo '<url><loc>' . esc_url( $base . $slug . '/' ) . '</loc><lastmod>' . $mod . '</lastmod></url>';
        }
        echo '</urlset>';
    } else {
        // Sitemap index — one sub-sitemap per letter
        echo '<?xml version="1.0" encoding="UTF-8"?>';
        echo '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
        $letters = array();
        foreach ( $meta as $id => $c ) {
            $label = isset( $c['p'] ) ? $c['p'] : ( isset( $c['l'] ) ? $c['l'] : $id );
            $l = strtoupper( mb_substr( $label, 0, 1, 'UTF-8' ) );
            if ( $l >= 'A' && $l <= 'Z' && ! isset( $letters[ $l ] ) ) {
                $letters[ $l ] = true;
            }
        }
        ksort( $letters );
        foreach ( $letters as $l => $v ) {
            echo '<sitemap><loc>' . esc_url( $base . 'sitemap-' . $l . '.xml' ) . '</loc><lastmod>' . $mod . '</lastmod></sitemap>';
        }
        echo '</sitemapindex>';
    }
    exit;
} );


/* =============================================================
   CHANTIER A — TAXONOMIES "serie" ET "dossier"
   - Deux taxonomies non hierarchiques, attachees au post type 'post'
   - Meta post : _serie_order (entier) et _dossier_order (entier)
   - Term meta : _serie_total (total d'episodes annonce, ex: 7)
   - Shortcode [serie_nav] : bloc "Episode X/Y  |  <- prec  suiv ->"
   - Auto-injection du bloc en haut du single post si membre d'une serie
   - Tri automatique des archives /serie/{slug}/ par _serie_order ASC
   - Shortcodes [liste_series] et [liste_dossiers] pour pages d'index
   ============================================================= */

/**
 * A1. Enregistrement des taxonomies 'serie' et 'dossier'
 */
add_action( 'init', function () {

    // --- Taxonomie SERIE ---
    register_taxonomy( 'serie', array( 'post' ), array(
        'labels' => array(
            'name'              => 'Series',
            'singular_name'     => 'Serie',
            'search_items'      => 'Rechercher une serie',
            'all_items'         => 'Toutes les series',
            'edit_item'         => 'Modifier la serie',
            'update_item'       => 'Mettre a jour la serie',
            'add_new_item'      => 'Ajouter une nouvelle serie',
            'new_item_name'     => 'Nom de la nouvelle serie',
            'menu_name'         => 'Series',
            'not_found'         => 'Aucune serie trouvee',
            'back_to_items'     => '&larr; Retour aux series',
        ),
        'public'            => true,
        'publicly_queryable'=> true,
        'hierarchical'      => false,
        'show_ui'           => true,
        'show_admin_column' => true,
        'show_in_nav_menus' => true,
        'show_in_rest'      => true,
        'query_var'         => true,
        'rewrite' => array(
            'slug'         => 'serie',
            'with_front'   => false,
            'hierarchical' => false,
        ),
    ) );

    // --- Taxonomie DOSSIER ---
    register_taxonomy( 'dossier', array( 'post' ), array(
        'labels' => array(
            'name'              => 'Dossiers',
            'singular_name'     => 'Dossier',
            'search_items'      => 'Rechercher un dossier',
            'all_items'         => 'Tous les dossiers',
            'edit_item'         => 'Modifier le dossier',
            'update_item'       => 'Mettre a jour le dossier',
            'add_new_item'      => 'Ajouter un nouveau dossier',
            'new_item_name'     => 'Nom du nouveau dossier',
            'menu_name'         => 'Dossiers',
            'not_found'         => 'Aucun dossier trouve',
            'back_to_items'     => '&larr; Retour aux dossiers',
        ),
        'public'            => true,
        'publicly_queryable'=> true,
        'hierarchical'      => false,
        'show_ui'           => true,
        'show_admin_column' => true,
        'show_in_nav_menus' => true,
        'show_in_rest'      => true,
        'query_var'         => true,
        'rewrite' => array(
            'slug'         => 'dossier',
            'with_front'   => false,
            'hierarchical' => false,
        ),
    ) );

    // --- Meta de post : ordre d'episode ---
    register_post_meta( 'post', '_serie_order', array(
        'type'              => 'integer',
        'single'            => true,
        'show_in_rest'      => true,
        'sanitize_callback' => 'absint',
        'auth_callback'     => function () { return current_user_can( 'edit_posts' ); },
    ) );
    register_post_meta( 'post', '_dossier_order', array(
        'type'              => 'integer',
        'single'            => true,
        'show_in_rest'      => true,
        'sanitize_callback' => 'absint',
        'auth_callback'     => function () { return current_user_can( 'edit_posts' ); },
    ) );

    // --- Meta de terme : total d'episodes annonce (ex: 7) ---
    register_term_meta( 'serie', '_serie_total', array(
        'type'              => 'integer',
        'single'            => true,
        'show_in_rest'      => true,
        'sanitize_callback' => 'absint',
    ) );
    register_term_meta( 'serie', '_serie_description_court', array(
        'type'              => 'string',
        'single'            => true,
        'show_in_rest'      => true,
        'sanitize_callback' => 'sanitize_text_field',
    ) );
    register_term_meta( 'dossier', '_dossier_description_court', array(
        'type'              => 'string',
        'single'            => true,
        'show_in_rest'      => true,
        'sanitize_callback' => 'sanitize_text_field',
    ) );
}, 5 );

/**
 * A2. Helpers — liste ordonnee des episodes d'une serie ou articles d'un dossier
 */
function figuier_get_serie_episodes( $term_id_or_slug ) {
    if ( ! is_numeric( $term_id_or_slug ) ) {
        $term = get_term_by( 'slug', $term_id_or_slug, 'serie' );
        if ( ! $term ) return array();
        $term_id = $term->term_id;
    } else {
        $term_id = (int) $term_id_or_slug;
    }
    $q = new WP_Query( array(
        'post_type'      => 'post',
        'post_status'    => 'publish',
        'posts_per_page' => -1,
        'tax_query'      => array(
            array( 'taxonomy' => 'serie', 'field' => 'term_id', 'terms' => $term_id ),
        ),
        'meta_key'       => '_serie_order',
        'orderby'        => 'meta_value_num',
        'order'          => 'ASC',
        'no_found_rows'  => true,
    ) );
    return $q->posts;
}

function figuier_get_dossier_articles( $term_id_or_slug ) {
    if ( ! is_numeric( $term_id_or_slug ) ) {
        $term = get_term_by( 'slug', $term_id_or_slug, 'dossier' );
        if ( ! $term ) return array();
        $term_id = $term->term_id;
    } else {
        $term_id = (int) $term_id_or_slug;
    }
    $q = new WP_Query( array(
        'post_type'      => 'post',
        'post_status'    => 'publish',
        'posts_per_page' => -1,
        'tax_query'      => array(
            array( 'taxonomy' => 'dossier', 'field' => 'term_id', 'terms' => $term_id ),
        ),
        'meta_key'       => '_dossier_order',
        'orderby'        => array( 'meta_value_num' => 'ASC', 'date' => 'ASC' ),
        'no_found_rows'  => true,
    ) );
    return $q->posts;
}

/**
 * A3. Tri des archives /serie/{slug}/ et /dossier/{slug}/ par ordre puis date
 */
add_action( 'pre_get_posts', function ( $query ) {
    if ( is_admin() || ! $query->is_main_query() ) return;
    if ( $query->is_tax( 'serie' ) ) {
        $query->set( 'meta_key', '_serie_order' );
        $query->set( 'orderby', 'meta_value_num' );
        $query->set( 'order', 'ASC' );
        $query->set( 'posts_per_page', 50 );
    }
    if ( $query->is_tax( 'dossier' ) ) {
        $query->set( 'meta_key', '_dossier_order' );
        $query->set( 'orderby', 'meta_value_num date' );
        $query->set( 'order', 'ASC' );
        $query->set( 'posts_per_page', 50 );
    }
} );

/**
 * A4. Shortcode [serie_nav] — bloc de navigation inter-episodes
 */
function figuier_serie_nav_shortcode( $atts = array() ) {
    if ( ! is_singular( 'post' ) ) return '';
    $post_id = get_the_ID();

    $terms = wp_get_post_terms( $post_id, 'serie' );
    if ( empty( $terms ) || is_wp_error( $terms ) ) return '';
    $serie = $terms[0];

    $episodes = figuier_get_serie_episodes( $serie->term_id );
    if ( empty( $episodes ) ) return '';

    $total_annonce = (int) get_term_meta( $serie->term_id, '_serie_total', true );
    $total_reel    = count( $episodes );
    $total_affiche = $total_annonce > 0 ? $total_annonce : $total_reel;

    $current_order = (int) get_post_meta( $post_id, '_serie_order', true );
    $prev = null; $next = null;
    foreach ( $episodes as $i => $ep ) {
        if ( $ep->ID === $post_id ) {
            if ( isset( $episodes[ $i - 1 ] ) ) $prev = $episodes[ $i - 1 ];
            if ( isset( $episodes[ $i + 1 ] ) ) $next = $episodes[ $i + 1 ];
            break;
        }
    }

    $serie_link = get_term_link( $serie );
    if ( is_wp_error( $serie_link ) ) $serie_link = '#';

    ob_start(); ?>
    <nav class="serie-nav" aria-label="Navigation de la serie <?php echo esc_attr( $serie->name ); ?>">
        <div class="serie-nav__header">
            <span class="serie-nav__badge">Serie</span>
            <a class="serie-nav__title" href="<?php echo esc_url( $serie_link ); ?>"><?php echo esc_html( $serie->name ); ?></a>
            <span class="serie-nav__position">Episode <?php echo (int) $current_order; ?>/<?php echo (int) $total_affiche; ?></span>
        </div>
        <div class="serie-nav__buttons">
            <?php if ( $prev ) : ?>
                <a class="serie-nav__btn serie-nav__btn--prev" href="<?php echo esc_url( get_permalink( $prev ) ); ?>" rel="prev">
                    <span class="serie-nav__arrow">&larr;</span>
                    <span class="serie-nav__label">Episode precedent</span>
                    <span class="serie-nav__ep-title"><?php echo esc_html( get_the_title( $prev ) ); ?></span>
                </a>
            <?php else : ?>
                <span class="serie-nav__btn serie-nav__btn--disabled" aria-hidden="true"></span>
            <?php endif; ?>

            <?php if ( $next ) : ?>
                <a class="serie-nav__btn serie-nav__btn--next" href="<?php echo esc_url( get_permalink( $next ) ); ?>" rel="next">
                    <span class="serie-nav__label">Episode suivant</span>
                    <span class="serie-nav__ep-title"><?php echo esc_html( get_the_title( $next ) ); ?></span>
                    <span class="serie-nav__arrow">&rarr;</span>
                </a>
            <?php else : ?>
                <span class="serie-nav__btn serie-nav__btn--disabled" aria-hidden="true"></span>
            <?php endif; ?>
        </div>
    </nav>
    <?php
    return ob_get_clean();
}
add_shortcode( 'serie_nav', 'figuier_serie_nav_shortcode' );

/**
 * A5. Auto-injection de [serie_nav] en haut du single si membre d'une serie
 */
add_filter( 'the_content', function ( $content ) {
    if ( ! is_singular( 'post' ) || ! in_the_loop() || ! is_main_query() ) return $content;
    if ( strpos( $content, 'serie-nav' ) !== false ) return $content;
    $terms = get_the_terms( get_the_ID(), 'serie' );
    if ( empty( $terms ) || is_wp_error( $terms ) ) return $content;
    $nav = figuier_serie_nav_shortcode();
    return $nav . $content;
}, 12 );

/**
 * A6. Shortcode [liste_series] — affiche toutes les series
 */
function figuier_liste_series_shortcode( $atts = array() ) {
    $atts = shortcode_atts( array(
        'limit'   => 50,
        'orderby' => 'name',
        'order'   => 'ASC',
    ), $atts, 'liste_series' );

    $terms = get_terms( array(
        'taxonomy'   => 'serie',
        'hide_empty' => true,
        'number'     => (int) $atts['limit'],
        'orderby'    => sanitize_key( $atts['orderby'] ),
        'order'      => sanitize_key( $atts['order'] ),
    ) );
    if ( is_wp_error( $terms ) || empty( $terms ) ) {
        return '<p class="figuier-empty">Aucune serie disponible pour le moment.</p>';
    }

    ob_start(); ?>
    <div class="figuier-series-grid">
    <?php foreach ( $terms as $term ) :
        $total      = (int) get_term_meta( $term->term_id, '_serie_total', true );
        $count_reel = (int) $term->count;
        $desc_court = (string) get_term_meta( $term->term_id, '_serie_description_court', true );
        $link       = get_term_link( $term );
        if ( is_wp_error( $link ) ) continue; ?>
        <article class="figuier-serie-card">
            <a class="figuier-serie-card__link" href="<?php echo esc_url( $link ); ?>">
                <span class="figuier-serie-card__badge">Serie</span>
                <h3 class="figuier-serie-card__title"><?php echo esc_html( $term->name ); ?></h3>
                <?php if ( $desc_court ) : ?>
                    <p class="figuier-serie-card__desc"><?php echo esc_html( $desc_court ); ?></p>
                <?php elseif ( $term->description ) : ?>
                    <p class="figuier-serie-card__desc"><?php echo esc_html( wp_trim_words( $term->description, 28 ) ); ?></p>
                <?php endif; ?>
                <span class="figuier-serie-card__meta">
                    <?php echo $count_reel; ?> episode<?php echo $count_reel > 1 ? 's' : ''; ?>
                    <?php if ( $total > 0 && $total !== $count_reel ) : ?>
                        &nbsp;/&nbsp;<?php echo $total; ?> prevus
                    <?php endif; ?>
                </span>
            </a>
        </article>
    <?php endforeach; ?>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode( 'liste_series', 'figuier_liste_series_shortcode' );

/**
 * A7. Shortcode [liste_dossiers] — affiche tous les dossiers
 */
function figuier_liste_dossiers_shortcode( $atts = array() ) {
    $atts = shortcode_atts( array(
        'limit'   => 50,
        'orderby' => 'name',
        'order'   => 'ASC',
    ), $atts, 'liste_dossiers' );

    $terms = get_terms( array(
        'taxonomy'   => 'dossier',
        'hide_empty' => true,
        'number'     => (int) $atts['limit'],
        'orderby'    => sanitize_key( $atts['orderby'] ),
        'order'      => sanitize_key( $atts['order'] ),
    ) );
    if ( is_wp_error( $terms ) || empty( $terms ) ) {
        return '<p class="figuier-empty">Aucun dossier disponible pour le moment.</p>';
    }

    ob_start(); ?>
    <div class="figuier-dossiers-grid">
    <?php foreach ( $terms as $term ) :
        $desc_court = (string) get_term_meta( $term->term_id, '_dossier_description_court', true );
        $link       = get_term_link( $term );
        if ( is_wp_error( $link ) ) continue; ?>
        <article class="figuier-dossier-card">
            <a class="figuier-dossier-card__link" href="<?php echo esc_url( $link ); ?>">
                <span class="figuier-dossier-card__badge">Dossier</span>
                <h3 class="figuier-dossier-card__title"><?php echo esc_html( $term->name ); ?></h3>
                <?php if ( $desc_court ) : ?>
                    <p class="figuier-dossier-card__desc"><?php echo esc_html( $desc_court ); ?></p>
                <?php elseif ( $term->description ) : ?>
                    <p class="figuier-dossier-card__desc"><?php echo esc_html( wp_trim_words( $term->description, 28 ) ); ?></p>
                <?php endif; ?>
                <span class="figuier-dossier-card__meta">
                    <?php echo (int) $term->count; ?> article<?php echo $term->count > 1 ? 's' : ''; ?>
                </span>
            </a>
        </article>
    <?php endforeach; ?>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode( 'liste_dossiers', 'figuier_liste_dossiers_shortcode' );

/**
 * A8. CSS inline du module serie/dossier
 */
add_action( 'wp_head', function () {
    ?>
    <style id="figuier-serie-dossier-css">
    .serie-nav{margin:2rem 0;padding:1rem 1.25rem;border:1px solid #e7d8b8;background:#fbf5e8;border-radius:10px;font-family:inherit}
    .serie-nav__header{display:flex;flex-wrap:wrap;align-items:center;gap:.6rem;margin-bottom:.8rem}
    .serie-nav__badge{display:inline-block;background:#8a5a1b;color:#fff;font-size:.72rem;letter-spacing:.06em;padding:.22rem .55rem;border-radius:4px;text-transform:uppercase}
    .serie-nav__title{font-weight:700;color:#5b3a0e;text-decoration:none;font-size:1rem}
    .serie-nav__title:hover{text-decoration:underline}
    .serie-nav__position{margin-left:auto;font-size:.85rem;color:#7a5a2a;font-weight:600}
    .serie-nav__buttons{display:grid;grid-template-columns:1fr 1fr;gap:.75rem}
    .serie-nav__btn{display:flex;flex-direction:column;gap:.2rem;padding:.7rem .9rem;background:#fff;border:1px solid #e0cfa5;border-radius:8px;text-decoration:none;color:#3a2608;transition:background .15s,border-color .15s}
    .serie-nav__btn:hover{background:#fff6e0;border-color:#c9a966}
    .serie-nav__btn--next{text-align:right}
    .serie-nav__btn--disabled{background:transparent;border:1px dashed #e0cfa5;pointer-events:none;opacity:.5}
    .serie-nav__label{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:#9a7a3a;font-weight:600}
    .serie-nav__ep-title{font-size:.92rem;font-weight:600;color:#3a2608;line-height:1.25}
    .serie-nav__arrow{font-size:1rem;color:#8a5a1b}
    @media (max-width:600px){.serie-nav__buttons{grid-template-columns:1fr}.serie-nav__btn--next{text-align:left}}
    .figuier-series-grid,.figuier-dossiers-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.25rem;margin:1.5rem 0}
    .figuier-serie-card,.figuier-dossier-card{background:#fff;border:1px solid #e7d8b8;border-radius:10px;overflow:hidden;transition:transform .15s,box-shadow .15s}
    .figuier-serie-card:hover,.figuier-dossier-card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(90,58,14,.08)}
    .figuier-serie-card__link,.figuier-dossier-card__link{display:block;padding:1.2rem 1.2rem 1rem;color:inherit;text-decoration:none}
    .figuier-serie-card__badge,.figuier-dossier-card__badge{display:inline-block;background:#8a5a1b;color:#fff;font-size:.7rem;letter-spacing:.06em;padding:.2rem .55rem;border-radius:4px;text-transform:uppercase;margin-bottom:.6rem}
    .figuier-dossier-card__badge{background:#5b3a7e}
    .figuier-serie-card__title,.figuier-dossier-card__title{margin:0 0 .5rem;font-size:1.1rem;color:#3a2608;line-height:1.3}
    .figuier-serie-card__desc,.figuier-dossier-card__desc{margin:0 0 .7rem;font-size:.9rem;color:#5a4828;line-height:1.4}
    .figuier-serie-card__meta,.figuier-dossier-card__meta{display:block;font-size:.82rem;color:#9a7a3a;font-weight:600}
    .figuier-empty{padding:2rem;text-align:center;color:#7a5a2a;font-style:italic}
    </style>
    <?php
}, 5 );

/* === FIN CHANTIER A ================================================ */

/**
 * 6. ROBOTS.TXT — declare sitemap
 */
add_filter( 'robots_txt', function ( $output ) {
    $output .= "\nSitemap: " . home_url( '/dictionnaire-biblique/sitemap.xml' ) . "\n";
    return $output;
}, 99 );
   

// Chantier B — Homepage v3 (shortcode [homepage_v3] + taxonomie pilier)
require_once get_stylesheet_directory() . '/inc/homepage-v3.php';

// Chantier A — UI admin pour taxonomies serie/dossier et post-metas
require_once get_stylesheet_directory() . "/inc/serie-dossier-admin.php";

// Chantier Articles Hub — shortcode [articles_hub] + REST endpoint
require_once get_stylesheet_directory() . '/inc/articles-hub.php';

// Chantier A — Colonnes et filtres custom sur /wp-admin/edit.php
require_once get_stylesheet_directory() . "/inc/admin-columns.php";
