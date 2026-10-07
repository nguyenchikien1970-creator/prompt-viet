/**
 * PROMPT VIỆT – Client-Side Search & Web Application Engine
 * Zero backend, instant Vietnamese full-text search across 2,479 prompts.
 */

// Bulletproof Vietnamese Accent & Unicode Normalizer (NFC, NFD & Mac keyboards)
function removeAccents(text) {
  if (!text) return '';
  return String(text)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/gi, 'd')
    .toLowerCase();
}

function tokenize(text) {
  if (!text) return [];
  const clean = removeAccents(text);
  const matches = clean.match(/[a-z0-9]+/g);
  return matches || [];
}

// App State
const state = {
  allCards: [],
  fullPromptsMap: new Map(), // lazy loaded on demand
  searchIndex: null,
  filteredCards: [],
  searchQuery: '',
  selectedCategory: '',
  selectedSubcategory: '',
  selectedModelType: '',
  selectedDifficulty: '',
  selectedTag: '',
  pageSize: 24,
  currentPage: 1,
  activePrompt: null
};

// DOM Elements
const elements = {};

function initElements() {
  elements.searchInput = document.getElementById('searchInput');
  elements.clearSearchBtn = document.getElementById('clearSearchBtn');
  elements.searchStats = document.getElementById('searchStats');
  elements.categorySelect = document.getElementById('categorySelect');
  elements.subcategorySelect = document.getElementById('subcategorySelect');
  elements.modelTypeSelect = document.getElementById('modelTypeSelect');
  elements.difficultySelect = document.getElementById('difficultySelect');
  elements.resetFiltersBtn = document.getElementById('resetFiltersBtn');
  elements.promptsGrid = document.getElementById('promptsGrid');
  elements.loadMoreContainer = document.getElementById('loadMoreContainer');
  elements.loadMoreBtn = document.getElementById('loadMoreBtn');
  elements.detailModal = document.getElementById('detailModal');
  elements.modalBackdrop = document.getElementById('modalBackdrop');
  elements.closeModalBtn = document.getElementById('closeModalBtn');
  elements.modalTitle = document.getElementById('modalTitle');
  elements.modalCategory = document.getElementById('modalCategory');
  elements.modalDifficulty = document.getElementById('modalDifficulty');
  elements.modalModelType = document.getElementById('modalModelType');
  elements.modalTags = document.getElementById('modalTags');
  elements.modalPromptContent = document.getElementById('modalPromptContent');
  elements.modalCopyBtn = document.getElementById('modalCopyBtn');
  elements.toast = document.getElementById('toast');
  elements.toastMessage = document.getElementById('toastMessage');
  elements.quickTagsContainer = document.getElementById('quickTagsContainer');
  elements.totalPromptsCounter = document.getElementById('totalPromptsCounter');

  // Architecture & AI Directory Section Elements
  elements.tabAiIndexBtn = document.getElementById('tabAiIndexBtn');
  elements.tabArchitectureBtn = document.getElementById('tabArchitectureBtn');
  elements.toggleSectionBtn = document.getElementById('toggleSectionBtn');
  elements.toggleSectionIcon = document.getElementById('toggleSectionIcon');
  elements.architectureSectionContent = document.getElementById('architectureSectionContent');
  elements.aiIndexView = document.getElementById('aiIndexView');
  elements.architectureView = document.getElementById('architectureView');
}

// Initialize Application
async function initApp() {
  try {
    initElements();
    showSearchStats('Đang tải chỉ mục tìm kiếm và 2,479 prompt...', 'text-slate-400');
    
    // Load lightweight cards and search index in parallel
    const [cardsRes, indexRes] = await Promise.all([
      fetch('data/prompts_cards.json'),
      fetch('data/search_index.json')
    ]);

    if (!cardsRes.ok || !indexRes.ok) {
      throw new Error('Không thể tải tệp dữ liệu tìm kiếm.');
    }

    state.allCards = await cardsRes.json();
    state.searchIndex = await indexRes.json();

    // Pre-calculate normalized search string for instant 0ms full-text lookup
    state.allCards.forEach(card => {
      card._searchStr = removeAccents([
        card.vi_title || '',
        card.snippet || '',
        card.category || '',
        card.subcategory || '',
        (card.tags || []).join(' ')
      ].join(' '));
    });

    if (elements.totalPromptsCounter) {
      elements.totalPromptsCounter.textContent = state.allCards.length.toLocaleString();
    }

    // Populate Filters
    populateFilterDropdowns();
    populateQuickTags();

    // Check URL search parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('q')) {
      state.searchQuery = urlParams.get('q');
      if (elements.searchInput) elements.searchInput.value = state.searchQuery;
    }
    if (urlParams.has('cat')) {
      state.selectedCategory = urlParams.get('cat');
      if (elements.categorySelect) elements.categorySelect.value = state.selectedCategory;
      updateSubcategories();
    }
    if (urlParams.has('subcat')) {
      state.selectedSubcategory = urlParams.get('subcat');
      if (elements.subcategorySelect) elements.subcategorySelect.value = state.selectedSubcategory;
    }
    if (urlParams.has('tag')) {
      state.selectedTag = urlParams.get('tag');
    }

    setupEventListeners();
    applyFiltersAndSearch();
  } catch (error) {
    console.error('Lỗi khởi tạo:', error);
    showSearchStats(`Lỗi khởi tạo: ${error.message}. Vui lòng thử lại.`, 'text-red-400');
  }
}

// Populate Category & Subcategory Selects
function populateFilterDropdowns() {
  if (!state.searchIndex) return;

  // Categories: Aggregate case-insensitively with canonical display name
  const catMap = new Map();
  const rawCats = state.searchIndex.categories || {};
  Object.keys(rawCats).forEach(rawCat => {
    const key = rawCat.trim().toLowerCase();
    const count = rawCats[rawCat];
    if (catMap.has(key)) {
      const entry = catMap.get(key);
      entry.count += count;
      if (rawCat[0] === rawCat[0].toUpperCase() && entry.canonicalName[0] !== entry.canonicalName[0].toUpperCase()) {
        entry.canonicalName = rawCat;
      }
    } else {
      catMap.set(key, { canonicalName: rawCat, count });
    }
  });

  const sortedCats = Array.from(catMap.values()).sort((a, b) => b.count - a.count);
  if (elements.categorySelect) {
    elements.categorySelect.innerHTML = '<option value="">Tất cả danh mục (' + state.allCards.length.toLocaleString() + ')</option>';
    sortedCats.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.canonicalName;
      opt.textContent = `${item.canonicalName} (${item.count})`;
      elements.categorySelect.appendChild(opt);
    });
  }

  // Model Types: Aggregate case-insensitively
  const modelMap = new Map();
  const rawModels = state.searchIndex.model_types || {};
  Object.keys(rawModels).forEach(rawM => {
    const key = rawM.trim().toLowerCase();
    const count = rawModels[rawM];
    modelMap.set(key, (modelMap.get(key) || 0) + count);
  });
  if (elements.modelTypeSelect) {
    elements.modelTypeSelect.innerHTML = '<option value="">Tất cả loại model</option>';
    Array.from(modelMap.entries())
      .sort((a, b) => b[1] - a[1])
      .forEach(([m, count]) => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = `${m.toUpperCase()} (${count})`;
        elements.modelTypeSelect.appendChild(opt);
      });
  }

  // Difficulties: Aggregate case-insensitively
  const diffMap = new Map();
  const rawDiffs = state.searchIndex.difficulties || {};
  Object.keys(rawDiffs).forEach(rawD => {
    const key = rawD.trim().toLowerCase();
    const count = rawDiffs[rawD];
    diffMap.set(key, (diffMap.get(key) || 0) + count);
  });
  if (elements.difficultySelect) {
    elements.difficultySelect.innerHTML = '<option value="">Tất cả độ khó</option>';
    Array.from(diffMap.entries())
      .sort((a, b) => b[1] - a[1])
      .forEach(([d, count]) => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = `${d.charAt(0).toUpperCase() + d.slice(1)} (${count})`;
        elements.difficultySelect.appendChild(opt);
      });
  }
}

function updateSubcategories() {
  if (!elements.categorySelect || !elements.subcategorySelect) return;
  const selectedCat = (elements.categorySelect.value || '').trim().toLowerCase();
  elements.subcategorySelect.innerHTML = '<option value="">Tất cả danh mục con</option>';
  
  if (!selectedCat || !state.searchIndex || !state.searchIndex.subcategories) {
    elements.subcategorySelect.disabled = true;
    return;
  }

  const subcatSet = new Set();
  Object.keys(state.searchIndex.subcategories).forEach(catKey => {
    if (catKey.trim().toLowerCase() === selectedCat) {
      (state.searchIndex.subcategories[catKey] || []).forEach(sub => {
        if (sub && sub.trim()) subcatSet.add(sub.trim());
      });
    }
  });

  if (subcatSet.size === 0) {
    elements.subcategorySelect.disabled = true;
    return;
  }

  elements.subcategorySelect.disabled = false;
  Array.from(subcatSet).sort().forEach(sub => {
    const opt = document.createElement('option');
    opt.value = sub;
    opt.textContent = sub;
    elements.subcategorySelect.appendChild(opt);
  });
}

// Populate Quick Search Tags
function populateQuickTags() {
  if (!state.searchIndex || !elements.quickTagsContainer) return;
  const tags = state.searchIndex.top_tags ? state.searchIndex.top_tags.slice(0, 12) : [];
  elements.quickTagsContainer.innerHTML = '';
  
  tags.forEach(tag => {
    const btn = document.createElement('button');
    btn.className = 'px-3 py-1 text-xs rounded-full bg-slate-800 text-slate-300 hover:bg-indigo-900/60 hover:text-indigo-200 border border-slate-700/60 transition';
    btn.textContent = '#' + tag;
    btn.addEventListener('click', () => {
      state.searchQuery = tag;
      elements.searchInput.value = tag;
      applyFiltersAndSearch();
    });
    elements.quickTagsContainer.appendChild(btn);
  });
}

// Search and Filter Logic
function applyFiltersAndSearch() {
  const startTime = performance.now();
  const query = state.searchQuery.trim();
  const queryClean = removeAccents(query);
  const qTokens = queryClean.split(/\s+/).filter(Boolean);

  let candidates = state.allCards;

  // 1. Instant Multi-Strategy Search if query exists
  if (qTokens.length > 0) {
    const scores = new Map();
    const inv = (state.searchIndex && state.searchIndex.inverted_index) ? state.searchIndex.inverted_index : null;

    // A. Inverted Index token match
    if (inv) {
      qTokens.forEach(token => {
        const postings = inv[token] || [];
        postings.forEach(([docIdx, weight]) => {
          scores.set(docIdx, (scores.get(docIdx) || 0) + weight);
        });
      });
    }

    // B. Substring & Prefix matching across all fields (handles partial words, prefixes, Vietnamese phrases)
    state.allCards.forEach((card, docIdx) => {
      const searchStr = card._searchStr || '';
      const titleClean = removeAccents(card.vi_title || '');

      const allTokensMatch = qTokens.every(tok => searchStr.includes(tok));
      if (allTokensMatch) {
        let boost = (scores.get(docIdx) || 0) + 20;
        // Exact phrase bonus in title
        if (titleClean.includes(queryClean)) boost += 50;
        // Starts with bonus
        if (titleClean.startsWith(queryClean)) boost += 30;
        scores.set(docIdx, boost);
      }
    });

    if (scores.size > 0) {
      candidates = Array.from(scores.entries())
        .sort((a, b) => b[1] - a[1])
        .map(([docIdx]) => state.allCards[docIdx])
        .filter(Boolean);
    } else {
      candidates = [];
    }
  }

  // 2. Multi-dimensional Filtering
  const filtered = candidates.filter(card => {
    // Category (case-insensitive & trimmed)
    if (state.selectedCategory) {
      const cardCat = String(card.category || '').trim().toLowerCase();
      const selCat = state.selectedCategory.trim().toLowerCase();
      if (cardCat !== selCat) return false;
    }
    // Subcategory (case-insensitive & trimmed)
    if (state.selectedSubcategory) {
      const cardSub = String(card.subcategory || '').trim().toLowerCase();
      const selSub = state.selectedSubcategory.trim().toLowerCase();
      if (cardSub !== selSub) return false;
    }
    // Model Type (array or string)
    if (state.selectedModelType) {
      const targetM = state.selectedModelType.trim().toLowerCase();
      const rawM = card.model_type;
      const mList = Array.isArray(rawM) 
        ? rawM.map(m => String(m).trim().toLowerCase()) 
        : [String(rawM || '').trim().toLowerCase()];
      if (!mList.includes(targetM)) return false;
    }
    // Difficulty
    if (state.selectedDifficulty) {
      const cardDiff = String(card.difficulty || '').trim().toLowerCase();
      const selDiff = state.selectedDifficulty.trim().toLowerCase();
      if (cardDiff !== selDiff) return false;
    }
    // Tag filter
    if (state.selectedTag) {
      const targetTag = state.selectedTag.trim().toLowerCase();
      const tags = (card.tags || []).map(t => String(t).trim().toLowerCase());
      if (!tags.includes(targetTag)) return false;
    }
    return true;
  });

  const duration = (performance.now() - startTime).toFixed(1);
  state.filteredCards = filtered;
  state.currentPage = 1;

  // Update Stats UI
  const total = filtered.length;
  showSearchStats(`Tìm thấy ${total.toLocaleString()} prompt (${duration} ms)`, total > 0 ? 'text-indigo-400' : 'text-amber-400');

  // Render
  renderPromptsGrid();
}

function showSearchStats(message, colorClass = 'text-slate-400') {
  if (elements.searchStats) {
    elements.searchStats.className = `text-sm font-medium ${colorClass}`;
    elements.searchStats.textContent = message;
  }
}

// Render Results Grid
function renderPromptsGrid() {
  const container = elements.promptsGrid;
  if (!container) return;

  const total = state.filteredCards.length;
  const itemsToShow = state.filteredCards.slice(0, state.currentPage * state.pageSize);

  if (total === 0) {
    container.innerHTML = `
      <div class="col-span-full py-16 text-center text-slate-400">
        <div class="text-4xl mb-3">🔍</div>
        <h3 class="text-lg font-semibold text-slate-200">Không tìm thấy prompt phù hợp</h3>
        <p class="text-sm mt-1 text-slate-400">Thử tìm kiếm với từ khóa khác hoặc đặt lại bộ lọc.</p>
        <button id="resetFromEmptyBtn" class="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition font-medium">Đặt lại bộ lọc</button>
      </div>
    `;
    const btn = document.getElementById('resetFromEmptyBtn');
    if (btn) btn.addEventListener('click', resetAllFilters);
    if (elements.loadMoreContainer) elements.loadMoreContainer.classList.add('hidden');
    return;
  }

  let html = '';
  itemsToShow.forEach(card => {
    const diffClass = getDifficultyBadgeClass(card.difficulty);
    const tagsHtml = (card.tags || []).slice(0, 3).map(t => 
      `<span class="tag-pill text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/50 hover:border-indigo-500 cursor-pointer" data-tag="${escapeHtml(t)}">#${escapeHtml(t)}</span>`
    ).join(' ');

    const modelDisplay = Array.isArray(card.model_type) 
      ? card.model_type.join(', ') 
      : String(card.model_type || 'text');

    html += `
      <div class="glass-card rounded-xl p-5 flex flex-col justify-between animate-fade-in group">
        <div>
          <div class="flex items-center justify-between gap-2 mb-3">
            <span class="text-xs px-2.5 py-0.5 rounded-full font-medium ${diffClass}">${escapeHtml(card.difficulty || 'Mặc định')}</span>
            <span class="text-xs font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">${escapeHtml(modelDisplay)}</span>
          </div>

          <h3 class="text-base font-bold text-slate-100 group-hover:text-indigo-400 transition line-clamp-2 mb-2 cursor-pointer card-title-link" data-id="${card.id}">
            ${escapeHtml(card.vi_title)}
          </h3>

          <p class="text-xs text-slate-400 mb-3 font-medium">
            <span class="text-indigo-300">${escapeHtml(card.category || 'Chung')}</span>
            ${card.subcategory ? `<span class="text-slate-500"> › </span><span class="text-slate-400">${escapeHtml(card.subcategory)}</span>` : ''}
          </p>

          <p class="text-xs text-slate-300/80 line-clamp-3 mb-4 leading-relaxed bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/80 font-mono">
            ${escapeHtml(card.snippet)}
          </p>
        </div>

        <div>
          <div class="flex flex-wrap gap-1 mb-4">
            ${tagsHtml}
          </div>

          <div class="flex items-center gap-2 pt-3 border-t border-slate-800/80">
            <button class="view-detail-btn flex-1 py-1.5 px-3 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition text-center" data-id="${card.id}">
              Xem chi tiết
            </button>
            <button class="quick-copy-btn p-2 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 transition flex items-center justify-center" data-id="${card.id}" title="Sao chép Prompt">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="pointer-events-none"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;

  // Toggle Load More Button
  if (elements.loadMoreContainer) {
    if (itemsToShow.length < total) {
      elements.loadMoreContainer.classList.remove('hidden');
      elements.loadMoreBtn.textContent = `Tải thêm prompt (${total - itemsToShow.length} còn lại)`;
    } else {
      elements.loadMoreContainer.classList.add('hidden');
    }
  }
}

function getDifficultyBadgeClass(diff) {
  const d = String(diff).toLowerCase();
  if (d.includes('beginner') || d.includes('cơ bản') || d.includes('dễ') || d.includes('easy')) return 'badge-beginner';
  if (d.includes('intermediate') || d.includes('trung bình') || d.includes('medium')) return 'badge-intermediate';
  if (d.includes('advanced') || d.includes('nâng cao') || d.includes('hard')) return 'badge-advanced';
  return 'badge-hard';
}

// Modal Handlers
async function openDetailModal(promptId) {
  const card = state.allCards.find(c => c.id === promptId);
  if (!card) return;

  state.activePrompt = card;
  if (elements.modalTitle) elements.modalTitle.textContent = card.vi_title;
  if (elements.modalCategory) elements.modalCategory.textContent = `${card.category || ''} ${card.subcategory ? '› ' + card.subcategory : ''}`;
  if (elements.modalDifficulty) {
    elements.modalDifficulty.textContent = card.difficulty || 'Mặc định';
    elements.modalDifficulty.className = `text-xs px-2.5 py-0.5 rounded-full font-medium ${getDifficultyBadgeClass(card.difficulty)}`;
  }
  
  // Safe Model Type string conversion (handles array or string)
  if (elements.modalModelType) {
    const modelTypeStr = Array.isArray(card.model_type) 
      ? card.model_type.join(', ') 
      : String(card.model_type || 'text');
    elements.modalModelType.textContent = modelTypeStr.toUpperCase();
  }

  // Tags in modal
  if (elements.modalTags) {
    elements.modalTags.innerHTML = (card.tags || []).map(t => 
      `<span class="text-xs px-2.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">#${escapeHtml(t)}</span>`
    ).join(' ');
  }

  // Immediately show modal (< 1ms)
  if (elements.detailModal) {
    elements.detailModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  // Load full prompt
  let fullPrompt = state.fullPromptsMap.get(promptId);
  if (fullPrompt) {
    if (elements.modalPromptContent) elements.modalPromptContent.textContent = fullPrompt;
  } else {
    // Show snippet preview immediately while full prompt is fetched
    if (elements.modalPromptContent) {
      elements.modalPromptContent.textContent = card.snippet || 'Đang tải nội dung câu lệnh đầy đủ...';
    }
    try {
      if (state.fullPromptsMap.size === 0) {
        const res = await fetch('data/prompts_search.json');
        if (res.ok) {
          const fullData = await res.json();
          fullData.forEach(p => state.fullPromptsMap.set(p.id, p.vi_prompt));
        }
      }
      if (state.activePrompt && state.activePrompt.id === promptId && elements.modalPromptContent) {
        elements.modalPromptContent.textContent = state.fullPromptsMap.get(promptId) || card.snippet;
      }
    } catch (err) {
      console.warn('Could not load full prompt:', err);
      if (state.activePrompt && state.activePrompt.id === promptId && elements.modalPromptContent) {
        elements.modalPromptContent.textContent = card.snippet;
      }
    }
  }
}

function closeDetailModal() {
  if (elements.detailModal) elements.detailModal.classList.add('hidden');
  document.body.style.overflow = '';
  state.activePrompt = null;
}

// Copy Action
async function copyPromptById(promptId) {
  let textToCopy = state.fullPromptsMap.get(promptId);
  if (!textToCopy) {
    const card = state.allCards.find(c => c.id === promptId);
    if (card) {
      try {
        if (state.fullPromptsMap.size === 0) {
          const res = await fetch('data/prompts_search.json');
          if (res.ok) {
            const fullData = await res.json();
            fullData.forEach(p => state.fullPromptsMap.set(p.id, p.vi_prompt));
          }
        }
        textToCopy = state.fullPromptsMap.get(promptId) || card.snippet;
      } catch (err) {
        textToCopy = card.snippet;
      }
    }
  }

  if (textToCopy) {
    copyToClipboard(textToCopy);
  }
}

function copyToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Đã sao chép prompt vào bộ nhớ tạm!');
    }).catch(() => {
      fallbackCopy(text);
    });
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.opacity = '0';
  document.body.appendChild(textArea);
  textArea.select();
  try {
    document.execCommand('copy');
    showToast('Đã sao chép prompt vào bộ nhớ tạm!');
  } catch (err) {
    showToast('Không thể tự động sao chép. Vui lòng copy thủ công.');
  }
  document.body.removeChild(textArea);
}

function showToast(message) {
  if (!elements.toast || !elements.toastMessage) return;
  elements.toastMessage.textContent = message;
  elements.toast.classList.remove('opacity-0', 'translate-y-4', 'pointer-events-none');
  elements.toast.classList.add('opacity-100', 'translate-y-0');

  setTimeout(() => {
    if (elements.toast) {
      elements.toast.classList.remove('opacity-100', 'translate-y-0');
      elements.toast.classList.add('opacity-0', 'translate-y-4', 'pointer-events-none');
    }
  }, 2500);
}

// Event Listeners
function setupEventListeners() {
  // 1. Search input debounce & instant execution
  let debounceTimer;
  if (elements.searchInput) {
    const handleSearchInput = (val) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        state.searchQuery = val || '';
        if (elements.clearSearchBtn) {
          elements.clearSearchBtn.classList.toggle('hidden', state.searchQuery.length === 0);
        }
        applyFiltersAndSearch();
      }, 60);
    };

    elements.searchInput.addEventListener('input', (e) => {
      handleSearchInput(e.target.value);
    });

    elements.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        clearTimeout(debounceTimer);
        state.searchQuery = e.target.value || '';
        if (elements.clearSearchBtn) {
          elements.clearSearchBtn.classList.toggle('hidden', state.searchQuery.length === 0);
        }
        applyFiltersAndSearch();
        elements.searchInput.blur();
      }
    });

    elements.searchInput.addEventListener('search', (e) => {
      handleSearchInput(e.target.value);
    });
  }

  if (elements.clearSearchBtn) {
    elements.clearSearchBtn.addEventListener('click', () => {
      if (elements.searchInput) elements.searchInput.value = '';
      state.searchQuery = '';
      elements.clearSearchBtn.classList.add('hidden');
      applyFiltersAndSearch();
      if (elements.searchInput) elements.searchInput.focus();
    });
  }

  // 2. Filter Changes (support both change and input events)
  const onCategoryChange = (e) => {
    state.selectedCategory = e.target.value;
    state.selectedSubcategory = '';
    updateSubcategories();
    applyFiltersAndSearch();
  };
  if (elements.categorySelect) {
    elements.categorySelect.addEventListener('change', onCategoryChange);
  }

  const onSubcategoryChange = (e) => {
    state.selectedSubcategory = e.target.value;
    applyFiltersAndSearch();
  };
  if (elements.subcategorySelect) {
    elements.subcategorySelect.addEventListener('change', onSubcategoryChange);
  }

  const onModelTypeChange = (e) => {
    state.selectedModelType = e.target.value;
    applyFiltersAndSearch();
  };
  if (elements.modelTypeSelect) {
    elements.modelTypeSelect.addEventListener('change', onModelTypeChange);
  }

  const onDifficultyChange = (e) => {
    state.selectedDifficulty = e.target.value;
    applyFiltersAndSearch();
  };
  if (elements.difficultySelect) {
    elements.difficultySelect.addEventListener('change', onDifficultyChange);
  }

  if (elements.resetFiltersBtn) {
    elements.resetFiltersBtn.addEventListener('click', resetAllFilters);
  }

  // 3. Load More
  if (elements.loadMoreBtn) {
    elements.loadMoreBtn.addEventListener('click', () => {
      state.currentPage += 1;
      renderPromptsGrid();
    });
  }

  // 4. Prompts Grid Event Delegation (Detail, Copy, Tag clicks)
  if (elements.promptsGrid) {
    elements.promptsGrid.addEventListener('click', (e) => {
      // Copy Button
      const copyBtn = e.target.closest('.quick-copy-btn');
      if (copyBtn) {
        e.preventDefault();
        e.stopPropagation();
        const id = copyBtn.dataset.id;
        if (id) copyPromptById(id);
        return;
      }

      // Tag Pill
      const tagPill = e.target.closest('.tag-pill');
      if (tagPill) {
        e.preventDefault();
        e.stopPropagation();
        const tag = tagPill.dataset.tag;
        if (tag) {
          state.selectedTag = tag;
          applyFiltersAndSearch();
        }
        return;
      }

      // View Detail Button or Title Link
      const detailTarget = e.target.closest('.view-detail-btn, .card-title-link');
      if (detailTarget) {
        e.preventDefault();
        const id = detailTarget.dataset.id;
        if (id) openDetailModal(id);
        return;
      }
    });
  }

  // 5. Modal events
  if (elements.closeModalBtn) elements.closeModalBtn.addEventListener('click', closeDetailModal);
  if (elements.modalBackdrop) elements.modalBackdrop.addEventListener('click', closeDetailModal);
  if (elements.modalCopyBtn) {
    elements.modalCopyBtn.addEventListener('click', () => {
      if (state.activePrompt) {
        copyPromptById(state.activePrompt.id);
      }
    });
  }

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elements.detailModal && !elements.detailModal.classList.contains('hidden')) {
      closeDetailModal();
    }
  });

  // 6. Architecture & AI Directory Tabs & Interaction
  if (elements.tabAiIndexBtn && elements.tabArchitectureBtn) {
    elements.tabAiIndexBtn.addEventListener('click', () => {
      // Show AI Index, hide Architecture
      if (elements.aiIndexView) elements.aiIndexView.classList.remove('hidden');
      if (elements.architectureView) elements.architectureView.classList.add('hidden');
      
      // Update Tab Styles
      elements.tabAiIndexBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 bg-indigo-600 text-white shadow-md shadow-indigo-600/30';
      elements.tabArchitectureBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200';
    });

    elements.tabArchitectureBtn.addEventListener('click', () => {
      // Show Architecture, hide AI Index
      if (elements.architectureView) elements.architectureView.classList.remove('hidden');
      if (elements.aiIndexView) elements.aiIndexView.classList.add('hidden');

      // Update Tab Styles
      elements.tabArchitectureBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 bg-indigo-600 text-white shadow-md shadow-indigo-600/30';
      elements.tabAiIndexBtn.className = 'px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200';
    });
  }

  // Toggle Collapse / Expand
  if (elements.toggleSectionBtn && elements.architectureSectionContent) {
    let isCollapsed = false;
    elements.toggleSectionBtn.addEventListener('click', () => {
      isCollapsed = !isCollapsed;
      if (isCollapsed) {
        elements.architectureSectionContent.classList.add('hidden');
        if (elements.toggleSectionIcon) elements.toggleSectionIcon.style.transform = 'rotate(180deg)';
      } else {
        elements.architectureSectionContent.classList.remove('hidden');
        if (elements.toggleSectionIcon) elements.toggleSectionIcon.style.transform = 'rotate(0deg)';
      }
    });
  }

  // Topic Explore Buttons
  document.querySelectorAll('.ai-topic-explore-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const cat = btn.dataset.cat;
      const search = btn.dataset.search;

      if (cat) {
        // Clear search query so category results are not restricted
        state.searchQuery = '';
        if (elements.searchInput) elements.searchInput.value = '';
        if (elements.clearSearchBtn) elements.clearSearchBtn.classList.add('hidden');

        // Select category
        state.selectedCategory = cat;
        if (elements.categorySelect) {
          const catLower = cat.toLowerCase();
          for (let opt of elements.categorySelect.options) {
            if (opt.value && opt.value.toLowerCase().includes(catLower)) {
              elements.categorySelect.value = opt.value;
              state.selectedCategory = opt.value;
              break;
            }
          }
        }
        updateSubcategories();
      } else if (search) {
        // Clear category filter so search covers all items
        state.selectedCategory = '';
        state.selectedSubcategory = '';
        if (elements.categorySelect) elements.categorySelect.value = '';
        if (elements.subcategorySelect) {
          elements.subcategorySelect.value = '';
          elements.subcategorySelect.disabled = true;
        }

        state.searchQuery = search;
        if (elements.searchInput) elements.searchInput.value = search;
        if (elements.clearSearchBtn) elements.clearSearchBtn.classList.remove('hidden');
      }

      applyFiltersAndSearch();

      // Smooth scroll to prompts results
      const grid = document.getElementById('promptsGrid');
      if (grid) {
        grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Topic Tags
  document.querySelectorAll('.ai-topic-tag').forEach(tagBtn => {
    tagBtn.addEventListener('click', () => {
      const tag = tagBtn.dataset.tag;
      if (tag) {
        // Reset category filter to allow global search
        state.selectedCategory = '';
        state.selectedSubcategory = '';
        if (elements.categorySelect) elements.categorySelect.value = '';
        if (elements.subcategorySelect) {
          elements.subcategorySelect.value = '';
          elements.subcategorySelect.disabled = true;
        }

        state.searchQuery = tag;
        if (elements.searchInput) elements.searchInput.value = tag;
        if (elements.clearSearchBtn) elements.clearSearchBtn.classList.remove('hidden');
        
        applyFiltersAndSearch();
        const grid = document.getElementById('promptsGrid');
        if (grid) {
          grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });
}

function resetAllFilters() {
  state.searchQuery = '';
  state.selectedCategory = '';
  state.selectedSubcategory = '';
  state.selectedModelType = '';
  state.selectedDifficulty = '';
  state.selectedTag = '';
  state.currentPage = 1;

  if (elements.searchInput) elements.searchInput.value = '';
  if (elements.categorySelect) elements.categorySelect.value = '';
  if (elements.subcategorySelect) {
    elements.subcategorySelect.value = '';
    elements.subcategorySelect.disabled = true;
  }
  if (elements.modelTypeSelect) elements.modelTypeSelect.value = '';
  if (elements.difficultySelect) elements.difficultySelect.value = '';
  if (elements.clearSearchBtn) elements.clearSearchBtn.classList.add('hidden');

  applyFiltersAndSearch();
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Run App on Load (resilient to readyState)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
