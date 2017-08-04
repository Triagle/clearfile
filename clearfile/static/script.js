function addResult(event) {
    if (event.keyCode == 13) {
        var clearfile_search_query = document.getElementById("clearfile-search-input");
        var clearfile_search_results = document.getElementById("clearfile-search-results");
        var result = document.createElement("li");
        result.classList.add("clearfile-search-result", "base07-background");
        var content = document.createElement("div");
        content.classList.add("clearfile-search-content");
        var title = document.createElement("b");
        title.appendChild(document.createTextNode("Search Query"));
        var description = document.createElement("p");
        description.appendChild(document.createTextNode(clearfile_search_query.value));
        content.appendChild(title);
        content.appendChild(description);
        result.appendChild(content);
        clearfile_search_results.append(result);
    }
}
