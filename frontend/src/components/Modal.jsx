import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
export function Modal({ children, onClose, label, busy = false }) {
  const ref = useRef(null);
  const [closing, setClosing] = useState(false);
  const requestClose = () => {
    if (busy || closing) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { onClose(); return; }
    setClosing(true);
  };
  useEffect(() => {
    if (!closing) return;
    const timer = setTimeout(onClose, 150);
    return () => clearTimeout(timer);
  }, [closing, onClose]);
  useEffect(() => {
    const previous = document.activeElement;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const panel = ref.current;
    panel.querySelectorAll("label").forEach((label, index) => {
      const input = label.parentElement.querySelector("input, select, textarea");
      if (input) { input.id ||= `dialog-field-${index}`; label.htmlFor = input.id; }
    });
    (panel.querySelector("input, select, textarea, button") || panel).focus();
    return () => { document.body.style.overflow = oldOverflow; previous?.focus(); };
  }, []);
  const handleKeyDown = event => {
    if (event.key === "Escape" && !busy) { event.stopPropagation(); requestClose(); }
    if (event.key !== "Tab") return;
    const items = [...ref.current.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')];
    const first = items[0], last = items.at(-1);
    if (!first) { event.preventDefault(); return; }
    if (event.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };
  return createPortal(<div className={`modal-backdrop ${closing ? "modal-closing" : ""}`} onMouseDown={event => { if (event.target === event.currentTarget) requestClose(); }}><div ref={ref} className="modal-container" role="dialog" aria-modal="true" aria-label={label} aria-busy={busy} tabIndex={-1} onKeyDown={handleKeyDown}>{typeof children === "function" ? children(requestClose) : children}</div></div>, document.body);
}
