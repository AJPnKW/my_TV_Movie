self.onmessage = (event) => {
  const { channels, query, category, sort, favoritesOnly, favorites, names } = event.data;
  const normalizedQuery = String(query || "").trim().toLowerCase();
  const favoriteSet = new Set(favorites || []);
  const renamed = names || {};

  const rows = (channels || []).filter((channel) => {
    if (favoritesOnly && !favoriteSet.has(channel.id)) return false;
    if (category && category !== "all" && channel.category !== category) return false;
    if (!normalizedQuery) return true;

    const haystack = [
      channel.name,
      renamed[channel.id],
      channel.category,
      ...(channel.altNames || []),
      ...(channel.owners || []),
    ].join(" ").toLowerCase();

    return haystack.includes(normalizedQuery);
  });

  rows.sort((a, b) => {
    if (sort === "favorites") {
      const favDelta = Number(favoriteSet.has(b.id)) - Number(favoriteSet.has(a.id));
      if (favDelta) return favDelta;
    }
    if (sort === "category") {
      const catDelta = String(a.category).localeCompare(String(b.category));
      if (catDelta) return catDelta;
    }
    const aName = renamed[a.id] || a.displayName || a.name;
    const bName = renamed[b.id] || b.displayName || b.name;
    return String(aName).localeCompare(String(bName), "hu", { sensitivity: "base" });
  });

  self.postMessage({ rows });
};
