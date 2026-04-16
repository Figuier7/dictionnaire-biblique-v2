<?php
/**
 * Template Name: Accueil personnalisée
 * Description: Page d’accueil en pleine largeur, incluant Hero, grilles dynamiques et outils d’étude.
 */
get_header(); ?>

<main class="figuier-full-layout">

  <!-- 🎯 Hero Banner -->
  <section class="hero">
    <img src="https://alombredufiguier.org/wp-content/uploads/2025/05/LogoSVG_transparent.svg" alt="Logo À l’ombre du figuier">
    <h1>À l’ombre du figuier</h1>
    <h2>Méditer, Étudier, Veiller et se Préparer au Retour du Mashiah</h2>
    <a href="/note-editoriale" class="btn-primary">Découvrir la vision</a>
  </section>

  <!-- 📰 Dernières actualités -->
  <section class="homepage-latest">
    <h2>Dernières actualités</h2>
    <?php if (function_exists('figuier_latest_posts')) {
      echo figuier_latest_posts('actualite');
    } ?>
    <div class="voir-tout-container">
      <a class="btn-voir-tout" href="/actualites">Voir toutes les actualités</a>
    </div>
  </section>

  <!-- ✍️ Études & Réflexions -->
  <section class="homepage-latest">
    <h2>Études & Réflexions</h2>
    <?php if (function_exists('figuier_latest_posts')) {
      echo figuier_latest_posts('post');
    } ?>
    <div class="voir-tout-container">
      <a class="btn-voir-tout" href="/etudes-reflexions">Voir toutes les études</a>
    </div>
  </section>

  <!-- 📖 Témoignages & Réveils -->
  <section class="homepage-latest">
    <h2>Témoignages & Réveils</h2>
    <?php if (function_exists('figuier_latest_posts')) {
      echo figuier_latest_posts('post-temoignages');
    } ?>
    <div class="voir-tout-container">
      <a class="btn-voir-tout" href="/temoignages-reveils">Voir tous les témoignages</a>
    </div>
  </section>

  <!-- 📚 Ouvrages -->
  <section class="homepage-latest">
    <h2>Ouvrages à lire</h2>
    <?php if (function_exists('figuier_latest_posts')) {
      echo figuier_latest_posts('ouvrage');
    } ?>
    <div class="voir-tout-container">
      <a class="btn-voir-tout" href="/ouvrages">Voir tous les ouvrages</a>
    </div>
  </section>

  <!-- 🎧 Podcasts -->
  <section class="homepage-latest">
    <h2>Podcasts récents</h2>
    <?php if (function_exists('figuier_latest_posts')) {
      echo figuier_latest_posts('podcast');
    } ?>
    <div class="voir-tout-container">
      <a class="btn-voir-tout" href="/podcasts">Voir tous les podcasts</a>
    </div>
  </section>

  <!-- 🧰 Bloc outils d’étude -->
  <section class="tools-block">
    <h2>Outils d’étude biblique</h2>
    <p>Explorez nos dictionnaires, encyclopédies, cartes et illustrations bibliques pour enrichir votre compréhension des Écritures.</p>
    <a class="btn-primary" href="/outils-d-etude">Découvrir les outils</a>
  </section>

</main>

<?php get_footer(); ?>