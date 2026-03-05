/* ═══════════════════════════════════════════════
   FINANCE AI — DASHBOARD ENGINE v10
═══════════════════════════════════════════════ */

const token = localStorage.getItem("token");
if (!token) window.location.href = "/login";

let dashboardData = null;
let currentMode   = "monthly";
let trendChart    = null;
let donutChart    = null;
let botHistory    = [];   // [{role, content}]

const CAT_ICONS = {
    food:          "🍔", transport: "🚗", shopping:  "🛍️",
    entertainment: "🎬", sports:    "⚽", health:    "💊",
    utilities:     "💡", assets:    "💰", income:    "💵", other: "📦"
};

function fmt(v) { return "₹" + Number(v || 0).toLocaleString("en-IN"); }
function setText(id, v) { const el = document.getElementById(id); if (el) el.innerText = v; }

/* ═══════════════════════════════
   SET DEFAULT MONTH TO CURRENT
═══════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
    const sel = document.getElementById("monthSelector");
    if (sel) sel.value = new Date().getMonth() + 1;

    loadDashboard();
    setupSmartInput();
    setupBotInput();
});

/* ═══════════════════════════════
   LOAD DASHBOARD
═══════════════════════════════ */
async function loadDashboard() {
    const month = document.getElementById("monthSelector")?.value;
    const year  = new Date().getFullYear();

    const res = await fetch(`/api/v1/dashboard-overview?month=${month}&year=${year}`, {
        headers: { Authorization: "Bearer " + token }
    });
    dashboardData = await res.json();

    renderKPIs();
    loadTrendChart();
    loadDonutChart(month, year);
    loadPrediction(month, year);
    loadRecentTransactions(month, year);
    loadBudgets(month, year);
}

/* ═══════════════════════════════
   KPIs
═══════════════════════════════ */
function renderKPIs() {
    if (!dashboardData) return;
    const m = dashboardData.monthly || {};
    const o = dashboardData.overall || {};

    if (currentMode === "monthly") {
        setText("kpi1Title", "Monthly Income");   setText("kpi1Value", fmt(m.income));
        setText("kpi2Title", "Monthly Expense");  setText("kpi2Value", fmt(m.expense));
        setText("kpi3Title", "Savings");          setText("kpi3Value", fmt(m.savings));
        setText("kpi4Title", "Net Worth");        setText("kpi4Value", fmt(o?.net_worth));
    } else {
        setText("kpi1Title", "Total Assets");     setText("kpi1Value", fmt(o?.assets));
        setText("kpi2Title", "Liabilities");      setText("kpi2Value", fmt(o?.liabilities));
        setText("kpi3Title", "Debt Ratio");       setText("kpi3Value", (o?.debt_ratio || 0) + "%");
        setText("kpi4Title", "Net Worth");        setText("kpi4Value", fmt(o?.net_worth));
    }
}

function setView(mode) {
    currentMode = mode;
    document.getElementById("monthlyBtn").classList.toggle("active", mode === "monthly");
    document.getElementById("overallBtn").classList.toggle("active", mode === "overall");
    renderKPIs();
}

/* ═══════════════════════════════
   TREND CHART (Line)
═══════════════════════════════ */
async function loadTrendChart() {
    const canvas = document.getElementById("trendChart");
    if (!canvas) return;

    const res  = await fetch("/api/v1/monthly-trend", { headers: { Authorization: "Bearer " + token } });
    const data = await res.json();

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.labels || [],
            datasets: [
                {
                    label: "Income",
                    data: data.income || [],
                    borderColor: "#22c55e",
                    backgroundColor: "rgba(34,197,94,0.1)",
                    fill: true, tension: 0.4, pointRadius: 3
                },
                {
                    label: "Expense",
                    data: data.expense || [],
                    borderColor: "#ef4444",
                    backgroundColor: "rgba(239,68,68,0.1)",
                    fill: true, tension: 0.4, pointRadius: 3
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: "#94a3b8", font: { size: 12 } } } },
            scales: {
                x: { ticks: { color: "#475569" }, grid: { color: "rgba(255,255,255,0.04)" } },
                y: { ticks: { color: "#475569" }, grid: { color: "rgba(255,255,255,0.04)" } }
            }
        }
    });
}

/* ═══════════════════════════════
   DONUT CHART (Category Breakdown)
═══════════════════════════════ */
async function loadDonutChart(month, year) {
    const canvas = document.getElementById("donutChart");
    if (!canvas) return;

    const res = await fetch(`/api/v1/category-breakdown-month?month=${month}&year=${year}`, {
        headers: { Authorization: "Bearer " + token }
    });
    const data = await res.json();

    if (donutChart) donutChart.destroy();

    const COLORS = [
        "#c9a84c","#63d1ff","#22c55e","#f59e0b",
        "#ef4444","#a78bfa","#f472b6","#34d399","#60a5fa","#94a3b8"
    ];

    if (!data.labels || data.labels.length === 0) {
        canvas.parentElement.innerHTML += `<p style="color:#475569;font-size:12px;text-align:center;margin-top:20px;">No expense data for this month</p>`;
        return;
    }

    donutChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: data.labels.map(l => l.charAt(0).toUpperCase() + l.slice(1)),
            datasets: [{
                data: data.values,
                backgroundColor: COLORS.slice(0, data.labels.length),
                borderColor: "#0e1017",
                borderWidth: 3,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            cutout: "65%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#94a3b8", font: { size: 11 }, padding: 12, boxWidth: 10 }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${fmt(ctx.raw)}`
                    }
                }
            }
        }
    });
}

/* ═══════════════════════════════
   SAVINGS PREDICTION
═══════════════════════════════ */
async function loadPrediction(month, year) {
    const res  = await fetch(`/api/v1/savings-prediction?month=${month}&year=${year}`, {
        headers: { Authorization: "Bearer " + token }
    });
    const data = await res.json();

    setText("predictionValue", fmt(data.predicted_savings));
    setText("predictionMsg", data.savings_message || "");
}

/* ═══════════════════════════════
   RECENT TRANSACTIONS
═══════════════════════════════ */
async function loadRecentTransactions(month, year) {
    const res  = await fetch(`/api/v1/recent-transactions?month=${month}&year=${year}`, {
        headers: { Authorization: "Bearer " + token }
    });
    const data = await res.json();
    const el   = document.getElementById("historyList");
    if (!el) return;

    if (!data.length) {
        el.innerHTML = `<p style="color:#475569;font-size:13px;text-align:center;padding:20px 0;">No transactions this month</p>`;
        return;
    }

    el.innerHTML = data.map(t => `
        <div class="txn-item">
            <div class="txn-left">
                <div class="txn-icon ci-${t.type === 'income' ? 'income' : t.category}">
                    ${t.type === 'income' ? '💵' : (CAT_ICONS[t.category] || '📦')}
                </div>
                <div>
                    <div class="txn-cat">${t.category}</div>
                    <div class="txn-date">${t.date}</div>
                </div>
            </div>
            <span class="txn-amount ${t.type}">
                ${t.type === 'income' ? '+' : '-'}${fmt(t.amount)}
            </span>
        </div>
    `).join("");
}

/* ═══════════════════════════════
   BUDGETS
═══════════════════════════════ */
async function loadBudgets(month, year) {
    const res  = await fetch(`/api/v1/budgets-status?month=${month}&year=${year}`, {
        headers: { Authorization: "Bearer " + token }
    });
    const data = await res.json();
    const el   = document.getElementById("budgetList");
    if (!el) return;

    if (!data.length) {
        el.innerHTML = `<p style="color:#475569;font-size:13px;text-align:center;padding:20px 0;">No budgets set. <a href="/budgets" style="color:#c9a84c;">Add one →</a></p>`;
        return;
    }

    el.innerHTML = data.map(b => {
        const color = b.percentage >= 100 ? "#ef4444" : b.percentage >= 80 ? "#f59e0b" : "#22c55e";
        return `
        <div class="budget-item">
            <div class="budget-header">
                <span class="budget-cat">${b.category}</span>
                <span class="budget-pct" style="color:${color}">${fmt(b.spent)} / ${fmt(b.limit)}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width:${Math.min(b.percentage,100)}%;background:${color}"></div>
            </div>
        </div>`;
    }).join("");
}

/* ═══════════════════════════════
   SMART TRANSACTION
═══════════════════════════════ */
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
    btn.textContent = "...";
    btn.disabled = true;

    try {
        const res  = await fetch("/api/v1/smart-transaction", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
            body: JSON.stringify({ text })
        });
        const data = await res.json();

        // Show feedback
        let msg = `✅ ${data.transaction.type === 'income' ? 'Income' : 'Expense'} of ${fmt(data.transaction.amount)} added as <strong>${data.transaction.category}</strong>`;
        if (data.asset_purchase) msg += ` &nbsp;<span style="color:#c9a84c;font-size:11px;font-weight:700;">ASSET</span>`;
        if (data.savings_message) msg += ` · ${data.savings_message}`;

        fb.innerHTML = msg;
        fb.className = "smart-feedback show " + (data.budget_warning ? "warning" : "success");
        if (data.budget_warning) {
            fb.innerHTML += `<br><span style="font-size:12px;">${data.budget_warning}</span>`;
            fb.className = "smart-feedback show warning";
        }

        // Update KPIs instantly
        if (data.monthly) {
            setText("kpi1Value", fmt(data.monthly.income));
            setText("kpi2Value", fmt(data.monthly.expense));
            setText("kpi3Value", fmt(data.monthly.savings));
        }

        input.value = "";
        setTimeout(() => fb.className = "smart-feedback", 5000);

        // Refresh charts + lists
        const month = document.getElementById("monthSelector")?.value;
        const year  = new Date().getFullYear();
        loadDonutChart(month, year);
        loadRecentTransactions(month, year);
        loadBudgets(month, year);
        loadPrediction(month, year);

    } catch (err) {
        fb.innerHTML = "❌ Failed to add transaction.";
        fb.className = "smart-feedback show danger";
    }

    btn.textContent = "Add →";
    btn.disabled = false;
}

/* ═══════════════════════════════
   AI BOT
═══════════════════════════════ */
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

    // Add typing indicator
    const typing = appendMsg("bot typing", "Thinking...");

    try {
        const res = await fetch("/api/v1/ai-bot", {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
            body: JSON.stringify({
                message: msg,
                history: botHistory
            })
        });
        const data = await res.json();
        typing.remove();

        const reply = data.reply || "Sorry, I couldn't get a response.";
        appendMsg("bot", reply);

        // Update history
        botHistory.push({ role: "user", content: msg });
        botHistory.push({ role: "assistant", content: reply });

        // Keep history to last 20 messages
        if (botHistory.length > 20) botHistory = botHistory.slice(-20);

    } catch (err) {
        typing.remove();
        appendMsg("bot", "⚠️ Connection error. Please try again.");
    }
}

// ── News Insights ──────────────────────────────────────────────────────────
async function loadNewsInsights() {
    const token = localStorage.getItem("token");
    const list = document.getElementById("newsInsightsList");
    const subtitle = document.getElementById("newsFetchedAt");
    if (!list) return;

    try {
        const res = await fetch("/api/v1/news-insights", {
            headers: { "Authorization": "Bearer " + token }
        });
        const data = await res.json();

        if (subtitle && data.fetched_at) {
            subtitle.textContent = "Powered by Indian Finance News · " + data.fetched_at;
        }

        if (!data.insights || data.insights.length === 0) {
            list.innerHTML = `<div style="color:#888; font-size:13px; padding:10px;">
                No major financial news signals detected right now. Check back later.
            </div>`;
            return;
        }

        list.innerHTML = data.insights.map(item => {
            const color = item.impact === "positive" ? "#4caf50"
                        : item.impact === "negative" ? "#f44336"
                        : "#ffa500";
            return `
            <div style="display:flex; gap:12px; align-items:flex-start;
                        padding:12px 14px; border-bottom:1px solid rgba(255,255,255,0.05);">
                <span style="font-size:22px; min-width:28px;">${item.icon}</span>
                <div>
                    <div style="font-size:12px; color:#aaa; margin-bottom:4px;">
                        ${item.headline}
                    </div>
                    <div style="font-size:13px; color:${color}; font-weight:500;">
                        💡 ${item.advice}
                    </div>
                    <span style="font-size:10px; color:#666; text-transform:uppercase;
                                 letter-spacing:1px;">${item.category}</span>
                </div>
            </div>`;
        }).join("");

    } catch (err) {
        list.innerHTML = `<div style="color:#888; font-size:13px; padding:10px;">
            Could not load news insights. Check connection.
        </div>`;
    }
}

// Load news on page start
loadNewsInsights();
// Refresh every 15 minutes
setInterval(loadNewsInsights, 15 * 60 * 1000);