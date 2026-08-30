/**
 * UnaniMed AI — Frontend Application Logic
 * Full Multimodal Voice, Vision, Lead Capture & Telegram Integration
 */

// ── State Management ─────────────────────────────────────────────────────────
const state = {
  currentView: 'chat',
  chatHistory: [],
  selectedImageBase64: null,
  selectedImageName: null,
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  audioContext: null,
  analyser: null,
  animationFrameId: null,
  recStartTime: null,
  recTimerInterval: null,
  allHerbs: [],
  allLeads: [],
  currentSelectedHerb: null
};

// ── DOM References ───────────────────────────────────────────────────────────
const elements = {
  chatContainer: document.getElementById('chat-container'),
  userTextInput: document.getElementById('user-text-input'),
  btnSend: document.getElementById('btn-send-message'),
  btnVoice: document.getElementById('btn-voice-record'),
  voiceIcon: document.getElementById('voice-icon'),
  recordingBar: document.getElementById('recording-bar'),
  recTimer: document.getElementById('rec-timer'),
  waveformCanvas: document.getElementById('audio-waveform-canvas'),
  imagePreviewContainer: document.getElementById('image-preview-container'),
  previewImageElem: document.getElementById('preview-image-elem'),
  previewFilename: document.getElementById('preview-filename'),
  imageFileInput: document.getElementById('image-file-input'),
  modalitySelect: document.getElementById('modality-select'),
  languageSelect: document.getElementById('language-select'),
  leadDetectedBanner: document.getElementById('lead-detected-banner'),
  leadBannerText: document.getElementById('lead-banner-text'),
  leadsCountBadge: document.getElementById('leads-count-badge'),
  herbsGrid: document.getElementById('herbs-grid-container'),
  leadsTableBody: document.getElementById('leads-tbody'),
  audioPlayer: document.getElementById('tts-audio-player'),
  orderModal: document.getElementById('order-modal'),
  herbDetailModal: document.getElementById('herb-detail-modal'),
  toastContainer: document.getElementById('toast-container')
};

// ── Initialization ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  // Set current time for intro card
  const introTimeElem = document.getElementById('intro-time');
  if (introTimeElem) {
    const now = new Date();
    introTimeElem.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Load initial data
  await loadHerbsCatalog();
  await loadLeadsFromDB();
  await checkSystemStatus();

  // Setup drag and drop for images
  setupDragAndDrop();
}

// ── View Navigation ──────────────────────────────────────────────────────────
function switchView(viewName) {
  state.currentView = viewName;
  
  // Update nav tabs
  document.querySelectorAll('.nav-tab').forEach(tab => tab.classList.remove('active'));
  const activeTab = document.getElementById(`tab-${viewName}`);
  if (activeTab) activeTab.classList.add('active');

  // Update view sections
  document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
  const activeSection = document.getElementById(`view-${viewName}`);
  if (activeSection) activeSection.classList.add('active');

  // Specific view refresh
  if (viewName === 'leads') {
    loadLeadsFromDB();
  } else if (viewName === 'status') {
    checkSystemStatus();
  }
}

// ── Quick Prompt Helper ──────────────────────────────────────────────────────
function sendQuickPrompt(promptText) {
  elements.userTextInput.value = promptText;
  handleSendMessage();
}

// ── Textarea Auto Resize ─────────────────────────────────────────────────────
function autoResizeTextarea(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function handleInputKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    handleSendMessage();
  }
}

// ── Image Attachment Handling ────────────────────────────────────────────────
function triggerImageUpload() {
  elements.imageFileInput.click();
}

function handleImageSelected(event) {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    state.selectedImageBase64 = e.target.result;
    state.selectedImageName = file.name;

    elements.previewImageElem.src = e.target.result;
    elements.previewFilename.textContent = file.name;
    elements.imagePreviewContainer.classList.remove('hidden');
    showToast(`ছবি সংযুক্ত করা হয়েছে: ${file.name}`, 'success');
  };
  reader.readAsDataURL(file);
}

function clearSelectedImage() {
  state.selectedImageBase64 = null;
  state.selectedImageName = null;
  elements.imageFileInput.value = '';
  elements.imagePreviewContainer.classList.add('hidden');
}

function setupDragAndDrop() {
  window.addEventListener('dragover', (e) => e.preventDefault());
  window.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          state.selectedImageBase64 = ev.target.result;
          state.selectedImageName = file.name;
          elements.previewImageElem.src = ev.target.result;
          elements.previewFilename.textContent = file.name;
          elements.imagePreviewContainer.classList.remove('hidden');
          showToast(`ছবি ড্রপ করা হয়েছে: ${file.name}`, 'success');
        };
        reader.readAsDataURL(file);
      }
    }
  });
}

// ── Voice Recording & Live Waveform ──────────────────────────────────────────
async function toggleVoiceRecording() {
  if (state.isRecording) {
    stopAndSendVoiceRecording();
  } else {
    startVoiceRecording();
  }
}

// ── Voice Recording & Live Waveform with Speech Recognition ──────────────────
let recognitionInstance = null;
let recognizedLiveText = "";

async function toggleVoiceRecording() {
  if (state.isRecording) {
    stopAndSendVoiceRecording();
  } else {
    startVoiceRecording();
  }
}

async function startVoiceRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    state.isRecording = true;
    state.audioChunks = [];
    recognizedLiveText = "";

    // Visual elements
    elements.btnVoice.classList.add('recording');
    elements.voiceIcon.className = 'fa-solid fa-stop';
    elements.recordingBar.classList.remove('hidden');

    // Timer setup
    state.recStartTime = Date.now();
    elements.recTimer.textContent = '00:00';
    state.recTimerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.recStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const secs = String(elapsed % 60).padStart(2, '0');
      elements.recTimer.textContent = `${mins}:${secs}`;
    }, 1000);

    // Audio context & Waveform setup
    state.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = state.audioContext.createMediaStreamSource(stream);
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 64;
    source.connect(state.analyser);
    drawWaveform();

    // MediaRecorder setup
    state.mediaRecorder = new MediaRecorder(stream);
    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) state.audioChunks.push(e.data);
    };
    state.mediaRecorder.start(100);

    // Browser Live Speech Recognition (Bilingual Bengali & English)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        recognitionInstance = new SpeechRecognition();
        recognitionInstance.lang = elements.languageSelect.value === 'en' ? 'en-US' : 'bn-BD';
        recognitionInstance.continuous = true;
        recognitionInstance.interimResults = true;

        recognitionInstance.onresult = (event) => {
          let interimText = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              recognizedLiveText += event.results[i][0].transcript + ' ';
            } else {
              interimText += event.results[i][0].transcript;
            }
          }
          const currentText = (recognizedLiveText + interimText).trim();
          if (currentText) {
            elements.userTextInput.value = currentText;
            autoResizeTextarea(elements.userTextInput);
          }
        };

        recognitionInstance.onerror = (e) => {
          console.log('Speech recognition event:', e.error);
        };

        recognitionInstance.start();
      } catch (e) {
        console.log('Speech recognition init error:', e);
      }
    }

  } catch (err) {
    console.error('Microphone access error:', err);
    showToast('মাইক্রোফোন চালু করা যায়নি। ব্রাউজার পারমিশন চেক করুন।', 'error');
    cancelVoiceRecording();
  }
}

function drawWaveform() {
  if (!state.isRecording || !state.analyser) return;

  const canvas = elements.waveformCanvas;
  const ctx = canvas.getContext('2d');
  const bufferLength = state.analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  state.analyser.getByteFrequencyData(dataArray);

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const barWidth = (canvas.width / bufferLength) * 1.5;
  let barHeight;
  let x = 0;

  for (let i = 0; i < bufferLength; i++) {
    barHeight = (dataArray[i] / 255) * canvas.height;
    
    // Gradient bar color
    const grad = ctx.createLinearGradient(0, canvas.height, 0, 0);
    grad.addColorStop(0, '#10b981');
    grad.addColorStop(1, '#34d399');

    ctx.fillStyle = grad;
    ctx.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);

    x += barWidth;
  }

  state.animationFrameId = requestAnimationFrame(drawWaveform);
}

function stopAndSendVoiceRecording() {
  if (!state.isRecording || !state.mediaRecorder) return;

  if (recognitionInstance) {
    try { recognitionInstance.stop(); } catch (e) {}
  }

  state.mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
    const reader = new FileReader();
    reader.onloadend = async () => {
      const audioBase64 = reader.result;
      const finalText = elements.userTextInput.value.trim() || recognizedLiveText.trim();
      elements.userTextInput.value = '';
      autoResizeTextarea(elements.userTextInput);
      cleanupRecordingUI();
      // Send message with recognized text and audio
      await executeSendMessage({ text: finalText, audio_base64: audioBase64 });
    };
    reader.readAsDataURL(audioBlob);
  };

  state.mediaRecorder.stop();
  state.mediaRecorder.stream.getTracks().forEach(track => track.stop());
}

function cancelVoiceRecording() {
  if (recognitionInstance) {
    try { recognitionInstance.stop(); } catch (e) {}
  }
  if (state.mediaRecorder) {
    try {
      state.mediaRecorder.stop();
      state.mediaRecorder.stream.getTracks().forEach(track => track.stop());
    } catch (e) {}
  }
  cleanupRecordingUI();
  showToast('ভয়েস রেকর্ডিং বাতিল করা হয়েছে', 'info');
}

function cleanupRecordingUI() {
  state.isRecording = false;
  clearInterval(state.recTimerInterval);
  if (state.animationFrameId) cancelAnimationFrame(state.animationFrameId);
  if (state.audioContext) {
    state.audioContext.close().catch(() => {});
  }
  elements.btnVoice.classList.remove('recording');
  elements.voiceIcon.className = 'fa-solid fa-microphone';
  elements.recordingBar.classList.add('hidden');
}

// ── Send Message Orchestrator ────────────────────────────────────────────────
async function handleSendMessage() {
  const text = elements.userTextInput.value.trim();
  const imageBase64 = state.selectedImageBase64;

  if (!text && !imageBase64) {
    return;
  }

  // Clear text input and auto-shrink
  elements.userTextInput.value = '';
  autoResizeTextarea(elements.userTextInput);

  const payload = {
    text: text,
    image_base64: imageBase64
  };

  // Clear image preview
  clearSelectedImage();

  await executeSendMessage(payload);
}

async function executeSendMessage({ text = '', audio_base64 = null, image_base64 = null }) {
  // Render user message in UI immediately
  appendUserMessage({ text, audio_base64, image_base64 });

  // Render typing indicator
  const typingElem = appendTypingIndicator();

  try {
    const modality = elements.modalitySelect.value;
    const language = elements.languageSelect.value;

    const requestBody = {
      text: text,
      audio_base64: audio_base64,
      image_base64: image_base64,
      modality_preference: modality,
      language: language,
      sender_id: 'web-user-' + getSessionId(),
      channel: 'web',
      history: state.chatHistory.slice(-6)
    };

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    const data = await response.json();
    typingElem.remove();

    if (data.success) {
      appendBotMessage(data);

      // Handle Voice Audio Playback
      if (data.audio && data.audio.audio_base64) {
        playBase64Audio(data.audio.audio_base64, data.audio.format);
      } else if (data.audio && data.audio.use_browser_speech) {
        speakWithBrowserSpeech(data.audio.speech_text || data.text_response, language);
      }

      // Handle Lead Detected Toast & Banner
      if (data.lead_detected) {
        showLeadDetectedBanner();
        loadLeadsFromDB(); // refresh leads count & table
      }

      // Update local history
      state.chatHistory.push({ role: 'user', content: text || 'Voice/Image Message' });
      state.chatHistory.push({ role: 'assistant', content: data.text_response });

    } else {
      appendBotMessage({
        text_response: 'দুঃখিত, কোনো ত্রুটি হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।'
      });
    }

  } catch (error) {
    console.error('Chat API error:', error);
    typingElem.remove();
    appendBotMessage({
      text_response: '⚠️ সার্ভারের সাথে সংযোগ বিচ্ছিন্ন হয়েছে। লোকাল সার্ভিসগুলো চালু আছে কি না পরীক্ষা করুন।'
    });
  }
}

// ── Chat Rendering ───────────────────────────────────────────────────────────
function appendUserMessage({ text, audio_base64, image_base64 }) {
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const msgElem = document.createElement('div');
  msgElem.className = 'chat-message user-message';

  let contentHtml = '';
  if (image_base64) {
    contentHtml += `<div style="margin-bottom:8px;"><img src="${image_base64}" style="max-width:200px; border-radius:8px; border:1px solid rgba(255,255,255,0.2);"></div>`;
  }
  if (audio_base64) {
    contentHtml += `<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;"><i class="fa-solid fa-microphone-lines" style="color:#38bdf8;"></i> <em>ভয়েস বার্তা পাঠানো হয়েছে</em></div>`;
  }
  if (text) {
    contentHtml += `<div>${escapeHtml(text)}</div>`;
  }

  msgElem.innerHTML = `
    <div class="message-avatar">
      <i class="fa-solid fa-user"></i>
    </div>
    <div class="message-body">
      <div class="message-header" style="justify-content:flex-end;">
        <span class="message-time">${timeStr}</span>
        <span class="bot-name" style="color:#60a5fa;">আপনি</span>
      </div>
      <div class="message-text">
        ${contentHtml}
      </div>
    </div>
  `;

  elements.chatContainer.appendChild(msgElem);
  scrollToBottom();
}

function appendBotMessage(data) {
  const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const msgElem = document.createElement('div');
  msgElem.className = 'chat-message bot-message';

  let formattedText = formatMarkdown(data.text_response || '');

  // Herb Visual Cards HTML
  let herbCardsHtml = '';
  if (data.herb_cards && data.herb_cards.length > 0) {
    herbCardsHtml = '<div class="chat-herb-cards">';
    data.herb_cards.forEach(herb => {
      herbCardsHtml += `
        <div class="mini-herb-card" onclick="openHerbDetailModal('${herb.id}')">
          <img class="mini-herb-img" src="${herb.thumbnail || herb.image_url}" alt="${herb.name_bn}">
          <div class="mini-herb-info">
            <div class="mini-herb-title">${herb.name_bn} (${herb.name_en})</div>
            <div class="mini-herb-sub">${herb.botanical_name}</div>
            <span class="mini-herb-mizaj">মিজাজ: ${herb.mizaj}</span>
          </div>
        </div>
      `;
    });
    herbCardsHtml += '</div>';
  }

  // Audio Playback Bar in message
  let audioPlayerHtml = '';
  if (data.audio && data.audio.audio_base64) {
    audioPlayerHtml = `
      <div class="audio-player-card">
        <button class="btn-play-voice" onclick="playBase64Audio('${data.audio.audio_base64}', '${data.audio.format}')">
          <i class="fa-solid fa-play"></i>
        </button>
        <div class="audio-bars">
          <span class="audio-bar"></span>
          <span class="audio-bar"></span>
          <span class="audio-bar"></span>
          <span class="audio-bar"></span>
          <span class="audio-bar"></span>
        </div>
        <span style="font-size:0.85rem; color:#34d399; font-weight:500;">ভয়েস উত্তর শুনুন (Audio Reply)</span>
      </div>
    `;
  }

  msgElem.innerHTML = `
    <div class="message-avatar">
      <i class="fa-solid fa-user-doctor"></i>
    </div>
    <div class="message-body">
      <div class="message-header">
        <span class="bot-name">ইউনানী মেড এআই</span>
        <span class="ai-badge"><i class="fa-solid fa-microchip"></i> llama3.1:8b</span>
        <span class="message-time">${timeStr}</span>
      </div>
      <div class="message-text">
        ${formattedText}
        ${audioPlayerHtml}
        ${herbCardsHtml}
      </div>
    </div>
  `;

  elements.chatContainer.appendChild(msgElem);
  scrollToBottom();
}

function appendTypingIndicator() {
  const typingElem = document.createElement('div');
  typingElem.className = 'chat-message bot-message';
  typingElem.innerHTML = `
    <div class="message-avatar"><i class="fa-solid fa-user-doctor"></i></div>
    <div class="message-body">
      <div class="message-text" style="display:flex; align-items:center; gap:8px; padding:10px 16px;">
        <span class="audio-bar" style="height:14px;"></span>
        <span class="audio-bar" style="height:18px;"></span>
        <span class="audio-bar" style="height:12px;"></span>
        <span style="font-size:0.85rem; color:var(--text-muted); margin-left:4px;">ইউনানী পরামর্শ প্রস্তুত হচ্ছে...</span>
      </div>
    </div>
  `;
  elements.chatContainer.appendChild(typingElem);
  scrollToBottom();
  return typingElem;
}

function scrollToBottom() {
  elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

// ── Audio & Speech Synthesis ─────────────────────────────────────────────────
function playBase64Audio(base64Data, format = 'mp3') {
  try {
    const audioSrc = `data:audio/${format};base64,${base64Data}`;
    elements.audioPlayer.src = audioSrc;
    elements.audioPlayer.play().catch(e => console.log('Audio autoplay prevented:', e));
  } catch (e) {
    console.error('Audio play error:', e);
  }
}

function speakWithBrowserSpeech(text, lang = 'bn') {
  if (!('speechSynthesis' in window)) return;

  window.speechSynthesis.cancel(); // stop previous speech

  const cleanText = text.replace(/[*_#`~\[\]\(\)]/g, '').slice(0, 300);
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.lang = lang === 'en' ? 'en-US' : 'bn-BD';
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  window.speechSynthesis.speak(utterance);
}

// ── Official Medicines Visual Catalog ────────────────────────────────────────
async function loadHerbsCatalog() {
  try {
    const res = await fetch('/api/herbs');
    const data = await res.json();
    if (data.success && data.herbs) {
      state.allHerbs = data.herbs;
      renderHerbsGrid(state.allHerbs);
    }
  } catch (err) {
    console.error('Failed to load products:', err);
  }
}

function renderHerbsGrid(herbs) {
  elements.herbsGrid.innerHTML = '';
  herbs.forEach(herb => {
    const card = document.createElement('div');
    card.className = 'herb-card';
    
    let benefitsHtml = '';
    const benefits = herb.benefits_bn || [];
    benefits.slice(0, 3).forEach(b => {
      benefitsHtml += `<li>${b}</li>`;
    });

    const formulaDisplay = herb.formula ? `সূত্র: ${herb.formula}` : (herb.botanical_name || '');
    const priceDisplay = herb.price_range ? `<span class="product-price-badge">${herb.price_range}</span>` : '';

    card.innerHTML = `
      <img class="herb-card-img" src="${herb.image_url}" alt="${herb.name_bn}">
      <div class="herb-card-body">
        <div class="herb-header">
          <div class="herb-name-bn">${herb.name_bn}</div>
          ${priceDisplay}
        </div>
        <div class="herb-botanical"><i class="fa-solid fa-mortar-pestle"></i> ${formulaDisplay}</div>
        <div style="font-size:0.8rem; color:#38bdf8; margin-bottom:8px;"><i class="fa-solid fa-tag"></i> ${herb.category || ''}</div>
        <ul class="herb-benefits-list">
          ${benefitsHtml}
        </ul>
        <div class="herb-card-actions">
          <button class="btn-secondary" onclick="openHerbDetailModal('${herb.id}')" style="flex:1;">
            <i class="fa-solid fa-circle-info"></i> বিস্তারিত
          </button>
          <button class="btn-primary" onclick="quickOrderHerb('${herb.name_bn}', '${herb.price_range || ''}')" style="flex:1;">
            <i class="fa-solid fa-cart-plus"></i> অর্ডার
          </button>
        </div>
      </div>
    `;
    elements.herbsGrid.appendChild(card);
  });
}

function filterHerbsCatalog() {
  const query = document.getElementById('herb-search-input').value.toLowerCase().trim();
  if (!query) {
    renderHerbsGrid(state.allHerbs);
    return;
  }
  const filtered = state.allHerbs.filter(herb => 
    herb.name_bn.toLowerCase().includes(query) ||
    herb.name_en.toLowerCase().includes(query) ||
    (herb.formula && herb.formula.toLowerCase().includes(query)) ||
    (herb.category && herb.category.toLowerCase().includes(query)) ||
    (herb.keywords && herb.keywords.some(kw => kw.toLowerCase().includes(query)))
  );
  renderHerbsGrid(filtered);
}

function openHerbDetailModal(herbId) {
  const herb = state.allHerbs.find(h => h.id === herbId);
  if (!herb) return;

  state.currentSelectedHerb = herb;
  document.getElementById('herb-modal-title').textContent = `${herb.name_bn}`;

  let benefitsHtml = '';
  (herb.benefits_bn || []).forEach(b => { benefitsHtml += `<li>${b}</li>`; });

  const contentElem = document.getElementById('herb-modal-content');
  contentElem.innerHTML = `
    <img src="${herb.image_url}" style="width:100%; height:220px; object-fit:cover; border-radius:12px; margin-bottom:16px;">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
      <div>
        <strong style="color:#34d399; font-size:1.1rem;">ইউনানী সূত্র (Nuskha):</strong> <em>${herb.formula || herb.name_unani || ''}</em><br>
        <span style="color:#38bdf8; font-size:0.9rem;">ক্যাটাগরি: ${herb.category || ''}</span>
      </div>
      <span class="product-price-badge" style="font-size:1rem; padding:6px 14px;">${herb.price_range || ''}</span>
    </div>
    
    <h4 style="color:#fff; margin-bottom:6px;">প্রধান কার্যকারিতা ও স্বাস্থ্য উপকারিতা:</h4>
    <ul class="herb-benefits-list" style="margin-bottom:14px;">${benefitsHtml}</ul>

    ${herb.pack_sizes ? `<div style="background:rgba(255,255,255,0.04); padding:8px 12px; border-radius:8px; margin-bottom:10px; font-size:0.85rem;"><strong>📦 প্যাক সাইজ:</strong> ${herb.pack_sizes}</div>` : ''}

    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.25); padding:10px 14px; border-radius:8px; margin-bottom:12px;">
      <strong style="color:#34d399;">🍵 সেবনবিধি:</strong> ${herb.usage_bn || ''}
    </div>
  `;

  elements.herbDetailModal.classList.remove('hidden');
}

function closeHerbDetailModal() {
  elements.herbDetailModal.classList.add('hidden');
}

function orderCurrentHerb() {
  closeHerbDetailModal();
  if (state.currentSelectedHerb) {
    quickOrderHerb(state.currentSelectedHerb.name_bn, state.currentSelectedHerb.price_range);
  }
}

function quickOrderHerb(herbName, priceRange = '') {
  document.getElementById('order-items').value = `${herbName} ${priceRange ? `(${priceRange})` : ''}`;
  openOrderModal();
}

// ── Customer Leads Management ────────────────────────────────────────────────
async function loadLeadsFromDB() {
  try {
    const res = await fetch('/api/leads');
    const data = await res.json();
    if (data.success && data.leads) {
      state.allLeads = data.leads;
      elements.leadsCountBadge.textContent = data.leads.length;
      renderLeadsTable(state.allLeads);
    }
  } catch (err) {
    console.error('Failed to load leads:', err);
  }
}

function renderLeadsTable(leads) {
  elements.leadsTableBody.innerHTML = '';
  if (leads.length === 0) {
    elements.leadsTableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--text-muted); padding:24px;">কোনো কাস্টমার লিড পাওয়া যায়নি</td></tr>`;
    return;
  }

  leads.forEach(lead => {
    const tr = document.createElement('tr');
    const dateStr = lead.created_at ? new Date(lead.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'N/A';
    
    tr.innerHTML = `
      <td><strong>#${lead.id}</strong></td>
      <td><strong>${escapeHtml(lead.name || 'নাম নেই')}</strong></td>
      <td><a href="tel:${lead.phone}" style="color:#38bdf8; text-decoration:none; font-family:var(--font-mono);">${escapeHtml(lead.phone || 'অনির্ধারিত')}</a></td>
      <td>${escapeHtml(lead.address || 'ঠিকানা নেই')}</td>
      <td style="max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(lead.inquiry_summary || '')}</td>
      <td><span style="font-size:0.75rem; background:rgba(255,255,255,0.08); padding:2px 6px; border-radius:4px;">${lead.channel || 'web'}</span></td>
      <td>${lead.telegram_notified ? '<span style="color:#34d399;"><i class="fa-solid fa-check-double"></i> প্রেরিত</span>' : '<span style="color:var(--text-subtle);"><i class="fa-solid fa-clock"></i> পেন্ডিং</span>'}</td>
      <td><span class="status-pill status-${lead.status || 'new'}">${lead.status || 'new'}</span></td>
      <td style="font-size:0.75rem; color:var(--text-subtle);">${dateStr}</td>
      <td>
        <select class="custom-select" style="font-size:0.75rem; border:1px solid var(--border-glass);" onchange="updateLeadStatus(${lead.id}, this.value)">
          <option value="new" ${lead.status === 'new' ? 'selected' : ''}>নতুন</option>
          <option value="contacted" ${lead.status === 'contacted' ? 'selected' : ''}>যোগাযোগকৃত</option>
          <option value="confirmed" ${lead.status === 'confirmed' ? 'selected' : ''}>নিশ্চিত</option>
          <option value="delivered" ${lead.status === 'delivered' ? 'selected' : ''}>ডেলিভার্ড</option>
          <option value="cancelled" ${lead.status === 'cancelled' ? 'selected' : ''}>বাতিল</option>
        </select>
      </td>
    `;
    elements.leadsTableBody.appendChild(tr);
  });
}

function filterLeadsTable() {
  const query = document.getElementById('leads-search-input').value.toLowerCase().trim();
  const status = document.getElementById('leads-status-filter').value;

  const filtered = state.allLeads.filter(lead => {
    const matchQuery = !query || 
      (lead.name && lead.name.toLowerCase().includes(query)) ||
      (lead.phone && lead.phone.toLowerCase().includes(query)) ||
      (lead.address && lead.address.toLowerCase().includes(query));
    const matchStatus = !status || lead.status === status;
    return matchQuery && matchStatus;
  });

  renderLeadsTable(filtered);
}

async function updateLeadStatus(leadId, newStatus) {
  try {
    const res = await fetch(`/api/leads/${leadId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`লিড #${leadId} স্ট্যাটাস আপডেট: ${newStatus}`, 'success');
      loadLeadsFromDB();
    }
  } catch (err) {
    showToast('স্ট্যাটাস আপডেট ব্যর্থ হয়েছে', 'error');
  }
}

function exportLeadsToCSV() {
  if (!state.allLeads || state.allLeads.length === 0) {
    showToast('এক্সপোর্ট করার মতো কোনো লিড নেই', 'error');
    return;
  }

  let csvContent = 'data:text/csv;charset=utf-8,';
  csvContent += 'ID,Name,Phone,Address,Inquiry,Status,Channel,TelegramNotified,CreatedAt\n';

  state.allLeads.forEach(l => {
    const row = [
      l.id,
      `"${(l.name || '').replace(/"/g, '""')}"`,
      `"${l.phone || ''}"`,
      `"${(l.address || '').replace(/"/g, '""')}"`,
      `"${(l.inquiry_summary || '').replace(/"/g, '""')}"`,
      l.status,
      l.channel,
      l.telegram_notified,
      l.created_at
    ].join(',');
    csvContent += row + '\n';
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', `unani_leads_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('CSV ফাইল ডাউনলোড হয়েছে!', 'success');
}

// ── Manual Order Modal ───────────────────────────────────────────────────────
function openOrderModal() {
  elements.orderModal.classList.remove('hidden');
}

function closeOrderModal() {
  elements.orderModal.classList.add('hidden');
}

async function submitManualOrder() {
  const name = document.getElementById('order-name').value.trim();
  const phone = document.getElementById('order-phone').value.trim();
  const address = document.getElementById('order-address').value.trim();
  const items = document.getElementById('order-items').value.trim();

  if (!name || !phone || !address) {
    showToast('নাম, মোবাইল নম্বর ও ঠিকানা পূরণ করা আবশ্যক!', 'error');
    return;
  }

  const btnSubmit = document.getElementById('btn-submit-order');
  btnSubmit.disabled = true;
  btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> প্রক্রিয়াকরণ হচ্ছে...';

  try {
    const res = await fetch('/api/leads/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name, phone, address, inquiry_summary: items, order_items: items
      })
    });
    const data = await res.json();
    if (data.success) {
      closeOrderModal();
      showToast('✅ অর্ডার সম্পন্ন হয়েছে! ডাটাবেজ ও টেলিগ্রামে পাঠানো হয়েছে।', 'success');
      loadLeadsFromDB();
      // Clear form
      document.getElementById('order-name').value = '';
      document.getElementById('order-phone').value = '';
      document.getElementById('order-address').value = '';
      document.getElementById('order-items').value = '';
    } else {
      showToast('অর্ডার গ্রহণে সমস্যা হয়েছে', 'error');
    }
  } catch (err) {
    showToast('সার্ভার এরর: অর্ডার পাঠানো যায়নি', 'error');
  } finally {
    btnSubmit.disabled = false;
    btnSubmit.innerHTML = '<i class="fa-solid fa-paper-plane"></i> অর্ডার সম্পন্ন করুন';
  }
}

// ── System Status & Telegram Tester ──────────────────────────────────────────
async function checkSystemStatus() {
  try {
    const res = await fetch('/api/system/status');
    const data = await res.json();

    // Ollama status
    const ollamaBadge = document.getElementById('badge-ollama');
    const ollamaDetail = document.getElementById('detail-ollama');
    if (data.ollama && data.ollama.online) {
      ollamaBadge.className = 'status-badge online';
      ollamaBadge.textContent = 'অনলাইন (Online)';
      ollamaDetail.textContent = `Model: ${data.ollama.target_model} • Models: ${data.ollama.available_models.join(', ') || 'ready'}`;
    } else {
      ollamaBadge.className = 'status-badge offline';
      ollamaBadge.textContent = 'অফলাইন (Offline)';
      ollamaDetail.textContent = 'Ollama চালু করুন: ollama serve';
    }

    // STT status
    const sttBadge = document.getElementById('badge-stt');
    if (data.stt && data.stt.online) {
      sttBadge.className = 'status-badge online';
      sttBadge.textContent = 'সক্রিয় (Port 8001)';
    } else {
      sttBadge.className = 'status-badge offline';
      sttBadge.textContent = 'বিল্ট-ইন মোড';
    }

    // TTS status
    const ttsBadge = document.getElementById('badge-tts');
    if (data.tts && data.tts.online) {
      ttsBadge.className = 'status-badge online';
      ttsBadge.textContent = 'সক্রিয় (Port 8002)';
    } else {
      ttsBadge.className = 'status-badge online';
      ttsBadge.textContent = 'ওয়েব স্পিচ সক্রিয়';
    }

    // Telegram status
    const tgBadge = document.getElementById('badge-telegram');
    if (data.telegram && data.telegram.configured) {
      tgBadge.className = 'status-badge online';
      tgBadge.textContent = 'কনফিগারড (Configured)';
    } else {
      tgBadge.className = 'status-badge offline';
      tgBadge.textContent = 'টোকেন প্রয়োজন (.env)';
    }

    showToast('সিস্টেম স্ট্যাটাস রিফ্রেশ সম্পন্ন', 'info');
  } catch (err) {
    console.error('Status check failed:', err);
  }
}

async function testTelegramAlert() {
  try {
    const res = await fetch('/test-telegram', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ custom_message: 'UnaniMed AI লাইভ সিস্টেম টেস্ট মেসেজ' })
    });
    const data = await res.json();
    if (data.success) {
      showToast('টেলিগ্রামে সফলভাবে টেস্ট মেসেজ পাঠানো হয়েছে!', 'success');
    } else {
      showToast('টেলিগ্রাম মেসেজ পাঠানো ব্যর্থ হয়েছে। BOT_TOKEN ও CHAT_ID চেক করুন।', 'error');
    }
  } catch (err) {
    showToast('টেলিগ্রাম টেস্ট কল ব্যর্থ হয়েছে', 'error');
  }
}

// ── Lead Banner Helper ───────────────────────────────────────────────────────
function showLeadDetectedBanner() {
  elements.leadDetectedBanner.classList.remove('hidden');
  setTimeout(() => {
    elements.leadDetectedBanner.classList.add('hidden');
  }, 9000);
}

function dismissLeadBanner() {
  elements.leadDetectedBanner.classList.add('hidden');
}

// ── Toast System ─────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = 'fa-circle-info';
  if (type === 'success') icon = 'fa-circle-check';
  if (type === 'error') icon = 'fa-circle-exclamation';

  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${escapeHtml(message)}</span>`;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ── Utilities & Markdown Formatter ───────────────────────────────────────────
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

function formatMarkdown(text) {
  if (!text) return '';
  let escaped = escapeHtml(text);
  
  // Headers
  escaped = escaped.replace(/^### (.*$)/gim, '<h4 style="color:#34d399; margin:10px 0 4px 0;">$1</h4>');
  escaped = escaped.replace(/^## (.*$)/gim, '<h3 style="color:#34d399; margin:12px 0 6px 0;">$1</h3>');
  escaped = escaped.replace(/^# (.*$)/gim, '<h2 style="color:#34d399; margin:14px 0 8px 0;">$1</h2>');
  
  // Bold & Italics
  escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff;">$1</strong>');
  escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Inline Code
  escaped = escaped.replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:4px; font-family:var(--font-mono); font-size:0.85em; color:#38bdf8;">$1</code>');
  
  // Line breaks & Bullet lists
  escaped = escaped.replace(/\n\s*-\s*(.*)/g, '<li style="margin-left:18px; margin-bottom:4px;">$1</li>');
  escaped = escaped.replace(/\n\s*\*\s*(.*)/g, '<li style="margin-left:18px; margin-bottom:4px;">$1</li>');
  escaped = escaped.replace(/\n/g, '<br>');

  return escaped;
}

function getSessionId() {
  let sid = sessionStorage.getItem('unani_sid');
  if (!sid) {
    sid = Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem('unani_sid', sid);
  }
  return sid;
}
