function buildDom(nodes) {
    let root = nodes[0];
    for (let index = 1; index < nodes.length; ++index) {
        let child = nodes[index];
        if (child.constructor === Array) {
            child = buildDom(child);
        }
        root.appendChild(child);
    }
    return root;
}

function emptyNotes() {
    var html = `<div class="col s12 m12 l12" id="no-notes-found">
                    <div class="full-height valign-wrapper">
                        <h2 class="center-align full-width grey-text text-lighten-1">No notes.</h1>
                    </div>
                </div>
                <div class="col s12 m12 l12">
                    <ul id="clearfile-search-results" class="search-results">
                    </ul>
                </div>`;
    var noteResults = $(".search-result-container");
    noteResults.html(html)
}

function buildNoteCard(uuid, title, image_link, tags, link) {
    var column = document.createElement("div");
    column.classList.add("col");
    column.classList.add("s12");
    column.classList.add("m6");
    column.classList.add("l6");
    var card = document.createElement("div");
    card.classList.add("card");
    var card_image = document.createElement("div");
    card_image.classList.add("card-image");
    var image = document.createElement("img");
    image.src = image_link;
    // image.setAttribute("src", image);
    var card_title = document.createElement("span");
    card_title.classList.add("card-title");
    card_title.appendChild(document.createTextNode(title));
    card_content = document.createElement("div");
    card_content.classList.add("card-content");
    for (let tag of tags) {
        var chip = document.createElement("div");
        chip.classList.add("chip");
        chip.innerText = tag.tag;
        var close = document.createElement("i");
        close.classList.add("close");
        close.classList.add("material-icons");
        close.classList.add("kill-tag");
        close.setAttribute("data-tag-id", tag.id);
        close.innerText = "close";
        chip.appendChild(close);
        card_content.appendChild(chip);
    }
    var card_action = document.createElement("div");
    card_action.classList.add("card-action");
    var note_link = document.createElement("a");
    note_link.href = link;
    note_link.innerHTML = "View";
    var delete_link = document.createElement("a");
    delete_link.classList.add("delete-note");
    delete_link.href = "/delete/" + uuid;
    delete_link.innerHTML = "Delete";
    var card = buildDom([column,
                         [card,
                         [card_image,
                          image,
                          card_title],
                         card_content,
                         [card_action,
                          note_link,
                          delete_link]]]);
   return card
}

function addResults(query) {
    var clearfile_search_results = document.getElementById("clearfile-search-results");
    $("#no-notes-found").remove();
    $.get('/search?query=' + query, function (text, status) {
        let json = JSON.parse(text);
        if (json.length === 0) {
            emptyNotes();
        } else {
            for (let card of json) {
                let link = '/uploads/' + card.uuid;
                let dom_card = buildNoteCard(card.uuid, card.name, link, card.tags, link);
                clearfile_search_results.appendChild(dom_card);
            }
        }
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
        let card = $(this).parents("div.card");
        $.get($(this).attr("href"), function (text, status) {
            let response = JSON.parse(text);
            if (response.status === "ok") {
                Materialize.toast("Note Deleted.", 1000);
                var searchList = $(this).parents("clearfile-search-results");
                card.remove();
                if (searchList.children().length === 0) {
                    emptyNotes();
                }
            } else {
                Materialize.toast("Error deleting note.", 1000);
            }
        });
        addResults("");
    });
    $('#form-upload-button').on('click', function() {
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
    });
    $('.search-result-container').on('click', '.kill-tag', function(e){
        let dataId = $(this).attr("data-tag-id");
        $.get("/delete-tag/" + dataId, function (data) {
            Materialize.toast("Tag Deleted.", 1000);
        }).fail(function() {
            Materialize.toast("Error deleting tag.", 1000);
        });
    });
    addResults("");
});
