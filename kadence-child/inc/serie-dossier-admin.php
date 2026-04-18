<?php
/**
 * Admin UI pour les taxonomies « serie » et « dossier » et leurs post-metas.
 *
 * Voie 2 — Chantier A (UI admin)
 *
 * Fournit :
 *   - Une metabox sur l'écran d'édition des articles pour renseigner
 *     `_serie_order` et `_dossier_order` (entiers positifs), avec un rappel
 *     des termes de série/dossier actuellement attachés.
 *   - Des champs custom sur l'écran d'édition des termes `serie` :
 *       * `_serie_total`               (entier >= 0)
 *       * `_serie_description_court`   (texte court)
 *       * `order`                      (entier — ordre d'affichage dans BLOC 3)
 *       * `image`                      (URL d'illustration)
 *   - Des champs custom sur l'écran d'édition des termes `dossier` :
 *       * `_dossier_description_court` (texte court)
 *       * `order`                      (entier — ordre d'affichage dans BLOC 3)
 *       * `image`                      (URL d'illustration)
 *
 * Tous les champs sont déjà enregistrés via register_post_meta / register_term_meta
 * dans functions.php — ce fichier se contente d'exposer une UI pour les éditer.
 *
 * @package kadence-child
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* =========================================================================
 * 1) METABOX SUR L'ÉCRAN D'ÉDITION DES ARTICLES
 * ========================================================================= */

/**
 * Enregistre la metabox « Série / Dossier — ordre » sur les posts.
 */
function figuier_sda_register_post_metabox() {
	add_meta_box(
		'figuier_serie_dossier_order',
		__( 'Série / Dossier — ordre', 'kadence-child' ),
		'figuier_sda_render_post_metabox',
		'post',
		'side',
		'default'
	);
}
add_action( 'add_meta_boxes', 'figuier_sda_register_post_metabox' );

/**
 * Rend la metabox.
 *
 * @param WP_Post $post Post courant.
 */
function figuier_sda_render_post_metabox( $post ) {
	wp_nonce_field( 'figuier_sda_save_post_meta', 'figuier_sda_post_nonce' );

	$serie_order   = get_post_meta( $post->ID, '_serie_order', true );
	$dossier_order = get_post_meta( $post->ID, '_dossier_order', true );

	$serie_terms   = wp_get_post_terms( $post->ID, 'serie', array( 'fields' => 'all' ) );
	$dossier_terms = wp_get_post_terms( $post->ID, 'dossier', array( 'fields' => 'all' ) );

	echo '<p style="margin-top:0;"><strong>' . esc_html__( 'Série attachée', 'kadence-child' ) . ' :</strong><br>';
	if ( ! is_wp_error( $serie_terms ) && ! empty( $serie_terms ) ) {
		$names = array();
		foreach ( $serie_terms as $t ) {
			$names[] = esc_html( $t->name );
		}
		echo esc_html( implode( ', ', $names ) );
	} else {
		echo '<em>' . esc_html__( 'Aucune', 'kadence-child' ) . '</em>';
	}
	echo '</p>';

	echo '<p><label for="figuier_serie_order"><strong>' . esc_html__( 'Ordre dans la série (_serie_order)', 'kadence-child' ) . '</strong></label><br>';
	echo '<input type="number" min="0" step="1" id="figuier_serie_order" name="figuier_serie_order" value="' . esc_attr( $serie_order ) . '" class="widefat" />';
	echo '<span class="description">' . esc_html__( 'Numéro d\'épisode dans la série. Obligatoire pour apparaître dans l\'archive de série.', 'kadence-child' ) . '</span></p>';

	echo '<hr>';

	echo '<p><strong>' . esc_html__( 'Dossier attaché', 'kadence-child' ) . ' :</strong><br>';
	if ( ! is_wp_error( $dossier_terms ) && ! empty( $dossier_terms ) ) {
		$names = array();
		foreach ( $dossier_terms as $t ) {
			$names[] = esc_html( $t->name );
		}
		echo esc_html( implode( ', ', $names ) );
	} else {
		echo '<em>' . esc_html__( 'Aucun', 'kadence-child' ) . '</em>';
	}
	echo '</p>';

	echo '<p><label for="figuier_dossier_order"><strong>' . esc_html__( 'Ordre dans le dossier (_dossier_order)', 'kadence-child' ) . '</strong></label><br>';
	echo '<input type="number" min="0" step="1" id="figuier_dossier_order" name="figuier_dossier_order" value="' . esc_attr( $dossier_order ) . '" class="widefat" />';
	echo '<span class="description">' . esc_html__( 'Position dans le dossier. Obligatoire pour apparaître dans l\'archive de dossier.', 'kadence-child' ) . '</span></p>';
}

/**
 * Sauvegarde les valeurs de la metabox.
 *
 * @param int $post_id Post ID.
 */
function figuier_sda_save_post_meta( $post_id ) {
	if ( ! isset( $_POST['figuier_sda_post_nonce'] ) ) {
		return;
	}
	if ( ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['figuier_sda_post_nonce'] ) ), 'figuier_sda_save_post_meta' ) ) {
		return;
	}
	if ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) {
		return;
	}
	if ( ! current_user_can( 'edit_post', $post_id ) ) {
		return;
	}
	if ( isset( $_POST['post_type'] ) && 'post' !== $_POST['post_type'] ) {
		return;
	}

	// _serie_order.
	if ( isset( $_POST['figuier_serie_order'] ) && '' !== $_POST['figuier_serie_order'] ) {
		$val = absint( wp_unslash( $_POST['figuier_serie_order'] ) );
		update_post_meta( $post_id, '_serie_order', $val );
	} else {
		delete_post_meta( $post_id, '_serie_order' );
	}

	// _dossier_order.
	if ( isset( $_POST['figuier_dossier_order'] ) && '' !== $_POST['figuier_dossier_order'] ) {
		$val = absint( wp_unslash( $_POST['figuier_dossier_order'] ) );
		update_post_meta( $post_id, '_dossier_order', $val );
	} else {
		delete_post_meta( $post_id, '_dossier_order' );
	}
}
add_action( 'save_post_post', 'figuier_sda_save_post_meta' );

/* =========================================================================
 * 2) CHAMPS CUSTOM SUR L'ÉCRAN D'ÉDITION DES TERMES « serie »
 * ========================================================================= */

/**
 * Rend les champs custom sur l'édition d'un terme « serie ».
 *
 * @param WP_Term $term Term courant.
 */
function figuier_sda_render_serie_fields( $term ) {
	$total       = get_term_meta( $term->term_id, '_serie_total', true );
	$desc_court  = get_term_meta( $term->term_id, '_serie_description_court', true );
	$order       = get_term_meta( $term->term_id, 'order', true );
	$image       = get_term_meta( $term->term_id, 'image', true );

	wp_nonce_field( 'figuier_sda_save_serie_meta', 'figuier_sda_serie_nonce' );
	?>
	<tr class="form-field">
		<th scope="row"><label for="figuier_serie_total"><?php esc_html_e( 'Nombre total d\'épisodes prévus (_serie_total)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="number" min="0" step="1" name="figuier_serie_total" id="figuier_serie_total" value="<?php echo esc_attr( $total ); ?>" />
			<p class="description"><?php esc_html_e( 'Utilisé pour afficher "X / N" et les épisodes "à venir". Laisser 0 si inconnu.', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<tr class="form-field">
		<th scope="row"><label for="figuier_serie_desc_court"><?php esc_html_e( 'Description courte (_serie_description_court)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="text" name="figuier_serie_desc_court" id="figuier_serie_desc_court" value="<?php echo esc_attr( $desc_court ); ?>" style="width:95%;" maxlength="200" />
			<p class="description"><?php esc_html_e( 'Phrase courte affichée en tête de série (env. 150 car. max).', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<tr class="form-field">
		<th scope="row"><label for="figuier_serie_order"><?php esc_html_e( 'Ordre d\'affichage dans BLOC 3 (order)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="number" min="0" step="1" name="figuier_serie_order" id="figuier_serie_order" value="<?php echo esc_attr( $order ); ?>" />
			<p class="description"><?php esc_html_e( 'Plus petit = affiché en premier dans « À la une » de la homepage.', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<tr class="form-field">
		<th scope="row"><label for="figuier_serie_image"><?php esc_html_e( 'URL de l\'image (image)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="url" name="figuier_serie_image" id="figuier_serie_image" value="<?php echo esc_attr( $image ); ?>" style="width:95%;" placeholder="https://..." />
			<p class="description"><?php esc_html_e( 'URL absolue de l\'image affichée dans BLOC 3. Laisser vide pour utiliser l\'image à la une du premier épisode.', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<?php
}
add_action( 'serie_edit_form_fields', 'figuier_sda_render_serie_fields' );

/**
 * Sauvegarde les champs custom du terme « serie ».
 *
 * @param int $term_id Term ID.
 */
function figuier_sda_save_serie_meta( $term_id ) {
	if ( ! isset( $_POST['figuier_sda_serie_nonce'] ) ) {
		return;
	}
	if ( ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['figuier_sda_serie_nonce'] ) ), 'figuier_sda_save_serie_meta' ) ) {
		return;
	}
	if ( ! current_user_can( 'manage_categories' ) ) {
		return;
	}

	if ( isset( $_POST['figuier_serie_total'] ) ) {
		update_term_meta( $term_id, '_serie_total', absint( wp_unslash( $_POST['figuier_serie_total'] ) ) );
	}
	if ( isset( $_POST['figuier_serie_desc_court'] ) ) {
		update_term_meta( $term_id, '_serie_description_court', sanitize_text_field( wp_unslash( $_POST['figuier_serie_desc_court'] ) ) );
	}
	if ( isset( $_POST['figuier_serie_order'] ) && '' !== $_POST['figuier_serie_order'] ) {
		update_term_meta( $term_id, 'order', absint( wp_unslash( $_POST['figuier_serie_order'] ) ) );
	} else {
		delete_term_meta( $term_id, 'order' );
	}
	if ( isset( $_POST['figuier_serie_image'] ) && '' !== $_POST['figuier_serie_image'] ) {
		update_term_meta( $term_id, 'image', esc_url_raw( wp_unslash( $_POST['figuier_serie_image'] ) ) );
	} else {
		delete_term_meta( $term_id, 'image' );
	}
}
add_action( 'edited_serie', 'figuier_sda_save_serie_meta' );

/* =========================================================================
 * 3) CHAMPS CUSTOM SUR L'ÉCRAN D'ÉDITION DES TERMES « dossier »
 * ========================================================================= */

/**
 * Rend les champs custom sur l'édition d'un terme « dossier ».
 *
 * @param WP_Term $term Term courant.
 */
function figuier_sda_render_dossier_fields( $term ) {
	$desc_court = get_term_meta( $term->term_id, '_dossier_description_court', true );
	$order      = get_term_meta( $term->term_id, 'order', true );
	$image      = get_term_meta( $term->term_id, 'image', true );

	wp_nonce_field( 'figuier_sda_save_dossier_meta', 'figuier_sda_dossier_nonce' );
	?>
	<tr class="form-field">
		<th scope="row"><label for="figuier_dossier_desc_court"><?php esc_html_e( 'Description courte (_dossier_description_court)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="text" name="figuier_dossier_desc_court" id="figuier_dossier_desc_court" value="<?php echo esc_attr( $desc_court ); ?>" style="width:95%;" maxlength="200" />
			<p class="description"><?php esc_html_e( 'Phrase courte affichée en tête de dossier (env. 150 car. max).', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<tr class="form-field">
		<th scope="row"><label for="figuier_dossier_order"><?php esc_html_e( 'Ordre d\'affichage dans BLOC 3 (order)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="number" min="0" step="1" name="figuier_dossier_order" id="figuier_dossier_order" value="<?php echo esc_attr( $order ); ?>" />
			<p class="description"><?php esc_html_e( 'Plus petit = affiché en premier dans « À la une » de la homepage.', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<tr class="form-field">
		<th scope="row"><label for="figuier_dossier_image"><?php esc_html_e( 'URL de l\'image (image)', 'kadence-child' ); ?></label></th>
		<td>
			<input type="url" name="figuier_dossier_image" id="figuier_dossier_image" value="<?php echo esc_attr( $image ); ?>" style="width:95%;" placeholder="https://..." />
			<p class="description"><?php esc_html_e( 'URL absolue de l\'image affichée dans BLOC 3. Laisser vide pour utiliser l\'image à la une du premier article.', 'kadence-child' ); ?></p>
		</td>
	</tr>
	<?php
}
add_action( 'dossier_edit_form_fields', 'figuier_sda_render_dossier_fields' );

/**
 * Sauvegarde les champs custom du terme « dossier ».
 *
 * @param int $term_id Term ID.
 */
function figuier_sda_save_dossier_meta( $term_id ) {
	if ( ! isset( $_POST['figuier_sda_dossier_nonce'] ) ) {
		return;
	}
	if ( ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST['figuier_sda_dossier_nonce'] ) ), 'figuier_sda_save_dossier_meta' ) ) {
		return;
	}
	if ( ! current_user_can( 'manage_categories' ) ) {
		return;
	}

	if ( isset( $_POST['figuier_dossier_desc_court'] ) ) {
		update_term_meta( $term_id, '_dossier_description_court', sanitize_text_field( wp_unslash( $_POST['figuier_dossier_desc_court'] ) ) );
	}
	if ( isset( $_POST['figuier_dossier_order'] ) && '' !== $_POST['figuier_dossier_order'] ) {
		update_term_meta( $term_id, 'order', absint( wp_unslash( $_POST['figuier_dossier_order'] ) ) );
	} else {
		delete_term_meta( $term_id, 'order' );
	}
	if ( isset( $_POST['figuier_dossier_image'] ) && '' !== $_POST['figuier_dossier_image'] ) {
		update_term_meta( $term_id, 'image', esc_url_raw( wp_unslash( $_POST['figuier_dossier_image'] ) ) );
	} else {
		delete_term_meta( $term_id, 'image' );
	}
}
add_action( 'edited_dossier', 'figuier_sda_save_dossier_meta' );
