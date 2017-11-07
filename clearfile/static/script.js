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

function buildNoteCard(title, image_link, description, link) {
    var row = document.createElement("div");
    row.classList.add("row");
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
    var description_el = document.createElement("p");
    description_el.appendChild(document.createTextNode(description));
    var card_action = document.createElement("div");
    card_action.classList.add("card-action");
    var note_link = document.createElement("a");
    note_link.href = link;
    note_link.innerHTML = "Download";


    var card = buildDom([row,
                     [card,
                      [card_image,
                       image,
                       card_title],
                      [card_content,
                       description_el],
                      [card_action,
                       note_link]]]);
   return card
}

function addResult(event) {
    if (event.keyCode == 13) {
        var clearfile_search_query = document.getElementById("clearfile-search-input");
        var clearfile_search_results = document.getElementById("clearfile-search-results");
        var card = buildNoteCard(clearfile_search_query.value, "http://via.placeholder.com/300", "Some note of some description", "http://via.placeholder.com/300");
        clearfile_search_results.appendChild(card);
    }
}
