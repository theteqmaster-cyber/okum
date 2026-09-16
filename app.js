/**
 * Okum — Personal Offline Assistant
 * Core Logic & State Management
 */

(function () {
  'use strict';

  // --- STATE & STORAGE KEYS ---
  const STORAGE_KEYS = {
    NOTES: 'okum_notes_v1',
    SETTINGS: 'okum_settings_v1',
    ORB_POS: 'okum_orb_pos_v1'
  };

  let state = {
    notes: [],
    activeNoteId: null,
    activeCategory: 'General',
    isPinned: false,
    settings: {
      soundEnabled: true,
      dailyGoal: ''
    },
    filterCategory: 'ALL',
    searchQuery: '',
    sortOrder: 'desc', // 'desc' = newest first
    speechRecognition: null,
    isRecording: false
  };

  // --- DOM ELEMENTS ---
  const el = {
    orb: document.getElementById('okum-orb'),
    orbStatusDot: document.getElementById('orb-status-dot'),
    
    // Quick Notepad
    notepadPanel: document.getElementById('quick-notepad-panel'),
    noteTitleInput: document.getElementById('note-title-input'),
    noteContentInput: document.getElementById('note-content-input'),
    categoryPills: document.getElementById('category-pills'),
    btnPinNote: document.getElementById('btn-pin-note'),
    btnVoiceNote: document.getElementById('btn-voice-note'),
    btnExpandDashboard: document.getElementById('btn-expand-dashboard'),
    btnCloseNotepad: document.getElementById('btn-close-notepad'),
    btnNewNote: document.getElementById('btn-new-note'),
    btnSaveNote: document.getElementById('btn-save-note'),
    notepadStatusTime: document.getElementById('notepad-status-time'),
    wordCharCount: document.getElementById('word-char-count'),
    voiceIndicatorBar: document.getElementById('voice-indicator-bar'),
    voiceStatusText: document.getElementById('voice-status-text'),
    btnStopVoice: document.getElementById('btn-stop-voice'),

    // Dashboard
    dashboardOverlay: document.getElementById('dashboard-overlay'),
    btnCloseDashboard: document.getElementById('btn-close-dashboard'),
    sidebarNav: document.querySelectorAll('.sidebar-nav .nav-item'),
    tabContents: document.querySelectorAll('.dashboard-tab-content'),
    totalNotesBadge: document.getElementById('total-notes-badge'),
    dashboardSearchInput: document.getElementById('dashboard-search-input'),
    btnCreateNoteDash: document.getElementById('btn-create-note-dash'),
    notesGrid: document.getElementById('notes-grid'),
    notesEmptyState: document.getElementById('notes-empty-state'),
    btnEmptyCreate: document.getElementById('btn-empty-create'),
    filterCategorySelect: document.getElementById('filter-category-select'),
    btnSortNotes: document.getElementById('btn-sort-notes'),
    sortLabel: document.getElementById('sort-label'),

    // Daily Briefing
    briefingTimeBadge: document.getElementById('briefing-time-badge'),
    briefingGreeting: document.getElementById('briefing-greeting'),
    briefingQuote: document.getElementById('briefing-quote'),
    briefingClock: document.getElementById('briefing-clock'),
    briefingDate: document.getElementById('briefing-date'),
    inputDailyGoal: document.getElementById('input-daily-goal'),
    statTotalCount: document.getElementById('stat-total-count'),
    statPinnedCount: document.getElementById('stat-pinned-count'),
    statWordsCount: document.getElementById('stat-words-count'),

    // Focus Timer
    timerDisplay: document.getElementById('timer-display'),
    btnTimerStart: document.getElementById('btn-timer-start'),
    btnTimerReset: document.getElementById('btn-timer-reset'),
    timerPills: document.querySelectorAll('.timer-pill'),

    // Settings
    btnExportJson: document.getElementById('btn-export-json'),
    inputImportFile: document.getElementById('input-import-file'),
    toggleSoundEffects: document.getElementById('toggle-sound-effects'),
    btnClearAll: document.getElementById('btn-clear-all'),

    // Command Palette
    cmdPaletteModal: document.getElementById('cmd-palette-modal'),
    cmdSearchInput: document.getElementById('cmd-search-input'),
    cmdResultsList: document.getElementById('cmd-results-list'),
    btnCmdK: document.getElementById('btn-cmd-k'),

    // Toast
    toastContainer: document.getElementById('toast-container')
  };

  // --- INITIALIZATION ---
  function init() {
    loadStateFromStorage();
    setupAudioContext();
    setupOrbDragging();
    setupEventListeners();
    setupSpeechRecognition();
    startClock();
    renderAll();
    
    // Feather icons replacement
    if (window.feather) {
      window.feather.replace();
    }
  }

  // --- STORAGE HELPERS ---
  function loadStateFromStorage() {
    try {
      const savedNotes = localStorage.getItem(STORAGE_KEYS.NOTES);
      if (savedNotes) state.notes = JSON.parse(savedNotes);
      
      const savedSettings = localStorage.getItem(STORAGE_KEYS.SETTINGS);
      if (savedSettings) state.settings = { ...state.settings, ...JSON.parse(savedSettings) };
      
      // Default sample note if completely empty
      if (state.notes.length === 0) {
        state.notes.push({
          id: 'welcome-note-1',
          title: 'Welcome to Okum! 🚀',
          category: 'General',
          content: 'Hello mphatic!\n\nOkum is your offline personal assistant.\n- Click the floating circle anytime to quickly jot down a note.\n- Drag the circle anywhere on your screen.\n- Press Ctrl + K to open the command palette.\n- Use the Focus Timer to stay productive.',
          pinned: true,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        });
        saveNotesToStorage();
      }
    } catch (err) {
      console.error('Failed to load state:', err);
    }
  }

  function saveNotesToStorage() {
    try {
      localStorage.setItem(STORAGE_KEYS.NOTES, JSON.stringify(state.notes));
    } catch (err) {
      showToast('Error saving note to local storage', 'error');
    }
  }

  function saveSettingsToStorage() {
    try {
      localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(state.settings));
    } catch (err) {
      console.error('Error saving settings:', err);
    }
  }

  // --- AUDIO SYNTHESIZER (WEB AUDIO API) ---
  let audioCtx = null;

  function setupAudioContext() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (AudioContext) {
      audioCtx = new AudioContext();
    }
  }

  function playSound(type = 'click') {
    if (!state.settings.soundEnabled || !audioCtx) return;
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    try {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      const now = audioCtx.currentTime;

      if (type === 'open') {
        osc.type = 'sine';
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.15);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
        osc.start(now);
        osc.stop(now + 0.15);
      } else if (type === 'save') {
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(523.25, now); // C5
        osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.12); // E5
        gain.gain.setValueAtTime(0.12, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
        osc.start(now);
        osc.stop(now + 0.2);
      } else if (type === 'delete') {
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(300, now);
        osc.frequency.exponentialRampToValueAtTime(150, now + 0.15);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
        osc.start(now);
        osc.stop(now + 0.15);
      } else {
        // Subtle click
        osc.type = 'sine';
        osc.frequency.setValueAtTime(600, now);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);
        osc.start(now);
        osc.stop(now + 0.05);
      }
    } catch (e) {
      // Ignore audio synthesis errors
    }
  }

  // --- FLOATING ORB WIDGET DRAGGING ---
  function setupOrbDragging() {
    let isDragging = false;
    let startX, startY, initialLeft, initialTop;
    let dragThreshold = false;

    // Load saved orb position
    const savedPos = localStorage.getItem(STORAGE_KEYS.ORB_POS);
    if (savedPos) {
      const pos = JSON.parse(savedPos);
      el.orb.style.left = pos.x + 'px';
      el.orb.style.top = pos.y + 'px';
      el.orb.style.right = 'auto';
      el.orb.style.bottom = 'auto';
    }

    el.orb.addEventListener('pointerdown', (e) => {
      isDragging = true;
      dragThreshold = false;
      startX = e.clientX;
      startY = e.clientY;
      const rect = el.orb.getBoundingClientRect();
      initialLeft = rect.left;
      initialTop = rect.top;
      el.orb.setPointerCapture(e.pointerId);
    });

    el.orb.addEventListener('pointermove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;

      if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
        dragThreshold = true;
      }

      let newLeft = initialLeft + dx;
      let newTop = initialTop + dy;

      // Keep within screen bounds
      const maxLeft = window.innerWidth - el.orb.offsetWidth - 10;
      const maxTop = window.innerHeight - el.orb.offsetHeight - 10;
      newLeft = Math.max(10, Math.min(newLeft, maxLeft));
      newTop = Math.max(10, Math.min(newTop, maxTop));

      el.orb.style.left = newLeft + 'px';
      el.orb.style.top = newTop + 'px';
      el.orb.style.right = 'auto';
      el.orb.style.bottom = 'auto';
    });

    el.orb.addEventListener('pointerup', (e) => {
      if (!isDragging) return;
      isDragging = false;

      // Save position
      const rect = el.orb.getBoundingClientRect();
      localStorage.setItem(STORAGE_KEYS.ORB_POS, JSON.stringify({ x: rect.left, y: rect.top }));

      // If it wasn't a drag, handle click (toggle notepad)
      if (!dragThreshold) {
        toggleQuickNotepad();
      }
    });
  }

  // --- QUICK NOTEPAD PANEL LOGIC ---
  function toggleQuickNotepad() {
    const isHidden = el.notepadPanel.classList.contains('hidden');
    if (isHidden) {
      openQuickNotepad();
    } else {
      closeQuickNotepad();
    }
  }

  function openQuickNotepad(noteId = null) {
    playSound('open');
    el.notepadPanel.classList.remove('hidden');

    if (noteId) {
      loadNoteToEditor(noteId);
    } else if (!state.activeNoteId) {
      // Start a fresh draft
      resetEditor();
    }
    el.noteTitleInput.focus();
  }

  function closeQuickNotepad() {
    playSound('click');
    el.notepadPanel.classList.add('hidden');
    stopSpeechRecognition();
  }

  function resetEditor() {
    state.activeNoteId = null;
    state.activeCategory = 'General';
    state.isPinned = false;

    el.noteTitleInput.value = '';
    el.noteContentInput.value = '';
    updateCategoryPills();
    updatePinButton();
    updateWordCharCount();
    el.notepadStatusTime.textContent = 'New draft auto-saving';
  }

  function loadNoteToEditor(noteId) {
    const note = state.notes.find((n) => n.id === noteId);
    if (!note) return;

    state.activeNoteId = note.id;
    state.activeCategory = note.category || 'General';
    state.isPinned = !!note.pinned;

    el.noteTitleInput.value = note.title;
    el.noteContentInput.value = note.content;
    updateCategoryPills();
    updatePinButton();
    updateWordCharCount();
    el.notepadStatusTime.textContent = `Editing note • ${formatDate(note.updatedAt)}`;
  }

  function saveCurrentNote() {
    const title = el.noteTitleInput.value.trim();
    const content = el.noteContentInput.value.trim();

    if (!title && !content) {
      showToast('Note is empty', 'warning');
      return;
    }

    const now = new Date().toISOString();

    if (state.activeNoteId) {
      // Update existing
      const note = state.notes.find((n) => n.id === state.activeNoteId);
      if (note) {
        note.title = title || 'Untitled Note';
        note.content = content;
        note.category = state.activeCategory;
        note.pinned = state.isPinned;
        note.updatedAt = now;
      }
    } else {
      // Create new note
      const newNote = {
        id: 'note_' + Date.now(),
        title: title || 'Untitled Note',
        category: state.activeCategory,
        content: content,
        pinned: state.isPinned,
        createdAt: now,
        updatedAt: now
      };
      state.notes.unshift(newNote);
      state.activeNoteId = newNote.id;
    }

    saveNotesToStorage();
    playSound('save');
    showToast('Note saved!', 'success');
    renderAll();
  }

  function updateCategoryPills() {
    const pills = el.categoryPills.querySelectorAll('.pill');
    pills.forEach((p) => {
      if (p.getAttribute('data-category') === state.activeCategory) {
        p.classList.add('active');
      } else {
        p.classList.remove('active');
      }
    });
  }

  function updatePinButton() {
    if (state.isPinned) {
      el.btnPinNote.classList.add('active');
      el.btnPinNote.innerHTML = `<i data-feather="bookmark"></i> Pinned`;
    } else {
      el.btnPinNote.classList.remove('active');
      el.btnPinNote.innerHTML = `<i data-feather="bookmark"></i> Pin`;
    }
    if (window.feather) window.feather.replace();
  }

  function updateWordCharCount() {
    const text = el.noteContentInput.value || '';
    const chars = text.length;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    el.wordCharCount.textContent = `${words} words • ${chars} chars`;
  }

  // --- SPEECH RECOGNITION (VOICE NOTES) ---
  function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      state.speechRecognition = new SpeechRecognition();
      state.speechRecognition.continuous = true;
      state.speechRecognition.interimResults = true;

      state.speechRecognition.onresult = (event) => {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript) {
          el.noteContentInput.value += (el.noteContentInput.value ? ' ' : '') + transcript;
          updateWordCharCount();
        }
      };

      state.speechRecognition.onerror = (e) => {
        console.warn('Speech recognition error:', e.error);
        stopSpeechRecognition();
        showToast('Voice listening stopped', 'info');
      };

      state.speechRecognition.onend = () => {
        if (state.isRecording) {
          state.speechRecognition.start(); // keep listening
        }
      };
    } else {
      el.btnVoiceNote.style.display = 'none'; // hide if not supported
    }
  }

  function toggleSpeechRecognition() {
    if (!state.speechRecognition) {
      showToast('Speech recognition not supported in this browser', 'warning');
      return;
    }

    if (state.isRecording) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  }

  function startSpeechRecognition() {
    try {
      state.isRecording = true;
      state.speechRecognition.start();
      el.btnVoiceNote.classList.add('active');
      el.voiceIndicatorBar.classList.remove('hidden');
      playSound('open');
      showToast('Listening... Speak to add text', 'info');
    } catch (e) {
      console.error(e);
    }
  }

  function stopSpeechRecognition() {
    if (state.speechRecognition && state.isRecording) {
      state.isRecording = false;
      state.speechRecognition.stop();
      el.btnVoiceNote.classList.remove('active');
      el.voiceIndicatorBar.classList.add('hidden');
      playSound('click');
    }
  }

  // --- DASHBOARD LOGIC ---
  function openDashboard(tabId = 'tab-notes') {
    playSound('open');
    el.dashboardOverlay.classList.remove('hidden');
    switchDashboardTab(tabId);
    renderAll();
  }

  function closeDashboard() {
    playSound('click');
    el.dashboardOverlay.classList.add('hidden');
  }

  function switchDashboardTab(tabId) {
    el.sidebarNav.forEach((btn) => {
      if (btn.getAttribute('data-tab') === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    el.tabContents.forEach((tab) => {
      if (tab.id === tabId) {
        tab.classList.remove('hidden');
        tab.classList.add('active');
      } else {
        tab.classList.add('hidden');
        tab.classList.remove('active');
      }
    });
  }

  function renderAll() {
    renderNotesGrid();
    renderBriefing();
    renderStats();
    updateBadges();
  }

  function renderNotesGrid() {
    let filtered = [...state.notes];

    // Filter by Category
    if (state.filterCategory !== 'ALL') {
      filtered = filtered.filter((n) => n.category === state.filterCategory);
    }

    // Filter by Search Query
    if (state.searchQuery.trim()) {
      const q = state.searchQuery.toLowerCase();
      filtered = filtered.filter(
        (n) => n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q) || (n.category && n.category.toLowerCase().includes(q))
      );
    }

    // Sort
    filtered.sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1; // Pinned first
      const timeA = new Date(a.updatedAt).getTime();
      const timeB = new Date(b.updatedAt).getTime();
      return state.sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });

    if (filtered.length === 0) {
      el.notesGrid.innerHTML = '';
      el.notesEmptyState.classList.remove('hidden');
      return;
    }

    el.notesEmptyState.classList.add('hidden');

    el.notesGrid.innerHTML = filtered
      .map(
        (note) => `
      <div class="note-card ${note.pinned ? 'pinned' : ''}" data-id="${note.id}">
        <div class="note-card-header">
          <h4 class="note-card-title">${escapeHtml(note.title || 'Untitled')}</h4>
          <span class="pill">${escapeHtml(note.category || 'General')}</span>
        </div>
        <div class="note-card-body">${escapeHtml(note.content || 'No content')}</div>
        <div class="note-card-footer">
          <span class="text-muted text-sm">${formatDate(note.updatedAt)}</span>
          <div class="note-card-actions">
            <button class="btn-icon btn-edit-note" data-id="${note.id}" title="Edit Note"><i data-feather="edit-2"></i></button>
            <button class="btn-icon btn-copy-note" data-id="${note.id}" title="Copy Text"><i data-feather="copy"></i></button>
            <button class="btn-icon btn-download-note" data-id="${note.id}" title="Download Markdown"><i data-feather="download"></i></button>
            <button class="btn-icon btn-delete-note" data-id="${note.id}" title="Delete Note"><i data-feather="trash-2"></i></button>
          </div>
        </div>
      </div>
    `
      )
      .join('');

    if (window.feather) window.feather.replace();

    // Event listeners for cards
    el.notesGrid.querySelectorAll('.btn-edit-note').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        openQuickNotepad(btn.getAttribute('data-id'));
      });
    });

    el.notesGrid.querySelectorAll('.btn-copy-note').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const note = state.notes.find((n) => n.id === btn.getAttribute('data-id'));
        if (note) {
          navigator.clipboard.writeText(`${note.title}\n\n${note.content}`);
          playSound('click');
          showToast('Copied to clipboard!', 'success');
        }
      });
    });

    el.notesGrid.querySelectorAll('.btn-download-note').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const note = state.notes.find((n) => n.id === btn.getAttribute('data-id'));
        if (note) {
          downloadFile(`${slugify(note.title)}.md`, `# ${note.title}\n\n${note.content}`);
          showToast('Downloaded .md file', 'success');
        }
      });
    });

    el.notesGrid.querySelectorAll('.btn-delete-note').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        deleteNote(id);
      });
    });

    el.notesGrid.querySelectorAll('.note-card').forEach((card) => {
      card.addEventListener('click', () => {
        openQuickNotepad(card.getAttribute('data-id'));
      });
    });
  }

  function deleteNote(id) {
    if (confirm('Are you sure you want to delete this note?')) {
      state.notes = state.notes.filter((n) => n.id !== id);
      if (state.activeNoteId === id) {
        resetEditor();
      }
      saveNotesToStorage();
      playSound('delete');
      showToast('Note deleted', 'info');
      renderAll();
    }
  }

  // --- BRIEFING & CLOCK ---
  function startClock() {
    function updateClock() {
      const now = new Date();
      const hours = now.getHours();
      let timeBadge = 'Good Morning';
      if (hours >= 12 && hours < 17) timeBadge = 'Good Afternoon';
      else if (hours >= 17 || hours < 5) timeBadge = 'Good Evening';

      el.briefingTimeBadge.textContent = timeBadge;
      el.briefingGreeting.textContent = `${timeBadge}, mphatic!`;
      el.briefingClock.textContent = now.toLocaleTimeString();
      el.briefingDate.textContent = now.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
    }
    updateClock();
    setInterval(updateClock, 1000);
  }

  function renderBriefing() {
    el.inputDailyGoal.value = state.settings.dailyGoal || '';
  }

  function renderStats() {
    el.statTotalCount.textContent = state.notes.length;
    el.statPinnedCount.textContent = state.notes.filter((n) => n.pinned).length;

    const totalWords = state.notes.reduce((acc, note) => {
      const text = note.content || '';
      return acc + (text.trim() ? text.trim().split(/\s+/).length : 0);
    }, 0);

    el.statWordsCount.textContent = totalWords;
  }

  function updateBadges() {
    el.totalNotesBadge.textContent = state.notes.length;
  }

  // --- FOCUS TIMER ---
  let timerInterval = null;
  let timerSeconds = 25 * 60;
  let isTimerRunning = false;

  function startFocusTimer() {
    if (isTimerRunning) {
      // Pause
      clearInterval(timerInterval);
      isTimerRunning = false;
      el.btnTimerStart.innerHTML = `<i data-feather="play"></i> Resume`;
    } else {
      // Start
      isTimerRunning = true;
      playSound('open');
      el.btnTimerStart.innerHTML = `<i data-feather="pause"></i> Pause`;
      timerInterval = setInterval(() => {
        timerSeconds--;
        updateTimerDisplay();
        if (timerSeconds <= 0) {
          clearInterval(timerInterval);
          isTimerRunning = false;
          playSound('save');
          showToast('Focus session complete! Great job mphatic 🎉', 'success');
          el.btnTimerStart.innerHTML = `<i data-feather="play"></i> Start Focus`;
        }
      }, 1000);
    }
    if (window.feather) window.feather.replace();
  }

  function resetFocusTimer(minutes = 25) {
    clearInterval(timerInterval);
    isTimerRunning = false;
    timerSeconds = minutes * 60;
    updateTimerDisplay();
    el.btnTimerStart.innerHTML = `<i data-feather="play"></i> Start Focus`;
    if (window.feather) window.feather.replace();
  }

  function updateTimerDisplay() {
    const mins = Math.floor(timerSeconds / 60);
    const secs = timerSeconds % 60;
    el.timerDisplay.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  // --- COMMAND PALETTE (Ctrl + K) ---
  function openCommandPalette() {
    playSound('open');
    el.cmdPaletteModal.classList.remove('hidden');
    el.cmdSearchInput.value = '';
    el.cmdSearchInput.focus();
    renderCommandResults('');
  }

  function closeCommandPalette() {
    playSound('click');
    el.cmdPaletteModal.classList.add('hidden');
  }

  function renderCommandResults(query) {
    const q = query.toLowerCase().trim();
    const defaultActions = [
      { icon: 'plus', title: 'Create New Quick Note', action: () => { openQuickNotepad(); resetEditor(); } },
      { icon: 'grid', title: 'Open Full Dashboard', action: () => openDashboard('tab-notes') },
      { icon: 'sun', title: 'View Daily Briefing', action: () => openDashboard('tab-briefing') },
      { icon: 'clock', title: 'Start Focus Timer', action: () => openDashboard('tab-focus') },
      { icon: 'download', title: 'Export Notes (JSON Backup)', action: exportNotesJson }
    ];

    let matches = defaultActions.filter((a) => a.title.toLowerCase().includes(q));

    // Search notes matching query
    if (q) {
      const noteMatches = state.notes
        .filter((n) => n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q))
        .map((n) => ({
          icon: 'file-text',
          title: `Note: ${n.title}`,
          action: () => openQuickNotepad(n.id)
        }));
      matches = [...matches, ...noteMatches];
    }

    if (matches.length === 0) {
      el.cmdResultsList.innerHTML = `<div class="p-3 text-muted text-sm">No matching commands found</div>`;
      return;
    }

    el.cmdResultsList.innerHTML = matches
      .map(
        (item, idx) => `
      <div class="cmd-item ${idx === 0 ? 'selected' : ''}" data-idx="${idx}">
        <i data-feather="${item.icon}"></i>
        <span>${escapeHtml(item.title)}</span>
      </div>
    `
      )
      .join('');

    if (window.feather) window.feather.replace();

    el.cmdResultsList.querySelectorAll('.cmd-item').forEach((item, idx) => {
      item.addEventListener('click', () => {
        closeCommandPalette();
        matches[idx].action();
      });
    });
  }

  // --- EXPORT & IMPORT ---
  function exportNotesJson() {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(state.notes, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `okum-notes-backup-${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
    showToast('Exported notes JSON backup', 'success');
  }

  function importNotesJson(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result);
        if (Array.isArray(imported)) {
          state.notes = [...imported, ...state.notes];
          // deduplicate by id
          const uniqueMap = new Map();
          state.notes.forEach((n) => uniqueMap.set(n.id, n));
          state.notes = Array.from(uniqueMap.values());
          saveNotesToStorage();
          renderAll();
          showToast(`Imported notes successfully!`, 'success');
        } else {
          showToast('Invalid backup format', 'error');
        }
      } catch (err) {
        showToast('Error reading JSON file', 'error');
      }
    };
    reader.readAsText(file);
  }

  // --- EVENT LISTENERS ---
  function setupEventListeners() {
    // Quick Notepad buttons
    el.btnCloseNotepad.addEventListener('click', closeQuickNotepad);
    el.btnNewNote.addEventListener('click', () => resetEditor());
    el.btnSaveNote.addEventListener('click', saveCurrentNote);
    el.btnExpandDashboard.addEventListener('click', () => {
      closeQuickNotepad();
      openDashboard('tab-notes');
    });
    el.btnVoiceNote.addEventListener('click', toggleSpeechRecognition);
    el.btnStopVoice.addEventListener('click', stopSpeechRecognition);

    // Inputs live count & auto title
    el.noteContentInput.addEventListener('input', updateWordCharCount);
    el.noteTitleInput.addEventListener('input', () => {
      el.notepadStatusTime.textContent = 'Editing draft...';
    });

    // Category pills click
    el.categoryPills.addEventListener('click', (e) => {
      if (e.target.classList.contains('pill')) {
        state.activeCategory = e.target.getAttribute('data-category');
        updateCategoryPills();
      }
    });

    // Pin button click
    el.btnPinNote.addEventListener('click', () => {
      state.isPinned = !state.isPinned;
      updatePinButton();
    });

    // Dashboard navigation & close
    el.btnCloseDashboard.addEventListener('click', closeDashboard);
    el.sidebarNav.forEach((btn) => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        switchDashboardTab(tabId);
      });
    });

    el.btnCreateNoteDash.addEventListener('click', () => {
      closeDashboard();
      openQuickNotepad();
      resetEditor();
    });
    el.btnEmptyCreate.addEventListener('click', () => {
      closeDashboard();
      openQuickNotepad();
      resetEditor();
    });

    // Search & Filter
    el.dashboardSearchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      renderNotesGrid();
    });

    el.filterCategorySelect.addEventListener('change', (e) => {
      state.filterCategory = e.target.value;
      renderNotesGrid();
    });

    el.btnSortNotes.addEventListener('click', () => {
      state.sortOrder = state.sortOrder === 'desc' ? 'asc' : 'desc';
      el.sortLabel.textContent = state.sortOrder === 'desc' ? 'Newest First' : 'Oldest First';
      renderNotesGrid();
    });

    // Daily Goal
    el.inputDailyGoal.addEventListener('change', (e) => {
      state.settings.dailyGoal = e.target.value;
      saveSettingsToStorage();
      showToast('Focus goal updated', 'success');
    });

    // Focus Timer
    el.btnTimerStart.addEventListener('click', startFocusTimer);
    el.btnTimerReset.addEventListener('click', () => resetFocusTimer(25));
    el.timerPills.forEach((pill) => {
      pill.addEventListener('click', () => {
        el.timerPills.forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        const mins = parseInt(pill.getAttribute('data-minutes'), 10);
        resetFocusTimer(mins);
      });
    });

    // Settings
    el.btnExportJson.addEventListener('click', exportNotesJson);
    el.inputImportFile.addEventListener('change', (e) => {
      if (e.target.files[0]) importNotesJson(e.target.files[0]);
    });
    el.toggleSoundEffects.checked = state.settings.soundEnabled;
    el.toggleSoundEffects.addEventListener('change', (e) => {
      state.settings.soundEnabled = e.target.checked;
      saveSettingsToStorage();
    });

    el.btnClearAll.addEventListener('click', () => {
      if (confirm('DANGER: This will delete ALL your notes permanently! Continue?')) {
        state.notes = [];
        saveNotesToStorage();
        renderAll();
        showToast('All notes cleared', 'info');
      }
    });

    // Command palette triggers
    el.btnCmdK.addEventListener('click', openCommandPalette);
    el.cmdSearchInput.addEventListener('input', (e) => {
      renderCommandResults(e.target.value);
    });

    // Keyboard Shortcuts (Esc, Ctrl+K)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        openCommandPalette();
      } else if (e.key === 'Escape') {
        if (!el.cmdPaletteModal.classList.contains('hidden')) {
          closeCommandPalette();
        } else if (!el.notepadPanel.classList.contains('hidden')) {
          closeQuickNotepad();
        } else if (!el.dashboardOverlay.classList.contains('hidden')) {
          closeDashboard();
        }
      }
    });
  }

  // --- TOAST NOTIFICATIONS ---
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
    el.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  // --- HELPERS ---
  function formatDate(isoStr) {
    if (!isoStr) return '';
    const date = new Date(isoStr);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  function slugify(text) {
    return (text || 'note')
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_-]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  function downloadFile(filename, text) {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Service worker for offline capability
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch(() => {});
    });
  }

  // Run on DOM loaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
