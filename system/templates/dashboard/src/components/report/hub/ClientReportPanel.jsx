// @ts-check
/* ClientReportPanel (#221 H1 placeholder): the panel the hub's cog opens. H3 REPLACES THIS FILE with the real client report settings
   (on or off, how often, the client's name, the reminder, the logo tiles). The hub mounts it as <ClientReportPanel code onClose />
   inside the slot [data-slot="ClientReportPanel"], which H1 positions (a popover under the cog) and closes on Esc or a click away. */

/** @param {{code: string, onClose: () => void}} props */
export function ClientReportPanel({ code, onClose }) {
  return (
    <div class="hubcfg-body">
      <p class="sub">Client report settings for {code} arrive in the next step.</p>
      <button type="button" class="btn sm" onClick={onClose}>Close</button>
    </div>
  );
}
