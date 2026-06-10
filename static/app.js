// app.js — Rom-til-rom festgenerator frontend

// ── Global state ───────────────────────────────
let state = null;
let activeTab = 'structured';
let lastVersion = -1;

// Drag state: { type: 'person'|'room', name?, fromRoom?, fromSlot?, room?, slot? }
let drag = null;

// ── API ────────────────────────────────────────

async function apiCall(path, body = null) {
  try {
    const opts = {
      method: body !== null ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json();
    if (data.error) { toast(data.error, 'error'); return null; }
    if (data.state) applyState(data.state);
    return data;
  } catch (e) {
    toast('Nettverksfeil: ' + e.message, 'error');
    return null;
  }
}

async function poll() {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();
    if (data.version !== lastVersion) {
      lastVersion = data.version;
      if (data.state) applyState(data.state);
    }
  } catch (e) { /* server ikke klar ennå */ }
  setTimeout(poll, 1000);
}

// ── State ──────────────────────────────────────

function applyState(s) {
  state = s;
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('btn-add').style.display = '';
  document.getElementById('btn-gen').style.display = '';
  document.getElementById('btn-save').style.display = '';
  flashSaved();
  renderCurrentTab();
}

function flashSaved() {
  const dot = document.getElementById('status-dot');
  const lbl = document.getElementById('status-label');
  dot.className = 'status-dot saved';
  lbl.textContent = 'Lagret ' + new Date().toLocaleTimeString('no');
  setTimeout(() => { dot.className = 'status-dot'; }, 2500);
}

// ── Tabs ───────────────────────────────────────

function showTab(name) {
  activeTab = name;
  ['structured', 'routes'].forEach(t => {
    document.getElementById(t + '-view').style.display = t === name ? '' : 'none';
    document.getElementById('tab-' + t).classList.toggle('active', t === name);
  });
  renderCurrentTab();
}

function renderCurrentTab() {
  if (!state) return;
  if (activeTab === 'structured') renderStructured();
  else renderRoutes();
}

// ── Structured view ────────────────────────────

function renderStructured() {
  const el = document.getElementById('structured-view');
  el.style.display = '';
  el.innerHTML = '';
  const grid = document.createElement('div');
  grid.className = 'structured-grid';

  state.timeslots.forEach(ts => {
    const card = document.createElement('div');
    card.className = 'slot-card';
    card.dataset.slot = ts.slot;

    const total = ts.rooms.reduce((a, r) => a + r.count, 0);
    card.innerHTML = `
      <div class="slot-header">
        <h3>TIDSPUNKT ${ts.slot}</h3>
        <span class="slot-count">${ts.rooms.length} rom · ${total} deltakere</span>
      </div>`;

    const body = document.createElement('div');
    body.className = 'slot-body';

    ts.rooms.forEach(room => {
      body.appendChild(buildRoomBlock(room, ts.slot));
    });

    card.appendChild(body);
    attachSlotCardDropHandlers(card, ts.slot);
    grid.appendChild(card);
  });

  el.appendChild(grid);
}

function buildRoomBlock(room, slotNum) {
  const block = document.createElement('div');
  block.className = 'room-block';
  block.dataset.room = room.room;
  block.dataset.slot = slotNum;
  block.draggable = true;

  block.innerHTML = `
    <div class="room-block-header">
      <span class="room-label">${room.room}</span>
      <span class="host-tag">${room.host ? '⌂ ' + room.host : ''}</span>
      <span class="room-count">${room.count}</span>
    </div>
    <div class="people-list"></div>`;

  const list = block.querySelector('.people-list');

  if (room.host) {
    const chip = document.createElement('span');
    chip.className = 'person-chip host-chip';
    chip.textContent = room.host;
    chip.title = 'Vert – kan ikke flyttes';
    list.appendChild(chip);
  }

  room.guests.forEach(name => {
    list.appendChild(buildPersonChip(name, room.room, slotNum));
  });

  block.addEventListener('dragstart', onRoomDragStart);
  block.addEventListener('dragend', onRoomDragEnd);

  attachRoomBlockDropHandlers(block, room.room, slotNum);

  return block;
}

function buildPersonChip(name, fromRoom, fromSlot) {
  const chip = document.createElement('span');
  chip.className = 'person-chip';
  chip.textContent = name;
  chip.draggable = true;
  chip.dataset.name = name;
  chip.dataset.fromRoom = fromRoom;
  chip.dataset.fromSlot = fromSlot;

  chip.addEventListener('dragstart', e => { onPersonDragStart(e); e.stopPropagation(); });
  chip.addEventListener('dragend', onPersonDragEnd);

  // Lyser opp når en annen person holdes over
  chip.addEventListener('dragover', e => {
    if (drag && drag.type === 'person' && drag.name !== name) {
      e.preventDefault();
      chip.classList.add('drop-target');
    }
  });
  chip.addEventListener('dragleave', () => chip.classList.remove('drop-target'));
  chip.addEventListener('drop', e => {
    e.preventDefault();
    e.stopPropagation();
    chip.classList.remove('drop-target');
    if (!drag || drag.type !== 'person' || drag.name === name) return;
    const toSlot = parseInt(chip.closest('.room-block').dataset.slot);
    if (drag.fromSlot !== toSlot) {
      toast('Kan ikke bytte mellom tidspunkter', 'error');
      return;
    }
    apiCall('/api/swap_people', { slot: drag.fromSlot - 1, name1: drag.name, name2: name });
  });

  return chip;
}

function attachRoomBlockDropHandlers(block, roomName, slotNum) {
  block.addEventListener('dragover', e => {
    if (!drag) return;
    if (drag.type === 'person' && drag.fromSlot === slotNum && drag.fromRoom !== roomName) {
      e.preventDefault();
      block.classList.add('drag-over');
    }
    if (drag.type === 'room' && drag.room !== roomName) {
      e.preventDefault();
      block.classList.add('drag-over');
    }
  });

  block.addEventListener('dragleave', e => {
    if (!e.currentTarget.contains(e.relatedTarget)) {
      block.classList.remove('drag-over');
    }
  });

  block.addEventListener('drop', e => {
    e.preventDefault();
    e.stopPropagation();
    block.classList.remove('drag-over');
    if (!drag) return;

    if (drag.type === 'person') {
      if (drag.fromRoom === roomName) return;
      if (drag.fromSlot !== slotNum) { toast('Kan ikke flytte mellom tidspunkter', 'error'); return; }
      apiCall('/api/move_person', { slot: slotNum - 1, name: drag.name, room: roomName });
    } else if (drag.type === 'room') {
      if (drag.room === roomName) return;
      // Bytt — fungerer både innad i økt og på tvers
      apiCall('/api/swap_rooms', { room1: drag.room, room2: roomName });
    }
  });
}

function attachSlotCardDropHandlers(card, slotNum) {
  // Slot-kortet er drop-sone for å FLYTTE et rom til nytt tidspunkt (tom bakgrunn)
  card.addEventListener('dragover', e => {
    if (drag && drag.type === 'room' && drag.slot !== slotNum) {
      e.preventDefault();
      if (!e.target.closest('.room-block')) card.classList.add('room-drag-over');
    }
  });
  card.addEventListener('dragleave', e => {
    if (!card.contains(e.relatedTarget)) card.classList.remove('room-drag-over');
  });
  card.addEventListener('drop', e => {
    card.classList.remove('room-drag-over');
    if (!drag || drag.type !== 'room') return;
    if (drag.slot === slotNum) return;
    if (e.target.closest('.room-block')) return; // rom-blokk håndterer selv
    e.preventDefault();
    apiCall('/api/move_room', { room: drag.room, target_slot: slotNum - 1 });
  });
}

// ── Routes view ────────────────────────────────

function renderRoutes() {
  const el = document.getElementById('routes-view');
  el.style.display = '';
  el.className = 'routes-view';

  const openRows = state.timeslots.map(ts => {
    const rooms = ts.rooms.map(r => r.room).join(', ');
    return `<div class="open-row">
      <span class="slot-num">Tidspunkt ${ts.slot}:</span>
      <span class="slot-rooms">${rooms}</span>
    </div>`;
  }).join('');

  const routeRows = state.routes.map(p => {
    const cells = p.route.map((r, i) => {
      const isHost = p.host_slot === i;
      return `<span style="color:${isHost ? 'var(--green)' : 'var(--text)'}">${r}</span>`;
    }).join('<span class="rsep"> → </span>');
    const hostNote = p.host_slot !== null
      ? `<span class="rhost">[vert økt ${p.host_slot + 1}]</span>` : '';
    const name = p.name.replace(/'/g, "\\'");
    const room = (state.participants.find(q => q.name === p.name)?.room || '').replace(/'/g, "\\'");
    return `<tr>
      <td class="rname">${p.name}</td>
      <td class="rroute">${cells}${hostNote}</td>
      <td class="raction">
        <button class="btn-icon" title="Rediger" onclick="openEditModal('${name}','${room}')">✏</button>
        <button class="btn-icon danger" title="Fjern" onclick="removeParticipant('${name}')">✕</button>
      </td>
    </tr>`;
  }).join('');

  el.innerHTML = `
    <p class="routes-section-title">ÅPNE ROM PER TIDSPUNKT</p>
    <div class="open-rooms-grid">${openRows}</div>
    <p class="routes-section-title">DELTAKER-RUTER</p>
    <table class="routes-table">${routeRows}</table>`;
}

// ── Drag & drop handlers ───────────────────────

const ghost = document.getElementById('drag-ghost');

function onPersonDragStart(e) {
  drag = {
    type: 'person',
    name: e.target.dataset.name,
    fromRoom: e.target.dataset.fromRoom,
    fromSlot: parseInt(e.target.dataset.fromSlot),
  };
  e.target.classList.add('dragging');
  ghost.textContent = drag.name;
  ghost.style.display = 'block';
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setDragImage(ghost, -10, -10);
}

function onPersonDragEnd(e) {
  e.target.classList.remove('dragging');
  ghost.style.display = 'none';
  drag = null;
  document.querySelectorAll('.drag-over, .drop-target').forEach(el => {
    el.classList.remove('drag-over', 'drop-target');
  });
}

function onRoomDragStart(e) {
  if (e.target.classList.contains('person-chip')) return;
  const block = e.currentTarget;
  drag = {
    type: 'room',
    room: block.dataset.room,
    slot: parseInt(block.dataset.slot),
  };
  ghost.textContent = 'Rom ' + drag.room;
  ghost.style.display = 'block';
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setDragImage(ghost, -10, -10);
  e.stopPropagation();
  setTimeout(() => block.classList.add('room-dragging'), 0);
}

function onRoomDragEnd(e) {
  ghost.style.display = 'none';
  drag = null;
  document.querySelectorAll('.drag-over, .room-drag-over, .room-dragging').forEach(el => {
    el.classList.remove('drag-over', 'room-drag-over', 'room-dragging');
  });
}

// Flytt ghost med musa
document.addEventListener('dragover', e => {
  ghost.style.left = (e.clientX + 12) + 'px';
  ghost.style.top = (e.clientY + 12) + 'px';
});

// ── Modaler ────────────────────────────────────

function openEditModal(name, room) {
  document.getElementById('edit-old-name').value = name;
  document.getElementById('edit-name').value = name;
  document.getElementById('edit-room').value = room;
  document.getElementById('edit-modal').classList.add('open');
  setTimeout(() => document.getElementById('edit-name').focus(), 50);
}

async function editParticipant() {
  const oldName = document.getElementById('edit-old-name').value;
  const name = document.getElementById('edit-name').value.trim();
  const room = document.getElementById('edit-room').value.trim();
  if (!name || !room) return;
  const result = await apiCall('/api/edit', { old_name: oldName, name, room });
  if (result) { closeModal('edit-modal'); toast(`${name} oppdatert`, 'success'); }
}

async function removeParticipant(name) {
  const result = await apiCall('/api/remove', { name });
  if (result) toast(`${name} fjernet`, 'success');
}

function openAddModal() {
  document.getElementById('add-name').value = '';
  document.getElementById('add-room').value = '';
  document.getElementById('add-modal').classList.add('open');
  setTimeout(() => document.getElementById('add-name').focus(), 50);
}

async function addParticipant() {
  const name = document.getElementById('add-name').value.trim();
  const room = document.getElementById('add-room').value.trim();
  if (!name || !room) return;
  const result = await apiCall('/api/add', { name, room });
  if (result) { closeModal('add-modal'); toast(`${name} lagt til`, 'success'); }
}

function openLoadModal() {
  document.getElementById('load-modal').classList.add('open');
  setTimeout(() => document.getElementById('load-textarea').focus(), 50);
}
function openJsonModal() {
  document.getElementById('json-modal').classList.add('open');
  setTimeout(() => document.getElementById('json-textarea').focus(), 50);
}
function closeModal(id) {
  document.getElementById(id).classList.remove('open');
}

function readFileIntoTextarea(inputId, textareaId, nameId) {
  const input = document.getElementById(inputId);
  const file = input.files[0];
  if (!file) return;
  document.getElementById(nameId).textContent = file.name;
  const reader = new FileReader();
  reader.onload = e => { document.getElementById(textareaId).value = e.target.result; };
  reader.readAsText(file, 'UTF-8');
}

async function loadParticipants() {
  const text = document.getElementById('load-textarea').value.trim();
  if (!text) return;
  const result = await apiCall('/api/load', { text });
  if (result) { closeModal('load-modal'); toast('Timeplan generert!', 'success'); }
}

async function loadJson() {
  const text = document.getElementById('json-textarea').value.trim();
  if (!text) return;
  const result = await apiCall('/api/load_json', { text });
  if (result) { closeModal('json-modal'); toast('Timeplan lastet!', 'success'); }
}

async function saveJSON() {
  if (!state) return;
  const json = JSON.stringify(state.participants, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'timeplan.json';
  a.click();
  toast('JSON lastet ned', 'success');
}

// Lukk modal ved klikk utenfor
document.querySelectorAll('.modal-overlay').forEach(o => {
  o.addEventListener('click', e => { if (e.target === o) o.classList.remove('open'); });
});

// ── Toast ──────────────────────────────────────

let toastTimer;
function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (type ? ' ' + type : '');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = 'toast'; }, 3000);
}

// ── Start ──────────────────────────────────────
poll();
