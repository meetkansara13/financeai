/* ═══════════════════════════════════════
   AUTH — LOGIN
═══════════════════════════════════════ */
async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);
    const response = await fetch("/api/v1/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData
    });
    const data = await response.json();
    if (response.ok) {
        localStorage.setItem("token", data.access_token);
        window.location.href = "/dashboard";
    } else {
        document.getElementById("error").innerText = data.detail || "Login failed";
    }
}

/* ═══════════════════════════════════════
   AUTH — LOGOUT / TOKEN
═══════════════════════════════════════ */
function logout() {
    localStorage.removeItem("token");
    window.location.href = "/login";
}
function getToken() {
    return localStorage.getItem("token");
}

/* ═══════════════════════════════════════
   PREFERENCES HELPERS
═══════════════════════════════════════ */
const PREFS_KEY = 'financeai_prefs';
function getPrefs() {
    try { return JSON.parse(localStorage.getItem(PREFS_KEY) || '{}'); } catch(e) { return {}; }
}
function savePrefs(p) {
    localStorage.setItem(PREFS_KEY, JSON.stringify(p));
}

/* ═══════════════════════════════════════
   ACCENT COLOUR
═══════════════════════════════════════ */
function applyAccent(color) {
    if (!color) return;
    const r = document.documentElement;
    r.style.setProperty('--gold',         color);
    r.style.setProperty('--gold-dim',     color + '18');
    r.style.setProperty('--gold-glow',    color + '30');
    r.style.setProperty('--sb-gold',      color);
    r.style.setProperty('--sb-gold-dim',  color + '20');
    r.style.setProperty('--sb-gold-glow', color + '35');
}

/* ═══════════════════════════════════════
   DARK / LIGHT MODE
   — Always target <html> so it works
     even before <body> is parsed
═══════════════════════════════════════ */
function applyDarkMode(isDark) {
    // <html> is always available
    if (isDark) {
        document.documentElement.classList.remove('light-mode');
    } else {
        document.documentElement.classList.add('light-mode');
    }
    // body may not exist yet when called from <head>; set once DOM is ready
    if (document.body) {
        if (isDark) document.body.classList.remove('light-mode');
        else         document.body.classList.add('light-mode');
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            if (isDark) document.body.classList.remove('light-mode');
            else         document.body.classList.add('light-mode');
        }, { once: true });
    }
}

/* ═══════════════════════════════════════
   HIDE AMOUNTS
═══════════════════════════════════════ */
const AMOUNT_SELECTORS = [
    '.hero-balance-amount','.hero-mini-stat-val',
    '#kpi1Value','#kpi2Value','#kpi3Value','#kpi4Value',
    '.txn-amt','.txn-amount','.sum-val',
    '#sInc','#sExp','#sNet',
    '.an-kpi-val','#kInc','#kExp','#kSav','#kRate',
    '.kc-val','#kIncome','#kBudget','#kSpent','#kRemain','#kSaving',
    '.bc-amounts strong','.budget-spent','.budget-limit',
    '.wallet-balance','.wallet-amt',
    '#statSav','#statTxns',
    '.stat-card-val',
    '.hide-amount',
];

function tagAmountElements() {
    AMOUNT_SELECTORS.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => el.classList.add('hide-amount'));
    });
}

function applyHideAmounts(hide) {
    document.documentElement.classList.toggle('amounts-hidden', hide);
    if (document.body) document.body.classList.toggle('amounts-hidden', hide);
    if (hide) tagAmountElements();
}

/* ═══════════════════════════════════════
   APPLY ALL PREFS — runs immediately
   (targets <html> which always exists)
═══════════════════════════════════════ */
(function applyGlobalPrefs() {
    try {
        const p = getPrefs();
        applyDarkMode(p.dark !== false);          // default = dark
        if (p.hide)   applyHideAmounts(true);
        if (p.accent) applyAccent(p.accent);
    } catch(e) {}
})();

/* ═══════════════════════════════════════
   DOM READY — re-apply to body + tag amounts
═══════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', function() {
    const p = getPrefs();

    // Ensure body also has the class (belt-and-suspenders)
    applyDarkMode(p.dark !== false);
    if (p.hide) {
        applyHideAmounts(true);
        tagAmountElements();
    }
    if (p.accent) applyAccent(p.accent);

    // Sidebar active link
    const currentPath = window.location.pathname.split('/')[1] || 'dashboard';
    document.querySelectorAll('.nav-item[data-page], .sb-item[data-page]').forEach(link => {
        if (link.dataset.page === currentPath) link.classList.add('active');
    });

    // Sidebar user badge
    const token = getToken();
    if (token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const email = payload.sub || '';
            const name  = email.split('@')[0];
            const displayName = name.charAt(0).toUpperCase() + name.slice(1);
            const nameEl   = document.getElementById('sidebarUserName');
            const avatarEl = document.getElementById('sidebarAvatar');
            if (nameEl)   nameEl.textContent   = displayName;
            if (avatarEl) avatarEl.textContent  = displayName.charAt(0).toUpperCase();
        } catch(e) {}
    }

    // Redirect if no token
    const publicPages = ['login','register','forgot-password','reset-password'];
    if (!token && !publicPages.includes(window.location.pathname.split('/')[1])) {
        window.location.href = '/login';
    }

    // MutationObserver for dynamically added amounts
    if (p.hide && window.MutationObserver) {
        const obs = new MutationObserver(function(mutations) {
            if (!getPrefs().hide) return;
            mutations.forEach(function(m) {
                m.addedNodes.forEach(function(node) {
                    if (node.nodeType !== 1) return;
                    AMOUNT_SELECTORS.forEach(sel => {
                        try {
                            if (node.matches(sel)) node.classList.add('hide-amount');
                            node.querySelectorAll(sel).forEach(el => el.classList.add('hide-amount'));
                        } catch(e) {}
                    });
                });
            });
        });
        obs.observe(document.body, { childList: true, subtree: true });
    }
});