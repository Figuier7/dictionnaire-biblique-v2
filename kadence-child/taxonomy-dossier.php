<?php
/**
 * Template pour les archives de la taxonomie 'dossier'
 * Page récapitulative d'un dossier thématique
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

$desc_court = (string) get_term_meta( $term->term_id, '_dossier_description_court', true );
$articles   = figuier_get_dossier_articles( $term->term_id );
$count      = count( $articles );
?>

<div id="primary" class="content-area figuier-dossier-archive">
    <main id="main" class="site-main" role="main">

        <header class="figuier-dossier-hero">
            <div class="figuier-dossier-hero__inner">
                <span class="figuier-dossier-hero__badge">Dossier</span>
                <h1 class="figuier-dossier-hero__title"><?php echo esc_html( $term->name ); ?></h1>
                <?php if ( $desc_court || $term->description ) : ?>
                    <p class="figuier-dossier-hero__desc">
                        <?php echo esc_html( $desc_court ?: $term->description ); ?>
                    </p>
                <?php endif; ?>
                <div class="figuier-dossier-hero__meta">
                    <?php echo $count; ?> article<?php echo $count > 1 ? 's' : ''; ?> dans ce dossier
                </div>
            </div>
        </header>

        <?php if ( ! empty( $articles ) ) : ?>
            <div class="figuier-dossier-articles">
                <?php foreach ( $articles as $art ) :
                    $thumb_url = get_the_post_thumbnail_url( $art->ID, 'medium_large' );
                    $excerpt   = has_excerpt( $art->ID )
                        ? get_the_excerpt( $art->ID )
                        : wp_trim_words( wp_strip_all_tags( $art->post_content ), 45 );
                    $date = get_the_date( 'j F Y', $art->ID );
                ?>
                    <article class="figuier-dossier-article">
                        <a class="figuier-dossier-article__link" href="<?php echo esc_url( get_permalink( $art ) ); ?>">
                            <?php if ( $thumb_url ) : ?>
                                <div class="figuier-dossier-article__thumb" style="background-image:url('<?php echo esc_url( $thumb_url ); ?>')"></div>
                            <?php endif; ?>
                            <div class="figuier-dossier-article__body">
                                <time class="figuier-dossier-article__date"><?php echo esc_html( $date ); ?></time>
                                <h2 class="figuier-dossier-article__title"><?php echo esc_html( get_the_title( $art ) ); ?></h2>
                                <p class="figuier-dossier-article__excerpt"><?php echo esc_html( $excerpt ); ?></p>
                                <span class="figuier-dossier-article__cta">Lire l'article &rarr;</span>
                            </div>
                        </a>
                    </article>
                <?php endforeach; ?>
            </div>
        <?php else : ?>
            <p class="figuier-empty">Ce dossier ne contient encore aucun article publié.</p>
        <?php endif; ?>

    </main>
</div>

<style>
.figuier-dossier-archive{max-width:1100px;margin:2rem auto;padding:0 1.25rem}
.figuier-dossier-hero{padding:2.5rem 2rem;background:linear-gradient(135deg,#f4eafe 0%,#e4d4fa 100%);border:1px solid #d4bfe8;border-radius:14px;margin-bottom:2.5rem;text-align:center}
.figuier-dossier-hero__inner{max-width:720px;margin:0 auto}
.figuier-dossier-hero__badge{display:inline-block;background:#5b3a7e;color:#fff;font-size:.75rem;letter-spacing:.1em;padding:.3rem .8rem;border-radius:4px;text-transform:uppercase;margin-bottom:1rem}
.figuier-dossier-hero__title{margin:0 0 .8rem;font-size:clamp(1.7rem,4vw,2.4rem);color:#2a1858;line-height:1.25}
.figuier-dossier-hero__desc{margin:0 0 1.2rem;font-size:1.05rem;color:#4a3868;line-height:1.55}
.figuier-dossier-hero__meta{font-size:.95rem;color:#5b3a7e;font-weight:600}
.figuier-dossier-articles{display:grid;gap:1.5rem}
.figuier-dossier-article{background:#fff;border:1px solid #e7d8e8;border-radius:12px;overflow:hidden;transition:transform .18s,box-shadow .18s}
.figuier-dossier-article:hover{transform:translateY(-3px);box-shadow:0 10px 28px rgba(58,30,90,.1)}
.figuier-dossier-article__link{display:grid;grid-template-columns:260px 1fr;gap:0;color:inherit;text-decoration:none;min-height:180px}
.figuier-dossier-article__thumb{background-size:cover;background-position:center;background-color:#eadff5;min-height:180px}
.figuier-dossier-article__body{padding:1.4rem 1.6rem}
.figuier-dossier-article__date{display:block;font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:#8a6ca4;font-weight:600;margin-bottom:.5rem}
.figuier-dossier-article__title{margin:0 0 .7rem;font-size:1.3rem;color:#2a1858;line-height:1.3}
.figuier-dossier-article__excerpt{margin:0 0 .8rem;font-size:.94rem;color:#4a3868;line-height:1.55}
.figuier-dossier-article__cta{display:inline-block;font-size:.88rem;font-weight:600;color:#5b3a7e}
@media (max-width:720px){.figuier-dossier-article__link{grid-template-columns:1fr}.figuier-dossier-article__thumb{min-height:220px}}
</style>

<?php get_footer();
