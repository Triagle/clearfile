function parseQuery(query) {
    let searchRe = new Map([
        ['at', /@([^\+]+)/g],
        ['notebook', /\+([^@]+)/g],
        ['query', /^([^(\+|@)]+)/g]
    ]);
    let results = Array.from(searchRe.values()).map(re => (re.exec(query) || []).slice(1));
    let zip = (...rows) => [...rows[0]].map((_,c) => rows.map(row => row[c]))
    return new Map(zip(Array.from(searchRe.keys()), results));
}

function queryFromMap(map) {
    var entries = map.entries();
    var [key, value] = entries.next().value;
    return Array.from(entries).reduce((acc, [key, value]) => acc + `&${key}=${value || ''}`.trim(), `?${key}=${value || ''}`.trim());
}

function addResults(query) {
    let formatted_query = queryFromMap(parseQuery(query))
    $.get(SCRIPT_ROOT + '/search' + formatted_query, function (text, status) {
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
         $.ajax({
             type: 'DELETE',
             url: $(this).attr("href"),
             success: function (text, status) {
                 let response = JSON.parse(text);
                 if (response.status === "ok") {
                     Materialize.toast("Note Deleted.", 1000);
                 } else {
                     Materialize.toast("Error deleting note.", 1000);
                 }
                 addResults($("#clearfile-search-input").val());
             }
         });
     });

    $('.search-result-container').on('click', '.update-notebook', function (event) {
        event.preventDefault();
        var notebook = null;
        if (!$(this).hasClass("delete-notebook")) {
            notebook = $(this).attr('data-notebook');
        }
        var data = {
            notebook: notebook
        };
        $.ajax({
            type: 'PATCH',
            url: $(this).attr("href"),
            data: JSON.stringify(data),
            success: function (text, status) {
                addResults($("#clearfile-search-input").val());
            },
            dataType: 'json',
            contentType: 'application/json'
        });
    });

    $('.search-result-container').on('click', '.update-note', function (event) {
        let uuid = $(this).attr('data-note-uuid');
        $.get(SCRIPT_ROOT + '/api/note/' + uuid, function (text, status) {
            let json = JSON.parse(text);
            let tags = json['tags'];
            let title = json['name'];
            $('.chips').material_chip();
            $('#edit-chip').material_chip({
                data: tags.map(note_tag => ({tag: note_tag['tag']}))
            });
            $('#edit-note').modal();
            $('#edit-note').modal('open');
            $('#update-form input[name=title]').val(title);
            $('#update-form input[name=title]').attr('data-note-uuid', uuid);
        })
    });

    $('#modal-update-button').on('click', function (event) {
        $('#update-form').submit();
    })

    $('#update-form').submit(function (event) {
        event.preventDefault();
        var tags = $('#edit-chip').material_chip('data').map(c => c.tag);
        var title_form = $('#update-form input[name=title]');
        var title = title_form.val();
        let uuid = title_form.attr('data-note-uuid');
        var data = {
            tags: tags,
            name: title
        };
        $.ajax({
                type: 'PATCH',
                url: SCRIPT_ROOT + '/api/note/' + uuid,
                data: JSON.stringify(data),
                success: function (text, status) {
                    addResults($("#clearfile-search-input").val());
                },
                dataType: 'json',
                contentType: 'application/json'
        });
    });

    $('.search-result-container').on('click', '.add-notebook-button', function (event){
        $('#add-notebook').modal();
        $('#add-notebook').modal('open');
    });

    $("#notebook-form").submit(function (event) {
        event.preventDefault();
        $.ajax({
            url: SCRIPT_ROOT + "/api/notebook",
            data: new FormData($('#notebook-form')[0]),
            type: 'POST',
            contentType: false,
            processData: false,
            success: function (data, status) {
                addResults($("#clearfile-search-input").val());
                $('#add-notebook').modal('close');
            }
        });
    });

    $('#notebook-add-button').on('click', function() {
        $('#notebook-form').submit();
    });

    $('#upload-form').submit(function (event) {
        event.preventDefault();
        $.ajax({
            // Your server script to process the upload
            url: SCRIPT_ROOT + '/api/note',
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
        $.ajax({
            url: SCRIPT_ROOT + "/api/tag/" + dataId,
            type: 'DELETE',
            success: function (data, status) {
                Materialize.toast("Tag Deleted.", 1000);
            },
            error: function(request, status, errorThrown) {
                Materialize.toast("Error deleting tag.", 1000);
            }
        });
    });

    $('.reset-page').on('click', function () {
        $("#clearfile-search-input").val("");
        addResults("");
    });
    addResults("");
});
