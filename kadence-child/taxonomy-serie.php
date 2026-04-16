<?php
/**
 * Template pour les archives de la taxonomie 'serie'
 * Affichage d'une page récapitulative d'une série
 *
 * @package kadence-child
 */
if ( ! defined( 'ABSPATH' ) ) exit;

get_header();

$term = get_queried_object();
if ( ! $term || is_wp_error( $term ) ) {
    get_footer();
    return;
}

$total_annonce  = (int) get_term_meta( $term->term_id, '_serie_total', true );
$desc_court     = (string) get_term_meta( $term->term_id, '_serie_description_court', true );
$episodes       = figuier_get_serie_episodes( $term->term_id );
$count_publie   = count( $episodes );
$total_affiche  = $total_annonce > 0 ? $total_annonce : $count_publie;
$has_more       = $total_annonce > $count_publie;
?>

<div id="primary" class="content-area figuier-serie-archive">
    <main id="main" class="site-main" role="main">

        <header class="figuier-serie-hero">
            <div class="figuier-serie-hero__inner">
                <span class="figuier-serie-hero__badge">Série</span>
                <h1 class="figuier-serie-hero__title"><?php echo esc_html( $term->name ); ?></h1>
                <?php if ( $desc_court || $term->description ) : ?>
                    <p class="figuier-serie-hero__desc">
                        <?php echo esc_html( $desc_court ?: $term->description ); ?>
                    </p>
                <?php endif; ?>
                <div class="figuier-serie-hero__meta">
                    <span class="figuier-serie-hero__count">
                        <?php echo (int) $count_publie; ?> épisode<?php echo $count_publie > 1 ? 's' : ''; ?> publié<?php echo $count_publie > 1 ? 's' : ''; ?>
                    </span>
                    <?php if ( $has_more ) : ?>
                        <span class="figuier-serie-hero__total">
                            &nbsp;·&nbsp;<?php echo (int) $total_affiche; ?> au total
                        </span>
                    <?php endif; ?>
                </div>
            </div>
        </header>

        <?php if ( ! empty( $episodes ) ) : ?>
            <ol class="figuier-episodes-list" reversed="false">
                <?php foreach ( $episodes as $i => $ep ) :
                    $order = (int) get_post_meta( $ep->ID, '_serie_order', true );
                    if ( ! $order ) $order = $i + 1;
                    $thumb_url = get_the_post_thumbnail_url( $ep->ID, 'medium_large' );
                    $excerpt   = has_excerpt( $ep->ID )
                        ? get_the_excerpt( $ep->ID )
                        : wp_trim_words( wp_strip_all_tags( $ep->post_content ), 38 );
                ?>
                    <li class="figuier-episode-card" value="<?php echo $order; ?>">
                        <a class="figuier-episode-card__link" href="<?php echo esc_url( get_permalink( $ep ) ); ?>">
                            <span class="figuier-episode-card__number">Épisode <?php echo $order; ?>/<?php echo $total_affiche; ?></span>
                            <h2 class="figuier-episode-card__title"><?php echo esc_html( get_the_title( $ep ) ); ?></h2>
                            <?php if ( $thumb_url ) : ?>
                                <img class="figuier-episode-card__thumb" src="<?php echo esc_url( $thumb_url ); ?>" alt="" loading="lazy" />
                            <?php endif; ?>
                            <p class="figuier-episode-card__excerpt"><?php echo esc_html( $excerpt ); ?></p>
                            <span class="figuier-episode-card__cta">Lire l'épisode &rarr;</span>
                        </a>
                    </li>
                <?php endforeach; ?>
            </ol>

            <?php if ( $has_more ) : ?>
                <p class="figuier-serie-hero__waiting">
                    <em><?php echo (int) ( $total_affiche - $count_publie ); ?> épisode<?php echo ( $total_affiche - $count_publie ) > 1 ? 's' : ''; ?> à venir.</em>
                </p>
            <?php endif; ?>
        <?php else : ?>
            <p class="figuier-empty">Cette série ne contient encore aucun épisode publié.</p>
        <?php endif; ?>

    </main>
</div>

<style>
.figuier-serie-archive{max-width:1100px;margin:2rem auto;padding:0 1.25rem}
.figuier-serie-hero{padding:2.5rem 2rem;background:linear-gradient(135deg,#fbf5e8 0%,#f4e4c1 100%);border:1px solid #e7d8b8;border-radius:14px;margin-bottom:2.5rem;text-align:center}
.figuier-serie-hero__inner{max-width:720px;margin:0 auto}
.figuier-serie-hero__badge{display:inline-block;background:#8a5a1b;color:#fff;font-size:.75rem;letter-spacing:.1em;padding:.3rem .8rem;border-radius:4px;text-transform:uppercase;margin-bottom:1rem}
.figuier-serie-hero__title{margin:0 0 .8rem;font-size:clamp(1.7rem,4vw,2.4rem);color:#3a2608;line-height:1.2}
.figuier-serie-hero__desc{margin:0 0 1.2rem;font-size:1.05rem;color:#5a4828;line-height:1.5}
.figuier-serie-hero__meta{font-size:.95rem;color:#8a5a1b;font-weight:600}
.figuier-serie-hero__waiting{text-align:center;color:#9a7a3a;margin:2rem 0}
.figuier-episodes-list{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem;counter-reset:fig-ep}
.figuier-episode-card{position:relative;background:#fff;border:1px solid #e7d8b8;border-radius:12px;overflow:hidden;transition:transform .18s,box-shadow .18s}
.figuier-episode-card:hover{transform:translateY(-3px);box-shadow:0 10px 28px rgba(90,58,14,.12)}
.figuier-episode-card__link{display:flex;flex-direction:column;gap:.6rem;padding:1.3rem;color:inherit;text-decoration:none;height:100%}
.figuier-episode-card__number{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:#8a5a1b;font-weight:700}
.figuier-episode-card__title{margin:0;font-size:1.2rem;color:#3a2608;line-height:1.3}
.figuier-episode-card__thumb{width:100%;border-radius:8px;margin:.4rem 0}
.figuier-episode-card__excerpt{margin:0;font-size:.9rem;color:#5a4828;line-height:1.5;flex-grow:1}
.figuier-episode-card__cta{margin-top:.8rem;font-size:.88rem;font-weight:600;color:#8a5a1b}
@media (max-width:600px){.figuier-serie-hero{padding:1.8rem 1.2rem}.figuier-episodes-list{grid-template-columns:1fr}}
</style>

<?php get_footer();
