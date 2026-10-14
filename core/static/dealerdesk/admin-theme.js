/* Shared preference with the React workspace; runs before first paint. */
(() => {
  const media = matchMedia("(prefers-color-scheme: dark)");
  let preference = "system";
  try { preference = localStorage.getItem("vikmo-theme") || "system"; } catch { /* Storage is optional. */ }
  const apply = () => {
    if (!["light", "dark", "system"].includes(preference)) preference = "system";
    document.documentElement.dataset.theme = preference === "system" ? (media.matches ? "dark" : "light") : preference;
    const select = document.getElementById("vikmo-admin-theme");
    if (select) select.value = preference;
  };
  apply();
  media.addEventListener("change", apply);
  window.addEventListener("storage", event => { if (event.key === "vikmo-theme") { preference = event.newValue || "system"; apply(); } });
  document.addEventListener("DOMContentLoaded", () => {
    apply();
    document.getElementById("vikmo-admin-theme")?.addEventListener("change", event => {
      preference = event.target.value;
      try { localStorage.setItem("vikmo-theme", preference); } catch { /* Storage is optional. */ }
      apply();
    });
    document.querySelectorAll('input[type="password"]').forEach(input => {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "vikmo-password-toggle";
      toggle.textContent = "Show password";
      toggle.setAttribute("aria-controls", input.id);
      toggle.setAttribute("aria-pressed", "false");
      toggle.addEventListener("click", () => {
        const visible = input.type === "password";
        input.type = visible ? "text" : "password";
        toggle.textContent = visible ? "Hide password" : "Show password";
        toggle.setAttribute("aria-pressed", String(visible));
      });
      input.insertAdjacentElement("afterend", toggle);
    });
  });
})();
