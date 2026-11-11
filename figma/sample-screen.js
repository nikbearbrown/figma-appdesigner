// EXAMPLE, to adapt: the specimen page from the first run (2026-11-10). It builds two local
// components (primary button, list row) and, for each mode of the Palette collection, a column
// with the role swatches and one 390 x 844 phone screen. See docs/palette-kit.png for the result.
//
// Run figma/palette-variables.js first (`./fad palettes --figma`) and paste the collection ID
// from its receipt below. Variables are found by name inside that one collection.
const COLLECTION_ID = '__COLLECTION_ID__'; // e.g. 'VariableCollectionId:1:2' from the receipt

const coll = await figma.variables.getVariableCollectionByIdAsync(COLLECTION_ID);
if (!coll) throw new Error('Palette collection not found: ' + COLLECTION_ID);
const V = {};
for (const id of coll.variableIds) {
  const v = await figma.variables.getVariableByIdAsync(id);
  V[v.name.split('/')[1]] = v; // palette/ground -> ground, type/heading -> heading
}
for (const need of ['ground', 'surface', 'ink', 'ink-soft', 'border', 'accent', 'on-accent', 'heading', 'body']) {
  if (!V[need]) throw new Error('variable missing: ' + need + '. Found: ' + Object.keys(V).join(', '));
}

// Fonts first: every family any mode can show, in the three weights the kit uses.
const families = new Set();
for (const m of coll.modes) { families.add(V['heading'].valuesByMode[m.modeId]); families.add(V['body'].valuesByMode[m.modeId]); }
await Promise.all([...families].flatMap(family => ['Regular', 'Medium', 'Bold'].map(style => figma.loadFontAsync({ family, style }))));

const paint = v => figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }, 'color', v);
const toHex = c => '#' + [c.r, c.g, c.b].map(x => Math.round(x * 255).toString(16).padStart(2, '0')).join('').toUpperCase();
const created = [];
const text = (chars, size, style, colorVar, famVar, name) => {
  const t = figma.createText();
  t.fontName = { family: 'Inter', style };
  t.characters = chars;
  t.fontSize = size;
  t.fills = [paint(colorVar)];
  t.setBoundVariable('fontFamily', famVar);
  if (name) t.name = name;
  return t;
};

const page = figma.currentPage;

// Local components, kept outside the specimen frame.
const compArea = figma.createAutoLayout('VERTICAL', { name: 'Components', itemSpacing: 32 });
compArea.x = 100; compArea.y = 100;
compArea.fills = [];
page.appendChild(compArea);

const button = figma.createComponent();
button.name = 'Button / Primary';
button.layoutMode = 'HORIZONTAL';
button.primaryAxisAlignItems = 'CENTER';
button.counterAxisAlignItems = 'CENTER';
button.paddingLeft = 20; button.paddingRight = 20;
button.resize(350, 48); // 48 clears both the 44 pt (iOS) and 48 dp (Android) tap-target rules
button.primaryAxisSizingMode = 'FIXED';
button.counterAxisSizingMode = 'FIXED';
button.cornerRadius = 12;
button.fills = [paint(V['accent'])];
button.appendChild(text('New note', 16, 'Bold', V['on-accent'], V['body'], 'Label'));
button.description = 'The one main action on a screen.';
compArea.appendChild(button);

const row = figma.createComponent();
row.name = 'List row';
row.layoutMode = 'VERTICAL';
row.itemSpacing = 4;
row.paddingTop = 12; row.paddingBottom = 12;
row.primaryAxisAlignItems = 'CENTER';
row.resize(350, 60);
row.primaryAxisSizingMode = 'AUTO';
row.counterAxisSizingMode = 'FIXED';
row.minHeight = 60;
row.fills = [];
row.strokes = [paint(V['border'])];
row.strokeTopWeight = 0; row.strokeLeftWeight = 0; row.strokeRightWeight = 0; row.strokeBottomWeight = 1;
const rt = text('Title', 16, 'Medium', V['ink'], V['body'], 'Title');
const rs = text('Subtitle', 13, 'Regular', V['ink-soft'], V['body'], 'Subtitle');
row.appendChild(rt); row.appendChild(rs);
rt.layoutSizingHorizontal = 'FILL'; rs.layoutSizingHorizontal = 'FILL';
row.description = 'One item in a list: a title and a line of secondary text, with a hairline under it.';
compArea.appendChild(row);
created.push(compArea.id, button.id, row.id);

const wrap = figma.createAutoLayout('HORIZONTAL', { name: 'Palette specimens', itemSpacing: 40 });
wrap.x = 100 + 350 + 200; wrap.y = 100;
wrap.fills = [];
wrap.counterAxisAlignItems = 'MIN';
page.appendChild(wrap);
created.push(wrap.id);

const ROLES = ['ground', 'surface', 'ink', 'ink-soft', 'border', 'accent', 'on-accent'];
const NOTES = [['Ridge loop, north side', 'Water at mile 3. Shade after the saddle.'], ['Gear to replace', 'Left boot lace, stove gasket'], ['Trailhead parking', 'Lot fills by 8 on weekends'], ['Wildflowers', 'Lupine and paintbrush near the creek']];
const columns = [];
for (const m of coll.modes) {
  const col = figma.createAutoLayout('VERTICAL', { name: 'Specimen / ' + m.name, itemSpacing: 24 });
  wrap.appendChild(col);
  col.setExplicitVariableModeForCollection(coll, m.modeId); // everything inside takes this mode
  col.paddingTop = 24; col.paddingBottom = 24; col.paddingLeft = 24; col.paddingRight = 24;
  col.cornerRadius = 16;
  col.fills = [paint(V['surface'])];
  col.strokes = [paint(V['border'])];
  col.appendChild(text(m.name, 24, 'Bold', V['ink'], V['heading'], 'Mode name'));

  const sw = figma.createAutoLayout('VERTICAL', { name: 'Roles', itemSpacing: 8 });
  col.appendChild(sw);
  sw.fills = [];
  for (const role of ROLES) {
    const line = figma.createAutoLayout('HORIZONTAL', { name: 'Role / ' + role, itemSpacing: 12 });
    sw.appendChild(line);
    line.fills = [];
    line.counterAxisAlignItems = 'CENTER';
    const chip = figma.createRectangle();
    chip.name = 'Chip';
    chip.resize(44, 28);
    chip.cornerRadius = 6;
    chip.fills = [paint(V[role])];
    chip.strokes = [paint(V['ink-soft'])];
    line.appendChild(chip);
    line.appendChild(text(role, 13, 'Medium', V['ink'], V['body'], 'Role'));
    line.appendChild(text(toHex(V[role].valuesByMode[m.modeId]), 13, 'Regular', V['ink-soft'], V['body'], 'Hex'));
  }

  const phone = figma.createAutoLayout('VERTICAL', { name: 'S-01 Notes list / iphone / styled / default', itemSpacing: 16 });
  col.appendChild(phone);
  phone.resize(390, 844);
  phone.primaryAxisSizingMode = 'FIXED';
  phone.counterAxisSizingMode = 'FIXED';
  phone.paddingTop = 47 + 12; phone.paddingBottom = 34 + 12; // safe area plus breathing room
  phone.paddingLeft = 20; phone.paddingRight = 20;
  phone.cornerRadius = 40;
  phone.clipsContent = true;
  phone.fills = [paint(V['ground'])];
  phone.strokes = [paint(V['border'])];
  phone.appendChild(text('Notes', 34, 'Bold', V['ink'], V['heading'], 'Screen title'));

  const search = figma.createAutoLayout('HORIZONTAL', { name: 'Search field' });
  phone.appendChild(search);
  search.resize(350, 44);
  search.primaryAxisSizingMode = 'FIXED';
  search.counterAxisSizingMode = 'FIXED';
  search.layoutSizingHorizontal = 'FILL';
  search.counterAxisAlignItems = 'CENTER';
  search.paddingLeft = 14; search.paddingRight = 14;
  search.cornerRadius = 10;
  search.fills = [paint(V['surface'])];
  search.strokes = [paint(V['border'])];
  search.appendChild(text('Search notes', 16, 'Regular', V['ink-soft'], V['body'], 'Placeholder'));

  const list = figma.createAutoLayout('VERTICAL', { name: 'List' });
  phone.appendChild(list);
  list.fills = [];
  list.layoutSizingHorizontal = 'FILL';
  for (const [title, sub] of NOTES) {
    const inst = row.createInstance();
    list.appendChild(inst);
    inst.layoutSizingHorizontal = 'FILL';
    inst.findOne(n => n.type === 'TEXT' && n.name === 'Title').characters = title;
    inst.findOne(n => n.type === 'TEXT' && n.name === 'Subtitle').characters = sub;
  }

  const spacer = figma.createFrame();
  spacer.name = 'Spacer';
  spacer.fills = [];
  spacer.resize(10, 10);
  phone.appendChild(spacer);
  spacer.layoutSizingHorizontal = 'FILL';
  spacer.layoutGrow = 1;

  const btn = button.createInstance();
  phone.appendChild(btn);
  btn.layoutSizingHorizontal = 'FILL';

  columns.push({ mode: m.name, columnId: col.id, phoneId: phone.id, phoneSize: [phone.width, phone.height], buttonSize: [btn.width, btn.height], rowHeights: list.children.map(c => c.height) });
  created.push(col.id, phone.id);
}
return { pageId: page.id, wrapperId: wrap.id, componentsId: compArea.id, buttonId: button.id, rowId: row.id, columns, createdNodeIds: created, mutatedNodeIds: [] };
