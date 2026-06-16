const API = "";
let posts = [];
let current = null;
let currentRewrite = null;

// 预设领域；用户也可自定义添加
const PRESET_DOMAINS = ["AI", "人工智能", "情感", "养生", "职场", "科技", "财经", "教育", "健康", "美食"];
let selectedDomains = new Set();

// 数字格式化：>=1万 显示「x.x万」，-1/无数据显示「—」
function fmtNum(n) {
  if (n === undefined || n === null || n < 0) return "—";
  if (n >= 10000) return (n / 10000).toFixed(1).replace(/\.0$/, "") + "万";
  return String(n);
}

const $ = (id) => document.getElementById(id);

function toast(msg, ms = 2200) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.add("hidden"), ms);
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `请求失败 (${res.status})`);
  return data;
}

// ---- 热点列表 ----
async function loadPosts() {
  const kw = $("keywordFilter").value;
  const q = kw ? `?keyword=${encodeURIComponent(kw)}` : "";
  posts = await api(`/api/posts${q}`);
  renderList();
}

function renderList() {
  const box = $("postList");
  $("listCount").textContent = posts.length ? `· ${posts.length} 篇` : "";
  if (!posts.length) {
    box.innerHTML = '<div class="empty">暂无数据，点击「更新热点」抓取</div>';
    return;
  }
  box.innerHTML = posts
    .map(
      (p) => `
    <div class="post-item ${current?.id === p.id ? "active" : ""}" data-id="${p.id}">
      <h4>${escapeHtml(p.title)}</h4>
      <div class="sub">
        <span class="badge">🔥 ${Math.round(p.hotness)}</span>
        <span class="tag">${escapeHtml(p.keyword || "热点")}</span>
        <span>${escapeHtml(p.account || "")}</span>
        ${p.rewrite_count ? `<span class="rw-count">✓ 已改写${p.rewrite_count}</span>` : ""}
      </div>
      <div class="metrics">
        <span title="点赞量">👍 ${fmtNum(p.likes)}</span>
        <span title="转发量">🔁 ${fmtNum(p.shares)}</span>
        <span title="收藏量">⭐ ${fmtNum(p.favorites)}</span>
        <span title="评论量">💬 ${fmtNum(p.comments)}</span>
      </div>
    </div>`
    )
    .join("");
  box.querySelectorAll(".post-item").forEach((el) =>
    el.addEventListener("click", () => selectPost(+el.dataset.id))
  );
}

function refreshKeywordOptions() {
  const sel = $("keywordFilter");
  const cur = sel.value;
  const kws = [...new Set(posts.map((p) => p.keyword).filter(Boolean))];
  sel.innerHTML =
    '<option value="">全部话题</option>' +
    kws.map((k) => `<option value="${escapeHtml(k)}">${escapeHtml(k)}</option>`).join("");
  sel.value = cur;
}

// ---- 选中文章 ----
async function selectPost(id) {
  current = await api(`/api/posts/${id}`);
  renderList();
  $("workEmpty").classList.add("hidden");
  $("workArea").classList.remove("hidden");
  $("rewriteResult").classList.add("hidden");

  $("origTitle").textContent = current.title;
  $("origAccount").textContent = current.account || "未知来源";
  $("origHotness").textContent = `🔥 ${Math.round(current.hotness)}`;
  const link = $("origLink");
  if (current.url) { link.href = current.url; link.style.display = ""; }
  else link.style.display = "none";
  $("origContent").textContent = current.content || current.summary || "（未抓到正文，将基于标题/摘要进行改写）";
}

// ---- 改写 ----
async function doRewrite() {
  if (!current) return;
  const btn = $("rewriteBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 改写中…';
  try {
    const body = {
      style: $("styleSelect").value,
      extra_instruction: $("extraInput").value.trim(),
    };
    const r = await api(`/api/posts/${current.id}/rewrite`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    showRewrite(r);
    loadPosts(); // 更新「已改写」标记
  } catch (e) {
    toast("❌ " + e.message, 3500);
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ 开始改写";
  }
}

function showRewrite(r) {
  currentRewrite = r;
  $("rewriteResult").classList.remove("hidden");
  $("rwTitle").textContent = r.new_title;
  $("rwContent").textContent = r.content;
  renderTitleOptions(r.title_options || []);
  $("coverBox").classList.add("hidden"); // 新改写重置封面
  $("schedForm").classList.add("hidden");

  const pct = Math.round((1 - r.similarity) * 100); // 原创度
  const badge = $("origScore");
  let cls = "good", note = "原创度高";
  if (pct < 60) { cls = "bad"; note = "与原文较接近，建议再改"; }
  else if (pct < 80) { cls = "warn"; note = "原创度中等"; }
  badge.className = "orig-badge " + cls;
  badge.textContent = `原创度 ${pct}% · ${note}`;

  checkModeration(); // 自动跑一次合规检测
}

// ---- 多标题候选 ----
function renderTitleOptions(opts) {
  const box = $("titleOptions");
  if (!opts.length) { box.innerHTML = ""; return; }
  box.innerHTML =
    '<span class="opt-label">备选标题（点击替换）：</span>' +
    opts
      .map((t, i) => `<span class="title-chip" data-i="${i}">${escapeHtml(t)}</span>`)
      .join("");
  box.querySelectorAll(".title-chip").forEach((el) =>
    el.addEventListener("click", () => {
      $("rwTitle").textContent = opts[+el.dataset.i];
    })
  );
}

// ---- 合规检测 ----
async function checkModeration() {
  try {
    const r = await api("/api/moderation/check", {
      method: "POST",
      body: JSON.stringify({
        title: $("rwTitle").textContent.trim(),
        content: $("rwContent").textContent.trim(),
      }),
    });
    renderModeration(r);
  } catch (e) {
    /* 检测失败不阻断主流程 */
  }
}

function renderModeration(r) {
  const badge = $("modBadge");
  const hits = $("modHits");
  if (r.ok) {
    badge.className = "mod-badge ok";
    badge.textContent = "✅ 未发现违规词";
    hits.innerHTML = "";
    return;
  }
  badge.className = "mod-badge risk";
  badge.textContent = `⚠️ 发现 ${r.risk} 处风险词`;
  hits.innerHTML = r.hits
    .map(
      (h) => `
    <div class="mod-hit">
      <span class="mod-cat">${escapeHtml(h.label)}</span>
      <span class="mod-word">「${escapeHtml(h.word)}」×${h.count}</span>
      <span class="mod-advice">${escapeHtml(h.advice)}</span>
    </div>`
    )
    .join("");
}

function copyAll() {
  const text = $("rwTitle").textContent + "\n\n" + $("rwContent").textContent;
  navigator.clipboard.writeText(text).then(
    () => toast("✅ 已复制，可粘贴到公众号后台"),
    () => toast("复制失败，请手动选择")
  );
}

// ---- 定时发布 ----
function toggleSchedForm() {
  const f = $("schedForm");
  f.classList.toggle("hidden");
  if (!f.classList.contains("hidden") && !$("schedTime").value) {
    // 默认填 1 小时后
    const d = new Date(Date.now() + 3600 * 1000 - new Date().getTimezoneOffset() * 60000);
    $("schedTime").value = d.toISOString().slice(0, 16);
  }
}

async function confirmSchedule() {
  if (!currentRewrite) return;
  const t = $("schedTime").value;
  if (!t) { toast("请选择发布时间"); return; }
  const btn = $("schedConfirm");
  btn.disabled = true;
  try {
    await api(`/api/rewrites/${currentRewrite.id}/schedule`, {
      method: "POST",
      body: JSON.stringify({
        scheduled_at: t,
        action: $("schedAction").value,
        title: $("rwTitle").textContent.trim(),
        content: $("rwContent").textContent.trim(),
      }),
    });
    toast("✅ 已排期，到点自动执行");
    $("schedForm").classList.add("hidden");
  } catch (e) {
    toast("❌ " + e.message, 4000);
  } finally {
    btn.disabled = false;
  }
}

const STATUS_LABEL = {
  pending: "⏳ 待执行", done: "✅ 已完成", failed: "❌ 失败", canceled: "🚫 已取消",
};

async function openSchedList() {
  $("schedOverlay").classList.remove("hidden");
  const box = $("schedList");
  box.innerHTML = '<div class="empty">加载中…</div>';
  try {
    const items = await api("/api/schedules");
    if (!items.length) { box.innerHTML = '<div class="empty">暂无排期</div>'; return; }
    box.innerHTML = items
      .map(
        (s) => `
      <div class="sched-item">
        <div class="sched-main">
          <div class="sched-title">${escapeHtml(s.title_snapshot || "(无标题)")}</div>
          <div class="sched-sub">
            <span>${s.scheduled_at.replace("T", " ").slice(0, 16)}</span>
            <span class="tag">${s.action === "publish" ? "自动发表" : "存草稿"}</span>
            <span>${STATUS_LABEL[s.status] || s.status}</span>
          </div>
          ${s.result ? `<div class="sched-result">${escapeHtml(s.result)}</div>` : ""}
        </div>
        ${s.status === "pending" ? `<button class="btn small cancel-sched" data-id="${s.id}">取消</button>` : ""}
      </div>`
      )
      .join("");
    box.querySelectorAll(".cancel-sched").forEach((el) =>
      el.addEventListener("click", () => cancelSchedule(+el.dataset.id))
    );
  } catch (e) {
    box.innerHTML = `<div class="empty">加载失败：${escapeHtml(e.message)}</div>`;
  }
}

async function cancelSchedule(id) {
  try {
    await api(`/api/schedules/${id}`, { method: "DELETE" });
    openSchedList();
  } catch (e) {
    toast("❌ " + e.message, 3500);
  }
}

async function genCover() {
  if (!currentRewrite) return;
  const btn = $("coverBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 生成中…';
  try {
    const r = await api(`/api/rewrites/${currentRewrite.id}/cover`, { method: "POST" });
    $("coverImg").src = r.url + "?t=" + Date.now();
    $("coverBox").classList.remove("hidden");
    toast("✅ " + (r.message || "封面已生成"), 3000);
  } catch (e) {
    toast("❌ " + e.message, 4500);
  } finally {
    btn.disabled = false;
    btn.textContent = "🖼️ 生成封面";
  }
}

async function pushDraft() {
  if (!currentRewrite) return;
  const btn = $("draftBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 推送中…';
  try {
    // 推送页面上（可能已手动编辑过的）最新内容
    const body = {
      title: $("rwTitle").textContent.trim(),
      content: $("rwContent").textContent.trim(),
    };
    const r = await api(`/api/rewrites/${currentRewrite.id}/draft`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    toast("✅ " + (r.message || "已存入草稿箱"), 3500);
  } catch (e) {
    toast("❌ " + e.message, 4500);
  } finally {
    btn.disabled = false;
    btn.textContent = "📤 存公众号草稿";
  }
}

// ---- 领域选择 ----
function renderDomainChips() {
  const box = $("domainChips");
  box.innerHTML = PRESET_DOMAINS.map(
    (d) =>
      `<span class="domain-chip ${selectedDomains.has(d) ? "active" : ""}" data-d="${escapeHtml(d)}">${escapeHtml(d)}</span>`
  ).join("");
  box.querySelectorAll(".domain-chip").forEach((el) =>
    el.addEventListener("click", () => {
      const d = el.dataset.d;
      selectedDomains.has(d) ? selectedDomains.delete(d) : selectedDomains.add(d);
      renderDomainChips();
    })
  );
}

function addCustomDomain(e) {
  if (e.key !== "Enter") return;
  const v = e.target.value.trim();
  if (v) {
    if (!PRESET_DOMAINS.includes(v)) PRESET_DOMAINS.push(v);
    selectedDomains.add(v);
    e.target.value = "";
    renderDomainChips();
  }
}

// ---- 更新热点 ----
async function refresh() {
  const btn = $("refreshBtn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 抓取中…';
  try {
    const r = await api("/api/posts/refresh", {
      method: "POST",
      body: JSON.stringify({ domains: [...selectedDomains] }),
    });
    await loadPosts();
    refreshKeywordOptions();
    let msg = `✅ 抓取 ${r.fetched} 篇，新增 ${r.new} 篇`;
    if (r.message) msg += `（${r.message}）`;
    toast(msg, 3500);
  } catch (e) {
    toast("❌ " + e.message, 3500);
  } finally {
    btn.disabled = false;
    btn.textContent = "🔥 更新热点";
  }
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

// ---- 初始化 ----
$("refreshBtn").addEventListener("click", refresh);
$("rewriteBtn").addEventListener("click", doRewrite);
$("copyBtn").addEventListener("click", copyAll);
$("draftBtn").addEventListener("click", pushDraft);
$("recheckBtn").addEventListener("click", checkModeration);
$("coverBtn").addEventListener("click", genCover);
$("schedBtn").addEventListener("click", toggleSchedForm);
$("schedConfirm").addEventListener("click", confirmSchedule);
$("schedListBtn").addEventListener("click", openSchedList);
$("schedClose").addEventListener("click", () => $("schedOverlay").classList.add("hidden"));
$("customDomain").addEventListener("keydown", addCustomDomain);

renderDomainChips();
$("keywordFilter").addEventListener("change", loadPosts);

loadPosts().then(refreshKeywordOptions).catch(() => {});
