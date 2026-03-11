/* ═══════════════════════════════════════
   SMART BUDGET PLANNER — v12
   AI auto-generation + Investment signals
═══════════════════════════════════════ */
const token = localStorage.getItem("token");
if (!token) window.location.href = "/login";

let donutChart = null, barChart = null;
let currentMonth, currentYear;

const fmt = v => "₹" + Number(v||0).toLocaleString("en-IN");
const toast = (msg, type="ok") => {
    const t = document.getElementById("toast");
    t.textContent = msg; t.className = `toast show ${type}`;
    setTimeout(() => t.className = "toast", 4000);
};

/* ── Category icons ── */
const ICONS = {
    rent:"🏠", food:"🍔", grocery:"🛒", groceries:"🛒", transport:"🚗",
    fuel:"⛽", entertainment:"🎬", health:"💊", medical:"💊", shopping:"🛍️",
    education:"📚", utilities:"💡", electricity:"💡", gym:"💪",
    travel:"✈️", subscriptions:"📺", salary:"💼", gift:"🎁",
    insurance:"🛡️", investment:"📈", savings:"💰", petrol:"⛽",
    other:"📦"
};
const getIcon = cat => ICONS[cat?.toLowerCase()] || "📦";

/* ── Investment pulse data ── */
const INVESTMENTS = [
    { name:"Nifty 50 Index", ico:"📊", val:"23,842", chg:"+1.2%", up:true, rec:"buy",  note:"Strong momentum. SIP recommended." },
    { name:"Gold",           ico:"🥇", val:"₹73,200/10g", chg:"+0.4%", up:true,  rec:"hold", note:"Inflation hedge. Good for 5%+ of portfolio." },
    { name:"HDFC Nifty ETF", ico:"🏦", val:"₹248.3",  chg:"+0.9%", up:true,  rec:"buy",  note:"Low cost. Best for long-term wealth." },
    { name:"Fixed Deposit",  ico:"🏛️", val:"7.1% p.a.", chg:"Stable", up:true, rec:"hold", note:"Safe option if goal <2 years away." },
    { name:"Crypto (BTC)",   ico:"₿",  val:"₹67.4L",  chg:"-2.1%", up:false, rec:"wait", note:"High risk. Only 2-3% of portfolio." },
    { name:"Real Estate",    ico:"🏗️", val:"SG Highway +18%", chg:"+18%", up:true, rec:"buy", note:"Long term. Needs high capital." },
    { name:"Mutual Fund",    ico:"📈", val:"Flexi Cap",chg:"+14.2% YTD", up:true, rec:"buy", note:"Best for 3+ year horizon." },
    { name:"PPF",            ico:"🏛️", val:"7.1% p.a.", chg:"Tax Free", up:true, rec:"buy", note:"Lock-in 15yr. Tax-free returns." },
];

/* ── Goal templates ── */
const GOAL_TEMPLATES = [
    { name:"Emergency Fund", amt:300000, months:12, icon:"🆘" },
    { name:"New Car",        amt:800000, months:36, icon:"🚗" },
    { name:"Home Down Payment", amt:2000000, months:60, icon:"🏠" },
];

/* ══════════════════════════════
   INIT
══════════════════════════════ */
document.addEventListener("DOMContentLoaded", async () => {
    const now = new Date();
    currentMonth = now.getMonth() + 1;
    currentYear  = now.getFullYear();
    document.getElementById("monthSel").value = currentMonth;
    document.getElementById("yearSel").value  = currentYear;

    buildInvestmentPulse();
    await loadBudgets();
});

function onMonthChange() {
    currentMonth = parseInt(document.getElementById("monthSel").value);
    currentYear  = parseInt(document.getElementById("yearSel").value);
    loadBudgets();
}

/* ══════════════════════════════
   LOAD BUDGETS + KPIs
══════════════════════════════ */
async function loadBudgets() {
    try {
        // Load budgets
        const res = await fetch(`/api/v1/budgets-status?month=${currentMonth}&year=${currentYear}`, {
            headers: { Authorization: "Bearer " + token }
        });
        const budgets = await res.json();

        // Load income from snapshot
        let income = 0;
        try {
            const sr = await fetch(`/api/v1/savings-prediction?month=${currentMonth}&year=${currentYear}`, {
                headers: { Authorization: "Bearer " + token }
            });
            if (sr.ok) { const sd = await sr.json(); income = sd.current_income || 0; }
        } catch {}

        // Load profile for income fallback
        if (!income) {
            try {
                const pr = await fetch("/api/v1/financial-profile", { headers: { Authorization: "Bearer " + token } });
                if (pr.ok) { const pd = await pr.json(); income = pd.monthly_income || 0; }
            } catch {}
        }

        if (!budgets || budgets.length === 0) {
            // First time — show setup banner
            document.getElementById("setupBanner").style.display = "block";
            document.getElementById("budgetGrid").innerHTML = "";
            document.getElementById("chartRow").style.display = "none";
            document.getElementById("aiTipsPanel").style.display = "none";
            updateKPIs(income, 0, 0);
            return;
        }

        document.getElementById("setupBanner").style.display = "none";
        renderBudgets(budgets, income);
        updateKPIsFromBudgets(budgets, income);
        buildCharts(budgets);
        buildAITips(budgets, income);
        buildGoals(income);
    } catch (e) {
        console.error(e);
    }
}

function updateKPIs(income, budgeted, spent) {
    const remaining = income - spent;
    const savingRate = income > 0 ? ((income - spent) / income * 100).toFixed(1) : 0;
    document.getElementById("kIncome").textContent  = fmt(income);
    document.getElementById("kBudget").textContent  = fmt(budgeted);
    document.getElementById("kSpent").textContent   = fmt(spent);
    const rEl = document.getElementById("kRemain");
    rEl.textContent = fmt(remaining);
    rEl.className   = "kc-val " + (remaining >= 0 ? "g" : "r");
    const sEl = document.getElementById("kSaving");
    sEl.textContent = savingRate + "%";
    sEl.className   = "kc-val " + (savingRate >= 20 ? "g" : savingRate >= 10 ? "gold" : "r");
}

function updateKPIsFromBudgets(budgets, income) {
    const budgeted = budgets.reduce((s, b) => s + b.limit, 0);
    const spent    = budgets.reduce((s, b) => s + b.spent, 0);
    updateKPIs(income, budgeted, spent);
}

/* ══════════════════════════════
   RENDER BUDGET CARDS
══════════════════════════════ */
function renderBudgets(budgets, income) {
    const grid = document.getElementById("budgetGrid");
    grid.innerHTML = "";
    document.getElementById("chartRow").style.display = "grid";

    budgets.forEach(b => {
        const pct    = b.percentage;
        const color  = pct > 100 ? "#f87171" : pct > 75 ? "#f59e0b" : "#22c55e";
        const chipCls= pct > 100 ? "chip chip-r" : pct > 75 ? "chip chip-a" : "chip chip-g";
        const chipTxt= pct > 100 ? "🔴 Overspent" : pct > 75 ? "🟠 Warning" : "🟢 Healthy";
        const surplus = b.limit - b.spent;
        const noteCls = surplus >= 0 ? (pct < 75 ? "bc-note ok" : "bc-note warn") : "bc-note over";
        const noteTxt = surplus >= 0
            ? `₹${Math.abs(surplus).toLocaleString("en-IN")} remaining this month`
            : `₹${Math.abs(surplus).toLocaleString("en-IN")} over budget!`;

        const card = document.createElement("div");
        card.className = "bcard";
        card.innerHTML = `
            <button class="bc-edit" onclick="openEdit('${b.category}',${b.limit})">✏ Edit</button>
            <div class="bcard-head">
                <div class="bc-icon">${getIcon(b.category)}</div>
                <div>
                    <div class="bc-name">${b.category.charAt(0).toUpperCase() + b.category.slice(1)}</div>
                    <div class="bc-status">${pct.toFixed(1)}% of budget used</div>
                </div>
            </div>
            <div class="bc-amounts">
                <span>Spent: <strong class="hide-amount">${fmt(b.spent)}</strong></span>
                <span>Limit: <strong class="hide-amount">${fmt(b.limit)}</strong></span>
            </div>
            <div class="prog"><div class="prog-fill" style="width:${Math.min(pct,100)}%;background:${color};"></div></div>
            <div class="bc-foot">
                <span class="pct-lbl" style="color:${color}">${pct.toFixed(1)}%</span>
                <span class="${chipCls}">${chipTxt}</span>
            </div>
            <div class="${noteCls}">${noteTxt}</div>
        `;
        grid.appendChild(card);
    });
}

/* ══════════════════════════════
   CHARTS
══════════════════════════════ */
function buildCharts(budgets) {
    const labels = budgets.map(b => b.category.charAt(0).toUpperCase() + b.category.slice(1));
    const limits = budgets.map(b => b.limit);
    const spents = budgets.map(b => b.spent);
    const COLORS = ["#c9a84c","#63d1ff","#22c55e","#f59e0b","#a78bfa","#f472b6","#34d399","#60a5fa","#fb923c","#94a3b8"];

    // Donut
    const dCtx = document.getElementById("donutChart");
    if (donutChart) donutChart.destroy();
    donutChart = new Chart(dCtx, {
        type: "doughnut",
        data: { labels, datasets: [{ data: limits, backgroundColor: COLORS, borderColor:"#07090f", borderWidth:3, hoverOffset:6 }] },
        options: { responsive:true, maintainAspectRatio:false, cutout:"62%",
            plugins: { legend:{ position:"bottom", labels:{ color:"#94a3b8", font:{size:10}, padding:8, boxWidth:9 } },
                tooltip:{ callbacks:{ label: ctx => ` ${ctx.label}: ${fmt(ctx.raw)}` } } } }
    });

    // Bar
    const bCtx = document.getElementById("barChart");
    if (barChart) barChart.destroy();
    barChart = new Chart(bCtx, {
        type: "bar",
        data: { labels,
            datasets: [
                { label:"Budget", data:limits, backgroundColor:"rgba(201,168,76,0.5)", borderColor:"#c9a84c", borderWidth:1.5, borderRadius:5 },
                { label:"Spent",  data:spents, backgroundColor:"rgba(99,209,255,0.5)",  borderColor:"#63d1ff", borderWidth:1.5, borderRadius:5 }
            ]},
        options: { responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{ labels:{ color:"#64748b", font:{size:10} } } },
            scales:{ x:{ ticks:{color:"#64748b"}, grid:{color:"rgba(255,255,255,0.04)"} },
                     y:{ ticks:{color:"#64748b", callback: v=>"₹"+(v/1000).toFixed(0)+"k"}, grid:{color:"rgba(255,255,255,0.04)"} } }
        }
    });
}

/* ══════════════════════════════
   AI TIPS
══════════════════════════════ */
function buildAITips(budgets, income) {
    const panel = document.getElementById("aiTipsPanel");
    const grid  = document.getElementById("tipsGrid");
    panel.style.display = "block";

    const totalSpent   = budgets.reduce((s, b) => s + b.spent, 0);
    const overspent    = budgets.filter(b => b.percentage > 100);
    const savingRate   = income > 0 ? ((income - totalSpent) / income * 100) : 0;
    const topSpend     = budgets.sort((a,b) => b.spent - a.spent)[0];

    const tips = [];

    if (savingRate >= 30) {
        tips.push({ icon:"🌟", title:"Excellent Savings Rate!", body:`You're saving ${savingRate.toFixed(1)}% of your income. Consider investing the surplus in mutual funds or index ETFs for long-term growth.` });
    } else if (savingRate >= 15) {
        tips.push({ icon:"✅", title:"Good Progress", body:`Savings rate of ${savingRate.toFixed(1)}%. Push for 30%+ by trimming discretionary spending. Small cuts add up fast.` });
    } else {
        tips.push({ icon:"⚠️", title:"Savings Rate Low", body:`Only ${savingRate.toFixed(1)}% saved. Review recurring subscriptions and food spend — these are usually the easiest wins.` });
    }

    if (overspent.length > 0) {
        tips.push({ icon:"🔴", title:`${overspent.length} Budget(s) Exceeded`, body:`${overspent.map(b => b.category).join(", ")} went over budget. Redistribute limits or cut next month's spend in these areas.` });
    } else {
        tips.push({ icon:"💚", title:"All Budgets On Track", body:"Great discipline! You've stayed within all limits this month. Keep the streak going — consistency beats perfection." });
    }

    if (topSpend) {
        tips.push({ icon:"🔍", title:`Biggest Spend: ${topSpend.category}`, body:`You spent ${fmt(topSpend.spent)} on ${topSpend.category} (${topSpend.percentage.toFixed(0)}% of its budget). Is this aligned with your priorities?` });
    }

    if (income > 50000) {
        tips.push({ icon:"📈", title:"Start a SIP Today", body:`With ₹${Math.floor(income * 0.1).toLocaleString("en-IN")}/month (10% of income) in a Nifty 50 index fund, you could build ₹${Math.floor(income * 0.1 * 12 * 10 * 1.12).toLocaleString("en-IN")} in 10 years at 12% returns.` });
    }

    grid.innerHTML = tips.map(t => `
        <div class="tip-card">
            <div class="tip-icon">${t.icon}</div>
            <div class="tip-title">${t.title}</div>
            <div class="tip-body">${t.body}</div>
        </div>`).join("");
}

/* ══════════════════════════════
   INVESTMENT PULSE — LIVE
══════════════════════════════ */
async function buildInvestmentPulse() {
    const grid = document.getElementById("investGrid");

    // Show skeleton loading state
    grid.innerHTML = Array(8).fill(`
        <div class="inv-card" style="opacity:.4;">
            <div class="inv-ico">⏳</div>
            <div class="inv-name">Loading...</div>
            <div class="inv-val" style="font-size:13px;color:var(--sub);">Fetching live price</div>
            <div class="inv-chg">—</div>
        </div>`).join("");

    try {
        const res  = await fetch("/api/v1/market-data", {
            headers: { Authorization: "Bearer " + token }
        });
        const data = await res.json();

        if (!res.ok || !data.instruments?.length) throw new Error("No data");

        grid.innerHTML = data.instruments.map(inv => `
            <div class="inv-card">
                <div class="inv-ico">${inv.ico}</div>
                <div class="inv-name">${inv.name}</div>
                <div class="inv-val">${inv.val}</div>
                <div class="inv-chg ${inv.up ? 'up' : 'dn'}">${inv.chg}</div>
                <div class="inv-rec rec-${inv.rec}">${inv.rec.toUpperCase()}</div>
                <div class="inv-note">${inv.note}</div>
                ${inv.live ? '<div style="font-size:9px;color:var(--green);margin-top:3px;">🟢 Live</div>'
                           : '<div style="font-size:9px;color:var(--muted);margin-top:3px;">📌 Fixed rate</div>'}
            </div>`).join("");

    } catch (e) {
        // Fallback to static data if API fails
        console.warn("[Market] Live fetch failed, using static data:", e);
        grid.innerHTML = INVESTMENTS.map(inv => `
            <div class="inv-card">
                <div class="inv-ico">${inv.ico}</div>
                <div class="inv-name">${inv.name}</div>
                <div class="inv-val">${inv.val}</div>
                <div class="inv-chg ${inv.up ? 'up' : 'dn'}">${inv.chg}</div>
                <div class="inv-rec rec-${inv.rec}">${inv.rec.toUpperCase()}</div>
                <div class="inv-note">${inv.note}</div>
                <div style="font-size:9px;color:var(--muted);margin-top:3px;">📌 Cached</div>
            </div>`).join("");
    }
}

/* ══════════════════════════════
   GOAL PLANNER
══════════════════════════════ */
function buildGoals(income) {
    if (!income || income < 1000) return;
    const panel = document.getElementById("goalsPanel");
    const grid  = document.getElementById("goalsGrid");
    panel.style.display = "block";

    const monthlySavings = income * 0.25; // assume 25% savings
    grid.innerHTML = GOAL_TEMPLATES.map(g => {
        const months = Math.ceil(g.amt / monthlySavings);
        const years  = (months / 12).toFixed(1);
        return `
            <div class="goal-card">
                <div class="goal-name">${g.icon} ${g.name}</div>
                <div class="goal-amt">Target: ${fmt(g.amt)}</div>
                <div class="goal-months">At 25% savings → ${months} months (${years} yrs)</div>
                <div class="goal-months" style="color:var(--cyan);margin-top:3px;">Monthly SIP needed: ${fmt(Math.round(g.amt/g.months))}</div>
            </div>`;
    }).join("");
}

/* ══════════════════════════════
   FIRST-TIME BUDGET GENERATION
══════════════════════════════ */
async function generateFirstBudget() {
    const income = parseFloat(document.getElementById("siIncome").value) || 0;
    const saving = parseFloat(document.getElementById("siSaving").value) || 30;
    const rent   = parseFloat(document.getElementById("siRent").value)   || 0;

    if (!income) { toast("Please enter your monthly income.", "err"); return; }

    toast("⏳ Scanning transactions & building budget...", "info");

    // Fetch transaction categories
    let catData = { labels:[], values:[] };
    try {
        const r = await fetch(`/api/v1/category-breakdown-month?month=${currentMonth}&year=${currentYear}`,
            { headers:{ Authorization:"Bearer "+token } });
        if (r.ok) catData = await r.json();
    } catch {}

    const spendable = income * (1 - saving/100) - rent;
    const cats = catData.labels.length > 0
        ? catData.labels.map((lbl, i) => ({ category: lbl.toLowerCase(), limit: Math.round(catData.values[i] * 1.1) }))
        : defaultCategories(spendable, rent);

    // Add rent if provided
    if (rent > 0) cats.unshift({ category: "rent", limit: rent });

    // Save each budget
    for (const cat of cats) {
        try {
            await fetch("/api/v1/budgets", {
                method: "POST",
                headers: { "Content-Type":"application/json", Authorization:"Bearer "+token },
                body: JSON.stringify({ category: cat.category, monthly_limit: cat.limit })
            });
        } catch {}
    }

    document.getElementById("autoBadge").style.display = "inline-flex";
    toast("✅ Budget plan generated from your transactions!", "ok");
    await loadBudgets();
}

function defaultCategories(spendable, rent) {
    return [
        { category:"groceries",    limit: Math.round(spendable * 0.25) },
        { category:"food",         limit: Math.round(spendable * 0.15) },
        { category:"transport",    limit: Math.round(spendable * 0.10) },
        { category:"utilities",    limit: Math.round(spendable * 0.08) },
        { category:"entertainment",limit: Math.round(spendable * 0.08) },
        { category:"health",       limit: Math.round(spendable * 0.06) },
        { category:"shopping",     limit: Math.round(spendable * 0.12) },
        { category:"others",       limit: Math.round(spendable * 0.16) },
    ];
}

async function autoGenerate() {
    toast("⏳ Scanning this month's transactions...", "info");

    let catData = { labels:[], values:[] };
    try {
        const r = await fetch(`/api/v1/category-breakdown-month?month=${currentMonth}&year=${currentYear}`,
            { headers:{ Authorization:"Bearer "+token } });
        if (r.ok) catData = await r.json();
    } catch {}

    if (!catData.labels.length) {
        toast("No transactions found for this month. Add transactions first.", "err");
        return;
    }

    for (let i = 0; i < catData.labels.length; i++) {
        await fetch("/api/v1/budgets", {
            method: "POST",
            headers: { "Content-Type":"application/json", Authorization:"Bearer "+token },
            body: JSON.stringify({ category: catData.labels[i].toLowerCase(), monthly_limit: Math.round(catData.values[i] * 1.15) })
        });
    }

    document.getElementById("autoBadge").style.display = "inline-flex";
    toast("✅ Budget auto-generated from transactions!", "ok");
    await loadBudgets();
}

/* ══════════════════════════════
   MODAL
══════════════════════════════ */
function openModal() {
    document.getElementById("modalTitle").textContent = "Add Budget Category";
    document.getElementById("mCat").value   = "";
    document.getElementById("mLimit").value = "";
    document.getElementById("mCat").disabled = false;
    document.getElementById("budgetModal").classList.add("show");
}
function openEdit(cat, limit) {
    document.getElementById("modalTitle").textContent = "Edit Budget";
    document.getElementById("mCat").value     = cat;
    document.getElementById("mLimit").value   = limit;
    document.getElementById("mCat").disabled  = true; // category name locked
    document.getElementById("budgetModal").classList.add("show");
}
function closeModal() {
    document.getElementById("budgetModal").classList.remove("show");
}
async function saveModal() {
    const cat   = document.getElementById("mCat").value.trim().toLowerCase();
    const limit = parseFloat(document.getElementById("mLimit").value);
    if (!cat || !limit) { toast("Fill both fields.", "err"); return; }

    const res = await fetch("/api/v1/budgets", {
        method: "POST",
        headers: { "Content-Type":"application/json", Authorization:"Bearer "+token },
        body: JSON.stringify({ category: cat, monthly_limit: limit })
    });

    if (res.ok) { closeModal(); toast("✅ Budget saved!", "ok"); await loadBudgets(); }
    else { toast("❌ Failed to save.", "err"); }
}