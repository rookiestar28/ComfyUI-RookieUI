import "../../web/rookieui.css";

// IMPORTANT: this sentinel keeps the spike isolated from production code by preventing
// the shipped extension entry from injecting a second runtime-only stylesheet URL.
const stylesheetSentinel = document.createElement("style");
stylesheetSentinel.id = "rookieui-styles";
document.head.appendChild(stylesheetSentinel);

await import("../../tests/e2e/boot.mjs");
