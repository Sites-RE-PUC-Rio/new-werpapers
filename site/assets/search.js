(() => {
  const input = document.querySelector("#search");
  const results = document.querySelector("#search-results");
  const status = document.querySelector("#search-status");
  if (!input || !results || !window.WER_SEARCH_INDEX) return;

  const normalize = (value) => String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[-–—_/]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  const abstractSnippet = (abstract, query) => {
    const text = abstract || "";
    const position = normalize(text).indexOf(query);
    if (position < 0) return "";
    let start = Math.max(0, position - 90);
    let end = Math.min(text.length, position + query.length + 130);
    if (start > 0) {
      const nextSpace = text.indexOf(" ", start);
      if (nextSpace > -1 && nextSpace < position) start = nextSpace + 1;
    }
    if (end < text.length) {
      const nextSpace = text.indexOf(" ", end);
      if (nextSpace > -1) end = nextSpace;
    }
    return `${start > 0 ? "…" : ""}${text.slice(start, end)}${end < text.length ? "…" : ""}`;
  };

  input.addEventListener("input", () => {
    const query = normalize(input.value.trim());
    results.replaceChildren();
    if (query.length < 2) {
      status.textContent = "";
      return;
    }
    const ranked = window.WER_SEARCH_INDEX.map((item) => {
      const fields = {
        title: normalize(item.title),
        authors: normalize(item.authors.join(" ")),
        year: normalize(item.year),
        keywords: normalize(item.keywords),
        abstract: normalize(item.abstract),
      };
      let score = 0;
      const matchedFields = [];
      if (fields.title.includes(query)) { score += 1000; matchedFields.push("title"); }
      if (fields.year === query) { score += 900; matchedFields.push("year"); }
      if (fields.authors.includes(query)) { score += 700; matchedFields.push("authors"); }
      if (fields.keywords.includes(query)) { score += 500; matchedFields.push("keywords"); }
      if (fields.abstract.includes(query)) { score += 100; matchedFields.push("abstract"); }
      return {...item, score, matchedFields};
    }).filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || b.year - a.year || a.title.localeCompare(b.title));
    const matches = ranked.slice(0, 100);
    const label = window.WERI18N?.t("search.results") || "resultados";
    status.textContent = `${ranked.length > matches.length ? `${matches.length}+` : matches.length} ${label}`;
    for (const item of matches) {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = new URL(item.url, document.querySelector(".brand").href).href;
      link.textContent = item.title;
      const detail = document.createElement("span");
      detail.textContent = `${item.authors.join("; ")} · ${item.year}`;
      li.append(link, detail);
      const matchHint = document.createElement("p");
      matchHint.className = "search-match";
      const matchLabel = window.WERI18N?.t("search.match") || "Coincidencia en";
      const fieldLabels = item.matchedFields.map((field) => window.WERI18N?.t(`search.field.${field}`) || field);
      matchHint.textContent = `${matchLabel}: ${fieldLabels.join(", ")}`;
      li.append(matchHint);
      if (item.matchedFields.includes("abstract")) {
        const snippet = document.createElement("p");
        snippet.className = "search-snippet";
        snippet.textContent = abstractSnippet(item.abstract, query);
        li.append(snippet);
      }
      results.append(li);
    }
  });
  window.addEventListener("wer:languagechange", () => input.dispatchEvent(new Event("input")));
})();
