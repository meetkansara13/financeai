/* ═══════════════════════════════════════════════
   FINANCE AI — DASHBOARD ENGINE v12
   All sections properly bound & styled
═══════════════════════════════════════════════ */

const token = localStorage.getItem("token");
if (!token) window.location.href = "/login";

let dashboardData = null;
let currentMode   = "monthly";
let trendChart    = null;
let donutChart    = null;
let botHistory    = [];

const CAT_ICONS = {
    food:"🍔", transport:"🚗", shopping:"🛍️", entertainment:"🎬",
    sports:"⚽", health:"💊", utilities:"💡", assets:"💰",
    income:"💵", groceries:"🛒", rent:"🏠", travel:"✈️",
    education:"📚", bills:"🧾", salary:"💼", other:"📦"
};
const CAT_COLORS = {
    food:"rgba(245,158,11,.12)",      transport:"rgba(59,130,246,.12)",
    shopping:"rgba(139,92,246,.12)",  entertainment:"rgba(236,72,153,.12)",
    health:"rgba(16,185,129,.12)",    utilities:"rgba(99,209,255,.12)",
    assets:"rgba(245,200,66,.12)",    income:"rgba(16,185,129,.12)",
    groceries:"rgba(245,158,11,.12)", rent:"rgba(244,63,94,.12)",
    travel:"rgba(14,165,233,.12)",    education:"rgba(139,92,246,.12)",
    salary:"rgba(16,185,129,.12)",    other:"rgba(148,163,184,.1)"
};

const fmt = v => "₹" + Number(v||0).toLocaleString("en-IN");
const setText = (id, v) => { const el = document.getElementById(id); if (el) el.innerText = v; };

/* ─── GREETING & NAME ─── */
(function initGreeting() {
    const hr = new Date().getHours();
    const greet = hr < 12 ? "Good morning" : hr < 17 ? "Good afternoon" : "Good evening";
    const el = document.querySelector(".hero-greeting");
    if (el) el.textContent = greet + " 👋";
    try {
        const p = JSON.parse(atob(token.split(".")[1]));
        const raw = p.sub?.split("@")[0] || "";
        const name = raw.split(/[._]/).map(w => w[0]?.toUpperCase() + w.slice(1)).join(" ");
        setText("heroName", name);
        document.getElementById("notifBadge").style.display = "block";
    } catch(e) {}
})();

/* ─── INIT ─── */
document.addEventListener("DOMContentLoaded", () => {
    const sel = document.getElementById("monthSelector");
    if (sel) sel.value = new Date().getMonth() + 1;
    loadDashboard();
    setupSmartInput();
    setupBotInput();
    loadNewsInsights();
    setInterval(loadNewsInsights, 15 * 60 * 1000);
});

/* ─── LOAD ALL DATA ─── */
async function loadDashboard() {
    const month = document.getElementById("monthSelector")?.value || new Date().getMonth() + 1;
    const year  = new Date().getFullYear();

    // Show skeletons
    showSkeleton("historyList", 5);
    showSkeleton("budgetList", 3);

    try {
        const res = await fetch(`/api/v1/dashboard-overview?month=${month}&year=${year}`, {
            headers: { Authorization: "Bearer " + token }
        });
        dashboardData = await res.json();
        renderKPIs();
    } catch(e) {}

    loadTrendChart();
    loadDonutChart(month, year);
    loadPrediction(month, year);
    loadRecentTransactions(month, year);
    loadBudgets(month, year);
}

/* ─── SKELETON LOADER ─── */
function showSkeleton(containerId, count) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = Array(count).fill(0).map(() => `
        <div style="display:flex;align-items:center;gap:12px;padding:13px 16px;border-bottom:1px solid rgba(255,255,255,.04);">
            <div class="skeleton" style="width:40px;height:40px;border-radius:12px;flex-shrink:0;"></div>
            <div style="flex:1;">
                <div class="skeleton" style="height:13px;width:60%;border-radius:6px;margin-bottom:6px;"></div>
                <div class="skeleton" style="height:10px;width:40%;border-radius:6px;"></div>
            </div>
            <div class="skeleton" style="height:16px;width:70px;border-radius:6px;"></div>
        </div>`).join("");
}

/* ─── KPIs ─── */
function renderKPIs() {
    if (!dashboardData) return;
    const m = dashboardData.monthly || {};
    const o = dashboardData.overall || {};

    if (currentMode === "monthly") {
        setText("kpi1Value", fmt(m.income));
        setText("kpi2Value", fmt(m.expense));
        setText("kpi3Value", fmt(m.savings));
        setText("kpi4Value", fmt(o?.net_worth));
        // Trend arrows
        setTrend("kpi1Trend", m.income, m.prev_income);
        setTrend("kpi2Trend", m.expense, m.prev_expense, true);
        setTrend("kpi3Trend", m.savings, m.prev_savings);
    } else {
        setText("kpi1Value", fmt(o?.assets));
        setText("kpi2Value", fmt(o?.liabilities));
        setText("kpi3Value", (o?.debt_ratio || 0) + "%");
        setText("kpi4Value", fmt(o?.net_worth));
    }
}

function setTrend(id, curr, prev, invertGood) {
    const el = document.getElementById(id);
    if (!el || !prev) return;
    const pct = ((curr - prev) / (prev || 1) * 100).toFixed(1);
    const up = curr >= prev;
    const good = invertGood ? !up : up;
    el.textContent = (up ? "↑" : "↓") + " " + Math.abs(pct) + "%";
    el.style.color = good ? "#10b981" : "#f43f5e";
    el.style.display = "inline-block";
}

function setView(mode) {
    currentMode = mode;
    document.getElementById("monthlyBtn").classList.toggle("active", mode === "monthly");
    document.getElementById("overallBtn").classList.toggle("active", mode === "overall");
    renderKPIs();
}

/* ─── TREND CHART ─── */
async function loadTrendChart() {
    const canvas = document.getElementById("trendChart");
    if (!canvas) return;
    try {
        const res  = await fetch("/api/v1/monthly-trend", { headers: { Authorization: "Bearer " + token } });
        const data = await res.json();
        if (trendChart) trendChart.destroy();
        trendChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: data.labels || [],
                datasets: [
                    { label:"Income",  data:data.income||[],  borderColor:"#10b981", backgroundColor:"rgba(16,185,129,0.08)", fill:true, tension:0.4, pointRadius:4, pointBackgroundColor:"#10b981", borderWidth:2.5 },
                    { label:"Expense", data:data.expense||[], borderColor:"#f43f5e", backgroundColor:"rgba(244,63,94,0.08)",  fill:true, tension:0.4, pointRadius:4, pointBackgroundColor:"#f43f5e", borderWidth:2.5 }
                ]
            },
            options: {
                responsive:true, maintainAspectRatio:false,
                plugins: {
                    legend: { labels:{ color:"#64748b", font:{size:12,family:"Nunito"}, boxWidth:10, padding:16 } },
                    tooltip: { backgroundColor:"rgba(15,22,35,.95)", titleColor:"#f1f5f9", bodyColor:"#94a3b8", borderColor:"rgba(255,255,255,.08)", borderWidth:1, padding:10,
                        callbacks:{ label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.raw)}` } }
                },
                scales: {
                    x: { ticks:{ color:"#334155", font:{size:11} }, grid:{ color:"rgba(255,255,255,0.03)" } },
                    y: { ticks:{ color:"#334155", font:{size:11}, callback:v => "₹"+Number(v).toLocaleString("en-IN") }, grid:{ color:"rgba(255,255,255,0.03)" } }
                }
            }
        });
    } catch(e) {}
}

/* ─── DONUT CHART ─── */
async function loadDonutChart(month, year) {
    const canvas = document.getElementById("donutChart");
    if (!canvas) return;
    try {
        const res  = await fetch(`/api/v1/category-breakdown-month?month=${month}&year=${year}`, { headers:{ Authorization:"Bearer "+token } });
        const data = await res.json();
        if (donutChart) donutChart.destroy();
        if (!data.labels || !data.labels.length) {
            canvas.parentElement.innerHTML = `<div class="empty-state" style="padding:32px 0;"><div class="empty-state-icon">🍩</div><div class="empty-state-text">No expense data yet this month</div></div>`;
            return;
        }
        const COLORS = ["#f5c842","#3b82f6","#10b981","#f43f5e","#8b5cf6","#f97316","#06b6d4","#ec4899","#34d399","#94a3b8"];
        donutChart = new Chart(canvas, {
            type:"doughnut",
            data: {
                labels: data.labels.map(l => l.charAt(0).toUpperCase()+l.slice(1)),
                datasets:[{ data:data.values, backgroundColor:COLORS.slice(0,data.labels.length), borderColor:"#0f1623", borderWidth:3, hoverOffset:10 }]
            },
            options: {
                responsive:true, maintainAspectRatio:false, cutout:"68%",
                plugins: {
                    legend:{ position:"bottom", labels:{ color:"#64748b", font:{size:11,family:"Nunito"}, padding:10, boxWidth:10 } },
                    tooltip:{ backgroundColor:"rgba(15,22,35,.95)", titleColor:"#f1f5f9", bodyColor:"#94a3b8", borderColor:"rgba(255,255,255,.08)", borderWidth:1, padding:10,
                        callbacks:{ label: ctx => ` ${ctx.label}: ${fmt(ctx.raw)}` } }
                }
            }
        });
    } catch(e) {}
}

/* ─── PREDICTION ─── */
async function loadPrediction(month, year) {
    try {
        const res  = await fetch(`/api/v1/savings-prediction?month=${month}&year=${year}`, { headers:{ Authorization:"Bearer "+token } });
        const data = await res.json();
        setText("predictionValue", fmt(data.predicted_savings));
        setText("predictionMsg",   data.savings_message || "Forecast ready");
        // Color based on positive/negative
        const val = Number(data.predicted_savings || 0);
        const el = document.getElementById("predictionValue");
        if (el) el.style.color = val >= 0 ? "#10b981" : "#f43f5e";
    } catch(e) {}
}

/* ─── RECENT TRANSACTIONS — properly styled ─── */
async function loadRecentTransactions(month, year) {
    const el = document.getElementById("historyList");
    if (!el) return;
    try {
        const res  = await fetch(`/api/v1/recent-transactions?month=${month}&year=${year}`, { headers:{ Authorization:"Bearer "+token } });
        const data = await res.json();

        if (!data.length) {
            el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">💸</div><div class="empty-state-title">No transactions yet</div><div class="empty-state-text">Add your first transaction using the smart bar above</div></div>`;
            return;
        }

        el.innerHTML = data.map(t => {
            const cat   = (t.category || "other").toLowerCase();
            const icon  = t.type === "income" ? "💵" : (CAT_ICONS[cat] || "📦");
            const color = CAT_COLORS[cat] || "rgba(148,163,184,.1)";
            const isInc = t.type === "income";
            const amt   = fmt(t.amount);
            const desc  = t.description || t.category || "Transaction";
            // Format date nicely
            const dateStr = formatDate(t.date);
            return `
            <div class="txn-row" onclick="void(0)">
                <div class="txn-icon-wrap" style="background:${color};">
                    <span style="font-size:18px;">${icon}</span>
                </div>
                <div class="txn-info">
                    <div class="txn-name">${cap(desc)}</div>
                    <div class="txn-meta">
                        <span style="text-transform:capitalize;">${cat}</span>
                        <span style="margin:0 4px;color:#1e293b;">·</span>
                        <span>${dateStr}</span>
                    </div>
                </div>
                <div style="text-align:right;flex-shrink:0;">
                    <div class="txn-amount hide-amount" style="color:${isInc ? '#10b981' : '#f43f5e'};">
                        ${isInc ? "+" : "-"}${amt}
                    </div>
                    <div style="font-size:10px;color:#334155;margin-top:2px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;">
                        ${t.type}
                    </div>
                </div>
            </div>`;
        }).join("");
    } catch(e) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Failed to load transactions</div></div>`;
    }
}

/* ─── BUDGETS — properly styled ─── */
async function loadBudgets(month, year) {
    const el = document.getElementById("budgetList");
    if (!el) return;
    try {
        const res  = await fetch(`/api/v1/budgets-status?month=${month}&year=${year}`, { headers:{ Authorization:"Bearer "+token } });
        const data = await res.json();

        if (!data.length) {
            el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🎯</div><div class="empty-state-title">No budgets set</div><div class="empty-state-text">Set spending limits to track your goals</div><a href="/budgets" style="margin-top:12px;padding:9px 20px;background:rgba(245,200,66,.12);border:1px solid rgba(245,200,66,.2);border-radius:10px;color:#f5c842;font-size:13px;font-weight:700;text-decoration:none;">+ Add Budget</a></div>`;
            return;
        }

        el.innerHTML = data.map(b => {
            const pct   = Math.min(Math.round(b.percentage || 0), 100);
            const over  = b.percentage >= 100;
            const warn  = b.percentage >= 80 && !over;
            const color = over ? "#f43f5e" : warn ? "#f59e0b" : "#10b981";
            const bgcol = over ? "rgba(244,63,94,.1)" : warn ? "rgba(245,158,11,.1)" : "rgba(16,185,129,.1)";
            const cat   = (b.category || "other").toLowerCase();
            const icon  = CAT_ICONS[cat] || "📦";
            const remaining = b.limit - b.spent;
            return `
            <div class="budget-row">
                <div class="budget-row-top">
                    <div class="budget-cat">
                        <div class="budget-cat-icon" style="background:${bgcol};">${icon}</div>
                        <div>
                            <div class="budget-cat-name">${cap(b.category)}</div>
                            <div class="budget-cat-sub">${over ? "⚠️ Over limit" : warn ? "⚠️ Near limit" : remaining > 0 ? fmt(remaining)+" left" : "On track"}</div>
                        </div>
                    </div>
                    <div class="budget-amount-info">
                        <div class="budget-spent" style="color:${color};">${fmt(b.spent)}</div>
                        <div class="budget-limit">of ${fmt(b.limit)}</div>
                    </div>
                </div>
                <div style="position:relative;height:6px;background:rgba(255,255,255,.06);border-radius:6px;overflow:hidden;">
                    <div style="position:absolute;left:0;top:0;height:100%;width:${pct}%;background:${color};border-radius:6px;transition:width .6s ease;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:5px;">
                    <span style="font-size:10px;color:#334155;font-weight:700;">${pct}% used</span>
                    <span style="font-size:10px;color:#334155;font-weight:700;">${fmt(b.limit)} limit</span>
                </div>
            </div>`;
        }).join("");
    } catch(e) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><div class="empty-state-text">Failed to load budgets</div></div>`;
    }
}

/* ─── NEWS INSIGHTS ─── */
async function loadNewsInsights() {
    const list = document.getElementById("newsInsightsList");
    const subtitle = document.getElementById("newsFetchedAt");
    if (!list) return;

    list.innerHTML = Array(3).fill(0).map(() => `
        <div style="display:flex;gap:12px;padding:13px 16px;border-bottom:1px solid rgba(255,255,255,.04);">
            <div class="skeleton" style="width:36px;height:36px;border-radius:10px;flex-shrink:0;"></div>
            <div style="flex:1;">
                <div class="skeleton" style="height:11px;width:80%;border-radius:5px;margin-bottom:6px;"></div>
                <div class="skeleton" style="height:13px;width:60%;border-radius:5px;margin-bottom:5px;"></div>
                <div class="skeleton" style="height:10px;width:30%;border-radius:5px;"></div>
            </div>
        </div>`).join("");

    try {
        const res  = await fetch("/api/v1/news-insights", { headers:{ Authorization:"Bearer "+token } });
        const data = await res.json();
        if (subtitle && data.fetched_at) subtitle.textContent = data.fetched_at;

        if (!data.insights || !data.insights.length) {
            list.innerHTML = `<div class="empty-state" style="padding:24px;"><div class="empty-state-text">No major signals right now. Check back soon.</div></div>`;
            return;
        }

        list.innerHTML = data.insights.map(item => {
            const impactColor = item.impact === "positive" ? "#10b981" : item.impact === "negative" ? "#f43f5e" : "#f59e0b";
            const impactBg    = item.impact === "positive" ? "rgba(16,185,129,.1)" : item.impact === "negative" ? "rgba(244,63,94,.1)" : "rgba(245,158,11,.1)";
            const impactLabel = item.impact === "positive" ? "Positive" : item.impact === "negative" ? "Negative" : "Neutral";
            return `
            <div style="display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-bottom:1px solid rgba(255,255,255,.04);">
                <div style="width:38px;height:38px;border-radius:11px;background:${impactBg};display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;">${item.icon || "📰"}</div>
                <div style="flex:1;">
                    <div style="font-size:12px;color:#475569;margin-bottom:4px;line-height:1.4;">${item.headline || ""}</div>
                    <div style="font-size:13px;color:${impactColor};font-weight:700;line-height:1.4;">💡 ${item.advice || ""}</div>
                    <div style="display:flex;align-items:center;gap:6px;margin-top:6px;">
                        <span style="font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#334155;">${item.category || ""}</span>
                        <span style="font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:4px;background:${impactBg};color:${impactColor};">${impactLabel}</span>
                    </div>
                </div>
            </div>`;
        }).join("");
    } catch(e) {
        list.innerHTML = `<div class="empty-state" style="padding:24px;"><div class="empty-state-text">Could not load news. Check your connection.</div></div>`;
    }
}

/* ─── SMART TRANSACTION ─── */
function setupSmartInput() {
    document.getElementById("smartInput")?.addEventListener("keypress", e => {
        if (e.key === "Enter") submitSmartTransaction();
    });
}

async function submitSmartTransaction() {
    const input = document.getElementById("smartInput");
    const fb    = document.getElementById("smartFeedback");
    const text  = input?.value.trim();
    if (!text) return;

    const btn = document.querySelector(".smart-send-btn");
    if (btn) { btn.textContent = "⏳"; btn.disabled = true; }

    try {
        const res  = await fetch("/api/v1/smart-transaction", {
            method:"POST",
            headers:{ "Content-Type":"application/json", Authorization:"Bearer "+token },
            body: JSON.stringify({ text })
        });
        const data = await res.json();

        const t = data.transaction || {};
        const isInc = t.type === "income";
        let msg = `${isInc ? "💰" : "💸"} <strong>${cap(t.category || "Transaction")}</strong> of <strong>${fmt(t.amount)}</strong> added`;
        if (data.budget_warning) msg += `<br><span style="font-size:11.5px;">⚠️ ${data.budget_warning}</span>`;

        fb.innerHTML = msg;
        fb.className = "smart-feedback show " + (data.budget_warning ? "warning" : "success");

        if (data.monthly) {
            setText("kpi1Value", fmt(data.monthly.income));
            setText("kpi2Value", fmt(data.monthly.expense));
            setText("kpi3Value", fmt(data.monthly.savings));
        }

        input.value = "";
        setTimeout(() => fb.className = "smart-feedback", 5000);

        const month = document.getElementById("monthSelector")?.value;
        const year  = new Date().getFullYear();
        loadDonutChart(month, year);
        loadRecentTransactions(month, year);
        loadBudgets(month, year);
        loadPrediction(month, year);
    } catch(e) {
        fb.innerHTML = "❌ Failed to add transaction. Try again.";
        fb.className = "smart-feedback show danger";
    }

    if (btn) { btn.textContent = "Add →"; btn.disabled = false; }
}

/* ─── AI BOT ─── */
function setupBotInput() {
    document.getElementById("botInput")?.addEventListener("keypress", e => {
        if (e.key === "Enter") sendBotMessage();
    });
}

function appendMsg(role, text) {
    const container = document.getElementById("botMessages");
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
}

async function sendBotMessage() {
    const input = document.getElementById("botInput");
    const msg   = input?.value.trim();
    if (!msg) return;
    input.value = "";
    appendMsg("user", msg);
    const typing = appendMsg("bot typing", "Thinking…");
    try {
        const res  = await fetch("/api/v1/ai-bot", {
            method:"POST",
            headers:{ "Content-Type":"application/json", Authorization:"Bearer "+token },
            body: JSON.stringify({ message:msg, history:botHistory })
        });
        const data = await res.json();
        typing.remove();
        const reply = data.reply || "Sorry, I couldn't respond.";
        appendMsg("bot", reply);
        botHistory.push({ role:"user", content:msg });
        botHistory.push({ role:"assistant", content:reply });
        if (botHistory.length > 20) botHistory = botHistory.slice(-20);
    } catch(e) {
        typing.remove();
        appendMsg("bot", "⚠️ Connection error. Please try again.");
    }
}

/* ─── HELPERS ─── */
function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ""; }

function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
        const d = new Date(dateStr);
        const today = new Date();
        const diff  = Math.floor((today - d) / 86400000);
        if (diff === 0) return "Today";
        if (diff === 1) return "Yesterday";
        if (diff < 7)  return diff + "d ago";
        return d.toLocaleDateString("en-IN", { day:"numeric", month:"short" });
    } catch(e) { return dateStr; }
}