<?php
/**
 * Colonnes et filtres custom sur l'écran /wp-admin/edit.php (type post).
 *
 * Ajoute trois colonnes : Pilier, Série, Dossier — ainsi que trois filtres
 * dropdown dans la toolbar pour permettre un tri et une recatégorisation
 * rapide des articles.
 *
 * @package kadence-child
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Déclare les colonnes.
 *
 * @param array $cols Colonnes existantes.
 * @return array
 */
function figuier_ac_manage_columns( $cols ) {
	$new = array();
	foreach ( $cols as $key => $label ) {
		$new[ $key ] = $label;
		// Insère les 3 colonnes juste après « Catégories ».
		if ( 'categories' === $key ) {
			$new['figuier_pilier']  = __( 'Pilier', 'kadence-child' );
			$new['figuier_serie']   = __( 'Série', 'kadence-child' );
			$new['figuier_dossier'] = __( 'Dossier', 'kadence-child' );
		}
	}
	// Si « categories » n'existe pas (écrans custom), on ajoute en fin.
	if ( ! isset( $new['figuier_pilier'] ) ) {
		$new['figuier_pilier']  = __( 'Pilier', 'kadence-child' );
		$new['figuier_serie']   = __( 'Série', 'kadence-child' );
		$new['figuier_dossier'] = __( 'Dossier', 'kadence-child' );
	}
	return $new;
}
add_filter( 'manage_post_posts_columns', 'figuier_ac_manage_columns' );

/**
 * Rend le contenu des colonnes.
 *
 * @param string $col     Slug de la colonne.
 * @param int    $post_id Post ID.
 */
function figuier_ac_render_column( $col, $post_id ) {
	$tax_map = array(
		'figuier_pilier'  => 'pilier',
		'figuier_serie'   => 'serie',
		'figuier_dossier' => 'dossier',
	);
	if ( ! isset( $tax_map[ $col ] ) ) {
		return;
	}
	$tax   = $tax_map[ $col ];
	$terms = get_the_terms( $post_id, $tax );
	if ( empty( $terms ) || is_wp_error( $terms ) ) {
		echo '<span style="color:#c00;">—</span>';
		return;
	}
	$links = array();
	foreach ( $terms as $t ) {
		$url     = add_query_arg(
			array(
				'post_type' => 'post',
				$tax        => $t->slug,
			),
			admin_url( 'edit.php' )
		);
		$links[] = '<a href="' . esc_url( $url ) . '">' . esc_html( $t->name ) . '</a>';
	}
	echo wp_kses_post( implode( ', ', $links ) );
}
add_action( 'manage_post_posts_custom_column', 'figuier_ac_render_column', 10, 2 );

/**
 * Rend les filtres dropdown au-dessus de la liste.
 *
 * @param string $post_type Post type courant.
 */
function figuier_ac_restrict_by_taxonomy( $post_type ) {
	if ( 'post' !== $post_type ) {
		return;
	}
	foreach ( array( 'pilier', 'serie', 'dossier' ) as $tax ) {
		if ( ! taxonomy_exists( $tax ) ) {
			continue;
		}
		$selected = isset( $_GET[ $tax ] ) ? sanitize_text_field( wp_unslash( $_GET[ $tax ] ) ) : '';
		$tax_obj  = get_taxonomy( $tax );
		wp_dropdown_categories(
			array(
				'show_option_all' => sprintf( /* translators: %s = taxonomy label */ __( 'Tous les %s', 'kadence-child' ), strtolower( $tax_obj->labels->name ) ),
				'taxonomy'        => $tax,
				'name'            => $tax,
				'orderby'         => 'name',
				'selected'        => $selected,
				'hierarchical'    => (bool) $tax_obj->hierarchical,
				'show_count'      => true,
				'hide_empty'      => false,
				'value_field'     => 'slug',
			)
		);
	}
}
add_action( 'restrict_manage_posts', 'figuier_ac_restrict_by_taxonomy' );

/**
 * Ajoute un style minimal pour les colonnes et rend la colonne Pilier plus visible.
 */
function figuier_ac_admin_head() {
	$screen = function_exists( 'get_current_screen' ) ? get_current_screen() : null;
	if ( ! $screen || 'edit-post' !== $screen->id ) {
		return;
	}
	?>
	<style>
		.column-figuier_pilier  { width: 12%; }
		.column-figuier_serie   { width: 12%; }
		.column-figuier_dossier { width: 12%; }
	</style>
	<?php
}
add_action( 'admin_head', 'figuier_ac_admin_head' );
