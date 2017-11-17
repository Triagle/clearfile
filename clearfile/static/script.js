function addResults(query) {
    let rx = /(\w+):"([^"]+)"/g;
    let opts = rx.exec(query);
    var search_query = query;
    var opts_string = "";
    if (opts != null) {
        for (var i = 1; i < opts.length; i += 2) {
            opts_string += `&${opts[i]}=${opts[i + 1]}`;
        }
        search_query = query.replace(rx, "").trim();
    }
    $.get('/search?query=' + search_query + opts_string, function (text, status) {
        $(".search-result-container").html(text);
        $('.materialboxed').materialbox();
        $('.dropdown-button').dropdown({
            inDuration: 300,
            outDuration: 225,
            constrainWidth: false, // Does not change width of dropdown to that of the activator
            gutter: 0, // Spacing from edge
            belowOrigin: false, // Displays dropdown below the button
            alignment: 'left', // Displays dropdown with edge aligned to the left of button
            stopPropagation: false // Stops event propagation
        });

    });
}

$(document).ready(function() {
    // the "href" attribute of .modal-trigger must specify the modal ID that wants to be triggered
    $('#upload-button').click(function (){
        $('#upload').modal();
        $('#upload').modal('open');
    });

    $('#upload-file').click(function () {
        $('#upload-form').submit();
    })
    $("#search-form").submit(function(e) {
        e.preventDefault();
        $(".search-results").each(function (index) {
            $(this).empty();
        });
        addResults($("#clearfile-search-input").val());
    });

    $("#clearfile-search-input").val("");

    $('.search-result-container').on('click', '.delete-note', function (event) {
        event.preventDefault();
        $.get($(this).attr("href"), function (text, status) {
            let response = JSON.parse(text);
            if (response.status === "ok") {
                Materialize.toast("Note Deleted.", 1000);
            } else {
                Materialize.toast("Error deleting note.", 1000);
            }
            addResults("");
        });
    });

    $('.search-result-container').on('click', '.update-notebook', function (event) {
        event.preventDefault();
        $.get($(this).attr("href"), function (text, status) {
            addResults("");
        });
    });

    $('.search-result-container').on('click', '.add-notebook-button', function (event){
        $('#add-notebook').modal();
        $('#add-notebook').modal('open');
    });

    $("#notebook-form").submit(function (event) {
        event.preventDefault();
        $.get("/add/notebook?" + $('#notebook-form').serialize(), function (data, status) {
            addResults("");
            $('#add-notebook').modal('close');
        });
    });

    $('#notebook-add-button').on('click', function() {
        $('#notebook-form').submit();
    });

    $('#upload-form').submit(function (event) {
        event.preventDefault();
        $.ajax({
            // Your server script to process the upload
            url: '/upload',
            type: 'POST',
            // Form data
            data: new FormData($('#upload-form')[0]),
            // Tell jQuery not to process data or worry about content-type
            // You *must* include these options!
            cache: false,
            contentType: false,
            processData: false,
        }).done(function (data) {
            addResults("");
        });
    })

    $('#form-upload-button').on('click', function() {
        $('#upload-form').submit();
    });

    $('.search-result-container').on('click', '.kill-tag', function(e){
        let dataId = $(this).attr("data-tag-id");
        $.get("/delete/tag/" + dataId, function (data) {
            Materialize.toast("Tag Deleted.", 1000);
        }).fail(function() {
            Materialize.toast("Error deleting tag.", 1000);
        });
    });

    addResults("");
});
