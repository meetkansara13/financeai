/* ═══════════════════════════════════════════
   WEALTH PLANNER — ENGINE v11
   Real file upload + OCR verification
═══════════════════════════════════════════ */

const token = localStorage.getItem("token");
if (!token) window.location.href = "/login";

let currentStep = 1;
let assetChart = null;
let incomeExpenseChart = null;
let completedSteps = new Set();

const fmt  = v  => "₹" + Number(v || 0).toLocaleString("en-IN");
const num  = id => Number(document.getElementById(id)?.value) || 0;
const val  = id => document.getElementById(id)?.value?.trim() || "";
const setText = (id, v) => { const el = document.getElementById(id); if (el) el.innerText = v; };
const setVal  = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };

/* ════════════════════════════
   STEP NAVIGATION
════════════════════════════ */
function goToStep(n) {
    // Check if jumping ahead with incomplete data — show warning badge, not block
    if (n > currentStep) {
        for (let s = currentStep; s < n; s++) {
            if (!completedSteps.has(s)) {
                // Mark as incomplete with orange warning instead of green done
                const tab = document.getElementById(`tab-${s}`);
                if (tab) {
                    tab.classList.remove('active', 'done');
                    tab.classList.add('incomplete');
                    const numEl = tab.querySelector('.st-num');
                    if (numEl) numEl.innerHTML = '!';
                }
            }
        }
    }

    document.querySelectorAll(".form-step").forEach(s => s.classList.remove("active"));
    document.querySelectorAll(".step-tab").forEach(t => t.classList.remove("active"));

    document.getElementById(`step-${n}`)?.classList.add("active");
    document.getElementById(`tab-${n}`)?.classList.add("active");

    // Mark all completed steps as done (green check)
    for (let i = 1; i < n; i++) {
        const tab = document.getElementById(`tab-${i}`);
        if (tab) {
            tab.classList.remove("active", "incomplete");
            if (completedSteps.has(i)) {
                tab.classList.add("done");
                const numEl = tab.querySelector(".st-num");
                if (numEl) numEl.innerHTML = "✓";
            } else {
                // Not completed — show warning
                tab.classList.add("incomplete");
                const numEl = tab.querySelector(".st-num");
                if (numEl) numEl.innerHTML = "!";
            }
        }
    }
    currentStep = n;
    if (n === 5) buildReviewStep();
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function nextStep(n) { if (n < 5) { completedSteps.add(n); goToStep(n + 1); } }
function prevStep(n) { if (n > 1) goToStep(n - 1); }

/* ════════════════════════════
   LIVE SUMMARY
════════════════════════════ */
function updateSummary() {
    const income = num("salary") + num("sideIncome") + num("rentalIncome") + num("passiveIncome");
    const assets = num("stocks") + num("mutualFunds") + num("bonds") + num("crypto") +
                   num("realEstate") + num("gold") + num("vehicles") + num("cash") +
                   num("fixedDeposits") + num("insurance");
    const liabilities = num("homeLoan") + num("carLoan") + num("personalLoan") +
                        num("eduLoan") + num("bizLoan") + num("otherLoans") +
                        num("creditCard") + num("fixedExpense");
    const netWorth    = assets - liabilities;
    const savingsRate = income > 0 ? ((income - num("fixedExpense")) / income * 100).toFixed(1) : 0;

    const nwEl = document.getElementById("sk-networth");
    if (nwEl) { nwEl.textContent = fmt(netWorth); nwEl.className = "sk-value " + (netWorth >= 0 ? "gold" : "red"); }
    setText("sk-income",      fmt(income));
    setText("sk-assets",      fmt(assets));
    setText("sk-liabilities", fmt(liabilities));
    setText("sk-savings",     savingsRate + "%");
}

/* ════════════════════════════
   FILE UPLOAD + OCR VERIFY
════════════════════════════ */
async function uploadAndVerify(input, statusId, docType) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById(statusId);
    if (!statusEl) return;

    // Show scanning animation
    statusEl.className = "upload-status show";
    statusEl.innerHTML = `
        <div style="color:#f59e0b;font-weight:600;">
            ⏳ Uploading & scanning <em>${file.name}</em>...
        </div>
        <div style="color:#475569;font-size:10px;margin-top:3px;">
            Running OCR · Extracting PAN & name · Cross-checking profile
        </div>`;

    const formData = new FormData();
    formData.append("file",     file);
    formData.append("doc_type", docType);

    try {
        const res  = await fetch("/api/v1/upload-document", {
            method:  "POST",
            headers: { Authorization: "Bearer " + token },
            body:    formData
        });
        const data = await res.json();

        if (res.ok) {
            const isVerified = data.status === "verified";
            const isReview   = data.status === "manual_review";
            const icon  = isVerified ? "✅" : isReview ? "🔍" : "⚠️";
            const color = isVerified ? "#22c55e" : isReview ? "#f59e0b" : "#f87171";
            const scorePct = Math.round(data.match_score || 0);

            // Score bar HTML
            const barColor = scorePct >= 70 ? "#22c55e" : scorePct >= 40 ? "#f59e0b" : "#f87171";
            const scoreBar = `
                <div style="margin-top:6px;background:rgba(255,255,255,0.06);border-radius:4px;height:5px;overflow:hidden;">
                    <div style="width:${scorePct}%;height:100%;background:${barColor};border-radius:4px;transition:width 0.8s ease;"></div>
                </div>
                <div style="color:#475569;font-size:10px;margin-top:2px;">Match score: ${scorePct}/100</div>`;

            statusEl.innerHTML = `
                <div style="color:${color};font-weight:600;font-size:12px;">${icon} ${data.message}</div>
                ${data.extracted_pan  ? `<div style="color:#64748b;font-size:10.5px;margin-top:4px;">🪪 PAN found: <strong style="color:#c9a84c">${data.extracted_pan}</strong></div>` : ""}
                ${data.extracted_name ? `<div style="color:#64748b;font-size:10.5px;">👤 Name found: <strong style="color:#e2e8f0">${data.extracted_name}</strong></div>` : ""}
                ${scoreBar}`;

            // Refresh the verification bar from server
            await loadVerificationStatus();
        } else {
            statusEl.innerHTML = `<div style="color:#f87171;font-weight:600;">❌ Upload failed: ${data.detail || "Server error"}</div>`;
        }
    } catch (err) {
        statusEl.innerHTML = `<div style="color:#f87171;font-weight:600;">❌ Network error. Check server is running.</div>`;
    }
}

/* ════════════════════════════
   VERIFICATION BAR (from API)
════════════════════════════ */
async function loadVerificationStatus() {
    try {
        const res  = await fetch("/api/v1/verification-status", {
            headers: { Authorization: "Bearer " + token }
        });
        if (!res.ok) return;
        const data = await res.json();

        const pct  = Math.round(data.percentage || 0);
        const cats = data.categories || {};

        // Animate bar
        const fill  = document.getElementById("verifyFill");
        const pctEl = document.getElementById("verifyPct");
        if (fill)  fill.style.width  = pct + "%";
        if (pctEl) pctEl.textContent = pct + "%";

        // Badge config
        const badgeCfg = {
            "badge-identity":    { cat: cats.identity,    label: "Identity"    },
            "badge-income":      { cat: cats.income,      label: "Income"      },
            "badge-assets":      { cat: cats.assets,      label: "Assets"      },
            "badge-liabilities": { cat: cats.liabilities, label: "Liabilities" },
        };

        const ICONS = { verified: "✅", pending: "🕐", failed: "❌", unverified: "🔘" };
        const CLASSES = { verified: "verified", pending: "pending", failed: "unverified", unverified: "unverified" };

        for (const [badgeId, { cat, label }] of Object.entries(badgeCfg)) {
            const badge  = document.getElementById(badgeId);
            if (!badge || !cat) continue;
            const status = cat.status || "unverified";
            badge.className = `vb-badge ${CLASSES[status] || "unverified"}`;
            badge.textContent = `${ICONS[status] || "🔘"} ${label}`;
        }

        // If 100% — show confetti effect on bar
        if (pct >= 100) {
            if (fill) fill.style.background = "linear-gradient(90deg, #22c55e, #16a34a)";
            if (pctEl) pctEl.style.color = "#22c55e";
        }

        // ── Also update the registered screen dynamic rows ──
        const regFill = document.getElementById("regVerifyFill");
        const regPct  = document.getElementById("regVerifyPct");
        const regRows = document.getElementById("regVerifyRows");

        if (regFill) regFill.style.width = pct + "%";
        if (regPct)  regPct.textContent  = pct + "%";

        if (regRows && cats) {
            const statusCfg = {
                verified:   { label:"Verified",    bg:"rgba(34,197,94,0.15)",   color:"#22c55e" },
                pending:    { label:"Pending",      bg:"rgba(245,158,11,0.12)",  color:"#f59e0b" },
                unverified: { label:"Upload Docs",  bg:"rgba(100,116,139,0.12)", color:"#64748b" },
                failed:     { label:"Failed",       bg:"rgba(248,113,113,0.12)", color:"#f87171" },
            };
            const rows = [
                { icon:"🪪", label:"Personal Identity (PAN + Aadhaar)", cat: cats.identity    },
                { icon:"💼", label:"Income (Salary Slip / ITR)",         cat: cats.income      },
                { icon:"🏦", label:"Assets (Property / Demat)",          cat: cats.assets      },
                { icon:"📋", label:"Liabilities (CIBIL Bureau Check)",   cat: cats.liabilities },
            ];
            regRows.innerHTML = rows.map(r => {
                const s   = r.cat?.status || "unverified";
                const cfg = statusCfg[s] || statusCfg.unverified;
                const score = r.cat?.score || 0;
                const maxPt = r.cat?.max   || 0;
                return `
                <div style="display:flex;align-items:center;justify-content:space-between;font-size:13px;">
                    <span style="color:#e2e8f0;">${r.icon} ${r.label}</span>
                    <div style="display:flex;align-items:center;gap:8px;">
                        ${maxPt > 0 ? `<span style="font-size:10px;color:#475569;">${score}/${maxPt}pts</span>` : ""}
                        <span style="background:${cfg.bg};color:${cfg.color};font-size:10.5px;font-weight:700;padding:2px 9px;border-radius:4px;">
                            ${cfg.label}
                        </span>
                    </div>
                </div>`;
            }).join("");
        }

    } catch (e) {
        console.log("Verification fetch error:", e);
    }
}

/* ════════════════════════════
   REVIEW STEP
════════════════════════════ */
function buildReviewStep() {
    const income      = num("salary") + num("sideIncome") + num("rentalIncome") + num("passiveIncome");
    const expenses    = num("fixedExpense");
    const assets      = num("stocks") + num("mutualFunds") + num("bonds") + num("crypto") +
                        num("realEstate") + num("gold") + num("vehicles") + num("cash") +
                        num("fixedDeposits") + num("insurance");
    const liabilities = num("homeLoan") + num("carLoan") + num("personalLoan") +
                        num("eduLoan") + num("bizLoan") + num("otherLoans") + num("creditCard");
    const netWorth    = assets - liabilities;
    const savingsRate = income > 0 ? ((income - expenses) / income * 100).toFixed(1) : 0;

    setVal("rev-income",      fmt(income));
    setVal("rev-assets",      fmt(assets));
    setVal("rev-liabilities", fmt(liabilities));
    setVal("rev-networth",    fmt(netWorth));
    setVal("rev-savings",     savingsRate + "%");
    setVal("rev-expcap",      fmt(income * 0.6));

    buildCharts(assets, income, expenses, liabilities);
}

/* ════════════════════════════
   CHARTS
════════════════════════════ */
function buildCharts(assets, income, expenses, liabilities) {
    const assetCtx = document.getElementById("assetChart");
    if (assetCtx) {
        if (assetChart) assetChart.destroy();
        const AL = ["Stocks","MF/SIP","Bonds","Crypto","Real Estate","Gold","Vehicles","Cash","FD/PPF","Insurance"];
        const AV = [num("stocks"),num("mutualFunds"),num("bonds"),num("crypto"),num("realEstate"),
                    num("gold"),num("vehicles"),num("cash"),num("fixedDeposits"),num("insurance")];
        const filtered = AL.map((l,i) => ({l, v: AV[i]})).filter(x => x.v > 0);
        assetChart = new Chart(assetCtx, {
            type: "doughnut",
            data: {
                labels: filtered.map(x => x.l),
                datasets: [{ data: filtered.map(x => x.v),
                    backgroundColor: ["#c9a84c","#63d1ff","#22c55e","#f59e0b","#a78bfa","#f472b6","#34d399","#60a5fa","#fb923c","#94a3b8"],
                    borderColor: "#07090f", borderWidth: 3, hoverOffset: 6 }]
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: "62%",
                plugins: { legend: { position: "bottom", labels: { color: "#94a3b8", font: { size: 10 }, padding: 8, boxWidth: 9 } },
                    tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${fmt(ctx.raw)}` } } } }
        });
    }

    const ieCtx = document.getElementById("incomeExpenseChart");
    if (ieCtx) {
        if (incomeExpenseChart) incomeExpenseChart.destroy();
        incomeExpenseChart = new Chart(ieCtx, {
            type: "bar",
            data: {
                labels: ["Income", "Expenses", "Net Worth"],
                datasets: [{ data: [income, expenses + liabilities, income - expenses],
                    backgroundColor: ["rgba(34,197,94,0.7)","rgba(248,113,113,0.7)","rgba(201,168,76,0.7)"],
                    borderColor: ["#22c55e","#f87171","#c9a84c"], borderWidth: 1.5, borderRadius: 6 }]
            },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: "#64748b" }, grid: { color: "rgba(255,255,255,0.04)" } },
                    y: { ticks: { color: "#64748b", callback: v => "₹" + (v/1000).toFixed(0) + "k" },
                         grid: { color: "rgba(255,255,255,0.04)" } }
                }
            }
        });
    }
}

/* ════════════════════════════
   SUBMIT PROFILE
════════════════════════════ */
async function submitProfile() {
    if (!document.getElementById("consent1")?.checked ||
        !document.getElementById("consent2")?.checked ||
        !document.getElementById("consent3")?.checked) {
        showToast("⚠️ Please accept all declarations before submitting.", "warning");
        return;
    }

    const btn = document.querySelector(".btn-submit");
    if (btn) { btn.textContent = "Saving..."; btn.disabled = true; }

    const profileData = {
        // Step 1 — Identity
        full_name:      val("fullName"),
        dob:            val("dob"),
        pan:            val("pan"),
        aadhaar:        val("aadhaar"),
        mobile:         val("mobile"),
        email_addr:     val("emailAddr"),
        address_line1:  val("addr1"),
        city:           val("city"),
        state:          val("state"),
        pincode:        val("pincode"),
        occupation:     val("occupation"),
        employer:       val("employer"),
        income_bracket: val("incomeBracket"),

        // Step 2 — Income
        monthly_income: num("salary"),
        side_income:    num("sideIncome"),
        rental_income:  num("rentalIncome"),
        passive_income: num("passiveIncome"),

        // Step 3 — Assets (all individual)
        stocks:          num("stocks"),
        mutual_funds:    num("mutualFunds"),
        bonds:           num("bonds"),
        crypto:          num("crypto"),
        real_estate:     num("realEstate"),
        gold:            num("gold"),
        vehicles:        num("vehicles"),
        cash_savings:    num("cash"),
        fixed_deposits:  num("fixedDeposits"),
        insurance_value: num("insurance"),

        // Step 4 — Liabilities (all individual)
        home_loan:      num("homeLoan"),
        car_loan:       num("carLoan"),
        personal_loan:  num("personalLoan"),
        education_loan: num("eduLoan"),
        business_loan:  num("bizLoan"),
        other_loans:    num("otherLoans"),
        credit_card:    num("creditCard"),
        fixed_expenses: num("fixedExpense"),
    };

    try {
        const res = await fetch("/api/v1/financial-profile", {
            method:  "POST",
            headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
            body:    JSON.stringify(profileData)
        });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || "Server error " + res.status);
        }

        // Mark profile as submitted so next page load shows registered screen instantly
        const _key = "wp_submitted_" + (token ? token.slice(-12) : "user");
        localStorage.setItem(_key, "1");

        showAlreadyRegisteredScreen(profileData);
        await loadVerificationStatus();
        window.scrollTo({ top: 0, behavior: "smooth" });

    } catch(err) {
        console.error("Submit error:", err);
        showToast("❌ Failed to save: " + (err.message || "Please try again."), "warning");
        if (btn) { btn.textContent = "🚀 Submit Wealth Profile"; btn.disabled = false; }
    }
}

/* ════════════════════════════
   TOAST
════════════════════════════ */
function showToast(msg, type = "success") {
    const t = document.getElementById("toast");
    if (!t) return;
    t.textContent = msg;
    t.className   = `toast show ${type}`;
    setTimeout(() => t.className = "toast", 4500);
}

/* ════════════════════════════
   ALREADY-REGISTERED SCREEN
════════════════════════════ */
function showAlreadyRegisteredScreen(profileData) {
    // Hide the form UI
    document.querySelectorAll(".form-step").forEach(s => s.style.display = "none");
    document.querySelector(".step-nav").style.display = "none";
    document.querySelector(".profile-summary").style.display = "none";
    document.querySelector(".verification-bar").style.display = "none";

    // Build the registered message screen
    const wrapper = document.querySelector(".page-wrapper");
    const existing = document.getElementById("alreadyRegisteredScreen");
    if (existing) { existing.style.display = "block"; return; }

    const d = profileData || {};
    const totalAssets = (d.stocks || 0) + (d.bonds || 0) + (d.real_estate || 0) +
                        (d.gold || 0) + (d.cash_savings || 0);
    const totalIncome = (d.monthly_income || 0) + (d.side_income || 0) +
                        (d.rental_income || 0) + (d.passive_income || 0);
    const totalLiab   = (d.loans || 0) + (d.credit_card || 0);
    const netWorth    = totalAssets - totalLiab;

    const screen = document.createElement("div");
    screen.id = "alreadyRegisteredScreen";
    screen.innerHTML = `
        <div style="
            max-width: 600px;
            margin: 60px auto;
            text-align: center;
            animation: fadeUp .5s ease;
        ">
            <div style="font-size:72px;margin-bottom:18px;">🏦</div>

            <div style="
                background: linear-gradient(135deg, rgba(201,168,76,0.12), rgba(34,197,94,0.08));
                border: 1px solid rgba(201,168,76,0.3);
                border-radius: 20px;
                padding: 40px 36px;
                margin-bottom: 24px;
            ">
                <div style="
                    display:inline-flex;
                    align-items:center;
                    gap:8px;
                    background:rgba(34,197,94,0.12);
                    border:1px solid rgba(34,197,94,0.3);
                    border-radius:20px;
                    padding:5px 16px;
                    font-size:11.5px;
                    font-weight:700;
                    color:#22c55e;
                    letter-spacing:.5px;
                    margin-bottom:18px;
                ">✅ REGISTERED WITH FINANCEAI</div>

                <h2 style="
                    font-family: 'DM Serif Display', serif;
                    font-size: 26px;
                    color: #e2e8f0;
                    margin-bottom: 10px;
                    line-height: 1.3;
                ">Your Assets Are Secured & Registered</h2>

                <p style="
                    font-size: 14px;
                    color: #64748b;
                    line-height: 1.7;
                    max-width: 440px;
                    margin: 0 auto 28px;
                ">
                    Your wealth profile has already been submitted and is securely stored with FinanceAI.
                    All your assets, income, and liabilities are registered and under verification.
                </p>

                <div style="
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 14px;
                    margin-bottom: 28px;
                ">
                    <div style="background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:12px;padding:16px 12px;">
                        <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;">Monthly Income</div>
                        <div style="font-size:17px;font-weight:700;color:#22c55e;">₹${Number(totalIncome).toLocaleString("en-IN")}</div>
                    </div>
                    <div style="background:rgba(201,168,76,0.08);border:1px solid rgba(201,168,76,0.2);border-radius:12px;padding:16px 12px;">
                        <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;">Total Assets</div>
                        <div style="font-size:17px;font-weight:700;color:#c9a84c;">₹${Number(totalAssets).toLocaleString("en-IN")}</div>
                    </div>
                    <div style="background:rgba(99,209,255,0.08);border:1px solid rgba(99,209,255,0.2);border-radius:12px;padding:16px 12px;">
                        <div style="font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;">Net Worth</div>
                        <div style="font-size:17px;font-weight:700;color:${netWorth >= 0 ? '#c9a84c' : '#f87171'};">₹${Number(netWorth).toLocaleString("en-IN")}</div>
                    </div>
                </div>

                <div style="
                    text-align:left;
                    background:rgba(15,20,32,0.5);
                    border:1px solid rgba(255,255,255,0.07);
                    border-radius:12px;
                    padding:18px 20px;
                    margin-bottom:24px;
                ">
                    <div style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Verification Status</div>
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                        <div style="flex:1;height:6px;background:rgba(255,255,255,.06);border-radius:6px;overflow:hidden;">
                            <div id="regVerifyFill" style="height:100%;border-radius:6px;background:linear-gradient(90deg,#c9a84c,#22c55e);width:0%;transition:width 1s ease;"></div>
                        </div>
                        <span id="regVerifyPct" style="font-size:12px;font-weight:700;color:#c9a84c;min-width:36px;">0%</span>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:10px;" id="regVerifyRows">
                        <div style="color:#475569;font-size:12px;">Loading verification status...</div>
                    </div>
                </div>

                <p style="font-size:12px;color:#475569;margin-bottom:20px;">
                    🔒 Your data is encrypted end-to-end. Document verification takes 24–48 hours.
                </p>

                <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                    <button class="btn-next" onclick="window.location.href='/dashboard'"
                        style="padding:11px 22px;">← Back to Dashboard</button>
                    <button class="btn-next" onclick="enterUpdateMode()"
                        style="background:rgba(201,168,76,.1);color:#c9a84c;border:1px solid rgba(201,168,76,.25);padding:11px 22px;">
                        ✏️ Update My Profile
                    </button>
                </div>
            </div>

            <p style="font-size:11px;color:#334155;">
                ⚠️ Re-submitting will flag changed fields for re-verification.
            </p>
        </div>
    `;
    wrapper.appendChild(screen);
}

/* ════════════════════════════
   STORED PROFILE (for prefill)
════════════════════════════ */
let _storedProfile = null;

function prefillFormFromProfile(d) {
    if (!d) return;
    const sf = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined && v !== null) el.value = v; };

    // Step 1 — Identity
    sf("fullName",      d.full_name);
    sf("dob",           d.dob);
    sf("pan",           d.pan);
    sf("aadhaar",       d.aadhaar);
    sf("mobile",        d.mobile);
    sf("emailAddr",     d.email_addr);
    sf("addr1",         d.address_line1);
    sf("city",          d.city);
    sf("pincode",       d.pincode);
    sf("employer",      d.employer);
    if (d.state)          { const el = document.getElementById("state");          if (el) el.value = d.state; }
    if (d.occupation)     { const el = document.getElementById("occupation");     if (el) el.value = d.occupation; }
    if (d.income_bracket) { const el = document.getElementById("incomeBracket"); if (el) el.value = d.income_bracket; }

    // Step 2 — Income
    sf("salary",        d.monthly_income);
    sf("sideIncome",    d.side_income);
    sf("rentalIncome",  d.rental_income);
    sf("passiveIncome", d.passive_income);

    // Step 3 — Assets (all individual)
    sf("stocks",        d.stocks);
    sf("mutualFunds",   d.mutual_funds);
    sf("bonds",         d.bonds);
    sf("crypto",        d.crypto);
    sf("realEstate",    d.real_estate);
    sf("gold",          d.gold);
    sf("vehicles",      d.vehicles);
    sf("cash",          d.cash_savings);
    sf("fixedDeposits", d.fixed_deposits);
    sf("insurance",     d.insurance_value);

    // Step 4 — Liabilities (all individual)
    sf("homeLoan",      d.home_loan);
    sf("carLoan",       d.car_loan);
    sf("personalLoan",  d.personal_loan);
    sf("eduLoan",       d.education_loan);
    sf("bizLoan",       d.business_loan);
    sf("otherLoans",    d.other_loans);
    sf("creditCard",    d.credit_card);
    sf("fixedExpense",  d.fixed_expenses);

    updateSummary();
}

async function enterUpdateMode() {
    const screen = document.getElementById("alreadyRegisteredScreen");
    if (screen) screen.style.display = "none";
    document.querySelectorAll(".form-step").forEach(s => s.style.display = "");
    document.querySelector(".step-nav").style.display = "";
    document.querySelector(".profile-summary").style.display = "";
    document.querySelector(".verification-bar").style.display = "";
    goToStep(1);

    showToast("⏳ Loading your saved details...", "info");

    try {
        // Always fetch fresh from API — never rely on stale cache
        const res = await fetch("/api/v1/financial-profile", {
            headers: { Authorization: "Bearer " + token }
        });
        if (res.ok) {
            const d = await res.json();
            _storedProfile = d;
            prefillFormFromProfile(d);
            showToast("✏️ Your saved details are loaded — edit and re-submit.", "success");
        } else {
            showToast("✏️ No saved profile found — fill in your details.", "info");
        }
    } catch(e) {
        // Fallback to cached if API fails
        if (_storedProfile) {
            prefillFormFromProfile(_storedProfile);
            showToast("✏️ Details loaded from cache.", "info");
        } else {
            showToast("⚠️ Could not load saved details.", "warning");
        }
    }
}

/* ════════════════════════════
   INIT
════════════════════════════ */
document.addEventListener("DOMContentLoaded", async () => {

    // Fast-path: if we already know profile was submitted (stored locally), hide form immediately
    const profileKey = "wp_submitted_" + (token ? token.slice(-12) : "user");
    if (localStorage.getItem(profileKey) === "1") {
        // Hide form instantly while API loads
        document.querySelectorAll(".form-step").forEach(s => s.style.display = "none");
        const nav = document.querySelector(".step-nav");
        if (nav) nav.style.display = "none";
    }

    try {
        const res = await fetch("/api/v1/financial-profile", {
            headers: { Authorization: "Bearer " + token }
        });

        if (res.ok) {
            const d = await res.json();

            // Profile exists if API returns a non-null object with any key present
            const profileExists = d !== null &&
                                  d !== undefined &&
                                  typeof d === "object" &&
                                  Object.keys(d).length > 0;

            if (profileExists) {
                localStorage.setItem(profileKey, "1");
                _storedProfile = d;          // ← store for prefill on update
                showAlreadyRegisteredScreen(d);
                await loadVerificationStatus();
                return;
            }
        } else {
            // 404 = no profile — restore form if we hid it prematurely
            localStorage.removeItem(profileKey);
            document.querySelectorAll(".form-step").forEach((s, i) => {
                s.style.display = i === 0 ? "block" : "none";
            });
            const nav = document.querySelector(".step-nav");
            if (nav) nav.style.display = "";
        }

        // No profile yet, show the form normally
    } catch (e) {
        console.log("Profile fetch error:", e);
    }

    await loadVerificationStatus();
});