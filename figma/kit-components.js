// EXAMPLE, to adapt: adds the kit components the three tutorial apps use (task rows, hour cell,
// day row, chat bubbles, text field, quiet button) to an existing Components area, and makes the
// pages '01 Wireframes' and '02 Screens'. As run on 2026-11-10.
//
// Run figma/palette-variables.js first; it makes the Palette collection, the Wireframe mode
// included. Paste the collection ID and the ID of the frame that holds your components.
const COLLECTION_ID = '__COLLECTION_ID__';   // e.g. 'VariableCollectionId:1:2'
const COMPONENTS_AREA = '__COMPONENTS_FRAME_ID__'; // an auto-layout frame on the kit page

const coll = await figma.variables.getVariableCollectionByIdAsync(COLLECTION_ID);
if (!coll) throw new Error('Palette collection not found: ' + COLLECTION_ID);
const V = {};
for (const id of coll.variableIds) {
  const v = await figma.variables.getVariableByIdAsync(id);
  V[v.name.split('/')[1]] = v;
}
const families = new Set(['Inter']);
for (const m of coll.modes) { families.add(V['heading'].valuesByMode[m.modeId]); families.add(V['body'].valuesByMode[m.modeId]); }
await Promise.all([...families].flatMap(family => ['Regular', 'Medium', 'Bold'].map(style => figma.loadFontAsync({ family, style }))));

const area = await figma.getNodeByIdAsync(COMPONENTS_AREA);
if (!area || area.type !== 'FRAME') throw new Error('Components area not found: ' + COMPONENTS_AREA);
const paint = v => figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }, 'color', v);
const text = (chars, size, style, colorVar, famVar, name) => {
  const t = figma.createText();
  t.fontName = { family: 'Inter', style };
  t.characters = chars;
  t.fontSize = size;
  t.fills = [paint(colorVar)];
  t.setBoundVariable('fontFamily', famVar);
  t.name = name;
  return t;
};
const bottomBorder = n => { n.strokes = [paint(V['border'])]; n.strokeTopWeight = 0; n.strokeLeftWeight = 0; n.strokeRightWeight = 0; n.strokeBottomWeight = 1; };
const made = {};

function taskRow(done) {
  const c = figma.createComponent();
  c.name = done ? 'Task row / done' : 'Task row / open';
  c.layoutMode = 'HORIZONTAL';
  c.counterAxisAlignItems = 'CENTER';
  c.itemSpacing = 8;
  c.paddingTop = 8; c.paddingBottom = 8;
  c.resize(350, 60);
  c.primaryAxisSizingMode = 'FIXED';
  c.counterAxisSizingMode = 'AUTO';
  c.minHeight = 60;
  c.fills = [];
  bottomBorder(c);
  // The circle is 24; the thing you tap is this 44 by 44 frame around it.
  const check = figma.createAutoLayout('HORIZONTAL', { name: 'Check (tap target)' });
  c.appendChild(check);
  check.resize(44, 44);
  check.primaryAxisSizingMode = 'FIXED'; check.counterAxisSizingMode = 'FIXED';
  check.primaryAxisAlignItems = 'CENTER'; check.counterAxisAlignItems = 'CENTER';
  check.fills = [];
  const ring = figma.createEllipse();
  ring.name = 'Ring';
  ring.resize(24, 24);
  ring.fills = done ? [paint(V['ink-soft'])] : [];
  ring.strokes = [paint(V['ink-soft'])];
  ring.strokeWeight = 2;
  check.appendChild(ring);
  const col = figma.createAutoLayout('VERTICAL', { name: 'Words', itemSpacing: 2 });
  c.appendChild(col);
  col.fills = [];
  col.layoutSizingHorizontal = 'FILL';
  const title = text('Task', 16, 'Medium', done ? V['ink-soft'] : V['ink'], V['body'], 'Title');
  if (done) title.textDecoration = 'STRIKETHROUGH'; // done is said twice: struck through, and the word Done
  const note = text(done ? 'Done' : 'Note', 13, 'Regular', V['ink-soft'], V['body'], 'Note');
  col.appendChild(title); col.appendChild(note);
  title.layoutSizingHorizontal = 'FILL'; note.layoutSizingHorizontal = 'FILL';
  c.description = done ? 'A finished task: struck through and labelled Done, so it does not depend on color.' : 'A task to do. The whole 44 by 44 check area is the tap target.';
  return c;
}
made['Task row / open'] = taskRow(false);
made['Task row / done'] = taskRow(true);

{
  const c = figma.createComponent();
  c.name = 'Hour cell';
  c.layoutMode = 'VERTICAL';
  c.counterAxisAlignItems = 'CENTER';
  c.itemSpacing = 6;
  c.paddingTop = 10; c.paddingBottom = 10; c.paddingLeft = 8; c.paddingRight = 8;
  c.resize(52, 60);
  c.primaryAxisSizingMode = 'AUTO'; c.counterAxisSizingMode = 'FIXED';
  c.cornerRadius = 12;
  c.fills = [paint(V['surface'])];
  // ink-soft on surface is the pairing the palettes command marks LOW in the Brutalist set.
  // The check (measure-screen.js) catches it; the weather tutorial is about fixing it.
  c.appendChild(text('Now', 13, 'Regular', V['ink-soft'], V['body'], 'Time'));
  c.appendChild(text('64°', 17, 'Medium', V['ink'], V['body'], 'Temp'));
  c.description = 'One hour of a forecast: the time and the temperature, as words and numbers.';
  made['Hour cell'] = c;
}
{
  const c = figma.createComponent();
  c.name = 'Day row';
  c.layoutMode = 'HORIZONTAL';
  c.counterAxisAlignItems = 'CENTER';
  c.itemSpacing = 12;
  c.resize(350, 48);
  c.primaryAxisSizingMode = 'FIXED'; c.counterAxisSizingMode = 'FIXED';
  c.fills = [];
  bottomBorder(c);
  const day = text('Monday', 16, 'Medium', V['ink'], V['body'], 'Day');
  const cond = text('Sunny', 15, 'Regular', V['ink-soft'], V['body'], 'Condition');
  const range = text('68° / 52°', 16, 'Medium', V['ink'], V['body'], 'Range');
  c.appendChild(day); c.appendChild(cond); c.appendChild(range);
  day.resize(104, day.height); day.textAutoResize = 'HEIGHT';
  cond.layoutSizingHorizontal = 'FILL';
  c.description = 'One day of a forecast: day, condition in words, high and low.';
  made['Day row'] = c;
}
function bubble(out) {
  const c = figma.createComponent();
  c.name = out ? 'Bubble / out' : 'Bubble / in';
  c.layoutMode = 'VERTICAL';
  c.itemSpacing = 4;
  c.paddingTop = 10; c.paddingBottom = 10; c.paddingLeft = 14; c.paddingRight = 14;
  c.primaryAxisSizingMode = 'AUTO'; c.counterAxisSizingMode = 'AUTO';
  c.cornerRadius = 18;
  c.fills = [paint(out ? V['surface'] : V['ground'])];
  c.strokes = [paint(V['border'])];
  const msg = text('Message', 16, 'Regular', V['ink'], V['body'], 'Text');
  c.appendChild(msg);
  msg.maxWidth = 236;                       // a short message hugs its words; a long one wraps here
  msg.textAutoResize = 'WIDTH_AND_HEIGHT';
  c.appendChild(text(out ? 'You, 9:41' : 'Dana, 9:41', 12, 'Regular', V['ink-soft'], V['body'], 'Meta'));
  c.description = out ? 'A message you sent. It sits on the right and says who and when in words.' : 'A message you received. It sits on the left and says who and when in words.';
  return c;
}
made['Bubble / in'] = bubble(false);
made['Bubble / out'] = bubble(true);
{
  const c = figma.createComponent();
  c.name = 'Text field';
  c.layoutMode = 'HORIZONTAL';
  c.counterAxisAlignItems = 'CENTER';
  c.paddingLeft = 14; c.paddingRight = 14;
  c.resize(350, 44);
  c.primaryAxisSizingMode = 'FIXED'; c.counterAxisSizingMode = 'FIXED';
  c.cornerRadius = 12;
  c.fills = [paint(V['surface'])];
  c.strokes = [paint(V['border'])];
  c.appendChild(text('Placeholder', 16, 'Regular', V['ink-soft'], V['body'], 'Placeholder'));
  c.description = 'A one-line text field, 44 high.';
  made['Text field'] = c;
}
{
  const c = figma.createComponent();
  c.name = 'Button / Quiet';
  c.layoutMode = 'HORIZONTAL';
  c.primaryAxisAlignItems = 'CENTER'; c.counterAxisAlignItems = 'CENTER';
  c.paddingLeft = 8; c.paddingRight = 8;
  c.resize(80, 44);
  c.primaryAxisSizingMode = 'AUTO'; c.counterAxisSizingMode = 'FIXED';
  c.minWidth = 44;
  c.fills = [];
  const l = text('Back', 16, 'Medium', V['ink'], V['body'], 'Label');
  l.textDecoration = 'UNDERLINE';
  c.appendChild(l);
  c.description = 'A secondary action: underlined words, 44 high, no accent.';
  made['Button / Quiet'] = c;
}
const ids = {};
for (const [name, c] of Object.entries(made)) { area.appendChild(c); ids[name] = c.id; }

const pages = {};
for (const name of ['01 Wireframes', '02 Screens']) {
  let p = figma.root.children.find(x => x.name === name);
  if (!p) { p = figma.createPage(); p.name = name; }
  pages[name] = p.id;
}
return {
  modes: coll.modes.map(m => ({ name: m.name, modeId: m.modeId })),
  components: ids,
  sizes: Object.fromEntries(Object.entries(made).map(([n, c]) => [n, [Math.round(c.width), Math.round(c.height)]])),
  pages, createdNodeIds: Object.values(ids).concat(Object.values(pages)), mutatedNodeIds: [COMPONENTS_AREA],
};
