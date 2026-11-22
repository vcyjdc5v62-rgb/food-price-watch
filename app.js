// Google Analytics (GA4)
window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }
gtag("js", new Date());
gtag("config", "G-WQXKJFL4K4");

const state = { items: [], category: "すべて", query: "", sort: "default", watch: new Set() };

try {
  const saved = JSON.parse(localStorage.getItem("fpw-watch") || "[]");
  saved.forEach((u) => state.watch.add(u));
} catch (e) {}

function yen(n) {
  return "¥" + Number(n).toLocaleString("ja-JP");
}

function saveWatch() {
  try {
    localStorage.setItem("fpw-watch", JSON.stringify([...state.watch]));
  } catch (e) {}
}

function renderTabs() {
  const cats = ["すべて", ...new Set(state.items.map((i) => i.category))];
  const tabs = document.getElementById("tabs");
  tabs.innerHTML = "";
  cats.forEach((c) => {
    const b = document.createElement("button");
    b.textContent = c;
    b.className = "tab" + (state.category === c ? " active" : "");
    b.addEventListener("click", () => {
      state.category = c;
      render();
    });
    tabs.appendChild(b);
  });
}

function visibleItems() {
  let list = state.items.filter(
    (i) =>
      (state.category === "すべて" || i.category === state.category) &&
      (i.name + i.store).toLowerCase().includes(state.query.toLowerCase())
  );
  if (state.sort === "price-asc") list = [...list].sort((a, b) => a.price - b.price);
  if (state.sort === "price-desc") list = [...list].sort((a, b) => b.price - a.price);
  if (state.sort === "name") list = [...list].sort((a, b) => a.name.localeCompare(b.name, "ja"));
  return list;
}

function render() {
  renderTabs();
  const grid = document.getElementById("grid");
  const list = visibleItems();
  document.getElementById("empty").hidden = list.length > 0;
  grid.innerHTML = "";
  list.forEach((i) => {
    const card = document.createElement("article");
    card.className = "card";
    const watched = state.watch.has(i.url);
    card.innerHTML = `
      <div class="card-top">
        <span class="cat">${i.category}</span>
        <button class="star" aria-label="買い物メモに追加">${watched ? "★" : "☆"}</button>
      </div>
      <h3>${i.name}</h3>
      <p class="price">${yen(i.price)}</p>
      <p class="store">${i.store}</p>
      <a class="buy" href="${i.url}" target="_blank" rel="noopener sponsored">商品を見る</a>`;
    card.querySelector(".star").addEventListener("click", () => {
      if (state.watch.has(i.url)) state.watch.delete(i.url);
      else state.watch.add(i.url);
      saveWatch();
      render();
    });
    grid.appendChild(card);
  });
  renderWatch();
}

function renderWatch() {
  const ul = document.getElementById("watch-list");
  const picked = state.items.filter((i) => state.watch.has(i.url));
  document.getElementById("watch-count").textContent = picked.length ? `（${picked.length}件）` : "";
  ul.innerHTML = "";
  picked.forEach((i) => {
    const li = document.createElement("li");
    li.textContent = `${i.name} — ${yen(i.price)}`;
    ul.appendChild(li);
  });
  const total = picked.reduce((s, i) => s + Number(i.price), 0);
  document.getElementById("watch-total").textContent = picked.length
    ? `合計目安：${yen(total)}（送料別）`
    : "カードの ☆ を押すとメモに追加されます。";
}

async function load() {
  try {
    const res = await fetch("/api/prices");
    const data = await res.json();
    state.items = data.items || [];
    document.getElementById("data-meta").textContent =
      `出典：${data.source}／${data.fetched_at} 時点の価格`;
  } catch (e) {
    document.getElementById("data-meta").textContent = "価格データの読み込みに失敗しました。";
  }
  render();
}

document.getElementById("search").addEventListener("input", (e) => {
  state.query = e.target.value;
  render();
});
document.getElementById("sort").addEventListener("change", (e) => {
  state.sort = e.target.value;
  render();
});

load();
