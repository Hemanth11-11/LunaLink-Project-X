"""Floating browser-fullscreen toggle for the whole dashboard.

Streamlit's per-chart button only expands one chart. This injects a single
fixed control (top-right) into the parent page that toggles true browser
fullscreen for the entire app via the Fullscreen API. Rendered through a
zero-height component iframe; the click is a genuine user gesture in the parent
document, which the Fullscreen API requires.
"""

from __future__ import annotations

_HTML = """
<script>
(function () {
  var doc = window.parent.document;
  if (doc.getElementById("ll-fs-btn")) return;
  var btn = doc.createElement("button");
  btn.id = "ll-fs-btn";
  btn.title = "Toggle fullscreen";
  var EXPAND = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" '
    + 'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    + 'stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3"/>'
    + '<path d="M16 3h3a2 2 0 0 1 2 2v3"/><path d="M8 21H5a2 2 0 0 1-2-2v-3"/>'
    + '<path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
  var SHRINK = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" '
    + 'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    + 'stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3"/>'
    + '<path d="M21 8h-3a2 2 0 0 1-2-2V3"/><path d="M3 16h3a2 2 0 0 1 2 2v3"/>'
    + '<path d="M16 21v-3a2 2 0 0 1 2-2h3"/></svg>';
  btn.innerHTML = EXPAND;
  Object.assign(btn.style, {
    position: "fixed", top: "56px", right: "16px", zIndex: "100000",
    width: "36px", height: "36px", display: "flex", alignItems: "center",
    justifyContent: "center", borderRadius: "10px", cursor: "pointer",
    background: "rgba(9,14,26,0.72)", color: "#e7eefb",
    border: "1px solid rgba(120,150,190,0.30)", backdropFilter: "blur(6px)",
    boxShadow: "0 2px 8px rgba(0,0,0,0.35)"
  });
  btn.onmouseenter = function () {
    btn.style.background = "#38bdf8"; btn.style.color = "#04121f";
  };
  btn.onmouseleave = function () {
    btn.style.background = "rgba(9,14,26,0.72)"; btn.style.color = "#e7eefb";
  };
  // Inline handler runs in the PARENT realm (parent is the responsible document),
  // so the Fullscreen API's permission check passes and there is no dead-realm
  // closure after Streamlit reruns.
  btn.setAttribute("onclick",
    "var d=document,e=d.documentElement;"
    + "if(!d.fullscreenElement){(e.requestFullscreen||e.webkitRequestFullscreen).call(e);"
    + "this.dataset.fs='1';}"
    + "else{(d.exitFullscreen||d.webkitExitFullscreen).call(d);this.dataset.fs='';}");
  doc.body.appendChild(btn);
  doc.addEventListener("fullscreenchange", function () {
    var b = doc.getElementById("ll-fs-btn");
    if (b) b.innerHTML = doc.fullscreenElement ? SHRINK : EXPAND;
  });
})();
</script>
"""


def fullscreen_button() -> None:
    """Inject the fullscreen toggle into the parent page (once)."""

    import streamlit.components.v1 as components

    components.html(_HTML, height=0)
