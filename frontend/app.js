/**
 * BambuRFID — Main Application Logic
 */

// ──────────────────────────────────────────────
// State
// ──────────────────────────────────────────────
let currentTab = 'dashboard';
let spools = [];
let presets = [];
let lastReadData = null;    // Last tag read result
let lastEncodeData = null;  // Last encoded tag data
let cloneSourceData = null; // Source tag for cloning
let libraryMaterials = {};  // Tag library material index
let librarySelectedDump = null; // Currently selected library dump

// ──────────────────────────────────────────────
// API Helpers
// ──────────────────────────────────────────────
async function api(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'API error');
    }
    return res.json();
}

// ──────────────────────────────────────────────
// Tab Navigation
// ──────────────────────────────────────────────
function switchTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    const tabEl = document.getElementById(`tab-${tabId}`);
    if (tabEl) tabEl.classList.remove('hidden');
    const btnEl = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (btnEl) btnEl.classList.add('active');

    // Load data when switching tabs
    if (tabId === 'spools') loadSpools();
    if (tabId === 'presets') loadPresets();
    if (tabId === 'dashboard') loadDashboard();
    if (tabId === 'mqtt-panel') loadMqttSpools();
    if (tabId === 'tag-library') loadLibrary();
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ──────────────────────────────────────────────
// Toast Notifications
// ──────────────────────────────────────────────
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

// ──────────────────────────────────────────────
// Status Polling
// ──────────────────────────────────────────────
async function pollStatus() {
    try {
        const bridge = await api('GET', '/api/bridge/status');
        updateBridgeStatus(bridge.connected);
    } catch (e) { /* ignore */ }

    try {
        const mqtt = await api('GET', '/api/mqtt/status');
        updateMqttStatus(mqtt.connected);
    } catch (e) { /* ignore */ }
}

function updateBridgeStatus(connected) {
    const dot = document.getElementById('bridge-dot');
    const text = document.getElementById('bridge-text');
    const dash = document.getElementById('dash-bridge');
    dot.className = `w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`;
    text.textContent = connected ? 'Phone connected' : 'Phone disconnected';
    if (dash) dash.textContent = connected ? 'Connected' : 'Disconnected';
}

function updateMqttStatus(connected) {
    const dot = document.getElementById('mqtt-dot');
    const text = document.getElementById('mqtt-text');
    const dash = document.getElementById('dash-printer');
    dot.className = `w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`;
    text.textContent = connected ? 'Printer online' : 'Printer offline';
    if (dash) dash.textContent = connected ? 'Online' : 'Offline';
}

// ──────────────────────────────────────────────
// Dashboard
// ──────────────────────────────────────────────
async function loadDashboard() {
    try {
        const data = await api('GET', '/api/spools/');
        spools = data.spools || [];
        document.getElementById('dash-spool-count').textContent = spools.length;

        const recentEl = document.getElementById('recent-spools');
        if (spools.length === 0) {
            recentEl.innerHTML = '<p class="text-gray-400">No spools yet. Read a tag or add one manually.</p>';
        } else {
            recentEl.innerHTML = spools.slice(0, 5).map(s => spoolCardHTML(s)).join('');
        }
    } catch (e) {
        console.error('Dashboard load error:', e);
    }
}

// ──────────────────────────────────────────────
// Read Tag
// ──────────────────────────────────────────────
async function readTagViaBridge() {
    const btn = document.getElementById('btn-read-nfc');
    btn.innerHTML = '<span class="spinner"></span> Waiting for tag...';
    btn.disabled = true;
    try {
        const result = await api('POST', '/api/tags/read', { timeout: 30 });
        lastReadData = result;
        displayTagData('read-result', result.filament, result.uid);
        document.getElementById('read-actions').classList.remove('hidden');
        showToast('Tag read successfully!', 'success');
    } catch (e) {
        showToast(`Read failed: ${e.message}`, 'error');
    } finally {
        btn.innerHTML = 'Read Tag via Phone';
        btn.disabled = false;
    }
}

async function decodeHexDump() {
    const hex = document.getElementById('hex-dump-input').value.trim();
    if (!hex) return showToast('Paste a hex dump first', 'error');
    try {
        const result = await api('POST', '/api/tags/decode/hex', { hex_data: hex });
        lastReadData = { filament: result, blocks: null };
        displayTagData('read-result', result);
        document.getElementById('read-actions').classList.remove('hidden');
        showToast('Tag decoded!', 'success');
    } catch (e) {
        showToast(`Decode failed: ${e.message}`, 'error');
    }
}

async function decodeProxmarkDump() {
    const dump = document.getElementById('hex-dump-input').value.trim();
    if (!dump) return showToast('Paste a Proxmark3 dump first', 'error');
    try {
        const result = await api('POST', '/api/tags/decode/proxmark', { dump_text: dump });
        lastReadData = { filament: result, blocks: null };
        displayTagData('read-result', result);
        document.getElementById('read-actions').classList.remove('hidden');
        showToast('Proxmark3 dump decoded!', 'success');
    } catch (e) {
        showToast(`Decode failed: ${e.message}`, 'error');
    }
}

async function decodeFileUpload() {
    const input = document.getElementById('dump-file-input');
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/tags/decode/file', { method: 'POST', body: formData });
        if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
        const result = await res.json();
        lastReadData = { filament: result, blocks: null };
        displayTagData('read-result', result);
        document.getElementById('read-actions').classList.remove('hidden');
        showToast('File decoded!', 'success');
    } catch (e) {
        showToast(`File decode failed: ${e.message}`, 'error');
    }
}

function displayTagData(containerId, data, uid = '') {
    const el = document.getElementById(containerId);
    const fields = [
        ['UID', uid || data.uid || '—'],
        ['Material', data.detailed_filament_type || data.filament_type || '—'],
        ['Material ID', data.material_id || '—'],
        ['Color', `<span class="inline-block w-4 h-4 rounded" style="background:${data.color_hex}"></span> ${data.color_hex}`],
        ['Spool Weight', `${data.spool_weight_g}g`],
        ['Diameter', `${data.filament_diameter_mm}mm`],
        ['Nozzle Temp', `${data.min_hotend_temp_c} - ${data.max_hotend_temp_c}°C`],
        ['Bed Temp', `${data.bed_temp_c}°C`],
        ['Length', `${data.filament_length_m}m`],
        ['Production', data.production_datetime || '—'],
        ['Tray UID', data.tray_uid || '—'],
        ['RSA Signature', data.has_rsa_signature ? 'Present' : 'None'],
    ];
    el.innerHTML = fields.map(([label, value]) =>
        `<div class="tag-field"><span class="tag-label">${label}</span><span class="tag-value">${value}</span></div>`
    ).join('');
}

async function saveReadToInventory() {
    if (!lastReadData || !lastReadData.filament) return;
    const f = lastReadData.filament;
    try {
        await api('POST', '/api/spools/', {
            name: `${f.detailed_filament_type || f.filament_type || 'Unknown'} ${f.color_hex}`,
            material: f.detailed_filament_type || f.filament_type || 'Unknown',
            material_id: f.material_id || '',
            color_hex: f.color_hex || '#000000',
            weight_g: f.spool_weight_g || 1000,
            remaining_g: f.spool_weight_g || 1000,
            filament_length_m: f.filament_length_m || 0,
            nozzle_temp_min: f.min_hotend_temp_c || 190,
            nozzle_temp_max: f.max_hotend_temp_c || 230,
            bed_temp: f.bed_temp_c || 60,
            tag_uid: lastReadData.uid || '',
        });
        showToast('Saved to inventory!', 'success');
    } catch (e) {
        showToast(`Save failed: ${e.message}`, 'error');
    }
}

function useForClone() {
    if (!lastReadData) return;
    cloneSourceData = lastReadData;
    switchTab('clone-tag');
    displayTagData('clone-source', lastReadData.filament, lastReadData.uid);
    document.getElementById('btn-clone-write').disabled = false;
    showToast('Source tag loaded for cloning', 'info');
}

// ──────────────────────────────────────────────
// Write Tag
// ──────────────────────────────────────────────
async function encodeTag() {
    const data = {
        material_id: document.getElementById('write-material-id').value,
        filament_type: document.getElementById('write-type').value,
        detailed_filament_type: document.getElementById('write-detailed-type').value,
        color_hex: document.getElementById('write-color').value,
        spool_weight_g: parseInt(document.getElementById('write-weight').value) || 1000,
        filament_diameter_mm: parseFloat(document.getElementById('write-diameter').value) || 1.75,
        min_hotend_temp_c: parseInt(document.getElementById('write-temp-min').value) || 190,
        max_hotend_temp_c: parseInt(document.getElementById('write-temp-max').value) || 230,
        bed_temp_c: parseInt(document.getElementById('write-bed-temp').value) || 60,
        filament_length_m: parseInt(document.getElementById('write-length').value) || 330,
        drying_temp_c: parseInt(document.getElementById('write-dry-temp').value) || 55,
        drying_time_h: parseInt(document.getElementById('write-dry-time').value) || 8,
    };

    try {
        const result = await api('POST', '/api/tags/encode', data);
        lastEncodeData = result;
        displayTagData('write-result', result.filament);
        document.getElementById('write-actions').classList.remove('hidden');
        showToast('Tag data generated!', 'success');
    } catch (e) {
        showToast(`Encode failed: ${e.message}`, 'error');
    }
}

async function writeTagViaBridge() {
    if (!lastEncodeData || !lastEncodeData.blocks) return;
    try {
        await api('POST', '/api/tags/write', { blocks: lastEncodeData.blocks });
        showToast('Tag written successfully!', 'success');
    } catch (e) {
        showToast(`Write failed: ${e.message}`, 'error');
    }
}

function downloadTagDump() {
    if (!lastEncodeData || !lastEncodeData.hex) return;
    const bytes = new Uint8Array(lastEncodeData.hex.match(/.{2}/g).map(b => parseInt(b, 16)));
    const blob = new Blob([bytes], { type: 'application/octet-stream' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tag_dump.bin';
    a.click();
    URL.revokeObjectURL(url);
}

async function applyPreset() {
    const select = document.getElementById('write-preset');
    const presetId = select.value;
    if (!presetId) return;

    try {
        const preset = await api('GET', `/api/spools/presets/${presetId}`);
        document.getElementById('write-material-id').value = preset.material_id || '';
        document.getElementById('write-type').value = preset.material_type || '';
        document.getElementById('write-detailed-type').value = preset.name || '';
        document.getElementById('write-temp-min').value = preset.nozzle_temp_min || 190;
        document.getElementById('write-temp-max').value = preset.nozzle_temp_max || 230;
        document.getElementById('write-bed-temp').value = preset.bed_temp || 60;
        document.getElementById('write-dry-temp').value = preset.drying_temp || 55;
        document.getElementById('write-dry-time').value = preset.drying_time_h || 8;
    } catch (e) {
        showToast(`Failed to load preset: ${e.message}`, 'error');
    }
}

// ──────────────────────────────────────────────
// Clone Tag
// ──────────────────────────────────────────────
async function readSourceTag() {
    try {
        const result = await api('POST', '/api/tags/read-and-save', { timeout: 30 });
        cloneSourceData = result;
        displayTagData('clone-source', result.filament, result.uid);
        document.getElementById('btn-clone-write').disabled = false;
        showToast('Source tag read! Now tap a blank tag to write.', 'success');
    } catch (e) {
        showToast(`Read failed: ${e.message}`, 'error');
    }
}

async function writeCloneTag() {
    if (!cloneSourceData || !cloneSourceData.blocks) {
        showToast('No source tag data. Read a source tag first.', 'error');
        return;
    }
    try {
        await api('POST', '/api/tags/write', {
            blocks: cloneSourceData.blocks,
            target_uid: cloneSourceData.uid,
        });
        showToast('Tag cloned successfully!', 'success');
    } catch (e) {
        showToast(`Clone write failed: ${e.message}`, 'error');
    }
}

// ──────────────────────────────────────────────
// Spool Inventory
// ──────────────────────────────────────────────
async function loadSpools() {
    try {
        const data = await api('GET', '/api/spools/');
        spools = data.spools || [];
        renderSpools(spools);
    } catch (e) {
        showToast(`Failed to load spools: ${e.message}`, 'error');
    }
}

function renderSpools(list) {
    const el = document.getElementById('spool-list');
    if (list.length === 0) {
        el.innerHTML = '<p class="text-gray-400">No spools in inventory.</p>';
        return;
    }
    el.innerHTML = list.map(s => spoolCardHTML(s)).join('');
}

function spoolCardHTML(s) {
    return `
        <div class="spool-card">
            <div class="spool-color" style="background-color: ${s.color_hex}"></div>
            <div class="flex-1">
                <div class="font-semibold">${escapeHTML(s.name)}</div>
                <div class="text-sm text-gray-400">
                    ${escapeHTML(s.material)} | ${s.remaining_g}g remaining | ${s.nozzle_temp_min}-${s.nozzle_temp_max}°C
                </div>
            </div>
            <div class="flex space-x-2">
                <button onclick="pushSpoolToSlot(${s.id})" class="btn-secondary text-xs" title="Push to printer">MQTT</button>
                <button onclick="deleteSpool(${s.id})" class="btn-secondary text-xs text-red-400" title="Delete">Del</button>
            </div>
        </div>`;
}

function filterSpools() {
    const query = document.getElementById('spool-search').value.toLowerCase();
    const filtered = spools.filter(s =>
        s.name.toLowerCase().includes(query) ||
        s.material.toLowerCase().includes(query) ||
        s.brand.toLowerCase().includes(query)
    );
    renderSpools(filtered);
}

function showAddSpoolModal() {
    document.getElementById('spool-modal').classList.remove('hidden');
}

function closeSpoolModal() {
    document.getElementById('spool-modal').classList.add('hidden');
}

async function saveSpool() {
    const data = {
        name: document.getElementById('modal-name').value || 'Unnamed Spool',
        brand: document.getElementById('modal-brand').value || '',
        material: document.getElementById('modal-material').value || 'PLA',
        color_hex: document.getElementById('modal-color').value || '#FFFFFF',
        weight_g: parseInt(document.getElementById('modal-weight').value) || 1000,
        remaining_g: parseInt(document.getElementById('modal-remaining').value) || 1000,
        nozzle_temp_min: parseInt(document.getElementById('modal-temp-min').value) || 190,
        nozzle_temp_max: parseInt(document.getElementById('modal-temp-max').value) || 230,
        notes: document.getElementById('modal-notes').value || '',
    };
    try {
        await api('POST', '/api/spools/', data);
        closeSpoolModal();
        loadSpools();
        showToast('Spool added!', 'success');
    } catch (e) {
        showToast(`Save failed: ${e.message}`, 'error');
    }
}

async function deleteSpool(id) {
    if (!confirm('Delete this spool?')) return;
    try {
        await api('DELETE', `/api/spools/${id}`);
        loadSpools();
        showToast('Spool deleted', 'info');
    } catch (e) {
        showToast(`Delete failed: ${e.message}`, 'error');
    }
}

// ──────────────────────────────────────────────
// Material Presets
// ──────────────────────────────────────────────
async function loadPresets() {
    try {
        const data = await api('GET', '/api/spools/presets/all');
        presets = data.presets || [];
        renderPresets(presets);
        populatePresetSelect();
    } catch (e) {
        showToast(`Failed to load presets: ${e.message}`, 'error');
    }
}

function renderPresets(list) {
    const el = document.getElementById('preset-list');
    if (list.length === 0) {
        el.innerHTML = '<p class="text-gray-400">No presets available.</p>';
        return;
    }
    el.innerHTML = list.map(p => `
        <div class="preset-card">
            <div class="font-semibold text-green-400">${escapeHTML(p.name)}</div>
            <div class="text-sm text-gray-400 mt-1">Type: ${escapeHTML(p.material_type)}</div>
            <div class="text-sm text-gray-400">ID: ${escapeHTML(p.material_id)}</div>
            <div class="text-sm text-gray-400">Nozzle: ${p.nozzle_temp_min}-${p.nozzle_temp_max}°C</div>
            <div class="text-sm text-gray-400">Bed: ${p.bed_temp}°C</div>
            <div class="text-sm text-gray-400">Drying: ${p.drying_temp}°C / ${p.drying_time_h}h</div>
        </div>
    `).join('');
}

function populatePresetSelect() {
    const select = document.getElementById('write-preset');
    select.innerHTML = '<option value="">— Select preset —</option>';
    presets.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        select.appendChild(opt);
    });
}

// ──────────────────────────────────────────────
// MQTT / OpenSpool
// ──────────────────────────────────────────────
async function connectMQTT() {
    const ip = document.getElementById('mqtt-ip').value.trim();
    const serial = document.getElementById('mqtt-serial').value.trim();
    const access = document.getElementById('mqtt-access').value.trim();
    if (!ip || !serial || !access) {
        return showToast('Fill in all printer fields', 'error');
    }
    try {
        await api('POST', '/api/mqtt/connect', { ip, serial, access_code: access });
        showToast('Connected to printer!', 'success');
        updateMqttStatus(true);
    } catch (e) {
        showToast(`Connection failed: ${e.message}`, 'error');
    }
}

async function disconnectMQTT() {
    try {
        await api('POST', '/api/mqtt/disconnect');
        showToast('Disconnected from printer', 'info');
        updateMqttStatus(false);
    } catch (e) {
        showToast(`Disconnect failed: ${e.message}`, 'error');
    }
}

async function loadMqttSpools() {
    try {
        const data = await api('GET', '/api/spools/');
        const select = document.getElementById('mqtt-spool-select');
        select.innerHTML = '<option value="">— Select a spool —</option>';
        (data.spools || []).forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `${s.name} (${s.material})`;
            select.appendChild(opt);
        });
    } catch (e) { /* ignore */ }
}

async function pushToSlot() {
    const slot = parseInt(document.getElementById('mqtt-slot').value);
    const spoolId = document.getElementById('mqtt-spool-select').value;
    if (!spoolId) return showToast('Select a spool first', 'error');

    try {
        await api('POST', '/api/mqtt/send-spool', { slot, spool_id: parseInt(spoolId) });
        showToast(`Pushed to slot ${slot + 1}!`, 'success');
    } catch (e) {
        showToast(`Push failed: ${e.message}`, 'error');
    }
}

async function pushSpoolToSlot(spoolId) {
    const slot = prompt('Enter AMS slot number (1-4):');
    if (!slot) return;
    const slotNum = parseInt(slot) - 1;
    if (isNaN(slotNum) || slotNum < 0 || slotNum > 15) {
        return showToast('Invalid slot number', 'error');
    }
    try {
        await api('POST', '/api/mqtt/send-spool', { slot: slotNum, spool_id: spoolId });
        showToast(`Pushed to slot ${slot}!`, 'success');
    } catch (e) {
        showToast(`Push failed: ${e.message}`, 'error');
    }
}

// ──────────────────────────────────────────────
// Tools — Key Derivation
// ──────────────────────────────────────────────
async function deriveKeys() {
    const uid = document.getElementById('kdf-uid').value.trim();
    if (!uid) return showToast('Enter a UID', 'error');
    try {
        const result = await api('POST', '/api/tags/derive-keys', { uid });
        const keysEl = document.getElementById('kdf-keys');
        keysEl.textContent = result.keys.map((k, i) => `Sector ${i.toString().padStart(2, ' ')}: ${k}`).join('\n');
        document.getElementById('kdf-result').classList.remove('hidden');
    } catch (e) {
        showToast(`Key derivation failed: ${e.message}`, 'error');
    }
}

// ──────────────────────────────────────────────
// Utility
// ──────────────────────────────────────────────
function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
}

// ──────────────────────────────────────────────
// Tag Library (Community Dumps)
// ──────────────────────────────────────────────
async function loadLibrary() {
    try {
        const data = await api('GET', '/api/library/materials');
        libraryMaterials = data.materials || {};

        const matSelect = document.getElementById('lib-material');
        matSelect.innerHTML = '<option value="">All Materials</option>';
        for (const mat of Object.keys(libraryMaterials)) {
            const opt = document.createElement('option');
            opt.value = mat;
            opt.textContent = mat;
            matSelect.appendChild(opt);
        }

        const status = await api('GET', '/api/library/status');
        document.getElementById('lib-count').textContent = `${status.total} tag dumps available`;
    } catch (e) {
        showToast(`Failed to load library: ${e.message}`, 'error');
    }
}

async function refreshLibrary() {
    try {
        showToast('Refreshing index from GitHub...', 'info');
        const data = await api('POST', '/api/library/refresh');
        libraryMaterials = data.materials || {};
        loadLibrary();
        showToast(`Index refreshed: ${Object.keys(data.materials).length} material categories`, 'success');
    } catch (e) {
        showToast(`Refresh failed: ${e.message}`, 'error');
    }
}

function onLibMaterialChange() {
    const mat = document.getElementById('lib-material').value;
    const subtypeSelect = document.getElementById('lib-subtype');
    subtypeSelect.innerHTML = '<option value="">All Types</option>';

    if (mat && libraryMaterials[mat]) {
        for (const st of libraryMaterials[mat]) {
            const opt = document.createElement('option');
            opt.value = st;
            opt.textContent = st;
            subtypeSelect.appendChild(opt);
        }
    }

    // Clear color filter
    document.getElementById('lib-color').innerHTML = '<option value="">All Colors</option>';
    searchLibrary();
}

async function onLibSubtypeChange() {
    const mat = document.getElementById('lib-material').value;
    const st = document.getElementById('lib-subtype').value;
    const colorSelect = document.getElementById('lib-color');
    colorSelect.innerHTML = '<option value="">All Colors</option>';

    if (mat && st) {
        try {
            const data = await api('GET', `/api/library/colors?material=${encodeURIComponent(mat)}&subtype=${encodeURIComponent(st)}`);
            for (const color of (data.colors || [])) {
                const opt = document.createElement('option');
                opt.value = color;
                opt.textContent = `${color} (${data.count})`;
                colorSelect.appendChild(opt);
            }
        } catch (e) { /* ignore */ }
    }

    searchLibrary();
}

async function searchLibrary() {
    const mat = document.getElementById('lib-material').value;
    const st = document.getElementById('lib-subtype').value;
    const color = document.getElementById('lib-color').value;
    const q = document.getElementById('lib-search').value.trim();

    let url = '/api/library/search?limit=60';
    if (mat) url += `&material=${encodeURIComponent(mat)}`;
    if (st) url += `&subtype=${encodeURIComponent(st)}`;
    if (color) url += `&color=${encodeURIComponent(color)}`;
    if (q) url += `&q=${encodeURIComponent(q)}`;

    try {
        const data = await api('GET', url);
        renderLibraryResults(data.entries || [], data.total);
    } catch (e) {
        showToast(`Search failed: ${e.message}`, 'error');
    }
}

function renderLibraryResults(entries, total) {
    const el = document.getElementById('lib-results');
    if (entries.length === 0) {
        el.innerHTML = '<p class="text-gray-400 col-span-3">No results. Try different filters.</p>';
        return;
    }

    // Group by subtype + color, show just one entry per group
    const groups = {};
    for (const e of entries) {
        const key = `${e.subtype}|${e.color}`;
        if (!groups[key]) groups[key] = { ...e, count: 0 };
        groups[key].count++;
    }

    const grouped = Object.values(groups);
    el.innerHTML = grouped.map(g => `
        <div class="preset-card cursor-pointer" onclick="selectLibraryEntry('${escapeHTML(g.material)}','${escapeHTML(g.subtype)}','${escapeHTML(g.color)}','${escapeHTML(g.uid)}')">
            <div class="flex items-center justify-between">
                <span class="font-semibold text-green-400">${escapeHTML(g.subtype)}</span>
                <span class="text-xs text-gray-500">${g.count} dump${g.count > 1 ? 's' : ''}</span>
            </div>
            <div class="text-sm text-gray-300 mt-1">${escapeHTML(g.color)}</div>
            <div class="text-xs text-gray-500 mt-1">UID: ${g.uid}</div>
        </div>
    `).join('');

    if (total > entries.length) {
        el.innerHTML += `<p class="text-gray-400 col-span-3 text-sm">Showing ${entries.length} of ${total} results. Use filters to narrow down.</p>`;
    }
}

async function selectLibraryEntry(material, subtype, color, uid) {
    try {
        showToast('Downloading tag dump...', 'info');
        const data = await api('POST', '/api/library/download', { material, subtype, color, uid });
        librarySelectedDump = data;

        // Show detail panel
        document.getElementById('lib-detail').classList.remove('hidden');
        document.getElementById('lib-detail-title').textContent = `${data.entry.subtype} - ${data.entry.color} (${data.entry.uid})`;
        displayTagData('lib-detail-data', data.filament, data.entry.uid);
        showToast('Tag dump loaded!', 'success');
    } catch (e) {
        showToast(`Download failed: ${e.message}`, 'error');
    }
}

async function cloneFromLibrary() {
    if (!librarySelectedDump) return showToast('Select a tag dump first', 'error');

    // Convert hex blocks to base64 for the clone workflow
    const hexBlocks = librarySelectedDump.blocks;
    const b64Blocks = hexBlocks.map(h => {
        const bytes = new Uint8Array(h.match(/.{2}/g).map(b => parseInt(b, 16)));
        return btoa(String.fromCharCode(...bytes));
    });

    cloneSourceData = {
        uid: librarySelectedDump.entry.uid,
        filament: librarySelectedDump.filament,
        blocks: b64Blocks,
    };

    switchTab('clone-tag');
    displayTagData('clone-source', librarySelectedDump.filament, librarySelectedDump.entry.uid);
    document.getElementById('btn-clone-write').disabled = false;
    showToast(`${librarySelectedDump.entry.display_name} loaded for cloning. Tap a blank tag.`, 'success');
}

async function saveLibraryToInventory() {
    if (!librarySelectedDump) return;
    const f = librarySelectedDump.filament;
    const e = librarySelectedDump.entry;
    try {
        await api('POST', '/api/spools/', {
            name: `${e.subtype} ${e.color}`,
            brand: 'Bambu Lab',
            material: f.detailed_filament_type || f.filament_type || e.subtype,
            material_id: f.material_id || '',
            color_hex: f.color_hex || '#000000',
            weight_g: f.spool_weight_g || 1000,
            remaining_g: f.spool_weight_g || 1000,
            filament_length_m: f.filament_length_m || 0,
            nozzle_temp_min: f.min_hotend_temp_c || 190,
            nozzle_temp_max: f.max_hotend_temp_c || 230,
            bed_temp: f.bed_temp_c || 60,
            tag_uid: e.uid,
        });
        showToast('Saved to inventory!', 'success');
    } catch (e) {
        showToast(`Save failed: ${e.message}`, 'error');
    }
}

function downloadLibraryDump() {
    if (!librarySelectedDump) return;
    const hexBlocks = librarySelectedDump.blocks;
    const allHex = hexBlocks.join('');
    const bytes = new Uint8Array(allHex.match(/.{2}/g).map(b => parseInt(b, 16)));
    const blob = new Blob([bytes], { type: 'application/octet-stream' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const entry = librarySelectedDump.entry;
    a.download = `${entry.subtype}_${entry.color}_${entry.uid}.bin`;
    a.click();
    URL.revokeObjectURL(url);
}

// ──────────────────────────────────────────────
// Initialization
// ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Set WebSocket URL display
    const wsUrl = document.getElementById('ws-url');
    if (wsUrl) {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl.textContent = `${protocol}//${location.host}/ws/nfc`;
    }

    // Load initial data
    loadDashboard();
    loadPresets();

    // Poll status every 5 seconds
    pollStatus();
    setInterval(pollStatus, 5000);
});
