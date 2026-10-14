import { useEffect, useState } from "react";
import { ThemeContext } from "./theme-context";
const validThemes = ["light", "dark", "system"];
export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(() => {
    try { const saved = localStorage.getItem("vikmo-theme"); return validThemes.includes(saved) ? saved : "system"; }
    catch { return "system"; }
  });
  const [reducedMotion, setReducedMotion] = useState(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    const motion = matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(motion.matches);
    motion.addEventListener("change", update);
    return () => motion.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () => { document.documentElement.dataset.theme = theme === "system" ? (media.matches ? "dark" : "light") : theme; };
    apply(); media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  useEffect(() => {
    const sync = event => { if (event.key === "vikmo-theme") setThemeState(validThemes.includes(event.newValue) ? event.newValue : "system"); };
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  const setTheme = value => {
    if (!validThemes.includes(value)) return;
    setThemeState(value);
    try { localStorage.setItem("vikmo-theme", value); } catch { /* Theme works in memory if storage is unavailable. */ }
  };
  return <ThemeContext.Provider value={{ theme, setTheme, reducedMotion }}>{children}</ThemeContext.Provider>;
}

