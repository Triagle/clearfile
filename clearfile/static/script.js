function buildDom(nodes) {
    for (let index = 1; index < nodes.length; ++index) {
        let child = nodes[index];
        if (child.constructor === Array) {
            child = buildDom(child);
        }
        root.appendChild(child);
    }
    return root;
}

function addResult(event) {
    if (event.keyCode == 13) {
        var clearfile_search_query = document.getElementById("clearfile-search-input");
        var clearfile_search_results = document.getElementById("clearfile-search-results");
        var row = document.createElement("div");
        row.classList.add("row");
        var card = document.createElement("div");
        card.classList.add("card");
        var card_image = document.createElement("div");
        card_image.classList.add("card-image");
        var image = document.createElement("img");
        image.setAttribute("src", "https://athlonecommunityradio.ie/wp-content/uploads/2017/04/placeholder.png");
        var card_title = document.createElement("span");
        card_title.classList.add("card-title");
        card_title.appendChild(document.createTextNode("Search Result"));
        card_content = document.createElement("div");
        card_content.classList.add("card-content");
        var description = document.createElement("p");
        description.appendChild(document.createTextNode(clearfile_search_query.value));

        card = buildDom([row,
                  [card,
                   [card_image,
                    image,
                    card_title],
                   [card_content,
                    description]]]);

        clearfile_search_results.append(card);
    }
}
