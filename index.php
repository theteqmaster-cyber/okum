<?php
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
$notesDir = '/home/mphatic/Documents/OkumNotes';
$dbPath = '/home/mphatic/.local/share/okum/okum.db';

function getOkumNotes($notesDir, $dbPath) {
    $notes = [];
    $seenTitles = [];

    if (file_exists($dbPath)) {
        try {
            $db = new SQLite3($dbPath, SQLITE3_OPEN_READONLY);
            $res = $db->query("SELECT * FROM notes ORDER BY pinned DESC, updated_at DESC");
            while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
                $notes[] = [
                    'id' => $row['id'],
                    'title' => $row['title'],
                    'category' => $row['category'],
                    'content' => $row['content'],
                    'pinned' => (bool)$row['pinned'],
                    'created_at' => $row['created_at'],
                    'updated_at' => $row['updated_at'],
                    'source' => 'sqlite'
                ];
                $seenTitles[strtolower(trim($row['title']))] = true;
            }
            $db->close();
        } catch (Exception $e) {}
    }

    if (is_dir($notesDir)) {
        $files = glob("$notesDir/*.md");
        foreach ($files as $filePath) {
            $filename = basename($filePath);
            $rawTitle = preg_replace('/\.md$/i', '', $filename);
            if (!isset($seenTitles[strtolower(trim($rawTitle))])) {
                $content = file_get_contents($filePath);
                $mtime = date('c', filemtime($filePath));
                $notes[] = [
                    'id' => 'md_' . md5($filename),
                    'title' => $rawTitle,
                    'category' => 'General',
                    'content' => $content,
                    'pinned' => false,
                    'created_at' => $mtime,
                    'updated_at' => $mtime,
                    'source' => 'md_file'
                ];
            }
        }
    }

    return $notes;
}

if (isset($_GET['api']) && $_GET['api'] === '1') {
    header('Content-Type: application/json');
    echo json_encode(['status' => 'success', 'notes' => getOkumNotes($notesDir, $dbPath)]);
    exit;
}

$allNotes = getOkumNotes($notesDir, $dbPath);
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Okum Document Vault & Notes Reader</title>
  <meta name="description" content="Web document reader for Okum Linux desktop notes in ~/Documents/OkumNotes/">
  
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  
  <!-- Markdown parser -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: #070913;
      color: #f3f4f6;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    /* Top Header Bar */
    .header-bar {
      height: 60px;
      background: rgba(15, 18, 30, 0.95);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      backdrop-filter: blur(12px);
      z-index: 10;
    }

    .brand-title {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      width: 34px;
      height: 34px;
      border-radius: 9px;
      background: rgba(99, 102, 241, 0.18);
      border: 1px solid rgba(99, 102, 241, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #8b5cf6;
    }
    .brand-text h1 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.15rem;
      font-weight: 700;
      color: #ffffff;
    }
    .brand-text p {
      font-size: 0.72rem;
      color: #9ca3af;
      font-family: 'JetBrains Mono', monospace;
    }

    .search-box {
      width: 320px;
      position: relative;
    }
    .search-input {
      width: 100%;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      padding: 8px 14px 8px 36px;
      color: #ffffff;
      font-size: 0.85rem;
      outline: none;
      transition: all 0.2s;
    }
    .search-input:focus {
      border-color: #6366f1;
      background: rgba(255, 255, 255, 0.09);
    }
    .search-icon {
      position: absolute;
      left: 12px;
      top: 50%;
      transform: translateY(-50%);
      color: #9ca3af;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .doc-count-badge {
      font-size: 0.75rem;
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      background: rgba(99, 102, 241, 0.15);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.3);
      padding: 4px 10px;
      border-radius: 20px;
    }
    .btn-refresh {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #f3f4f6;
      border-radius: 8px;
      padding: 6px 12px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-refresh:hover {
      background: rgba(255, 255, 255, 0.18);
    }

    /* Main Grid View */
    .main-container {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    /* Sidebar Document Navigation */
    .sidebar {
      width: 340px;
      background: rgba(11, 14, 25, 0.95);
      border-right: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    .category-bar {
      padding: 12px 14px;
      display: flex;
      gap: 6px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      overflow-x: auto;
    }
    .cat-pill {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 12px;
      padding: 4px 10px;
      font-size: 0.75rem;
      font-weight: 600;
      color: #9ca3af;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }
    .cat-pill:hover, .cat-pill.active {
      background: #6366f1;
      color: #ffffff;
      border-color: #8b5cf6;
    }

    .doc-list {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .doc-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 12px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .doc-card:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(99, 102, 241, 0.35);
      transform: translateY(-1px);
    }
    .doc-card.active {
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.6);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .card-title {
      font-size: 0.92rem;
      font-weight: 700;
      color: #ffffff;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 200px;
    }
    .card-category {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 6px;
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
    }

    .card-snippet {
      font-size: 0.78rem;
      color: #9ca3af;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      margin-bottom: 8px;
    }

    .card-footer {
      display: flex;
      justify-content: space-between;
      font-size: 0.7rem;
      color: #64748b;
      font-family: 'JetBrains Mono', monospace;
    }

    /* Document Reader View Area */
    .reader-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: #070913;
      overflow: hidden;
    }

    .reader-header {
      padding: 16px 24px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(11, 14, 25, 0.7);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .reader-meta h2 {
      font-family: 'Outfit', sans-serif;
      font-size: 1.35rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 4px;
    }
    .reader-submeta {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 0.75rem;
      color: #9ca3af;
      font-family: 'JetBrains Mono', monospace;
    }
    .path-badge {
      background: rgba(255, 255, 255, 0.06);
      padding: 2px 8px;
      border-radius: 6px;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .reader-controls {
      display: flex;
      gap: 8px;
    }
    .btn-toggle {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #9ca3af;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-toggle.active {
      background: #6366f1;
      color: #ffffff;
      border-color: #8b5cf6;
    }

    .reader-body {
      flex: 1;
      overflow-y: auto;
      padding: 24px 32px;
    }
    .markdown-content {
      font-size: 0.95rem;
      line-height: 1.7;
      color: #e2e8f0;
      max-width: 850px;
    }
    .markdown-content h1 { font-size: 1.7rem; font-weight: 700; color: #ffffff; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px; }
    .markdown-content h2 { font-size: 1.35rem; font-weight: 700; color: #f1f5f9; margin: 20px 0 10px; }
    .markdown-content h3 { font-size: 1.1rem; font-weight: 600; color: #a5b4fc; margin: 16px 0 8px; }
    .markdown-content p { margin-bottom: 14px; }
    .markdown-content ul, .markdown-content ol { margin: 10px 0 16px 20px; }
    .markdown-content li { margin-bottom: 6px; }
    .markdown-content code {
      background: rgba(255, 255, 255, 0.1);
      color: #a5b4fc;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
    }
    .markdown-content pre {
      background: rgba(10, 12, 22, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.12);
      padding: 14px;
      border-radius: 8px;
      overflow-x: auto;
      margin: 14px 0;
    }
    .markdown-content pre code { background: transparent; padding: 0; }

    .raw-content {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.88rem;
      color: #cbd5e1;
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(10, 12, 22, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 16px;
      border-radius: 10px;
    }

    .empty-reader {
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #64748b;
      gap: 10px;
    }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #6366f1; }
  </style>
</head>
<body>

  <!-- Header Bar -->
  <header class="header-bar">
    <div class="brand-title">
      <div class="brand-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      </div>
      <div class="brand-text">
        <h1>Okum Notes Vault</h1>
        <p>~/Documents/OkumNotes/</p>
      </div>
    </div>

    <div class="search-box">
      <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="search-input" class="search-input" placeholder="Search notes or content...">
    </div>

    <div class="header-actions">
      <span class="doc-count-badge" id="doc-count-label"><?= count($allNotes) ?> Documents</span>
      <button class="btn-refresh" id="btn-refresh-vault">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
        Refresh
      </button>
    </div>
  </header>

  <!-- Main View -->
  <main class="main-container">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="category-bar" id="cat-bar">
        <button class="cat-pill active" data-cat="ALL">All</button>
        <button class="cat-pill" data-cat="General">General</button>
        <button class="cat-pill" data-cat="Ideas">Ideas</button>
        <button class="cat-pill" data-cat="Tasks">Tasks</button>
        <button class="cat-pill" data-cat="Urgent">Urgent</button>
      </div>

      <div class="doc-list" id="doc-list-container">
        <!-- Document cards inserted dynamically -->
      </div>
    </aside>

    <!-- Document Reader Area -->
    <section class="reader-area">
      <div class="reader-header" id="reader-header" style="display: none;">
        <div class="reader-meta">
          <h2 id="doc-title-display">Select a Note</h2>
          <div class="reader-submeta">
            <span class="path-badge" id="doc-path-display">~/Documents/OkumNotes/</span>
            <span id="doc-updated-display">--</span>
            <span id="doc-words-display">0 words</span>
          </div>
        </div>

        <div class="reader-controls">
          <button class="btn-toggle active" id="btn-view-rendered">Rendered</button>
          <button class="btn-toggle" id="btn-view-raw">Raw MD</button>
        </div>
      </div>

      <div class="reader-body" id="reader-body">
        <div class="empty-reader" id="empty-reader-view">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <p>Select a note from the left to read its contents</p>
        </div>
        <div class="markdown-content" id="rendered-md-view" style="display: none;"></div>
        <div class="raw-content" id="raw-md-view" style="display: none;"></div>
      </div>
    </section>
  </main>

  <script>
    let allNotes = <?= json_encode($allNotes) ?>;
    let selectedNoteId = null;
    let activeCat = 'ALL';
    let searchQuery = '';
    let isRawMode = false;

    const el = {
      docList: document.getElementById('doc-list-container'),
      searchInput: document.getElementById('search-input'),
      docCountLabel: document.getElementById('doc-count-label'),
      btnRefresh: document.getElementById('btn-refresh-vault'),
      catBar: document.getElementById('cat-bar'),
      readerHeader: document.getElementById('reader-header'),
      emptyView: document.getElementById('empty-reader-view'),
      renderedView: document.getElementById('rendered-md-view'),
      rawView: document.getElementById('raw-md-view'),
      docTitle: document.getElementById('doc-title-display'),
      docPath: document.getElementById('doc-path-display'),
      docUpdated: document.getElementById('doc-updated-display'),
      docWords: document.getElementById('doc-words-display'),
      btnRendered: document.getElementById('btn-view-rendered'),
      btnRaw: document.getElementById('btn-view-raw')
    };

    function renderDocList() {
      el.docList.innerHTML = '';

      let filtered = allNotes.filter(n => {
        let matchesCat = activeCat === 'ALL' || (n.category || 'General').toLowerCase() === activeCat.toLowerCase();
        let q = searchQuery.toLowerCase();
        let matchesQuery = !q || (n.title && n.title.toLowerCase().includes(q)) || (n.content && n.content.toLowerCase().includes(q));
        return matchesCat && matchesQuery;
      });

      el.docCountLabel.textContent = `${filtered.length} Document${filtered.length === 1 ? '' : 's'}`;

      if (filtered.length === 0) {
        el.docList.innerHTML = '<div style="text-align: center; color: #64748b; padding: 20px; font-size: 0.85rem;">No matching notes found in ~/Documents/OkumNotes/</div>';
        return;
      }

      filtered.forEach(note => {
        let card = document.createElement('div');
        card.className = `doc-card ${note.id === selectedNoteId ? 'active' : ''}`;
        card.onclick = () => selectNote(note.id);

        let words = note.content ? note.content.trim().split(/\s+/).length : 0;
        let safeTitle = note.title || 'Untitled Note';
        let snippet = note.content ? note.content.replace(/^#+\s+.*$/gm, '').trim() : '';

        let formattedDate = note.updated_at ? new Date(note.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';

        card.innerHTML = `
          <div class="card-header">
            <span class="card-title">${escapeHtml(safeTitle)}</span>
            <span class="card-category">${escapeHtml(note.category || 'General')}</span>
          </div>
          <div class="card-snippet">${escapeHtml(snippet.substring(0, 100))}</div>
          <div class="card-footer">
            <span>${words} words</span>
            <span>${formattedDate}</span>
          </div>
        `;
        el.docList.appendChild(card);
      });
    }

    function selectNote(noteId) {
      selectedNoteId = noteId;
      let note = allNotes.find(n => n.id === noteId);
      if (!note) return;

      renderDocList();

      el.emptyView.style.display = 'none';
      el.readerHeader.style.display = 'flex';

      el.docTitle.textContent = note.title || 'Untitled Note';
      let safeFileName = (note.title || 'note').replace(/[^a-zA-Z0-9 _-]/g, '').trim() + '.md';
      el.docPath.textContent = `~/Documents/OkumNotes/${safeFileName}`;
      
      let formattedDate = note.updated_at ? new Date(note.updated_at).toLocaleString() : '';
      el.docUpdated.textContent = formattedDate;

      let words = note.content ? note.content.trim().split(/\s+/).length : 0;
      let chars = note.content ? note.content.length : 0;
      el.docWords.textContent = `${words} words • ${chars} chars`;

      if (typeof marked !== 'undefined') {
        el.renderedView.innerHTML = marked.parse(note.content || '*Empty note content*');
      } else {
        el.renderedView.textContent = note.content || '';
      }

      el.rawView.textContent = note.content || '';

      updateViewMode();
    }

    function updateViewMode() {
      if (isRawMode) {
        el.renderedView.style.display = 'none';
        el.rawView.style.display = 'block';
        el.btnRaw.classList.add('active');
        el.btnRendered.classList.remove('active');
      } else {
        el.renderedView.style.display = 'block';
        el.rawView.style.display = 'none';
        el.btnRendered.classList.add('active');
        el.btnRaw.classList.remove('active');
      }
    }

    function refreshVault() {
      fetch('index.php?api=1')
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            allNotes = data.notes;
            renderDocList();
            if (selectedNoteId) selectNote(selectedNoteId);
          }
        });
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    el.searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      renderDocList();
    });

    el.catBar.addEventListener('click', (e) => {
      if (e.target.classList.contains('cat-pill')) {
        document.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');
        activeCat = e.target.dataset.cat;
        renderDocList();
      }
    });

    el.btnRendered.addEventListener('click', () => { isRawMode = false; updateViewMode(); });
    el.btnRaw.addEventListener('click', () => { isRawMode = true; updateViewMode(); });
    el.btnRefresh.addEventListener('click', refreshVault);

    renderDocList();
    if (allNotes.length > 0) {
      selectNote(allNotes[0].id);
    }
  </script>
</body>
</html>
