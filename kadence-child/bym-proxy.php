<?php
/**
 * BYM Proxy — standalone AJAX handler
 * Fetches BYM markdown from GitLab, caches in WP transients (1h).
 * Loaded via require_once in functions.php.
 */

add_action( 'wp_ajax_figuier_bym_proxy', 'figuier_bym_proxy_handler' );
add_action( 'wp_ajax_nopriv_figuier_bym_proxy', 'figuier_bym_proxy_handler' );

function figuier_bym_proxy_handler() {
	$file = isset( $_GET['file'] ) ? sanitize_file_name( $_GET['file'] ) : '';

	if ( ! preg_match( '/^\d{2}-[A-Za-z0-9]+\.md$/', $file ) ) {
		wp_send_json_error( 'Invalid file', 400 );
		return;
	}

	$cache_key = 'bym_md_' . md5( $file );
	$cached    = get_transient( $cache_key );

	if ( false !== $cached ) {
		header( 'Content-Type: text/plain; charset=utf-8' );
		header( 'X-BYM-Cache: hit' );
		echo $cached;
		wp_die();
	}

	$url      = 'https://gitlab.com/anjc/bjc-source/-/raw/master/' . $file;
	$response = wp_remote_get( $url, array( 'timeout' => 15 ) );

	if ( is_wp_error( $response ) || 200 !== (int) wp_remote_retrieve_response_code( $response ) ) {
		wp_send_json_error( 'Source unavailable', 502 );
		return;
	}

	$body = wp_remote_retrieve_body( $response );
	set_transient( $cache_key, $body, HOUR_IN_SECONDS );

	header( 'Content-Type: text/plain; charset=utf-8' );
	header( 'X-BYM-Cache: miss' );
	echo $body;
	wp_die();
}
