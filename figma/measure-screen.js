// Phase 6, the check: measures screens that are already drawn. Read-only: it changes nothing.
// Run through the Figma MCP's use_figma tool. First run 2026-11-10 on the six tutorial screens;
// it found the six faint hour labels on the weather screen (4.34:1, needs 4.5:1).
//
// Fill in the three constants. FRAME_IDS come from the ledger's figma.write receipts, never from
// layer names. DEVICE comes from `./fad devices --json`. The TAPPABLE lists name what a person can
// tap in THIS design: the script cannot guess that, so say it.
const PAGE_ID = '__PAGE_ID__';                 // the page the frames are on, e.g. '4:95'
const FRAME_IDS = ['__FRAME_ID__'];            // one or more screen frames
const DEVICE = { width: 390, height: 844, safe_top: 47, safe_bottom: 34, min_target: 44, min_text: 11 };
const TAPPABLE_COMPONENTS = ['Button / Primary', 'Button / Quiet', 'Text field'];
const TAPPABLE_LAYERS = ['Check (tap target)'];

const page = await figma.getNodeByIdAsync(PAGE_ID);
if (!page || page.type !== 'PAGE') throw new Error('page not found: ' + PAGE_ID);
await figma.setCurrentPageAsync(page);

// WCAG 2.x relative luminance and contrast ratio, worked out from the colors Figma resolved.
const lin = c => (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
const lum = c => 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
const toHex = c => '#' + [c.r, c.g, c.b].map(x => Math.round(x * 255).toString(16).padStart(2, '0')).join('').toUpperCase();
const solid = node => {
  if (!('fills' in node) || !Array.isArray(node.fills)) return null;
  const p = node.fills.filter(f => f.type === 'SOLID' && f.visible !== false && (f.opacity === undefined || f.opacity > 0.99));
  return p.length ? p[p.length - 1] : null;
};
// The fill a text sits on: the nearest ancestor that has an opaque solid fill.
const behind = node => { for (let n = node.parent; n && n.type !== 'PAGE'; n = n.parent) { const s = solid(n); if (s) return { color: s.color, from: n.name }; } return null; };

const out = [];
for (const id of FRAME_IDS) {
  const frame = await figma.getNodeByIdAsync(id);
  if (!frame) throw new Error('frame not found: ' + id);
  const box = frame.absoluteBoundingBox;
  const rel = n => { const b = n.absoluteBoundingBox; return { top: Math.round(b.y - box.y), bottom: Math.round(b.y - box.y + b.height), w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10 }; };
  const all = frame.findAll(() => true);
  const targets = [], texts = [], loose = [], safe = [];
  for (const n of all) {
    let tappable = null;
    if (n.type === 'INSTANCE') {
      const mc = await n.getMainComponentAsync();
      if (mc && TAPPABLE_COMPONENTS.includes(mc.name)) tappable = mc.name;
    } else if (TAPPABLE_LAYERS.includes(n.name)) tappable = n.name;
    if (tappable) {
      const r = rel(n);
      targets.push({ what: tappable, w: r.w, h: r.h, ok: r.w >= DEVICE.min_target && r.h >= DEVICE.min_target });
      if (r.top < DEVICE.safe_top || r.bottom > DEVICE.height - DEVICE.safe_bottom) safe.push({ what: tappable, top: r.top, bottom: r.bottom });
    }
    if (n.type === 'TEXT') {
      const fg = solid(n), bg = behind(n);
      const r = rel(n);
      const size = typeof n.fontSize === 'number' ? n.fontSize : null;
      const bold = n.fontName && typeof n.fontName === 'object' && /Bold/.test(n.fontName.style);
      const large = size !== null && (size >= 24 || (bold && size >= 18.66)); // WCAG "large text"
      const cr = fg && bg ? Math.round(ratio(fg.color, bg.color) * 100) / 100 : null;
      texts.push({ name: n.name, chars: n.characters.slice(0, 28), size, large, fg: fg ? toHex(fg.color) : null, bg: bg ? toHex(bg.color) : null, on: bg ? bg.from : null, ratio: cr, needs: large ? 3 : 4.5, ok: cr !== null && cr >= (large ? 3 : 4.5) });
      if (r.top < DEVICE.safe_top || r.bottom > DEVICE.height - DEVICE.safe_bottom) safe.push({ what: 'text: ' + n.characters.slice(0, 20), top: r.top, bottom: r.bottom });
    }
    for (const prop of ['fills', 'strokes']) {
      if (!(prop in n) || !Array.isArray(n[prop])) continue;
      for (const p of n[prop]) {
        if (p.type === 'SOLID' && p.visible !== false && !(p.boundVariables && p.boundVariables.color)) loose.push({ node: n.name, prop, hex: toHex(p.color) });
      }
    }
  }
  const sizes = texts.map(t => t.size).filter(s => s !== null);
  out.push({
    id, name: frame.name, nodes: all.length,
    targets,                                                   // HIG-TARGET-44 / M3-TARGET-48 / WCAG22-2.5.8
    smallTargets: targets.filter(t => !t.ok),
    textCount: texts.length, smallestText: Math.min(...sizes),
    textUnderMinimum: texts.filter(t => t.size !== null && t.size < DEVICE.min_text).length, // HIG-TEXT-11
    lowestContrast: texts.filter(t => t.ratio !== null).sort((a, b) => a.ratio - b.ratio).slice(0, 2),
    lowContrast: texts.filter(t => !t.ok),                     // WCAG22-1.4.3
    looseColors: loose,                                        // HOUSE-PALETTE-ONLY
    inSafeArea: safe,                                          // HOUSE-SAFE-AREA
  });
}
// Nothing was created or changed. Save this as design/checks/R-.../checks.json, then write findings.
return { device: DEVICE, screens: out, createdNodeIds: [], mutatedNodeIds: [] };
