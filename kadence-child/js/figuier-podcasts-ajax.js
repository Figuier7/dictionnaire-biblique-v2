jQuery(document).ready(function($){
    let page = 1;

    function loadPodcasts() {
        $.ajax({
            url: figuier_ajax_obj.ajaxurl,
            type: 'POST',
            data: {
                action: 'load_podcasts',
                page: page
            },
            success: function(response){
                $('#figuier-podcast-grid').append(response);
            }
        });
    }

    loadPodcasts(); // Initial load

    $('#load-more-podcasts').on('click', function(){
        page++;
        loadPodcasts();
    });
});