// EXAMPLE, to adapt: draws the first screen of the three tutorial apps (to-do, weather, chat) from
// kit component instances. As run on 2026-11-10; the result is docs/tutorials/*.png.
//
// It was run twice with different constants and no other change:
//   wireframes: PAGE '01 Wireframes', STYLE 'wire',   every PLAN entry in mode 'Wireframe'
//   screens:    PAGE '02 Screens',    STYLE 'styled', to-do in 'Bear Brown', weather in 'Brutalist',
//               chat in 'Humanitarians AI', each with a second state
// A wireframe and a styled screen are the same drawing in a different mode of the Palette variables.
//
// IDs come from the receipts of palette-variables.js and kit-components.js (and sample-screen.js
// for 'Button / Primary'). Components live on the kit page; getNodeByIdAsync reaches them from here.
const PAGE_ID = '__PAGE_ID__';
const STYLE = 'styled'; // or 'wire': only changes the frame names
const PLAN = [
  { app: 'todo', state: 'default', mode: 'Bear Brown' }, { app: 'todo', state: 'empty', mode: 'Bear Brown' },
  { app: 'weather', state: 'default', mode: 'Brutalist' }, { app: 'weather', state: 'error', mode: 'Brutalist' },
  { app: 'chat', state: 'default', mode: 'Humanitarians AI' }, { app: 'chat', state: 'empty', mode: 'Humanitarians AI' },
];
const COLLECTION_ID = '__COLLECTION_ID__';
const C_IDS = { button: '__ID__', quiet: '__ID__', taskOpen: '__ID__', taskDone: '__ID__', hour: '__ID__', day: '__ID__', bubbleIn: '__ID__', bubbleOut: '__ID__', field: '__ID__' };
const TITLES = { todo: 'S-01 Today', weather: 'S-01 Now', chat: 'S-02 Conversation' };
const DEVICE = { width: 390, height: 844, safe_top: 47, safe_bottom: 34 }; // ./fad devices

const page = await figma.getNodeByIdAsync(PAGE_ID);
if (!page || page.type !== 'PAGE') throw new Error('page not found: ' + PAGE_ID);
await figma.setCurrentPageAsync(page);

const coll = await figma.variables.getVariableCollectionByIdAsync(COLLECTION_ID);
if (!coll) throw new Error('Palette collection not found: ' + COLLECTION_ID);
const V = {};
for (const id of coll.variableIds) { const v = await figma.variables.getVariableByIdAsync(id); V[v.name.split('/')[1]] = v; }
const families = new Set(['Inter']);
for (const m of coll.modes) { families.add(V['heading'].valuesByMode[m.modeId]); families.add(V['body'].valuesByMode[m.modeId]); }
await Promise.all([...families].flatMap(family => ['Regular', 'Medium', 'Bold'].map(style => figma.loadFontAsync({ family, style }))));
const C = {};
for (const [k, id] of Object.entries(C_IDS)) {
  C[k] = await figma.getNodeByIdAsync(id);
  if (!C[k] || C[k].type !== 'COMPONENT') throw new Error('component not found: ' + k + ' ' + id);
}

const paint = v => figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }, 'color', v);
const text = (chars, size, style, colorVar, famVar, name) => {
  const t = figma.createText();
  t.fontName = { family: 'Inter', style };
  t.characters = chars;
  t.fontSize = size;
  t.fills = [paint(colorVar)];
  t.setBoundVariable('fontFamily', famVar);
  t.name = name || chars.slice(0, 24);
  return t;
};
const put = (parent, node, fill) => { parent.appendChild(node); if (fill) node.layoutSizingHorizontal = 'FILL'; return node; };
// An instance with its words changed. A missing text layer is an error, never a silent skip.
const inst = (parent, comp, texts, fill) => {
  const i = comp.createInstance();
  parent.appendChild(i);
  if (fill) i.layoutSizingHorizontal = 'FILL';
  for (const [name, chars] of Object.entries(texts || {})) {
    const t = i.findOne(n => n.type === 'TEXT' && n.name === name);
    if (!t) throw new Error('no text named ' + name + ' in ' + comp.name);
    t.characters = chars;
  }
  return i;
};
const stack = (parent, name, dir, gap) => { const f = figma.createAutoLayout(dir, { name, itemSpacing: gap || 0 }); parent.appendChild(f); f.fills = []; f.layoutSizingHorizontal = 'FILL'; return f; };
const spacer = parent => { const s = figma.createFrame(); s.name = 'Spacer'; s.fills = []; s.resize(10, 10); parent.appendChild(s); s.layoutSizingHorizontal = 'FILL'; s.layoutGrow = 1; return s; };
// What a screen says when it has nothing to show: a title and one plain sentence.
const message = (parent, title, body) => {
  const b = stack(parent, 'Message', 'VERTICAL', 8);
  b.counterAxisAlignItems = 'CENTER';
  b.paddingTop = 96; b.paddingBottom = 24;
  const t = put(b, text(title, 22, 'Bold', V['ink'], V['heading'], 'Message title'));
  t.textAlignHorizontal = 'CENTER';
  const p = put(b, text(body, 16, 'Regular', V['ink-soft'], V['body'], 'Message body'));
  p.resize(300, p.height); p.textAutoResize = 'HEIGHT'; p.textAlignHorizontal = 'CENTER';
  return b;
};

function todo(ph, state) {
  put(ph, text('Today', 34, 'Bold', V['ink'], V['heading'], 'Screen title'));
  put(ph, text(state === 'empty' ? 'Tuesday. Nothing yet.' : 'Tuesday. 4 tasks, 1 done.', 15, 'Regular', V['ink-soft'], V['body'], 'Summary'));
  if (state === 'empty') {
    message(ph, 'Nothing for today', 'Add the first thing you want to get done. It stays on this phone.');
  } else {
    const list = stack(ph, 'Task list', 'VERTICAL', 0);
    inst(list, C.taskOpen, { Title: 'Call the plumber', Note: 'Before noon' }, true);
    inst(list, C.taskOpen, { Title: 'Renew library books', Note: 'Due Thursday' }, true);
    inst(list, C.taskDone, { Title: 'Water the tomatoes', Note: 'Done' }, true);
    inst(list, C.taskOpen, { Title: 'Send the rent', Note: 'Due on the 1st' }, true);
  }
  spacer(ph);
  inst(ph, C.button, { Label: 'Add a task' }, true);
}
function weather(ph, state) {
  const top = stack(ph, 'City bar', 'HORIZONTAL', 12);
  top.primaryAxisAlignItems = 'SPACE_BETWEEN'; top.counterAxisAlignItems = 'CENTER';
  put(top, text('Boston', 28, 'Bold', V['ink'], V['heading'], 'City'));
  inst(top, C.quiet, { Label: 'Cities' });
  if (state === 'error') {
    message(ph, "Can't get the weather", 'Check your connection, then try again. The last forecast is from 3 hours ago.');
    inst(ph, C.button, { Label: 'Try again' }, true);
    spacer(ph);
    return;
  }
  put(ph, text('Updated 2 minutes ago', 13, 'Regular', V['ink-soft'], V['body'], 'Updated'));
  const now = stack(ph, 'Now', 'VERTICAL', 4);
  put(now, text('64°', 72, 'Bold', V['ink'], V['heading'], 'Temperature'));
  put(now, text('Partly cloudy', 20, 'Medium', V['ink'], V['body'], 'Condition'));
  put(now, text('Feels like 61°. High 68°, low 52°.', 15, 'Regular', V['ink-soft'], V['body'], 'Detail'));
  const hours = stack(ph, 'Hours', 'HORIZONTAL', 6);
  for (const [t, d] of [['Now', '64°'], ['1 PM', '66°'], ['2 PM', '67°'], ['3 PM', '68°'], ['4 PM', '66°'], ['5 PM', '63°']]) inst(hours, C.hour, { Time: t, Temp: d }, true);
  put(ph, text('Next days', 13, 'Medium', V['ink-soft'], V['body'], 'Section label'));
  const days = stack(ph, 'Days', 'VERTICAL', 0);
  for (const [d, c, r] of [['Wednesday', 'Sunny', '70° / 54°'], ['Thursday', 'Rain', '61° / 50°'], ['Friday', 'Cloudy', '63° / 51°'], ['Saturday', 'Sunny', '72° / 55°']]) inst(days, C.day, { Day: d, Condition: c, Range: r }, true);
  spacer(ph);
  inst(ph, C.button, { Label: 'Add a city' }, true);
}
function chat(ph, state) {
  const top = stack(ph, 'Top bar', 'HORIZONTAL', 8);
  top.counterAxisAlignItems = 'CENTER';
  inst(top, C.quiet, { Label: 'Chats' });
  put(top, text('Dana Reyes', 20, 'Bold', V['ink'], V['heading'], 'Person'));
  if (state === 'empty') {
    message(ph, 'No messages yet', 'Say hello to Dana.');
  } else {
    const msgs = stack(ph, 'Messages', 'VERTICAL', 10);
    for (const [out, words, meta] of [[false, 'Are we still on for Saturday?', 'Dana, 9:41'], [true, 'Yes. Trailhead at 8?', 'You, 9:42'], [false, "Perfect. I'll bring the stove and coffee for everyone.", 'Dana, 9:42'], [true, 'See you there', 'You, 9:43']]) {
      const line = stack(msgs, out ? 'Line / out' : 'Line / in', 'HORIZONTAL', 0);
      line.primaryAxisAlignItems = out ? 'MAX' : 'MIN'; // yours on the right, theirs on the left
      inst(line, out ? C.bubbleOut : C.bubbleIn, { Text: words, Meta: meta });
    }
  }
  spacer(ph);
  const comp = stack(ph, 'Composer', 'HORIZONTAL', 8);
  comp.counterAxisAlignItems = 'CENTER';
  inst(comp, C.field, { Placeholder: 'Message' }, true);
  const send = inst(comp, C.button, { Label: 'Send' });
  send.resize(84, 48);
}
const BUILD = { todo, weather, chat };

const wrap = figma.createAutoLayout('HORIZONTAL', { name: 'Tutorial screens / ' + STYLE, itemSpacing: 60 });
page.appendChild(wrap);
wrap.x = 100; wrap.y = 100;
wrap.fills = [];
wrap.counterAxisAlignItems = 'MIN';
const frames = [];
for (const p of PLAN) {
  const modeId = (coll.modes.find(m => m.name === p.mode) || {}).modeId;
  if (!modeId) throw new Error('mode not found: ' + p.mode + '. Modes: ' + coll.modes.map(m => m.name).join(', '));
  const col = figma.createAutoLayout('VERTICAL', { name: 'Column / ' + p.app + ' / ' + p.state, itemSpacing: 16 });
  wrap.appendChild(col);
  col.fills = [];
  col.setExplicitVariableModeForCollection(coll, modeId);
  col.appendChild(text(TITLES[p.app] + ', ' + p.state + ' (' + p.mode + ')', 14, 'Medium', V['ink-soft'], V['body'], 'Caption'));
  const ph = figma.createAutoLayout('VERTICAL', { name: TITLES[p.app] + ' / iphone / ' + STYLE + ' / ' + p.state, itemSpacing: 16 });
  col.appendChild(ph);
  ph.resize(DEVICE.width, DEVICE.height);
  ph.primaryAxisSizingMode = 'FIXED'; ph.counterAxisSizingMode = 'FIXED';
  ph.paddingTop = DEVICE.safe_top + 12; ph.paddingBottom = DEVICE.safe_bottom + 12; ph.paddingLeft = 20; ph.paddingRight = 20;
  ph.cornerRadius = 40;
  ph.clipsContent = true;
  ph.fills = [paint(V['ground'])];
  ph.strokes = [paint(V['border'])];
  BUILD[p.app](ph, p.state);
  const lowest = Math.max(...ph.children.map(c => c.y + c.height));
  frames.push({ app: p.app, state: p.state, mode: p.mode, id: ph.id, name: ph.name, children: ph.children.length, lowest: Math.round(lowest), fits: lowest <= DEVICE.height - DEVICE.safe_bottom - 12 + 0.5 });
}
return { pageId: page.id, wrapperId: wrap.id, frames, createdNodeIds: [wrap.id].concat(frames.map(f => f.id)), mutatedNodeIds: [] };
