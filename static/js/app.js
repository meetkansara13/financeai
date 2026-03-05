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
   AUTH — LOGOUT
═══════════════════════════════════════ */
function logout() {
    localStorage.removeItem("token");
    window.location.href = "/login";
}

/* ═══════════════════════════════════════
   AUTH — GET TOKEN
═══════════════════════════════════════ */
function getToken() {
    return localStorage.getItem("token");
}

/* ═══════════════════════════════════════
   SIDEBAR — ACTIVE STATE & USER BADGE
═══════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {

    // 1. Mark active nav link based on current URL path
    const currentPath = window.location.pathname.split("/")[1] || "dashboard";
    document.querySelectorAll(".nav-item[data-page]").forEach(link => {
        if (link.dataset.page === currentPath) {
            link.classList.add("active");
        }
    });

    // 2. Decode JWT and show user's name initial in sidebar avatar
    const token = getToken();
    if (token) {
        try {
            const payload = JSON.parse(atob(token.split(".")[1]));
            const email = payload.sub || "";
            const name = email.split("@")[0];
            const displayName = name.charAt(0).toUpperCase() + name.slice(1);

            const nameEl = document.getElementById("sidebarUserName");
            const avatarEl = document.getElementById("sidebarAvatar");

            if (nameEl) nameEl.textContent = displayName;
            if (avatarEl) avatarEl.textContent = displayName.charAt(0).toUpperCase();
        } catch (e) {
            // token unreadable — silent fail
        }
    }

    // 3. If no token on a protected page, redirect to login
    const publicPages = ["login"];
    if (!token && !publicPages.includes(window.location.pathname.split("/")[1])) {
        window.location.href = "/login";
    }
});