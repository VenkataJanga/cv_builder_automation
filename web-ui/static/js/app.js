// CV Builder Automation - Comprehensive JavaScript Implementation
class CVBuilderApp {
    constructor({ autoInit = true } = {}) {
        this.apiBase = window.location.origin;
        this.currentSessionId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.currentCVData = null;
        this.currentCanonicalCV = null;
        this.activeFlow = null;
        this.isEditMode = false;
        this.editableData = null;
        this.token = localStorage.getItem('cv_builder_token') || null;
        this.currentUser = null;

        if (autoInit) {
            this.init();
        }
    }

    init() {
        this.bindEvents();
        this.checkServerStatus();
        this.setupDragAndDrop();
        this.checkAuthStatus();
    }

    getPreferredCVData(data, fallback = {}) {
        if (!data || typeof data !== 'object') {
            return fallback || {};
        }

        return (
            data.preview ||
            data.canonical_cv ||
            data.cv_data ||
            data.extracted_cv_data ||
            data.parsed_data ||
            fallback ||
            {}
        );
    }

    getInitialChatMarkup() {
        return `
            <div class="message bot-message">
                <div class="message-content">
                    Hello! I'm here to help you build your CV. You can:
                    <ul>
                        <li>Upload your existing CV (PDF/DOCX/DOC)</li>
                        <li>Record yourself talking about your experience</li>
                        <li>Chat with me to build your CV step by step</li>
                    </ul>
                    How would you like to start?
                </div>
            </div>
        `;
    }

    hasMeaningfulFlowData() {
        const hasPreviewData = Boolean(this.currentCVData && Object.keys(this.currentCVData).length > 0);
        const canonicalCandidate = this.currentCanonicalCV?.candidate || {};
        const canonicalExperience = this.currentCanonicalCV?.experience || {};
        const hasCanonicalData = Boolean(
            (canonicalCandidate.fullName && String(canonicalCandidate.fullName).trim())
            || (canonicalCandidate.summary && String(canonicalCandidate.summary).trim())
            || (Array.isArray(canonicalExperience.projects) && canonicalExperience.projects.length > 0)
            || (Array.isArray(this.currentCanonicalCV?.education) && this.currentCanonicalCV.education.length > 0)
        );

        const userMessages = document.querySelectorAll('#chatMessages .user-message');
        const hasConversationInput = userMessages.length > 0;

        return hasPreviewData || hasCanonicalData || hasConversationInput;
    }

    async ensureSingleActiveFlow(targetFlow) {
        if (!targetFlow) {
            return true;
        }

        if (!this.activeFlow || this.activeFlow === targetFlow) {
            this.activeFlow = targetFlow;
            return true;
        }

        if (!this.hasMeaningfulFlowData()) {
            this.activeFlow = targetFlow;
            return true;
        }

        const confirmed = window.confirm(
            `You are switching from ${this.activeFlow} to ${targetFlow}. ` +
            'This will clear the current preview and unsaved temporary session data. Do you want to continue?'
        );

        if (!confirmed) {
            return false;
        }

        await this.clearCurrentSession({
            resetBackend: true,
            notify: false,
            startFreshConversation: false,
        });

        this.activeFlow = targetFlow;
        return true;
    }

    resetApplicationState() {
        if (this.mediaRecorder && this.isRecording) {
            try {
                this.mediaRecorder.stop();
            } catch (_) {
                // Ignore recorder shutdown issues while resetting the UI state.
            }
        }

        this.currentSessionId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.currentCVData = null;
        this.currentCanonicalCV = null;
        this.activeFlow = null;
        this.isEditMode = false;
        this.editableData = null;

        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = this.getInitialChatMarkup();
        }

        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.value = '';
        }

        const sessionInput = document.getElementById('sessionId');
        if (sessionInput) {
            sessionInput.value = '';
        }

        const currentSession = document.getElementById('currentSession');
        if (currentSession) {
            currentSession.innerHTML = '';
        }

        const preview = document.getElementById('cvPreview');
        if (preview) {
            preview.innerHTML = `
                <div class="preview-placeholder">
                    <p>Your CV data will appear here as you build it</p>
                    <p>Upload a document, record audio, or start chatting to begin</p>
                </div>
            `;
        }

        const resultAreas = ['uploadResult', 'transcriptionResult'];
        resultAreas.forEach((elementId) => {
            const element = document.getElementById(elementId);
            if (element) {
                element.textContent = '';
                element.className = 'result-area';
                element.style.display = 'none';
            }
        });

        ['uploadProgress', 'audioProgress'].forEach((elementId) => this.hideProgress(elementId));

        const recordingStatus = document.getElementById('recordingStatus');
        if (recordingStatus) {
            recordingStatus.textContent = '';
        }

        const audioPlayback = document.getElementById('audioPlayback');
        if (audioPlayback) {
            try {
                audioPlayback.pause();
            } catch (_) {
                // Ignore pause errors during reset.
            }
            audioPlayback.removeAttribute('src');
            audioPlayback.style.display = 'none';
        }

        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            recordBtn.innerHTML = '<span class="record-icon">🔴</span> Start Recording';
            recordBtn.classList.remove('recording');
        }

        this.resetButtonStates();
        this.updateStatus('sessionStatus', 'No active session', '');
        this.updateStatus('lastUpdate', new Date().toLocaleTimeString(), '');
    }

    async clearCurrentSession({ resetBackend = true, notify = true, startFreshConversation = true } = {}) {
        const activeSessionId = this.currentSessionId;

        if (resetBackend && activeSessionId && this.token) {
            try {
                await this.request(`${this.apiBase}/session/${activeSessionId}`, {
                    method: 'DELETE'
                });
            } catch (_) {
                // Client state reset is the primary requirement; tolerate backend cleanup failures.
            }
        }

        this.resetApplicationState();

        if (startFreshConversation && this.token) {
            await this.createConversationSession();
        }

        if (notify) {
            this.showNotification('Session cleared. Started a fresh session.', 'success');
        }
    }

    // ── Auth helpers ──────────────────────────────────────────────────────────

    getAuthHeaders() {
        return this.token ? { 'Authorization': `Bearer ${this.token}` } : {};
    }

    async request(url, options = {}) {
        const headers = {
            ...(options.headers || {}),
            ...this.getAuthHeaders(),
        };
        const response = await fetch(url, { ...options, headers });
        if (response.status === 401) {
            this.logout();
            throw new Error('Session expired. Please sign in again.');
        }
        return response;
    }

    async checkAuthStatus() {
        if (!this.token) {
            this.resetApplicationState();
            this.showLoginOverlay();
            return;
        }
        try {
            const res = await fetch(`${this.apiBase}/auth/me`, {
                headers: { 'Authorization': `Bearer ${this.token}` },
            });
            if (res.ok) {
                this.currentUser = await res.json();
                this.showUserInfoBar();
                this.initializeChat();
            } else {
                this.logout();
            }
        } catch {
            this.logout();
        }
    }

    showLoginOverlay() {
        const overlay = document.getElementById('loginOverlay');
        if (overlay) overlay.style.display = 'flex';
        const bar = document.getElementById('userInfoBar');
        if (bar) bar.style.display = 'none';
    }

    hideLoginOverlay() {
        const overlay = document.getElementById('loginOverlay');
        if (overlay) overlay.style.display = 'none';
    }

    showUserInfoBar() {
        const bar = document.getElementById('userInfoBar');
        const text = document.getElementById('userInfoText');
        if (this.currentUser && text) {
            const role = this.currentUser.role || '';
            text.textContent = `👤 ${this.currentUser.username}  •  ${role}`;
        }
        if (bar) bar.style.display = 'flex';
    }

    async login(username, password) {
        const loginBtn = document.getElementById('loginBtn');
        const errorDiv = document.getElementById('loginError');
        loginBtn.disabled = true;
        loginBtn.textContent = 'Signing in…';
        errorDiv.style.display = 'none';

        try {
            const body = new URLSearchParams({ username, password });
            const res = await fetch(`${this.apiBase}/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: body.toString(),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Invalid credentials');
            }

            const data = await res.json();
            this.token = data.access_token;
            localStorage.setItem('cv_builder_token', this.token);

            // Fetch current user profile
            const meRes = await fetch(`${this.apiBase}/auth/me`, {
                headers: { 'Authorization': `Bearer ${this.token}` },
            });
            this.currentUser = meRes.ok ? await meRes.json() : { username };

            this.resetApplicationState();
            this.hideLoginOverlay();
            this.showUserInfoBar();
            this.initializeChat();
        } catch (err) {
            errorDiv.textContent = err.message;
            errorDiv.style.display = 'block';
        } finally {
            loginBtn.disabled = false;
            loginBtn.textContent = 'Sign In';
        }
    }

    logout() {
        this.resetApplicationState();
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('cv_builder_token');
        this.showLoginOverlay();
        this.showNotification('Signed out.', 'info');
    }

    // ── Event binding ─────────────────────────────────────────────────────────

    bindEvents() {
        // Login / logout
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;
            this.login(username, password);
        });
        document.getElementById('logoutBtn').addEventListener('click', () => this.logout());
        document.getElementById('clearSessionBtn').addEventListener('click', () => this.clearCurrentSession());

        // Session Management
        document.getElementById('createSession').addEventListener('click', () => this.createSession());
        document.getElementById('loadSession').addEventListener('click', () => this.loadSession());

        // File Upload
        document.getElementById('browseFiles').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileUpload(e.target.files[0]));

        // Audio Recording
        document.getElementById('recordBtn').addEventListener('click', () => this.toggleRecording());
        document.getElementById('browseAudioFiles').addEventListener('click', () => {
            document.getElementById('audioFileInput').click();
        });
        document.getElementById('audioFileInput').addEventListener('change', (e) => this.handleAudioUpload(e.target.files[0]));

        // Chat
        document.getElementById('sendChatBtn').addEventListener('click', () => this.sendChatMessage());
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendChatMessage();
        });

        // CV Preview
        document.getElementById('refreshPreview').addEventListener('click', () => this.refreshCVPreview());
        document.getElementById('toggleEditMode').addEventListener('click', () => this.toggleEditMode());
        document.getElementById('saveAndValidate').addEventListener('click', () => this.saveAndValidateCV());
        document.getElementById('exportCV').addEventListener('click', () => this.showExportModal());
        
        // Initialize tooltips
        this.initializeTooltips();

        // Export Modal
        document.querySelector('.modal-close').addEventListener('click', () => this.hideExportModal());
        document.querySelectorAll('.btn-export').forEach(btn => {
            btn.addEventListener('click', (e) => this.exportCV(e.target.dataset.format));
        });

        // Click outside modal to close
        document.getElementById('exportModal').addEventListener('click', (e) => {
            if (e.target.id === 'exportModal') this.hideExportModal();
        });
    }

    setupDragAndDrop() {
        // Document upload drag & drop
        const documentUpload = document.getElementById('documentUpload');
        documentUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            documentUpload.classList.add('dragover');
        });
        documentUpload.addEventListener('dragleave', () => {
            documentUpload.classList.remove('dragover');
        });
        documentUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            documentUpload.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) this.handleFileUpload(files[0]);
        });

        // Audio upload drag & drop
        const audioUpload = document.getElementById('audioUpload');
        audioUpload.addEventListener('dragover', (e) => {
            e.preventDefault();
            audioUpload.classList.add('dragover');
        });
        audioUpload.addEventListener('dragleave', () => {
            audioUpload.classList.remove('dragover');
        });
        audioUpload.addEventListener('drop', (e) => {
            e.preventDefault();
            audioUpload.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) this.handleAudioUpload(files[0]);
        });
    }

    async initializeChat() {
        this.resetApplicationState();
        await this.createConversationSession();
    }

    async createConversationSession() {
        try {
            const response = await this.request(`${this.apiBase}/chat/conversations/session`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });

            if (response.ok) {
                const data = await response.json();
                this.activeFlow = 'conversation';
                this.currentSessionId = data.session_id;
                this.currentCVData = this.getPreferredCVData(data, this.currentCVData);
                this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
                this.updateSessionDisplay(data.session_id);
                if (data.question) {
                    this.addChatMessage(data.question, 'bot');
                }
                this.refreshCVPreview();
            } else {
                throw new Error('Failed to create chat session');
            }
        } catch (error) {
            this.showNotification('Failed to start conversation: ' + error.message, 'error');
        }
    }

    async checkServerStatus() {
        try {
            const response = await fetch(`${this.apiBase}/health`, { method: 'GET' });
            if (response.ok) {
                this.updateStatus('serverStatus', 'Online', 'text-success');
            } else {
                throw new Error('Server not responding properly');
            }
        } catch (error) {
            this.updateStatus('serverStatus', 'Offline', 'text-error');
            this.showNotification('Server is offline. Please start the server.', 'error');
        }
    }

    async createSession() {
        try {
            const response = await this.request(`${this.apiBase}/session/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok) {
                const data = await response.json();
                this.currentSessionId = data.session_id;
                this.updateSessionDisplay(data.session_id);
                this.showNotification('New session created successfully!', 'success');
            } else {
                throw new Error('Failed to create session');
            }
        } catch (error) {
            this.showNotification('Failed to create session: ' + error.message, 'error');
        }
    }

    async loadSession() {
        const sessionId = document.getElementById('sessionId').value.trim();
        if (!sessionId) {
            this.showNotification('Please enter a session ID', 'error');
            return;
        }

        try {
            const response = await this.request(`${this.apiBase}/session/${sessionId}`, {
                method: 'GET'
            });

            if (response.ok) {
                const data = await response.json();
                this.activeFlow = 'loaded';
                this.currentSessionId = sessionId;
                this.currentCVData = this.getPreferredCVData(data, this.currentCVData);
                this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
                this.updateSessionDisplay(sessionId);
                this.refreshCVPreview();
                this.showNotification('Session loaded successfully!', 'success');
            } else {
                throw new Error('Session not found');
            }
        } catch (error) {
            this.showNotification('Failed to load session: ' + error.message, 'error');
        }
    }

    async handleFileUpload(file) {
        if (!file) return;

        const canProceed = await this.ensureSingleActiveFlow('upload');
        if (!canProceed) {
            return;
        }

        if (!file.name.match(/\.(pdf|docx|doc)$/i)) {
            this.showNotification('Please select a PDF, DOCX, or DOC file', 'error');
            return;
        }

        if (!this.currentSessionId) {
            await this.createSession();
            if (!this.currentSessionId) {
                this.showNotification('Unable to create a session for document upload.', 'error');
                return;
            }
        }

        this.showProgress('uploadProgress', 'Uploading file...');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            if (this.currentSessionId) {
                formData.append('session_id', this.currentSessionId);
            }

            const response = await this.request(`${this.apiBase}/cv/upload/document`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.activeFlow = 'upload';
                this.currentCVData = this.getPreferredCVData(data, this.currentCVData);
                this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
                this.currentSessionId = data.session_id || this.currentSessionId;
                
                if (data.session_id) {
                    this.updateSessionDisplay(data.session_id);
                }

                this.hideProgress('uploadProgress');
                this.showResult('uploadResult', 'File uploaded and processed successfully!', 'success');
                this.refreshCVPreview();
                this.addChatMessage(`I've processed your uploaded file "${file.name}". The CV data has been extracted. Would you like to review or add more information?`, 'bot');
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            this.hideProgress('uploadProgress');
            this.showResult('uploadResult', 'Upload failed: ' + error.message, 'error');
        }
    }

    async toggleRecording() {
        if (this.isRecording) {
            this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                await this.processAudio(audioBlob);
            };

            this.mediaRecorder.start();
            this.isRecording = true;
            
            const recordBtn = document.getElementById('recordBtn');
            recordBtn.innerHTML = '<span class="record-icon">⏹️</span> Stop Recording';
            recordBtn.classList.add('recording');
            
            document.getElementById('recordingStatus').textContent = 'Recording in progress...';
        } catch (error) {
            this.showNotification('Failed to start recording: ' + error.message, 'error');
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.isRecording = false;

            const recordBtn = document.getElementById('recordBtn');
            recordBtn.innerHTML = '<span class="record-icon">🔴</span> Start Recording';
            recordBtn.classList.remove('recording');
            
            document.getElementById('recordingStatus').textContent = 'Processing audio...';
        }
    }

    async handleAudioUpload(file) {
        if (!file) return;

        // Accept audio/* MIME types OR common audio extensions for files where
        // the browser reports an empty/octet-stream type (e.g. .mp3 on some OS).
        const audioExtensions = /\.(mp3|mp4|wav|m4a|ogg|flac|webm|mpeg|mpga)$/i;
        const isAudioMime = file.type.startsWith('audio/');
        const isAudioExt = audioExtensions.test(file.name);

        if (!isAudioMime && !isAudioExt) {
            this.showNotification('Please select an audio file (mp3, wav, m4a, ogg, flac, webm)', 'error');
            return;
        }

        // Guard against files the server will reject (server limit: 25 MB / ~12 min).
        const MAX_AUDIO_MB = 25;
        if (file.size > MAX_AUDIO_MB * 1024 * 1024) {
            this.showNotification(
                `Audio file is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). ` +
                `Maximum allowed is ${MAX_AUDIO_MB} MB (~10–12 minutes of audio).`,
                'error'
            );
            return;
        }

        await this.processAudio(file);
    }

    async processAudio(audioBlob, retryOnInvalidSession = true) {
        const canProceed = await this.ensureSingleActiveFlow('voice');
        if (!canProceed) {
            return;
        }

        this.showProgress('audioProgress', 'Processing audio...');

        try {
            const formData = new FormData();
            // Use real filename so Whisper can detect the audio format from the extension.
            // For recorded blobs (no .name), fall back to recording.webm.
            const filename = audioBlob.name || 'recording.webm';
            formData.append('file', audioBlob, filename);
            const sessionIdToSend = typeof this.currentSessionId === 'string'
                ? this.currentSessionId.trim()
                : '';
            if (sessionIdToSend) {
                formData.append('session_id', sessionIdToSend);
            }

            const response = await this.request(`${this.apiBase}/speech/transcribe`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();

                if (data.error) {
                    // If the in-memory backend session was reset, retry once without stale session_id.
                    if (retryOnInvalidSession && /invalid session/i.test(String(data.error))) {
                        this.currentSessionId = null;
                        this.updateStatus('sessionStatus', 'No active session', '');
                        this.updateStatus('lastUpdate', new Date().toLocaleTimeString(), '');
                        return await this.processAudio(audioBlob, false);
                    }
                    throw new Error(data.error);
                }

                this.currentCVData = this.getPreferredCVData(data, this.currentCVData);
                this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
                this.activeFlow = 'voice';
                this.currentSessionId = data.session_id || this.currentSessionId;

                if (data.session_id) {
                    this.updateSessionDisplay(data.session_id);
                }

                this.hideProgress('audioProgress');
                
                // Show transcription result
                let resultText = `Transcription completed!\n\n`;
                if (data.raw_transcript) {
                    resultText += `Transcript: ${data.raw_transcript.substring(0, 200)}${data.raw_transcript.length > 200 ? '...' : ''}`;
                }
                if (data.audio_quality_warning) {
                    resultText += `\n\n⚠️ ${data.audio_quality_warning}`;
                }
                
                this.showResult('transcriptionResult', resultText, data.audio_quality_warning ? 'error' : 'success');
                
                // Reset button states before refreshing preview
                this.resetButtonStates();
                await this.refreshCVPreview();
                
                this.addChatMessage(`I've processed your audio and extracted CV information. Would you like to review the details or add more information?`, 'bot');
                
                document.getElementById('recordingStatus').textContent = '';
            } else {
                // Read the server error detail so the user sees the actual failure reason.
                let detail = `HTTP ${response.status}`;
                try {
                    const errBody = await response.json();
                    detail = errBody.detail || errBody.message || detail;
                } catch (_) { /* ignore parse errors */ }
                throw new Error(detail);
            }
        } catch (error) {
            this.hideProgress('audioProgress');
            this.showResult('transcriptionResult', 'Audio processing failed: ' + error.message, 'error');
            document.getElementById('recordingStatus').textContent = '';
        }
    }

    async sendChatMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message) return;

        const canProceed = await this.ensureSingleActiveFlow('conversation');
        if (!canProceed) {
            return;
        }

        if (!this.currentSessionId) {
            await this.createConversationSession();
            if (!this.currentSessionId) {
                this.showNotification('Unable to start the conversation session.', 'error');
                return;
            }
        }

        this.addChatMessage(message, 'user');
        input.value = '';

        try {
            const response = await this.request(`${this.apiBase}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message, 
                    session_id: this.currentSessionId
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.activeFlow = 'conversation';
                this.addChatMessage(data.bot || 'No response', 'bot');
                
                const preferredData = this.getPreferredCVData(data, null);
                if (preferredData && Object.keys(preferredData).length > 0) {
                    this.currentCVData = preferredData;
                    this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
                    this.refreshCVPreview();
                }
                
                if (data.session_id && !this.currentSessionId) {
                    this.currentSessionId = data.session_id;
                    this.updateSessionDisplay(data.session_id);
                }
            } else {
                throw new Error('Chat request failed');
            }
        } catch (error) {
            this.addChatMessage('Sorry, I encountered an error: ' + error.message, 'bot');
        }
    }

    addChatMessage(message, sender) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = this.formatMessage(message);
        
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    formatMessage(message) {
        // Convert line breaks to HTML and format lists
        return message
            .replace(/\n/g, '<br>')
            .replace(/\*\s(.+)/g, '<li>$1</li>')
            .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    }

    mapToSchemaFormat(cvData) {
        // Transform UI CV data to match backend CVSchema exactly
        const personal = cvData.personal_details || cvData.header || {};
        const candidate = cvData.candidate || {};
        const personalDetails = cvData.personalDetails || {};
        const rawLocation = personal.location || cvData.location || candidate.currentLocation || candidate.location || '';
        const resolvedLocation = typeof rawLocation === 'string'
            ? rawLocation
            : (rawLocation?.fullAddress || [rawLocation?.city, rawLocation?.country].filter(Boolean).join(', '));

        const skillsData = cvData.skills || {};
        const primarySkills = Array.isArray(skillsData.primary_skills)
            ? skillsData.primary_skills
            : Array.isArray(skillsData.primarySkills)
                ? skillsData.primarySkills
                : Array.isArray(cvData.skills)
                    ? cvData.skills
                    : [];
        const secondarySkills = skillsData.secondary_skills || skillsData.secondarySkills || cvData.secondary_skills || cvData.secondarySkills || [];
        const toolsAndPlatforms = skillsData.tools_and_platforms || skillsData.toolsAndPlatforms || cvData.tools_and_platforms || cvData.toolsAndPlatforms || [];
        const domainExpertise = skillsData.domain_expertise
            || skillsData.domainExpertise
            || cvData.domain_expertise
            || cvData.domainExpertise
            || cvData.experience?.domainExperience
            || [];

        const projectSource = cvData.project_experience || cvData.experience?.projects || [];

        const mapped = {
            personal_details: {
                full_name: personal.full_name || personal.fullName || cvData.full_name || candidate.fullName || '',
                current_title: personal.current_title || personal.currentTitle || candidate.currentDesignation || candidate.designation || '',
                location: resolvedLocation || '',
                total_experience: personal.total_experience || personal.totalExperience || candidate.totalExperienceYears || null,
                current_organization: personal.current_organization || personal.currentOrganization || candidate.currentOrganization || null,
                email: personal.email || candidate.email || candidate.emailAddress || candidate.email_address || null,
                phone: personal.phone || personal.contact_number || candidate.phoneNumber || candidate.alternatePhoneNumber || null,
                linkedin: personal.linkedin || personalDetails.linkedinUrl || cvData.linkedin || null,
            },
            summary: {
                professional_summary: this.extractSummaryText(cvData.summary) || candidate.summary || '',
                target_role: cvData.summary?.target_role || cvData.summary?.targetRole || cvData.target_role || cvData.targetRole || candidate.careerObjective || null,
            },
            skills: {
                primary_skills: primarySkills,
                secondary_skills: secondarySkills,
                tools_and_platforms: toolsAndPlatforms,
                domain_expertise: domainExpertise,
            },
            work_experience: this.mapWorkExperience(cvData.work_experience || []),
            project_experience: this.mapProjectExperience(projectSource),
            certifications: this.mapCertifications(cvData.certifications || []),
            education: this.mapEducation(cvData.education || []),
            publications: cvData.publications || null,
            awards: cvData.awards || null,
            languages: cvData.languages || null,
            target_role: cvData.target_role || cvData.summary?.target_role || null,
            schema_version: '1.0',
        };

        return mapped;
    }

    extractSummaryText(summaryValue) {
        // Extract text from summary-like fields only; avoid flattening unrelated object values.
        if (typeof summaryValue === 'string') return summaryValue;

        if (Array.isArray(summaryValue)) {
            return summaryValue
                .map(item => this.extractSummaryText(item))
                .filter(Boolean)
                .join('\n');
        }

        if (summaryValue && typeof summaryValue === 'object') {
            const preferredKeys = [
                'professional_summary',
                'summary',
                'experience_summary',
                'profile_summary',
                'description',
                'text',
                'content'
            ];

            for (const key of preferredKeys) {
                if (summaryValue[key] !== undefined && summaryValue[key] !== null && summaryValue[key] !== '') {
                    const extracted = this.extractSummaryText(summaryValue[key]);
                    if (extracted) return extracted;
                }
            }

            const ignoredKeys = new Set([
                'target_role',
                'total_experience_years',
                'total_experience_months',
                'relevant_experience_years',
                'relevant_experience_months',
                'years_of_experience'
            ]);

            const fallbackParts = Object.entries(summaryValue)
                .filter(([key]) => !ignoredKeys.has(String(key).toLowerCase()))
                .map(([, value]) => this.extractSummaryText(value))
                .filter(Boolean);

            return fallbackParts.join('\n');
        }

        return '';
    }

    normalizeSummaryLines(summaryText) {
        const text = String(summaryText || '').replace(/\r\n/g, '\n').trim();
        if (!text) return [];

        const bulletChars = /[\u2022\u25E6\u25AA\u25CF\u25C6\u25BA\uF076]/g;
        let normalized = text.replace(bulletChars, '\n• ');

        normalized = normalized
            .replace(/\n{3,}/g, '\n\n')
            .split('\n')
            .map(line => line.trim())
            .filter(Boolean);

        if (normalized.length === 1) {
            // Fallback split for flattened text that still contains list markers like "a." or "1.".
            const single = normalized[0]
                .replace(/\s+([a-zA-Z]\.)\s+/g, '\n$1 ')
                .replace(/\s+(\d+\.)\s+/g, '\n$1 ');
            normalized = single
                .split('\n')
                .map(line => line.trim())
                .filter(Boolean);
        }

        return normalized.map(line => line.replace(/^([\-*\u2022•]|\d+[.)]|[a-zA-Z][.)])\s+/, '').trim()).filter(Boolean);
    }

    mapWorkExperience(experiences) {
        return experiences.map(exp => ({
            company_name: exp.company || exp.company_name || '',
            role_title: exp.position || exp.role_title || '',
            start_date: this.parseDate(exp.start_date),
            end_date: exp.end_date ? this.parseDate(exp.end_date) : null,
            responsibilities: Array.isArray(exp.responsibilities) ? exp.responsibilities : 
                            exp.description ? [exp.description] : [],
            achievements: exp.achievements || [],
            location: exp.location || null,
        }));
    }

    mapProjectExperience(projects) {
        return projects.map(proj => ({
            project_name: proj.project_name || proj.projectName || proj.name || proj.title || '',
            client_name: proj.client || proj.client_name || proj.clientName || null,
            role: proj.role || proj.designation || proj.role_title || proj.position || '',
            duration: proj.duration || (proj.durationFrom && proj.durationTo ? `${proj.durationFrom} to ${proj.durationTo}` : (proj.durationFrom || proj.durationTo || null)),
            team_size: proj.team_size || null,
            technologies: proj.technologies_used || proj.technologies || proj.toolsUsed || proj.environment || [],
            responsibilities: proj.responsibilities || [],
            outcomes: proj.outcomes || [],
            description: proj.description || proj.project_description || proj.projectDescription || '',
            project_description: proj.project_description || proj.projectDescription || proj.description || '',
        }));
    }

    mapCertifications(certifications) {
        return certifications.map(cert => {
            if (typeof cert === 'string') {
                return {
                    certification_name: cert,
                    issuing_organization: null,
                    issue_date: null,
                    expiry_date: null,
                };
            }
            return {
                certification_name: cert.certification_name || cert.name || '',
                issuing_organization: cert.issuing_organization || cert.organization || null,
                issue_date: cert.issue_date ? this.parseDate(cert.issue_date) : null,
                expiry_date: cert.expiry_date ? this.parseDate(cert.expiry_date) : null,
            };
        });
    }

    mapEducation(education) {
        const eduArray = Array.isArray(education) ? education : [education];
        return eduArray.map(edu => {
            if (typeof edu === 'string') {
                return {
                    degree: edu,
                    institution: '',
                    year_of_completion: null,
                };
            }
            return {
                degree: edu.qualification || edu.degree || edu.title || '',
                institution: edu.college || edu.institution || edu.university || '',
                year_of_completion: edu.year_of_passing || edu.year || null,
            };
        });
    }

    parseDate(dateStr) {
        if (!dateStr) return new Date().toISOString().split('T')[0];
        
        // If already in YYYY-MM-DD format
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
        
        // Try parsing common date formats
        try {
            const date = new Date(dateStr);
            if (!isNaN(date.getTime())) {
                return date.toISOString().split('T')[0];
            }
        } catch (e) {
            // Fall through to default
        }
        
        // Default to current date
        return new Date().toISOString().split('T')[0];
    }

    validateRequiredFields(cvData) {
        const errors = [];
        
        // Check personal details
        if (!cvData.personal_details?.full_name) {
            errors.push('Full name is required');
        }
        if (!cvData.personal_details?.current_title) {
            errors.push('Current title/position is required');
        }
        if (!cvData.personal_details?.location) {
            errors.push('Location is required');
        }
        
        // Check summary
        if (!cvData.summary?.professional_summary) {
            errors.push('Professional summary is required');
        }
        
        return errors;
    }

    async saveAndValidateCV() {
        if (!this.currentSessionId) {
            this.showNotification('No active session. Please create or load a session first.', 'error');
            return;
        }

        if (!this.currentCVData || Object.keys(this.currentCVData).length === 0) {
            this.showNotification('No CV data to validate. Please build your CV first.', 'error');
            return;
        }

        try {
            // Show loading indicator
            const saveBtn = document.getElementById('saveAndValidate');
            const originalText = saveBtn.innerHTML;
            saveBtn.innerHTML = '<span>⏳</span> Validating...';
            saveBtn.disabled = true;

            // Map CV data to schema format
            const mappedData = this.mapToSchemaFormat(this.currentCVData);
            
            // Pre-validation check
            const validationErrors = this.validateRequiredFields(mappedData);
            if (validationErrors.length > 0) {
                saveBtn.innerHTML = originalText;
                saveBtn.disabled = false;
                
                this.displayValidationFeedback({
                    can_export: false,
                    issues: validationErrors,
                    warnings: ['Please complete the required fields to proceed with validation.']
                });
                
                this.showNotification(`⚠ ${validationErrors.length} required field(s) missing. Please check the validation feedback.`, 'error');
                return;
            }

            // Use the correct review endpoint as per HITL documentation
            const response = await this.request(`${this.apiBase}/cv/review/${this.currentSessionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cv_data: mappedData })
            });

            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('DEBUG: Review response:', data);

            // Update current CV data with validated version
            this.currentCVData = this.getPreferredCVData(data, this.currentCVData);
            this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;

            // Update review status badge
            this.updateReviewStatusBadge(data.review_status);

            // Display validation feedback
            this.displayValidationFeedback(data.validation);
            this.ensureEditableSectionsForValidationIssues(data.validation);

            // Update export button state - check can_export from validation or root level
            const canExport = data.can_export || data.validation?.can_export || false;
            this.updateExportButtonState(data.review_status, canExport);

            // Show appropriate notification
            if (canExport && data.review_status === 'completed') {
                this.showNotification('✓ CV validated successfully! You can now export your CV.', 'success');
            } else if (data.validation && !data.validation.can_export) {
                this.showNotification('⚠ Please address validation issues before exporting.', 'error');
            } else {
                this.showNotification('CV saved. Please review any feedback.', 'info');
            }

            // Keep user in edit mode when there are validation issues so fields remain editable.
            const hasIssues = (data.validation && data.validation.can_export === false)
                || (Array.isArray(data.validation?.issues) && data.validation.issues.length > 0)
                || (Array.isArray(data.validation?.errors) && data.validation.errors.length > 0);

            if (!hasIssues) {
                // Refresh preview only when validation passes.
                await this.refreshCVPreview();
            }
        } catch (error) {
            console.error('Validation error:', error);
            this.showNotification('Failed to validate CV: ' + error.message, 'error');
            
            // Reset button
            const saveBtn = document.getElementById('saveAndValidate');
            saveBtn.innerHTML = '<span>💾</span> Save & Validate';
            saveBtn.disabled = false;
        }
    }

    ensureEditableSectionsForValidationIssues(validationResult) {
        const issues = validationResult?.issues || validationResult?.errors || [];
        if (!Array.isArray(issues) || issues.length === 0) return;

        let maxProjectIndex = 0;
        let maxEducationIndex = 0;

        issues.forEach(issue => {
            const projectMatch = String(issue).match(/Project\s*#(\d+)/i);
            const educationMatch = String(issue).match(/Education\s*#(\d+)/i);
            if (projectMatch) {
                maxProjectIndex = Math.max(maxProjectIndex, parseInt(projectMatch[1], 10) || 0);
            }
            if (educationMatch) {
                maxEducationIndex = Math.max(maxEducationIndex, parseInt(educationMatch[1], 10) || 0);
            }
        });

        if (maxProjectIndex === 0 && maxEducationIndex === 0) return;

        if (!this.isEditMode) {
            this.toggleEditMode();
        }

        const educationContainer = document.getElementById('education-entries');
        if (educationContainer && maxEducationIndex > 0) {
            while (educationContainer.querySelectorAll('.education-entry').length < maxEducationIndex) {
                this.addEducationEntry();
            }
        }

        const projectContainer = document.getElementById('project-entries');
        if (projectContainer && maxProjectIndex > 0) {
            while (projectContainer.querySelectorAll('.project-entry').length < maxProjectIndex) {
                this.addProjectEntry();
            }
        }

        const firstTarget =
            document.getElementById('edit_project_role_0') ||
            document.getElementById('edit_institution_0') ||
            document.getElementById('education-edit-section') ||
            document.getElementById('projects-edit-section');

        if (firstTarget) {
            firstTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        this.showNotification('Validation issues found. Edit mode opened so you can update the flagged Project/Education rows.', 'info');
    }

    updateReviewStatusBadge(status) {
        const badge = document.getElementById('reviewStatusBadge');
        if (!badge) return;

        const icon = badge.querySelector('.status-icon');
        const text = badge.querySelector('.status-text');

        badge.style.display = 'flex';

        // Map backend status to UI status
        if (status === 'completed' || status === 'approved') {
            badge.className = 'review-status-badge status-approved';
            if (icon) icon.textContent = '✓';
            if (text) text.textContent = 'Validated';
        } else if (status === 'in_progress' || status === 'pending') {
            badge.className = 'review-status-badge status-pending';
            if (icon) icon.textContent = '⏳';
            if (text) text.textContent = 'Pending Review';
        } else if (status === 'rejected') {
            badge.className = 'review-status-badge status-rejected';
            if (icon) icon.textContent = '✗';
            if (text) text.textContent = 'Issues Found';
        } else {
            badge.style.display = 'none';
        }
    }

    displayValidationFeedback(validationResult) {
        const feedbackPanel = document.getElementById('validationFeedback');
        if (!feedbackPanel) return;

        const feedbackContent = document.getElementById('validationContent');
        const feedbackIcon = feedbackPanel.querySelector('.validation-icon');

        if (!validationResult) {
            feedbackPanel.style.display = 'none';
            return;
        }

        feedbackPanel.style.display = 'block';

        let html = '';
        const canExport = validationResult.can_export !== false;
        // backend returns 'errors'; earlier code used 'issues' — support both
        const issues = validationResult.issues || validationResult.errors || [];
        const warnings = validationResult.warnings || [];

        // Update icon and panel style based on validation result
        if (canExport && issues.length === 0) {
            if (feedbackIcon) feedbackIcon.textContent = '✓';
            feedbackPanel.className = 'validation-feedback validation-success';
            html += `<div class="validation-score">
                <strong>Status:</strong> ✓ Your CV is ready for export!
            </div>`;
        } else {
            if (feedbackIcon) feedbackIcon.textContent = '⚠';
            feedbackPanel.className = 'validation-feedback validation-warning';
            html += `<div class="validation-score">
                <strong>Status:</strong> ⚠ Please address the following issues
            </div>`;
        }

        // Display critical issues
        if (issues && issues.length > 0) {
            const prettyIssues = issues.map(issue => {
                if (typeof issue !== 'string') return issue;
                if (issue.includes('Validation failed:')) {
                    return 'Some saved data has an older format. Please click Save Changes once more; the system will automatically normalize it.';
                }
                return issue;
            });
            html += `<div class="validation-section">
                <h4>⛔ Critical Issues (Must Fix):</h4>
                <ul class="validation-list">
                    ${prettyIssues.map(issue => `<li style="border-left-color: #dc2626;">${issue}</li>`).join('')}
                </ul>
            </div>`;
        }

        // Display warnings
        if (warnings && warnings.length > 0) {
            html += `<div class="validation-section">
                <h4>⚠️ Warnings (Recommended):</h4>
                <ul class="validation-list">
                    ${warnings.map(warning => `<li style="border-left-color: #f59e0b;">${warning}</li>`).join('')}
                </ul>
            </div>`;
        }

        // Success message
        if (canExport && issues.length === 0 && warnings.length === 0) {
            html += `<div class="validation-message" style="background: rgba(16, 185, 129, 0.1); color: #065f46;">
                <strong>✓ Excellent!</strong> Your CV meets all quality standards and is ready for export.
            </div>`;
        }

        // Enhanced next steps guidance with call-to-action
        if (!canExport || issues.length > 0) {
            html += `<div class="validation-message" style="background: rgba(245, 158, 11, 0.1); color: #92400e; padding: 16px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <strong>📝 Next Steps:</strong><br>
                <span style="font-size: 1.05em;">Edit Mode has been activated automatically. Please fill in the required fields below.</span><br>
                <small style="opacity: 0.8;">After making changes, click "Save Changes" to automatically validate again.</small>
            </div>`;
            
            // Auto-enable edit mode IMMEDIATELY if not already in edit mode
            if (!this.isEditMode && issues.length > 0) {
                // Enable edit mode immediately without delays
                this.isEditMode = true;
                this.editableData = JSON.parse(JSON.stringify(this.currentCVData));
                const toggleBtn = document.getElementById('toggleEditMode');
                if (toggleBtn) {
                    toggleBtn.innerHTML = '<span>👁️</span> View Mode';
                    toggleBtn.classList.add('btn-edit-active');
                }
                
                // Render editable form immediately
                setTimeout(() => {
                    this.renderEditablePreview();
                    
                    // Focus on the first missing required field after a short delay
                    setTimeout(() => {
                        // Check which field is missing and focus it
                        if (issues.some(issue => issue.toLowerCase().includes('location'))) {
                            const locationField = document.getElementById('edit_location');
                            if (locationField) {
                                locationField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                locationField.focus();
                                locationField.style.border = '2px solid #f59e0b';
                                locationField.style.backgroundColor = '#fffbeb';
                            }
                        } else if (issues.some(issue => issue.toLowerCase().includes('name'))) {
                            const nameField = document.getElementById('edit_full_name');
                            if (nameField) {
                                nameField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                nameField.focus();
                            }
                        }
                    }, 300);
                }, 100);
            }
        }

        if (feedbackContent) {
            feedbackContent.innerHTML = html || '<p>Validation completed with no specific feedback.</p>';
        }
    }

    updateExportButtonState(reviewStatus, canExport) {
        const exportBtn = document.getElementById('exportCV');
        if (!exportBtn) return;

        // Enable export if review is completed and validation passed
        if ((reviewStatus === 'completed' || reviewStatus === 'approved') && canExport) {
            exportBtn.disabled = false;
            exportBtn.title = 'Export your validated CV';
            exportBtn.classList.remove('btn-disabled');
        } else {
            exportBtn.disabled = true;
            
            if (!canExport) {
                exportBtn.title = '⚠ Please fix validation issues before exporting';
            } else if (reviewStatus === 'pending' || reviewStatus === 'in_progress') {
                exportBtn.title = '⏳ Please complete validation before exporting';
            } else {
                exportBtn.title = '💾 Click "Save & Validate" first';
            }
            
            exportBtn.classList.add('btn-disabled');
        }
    }

    toggleEditMode() {
        if (!this.currentSessionId || !this.currentCVData) {
            this.showNotification('No CV data to edit. Please build your CV first.', 'error');
            return;
        }

        this.isEditMode = !this.isEditMode;
        const toggleBtn = document.getElementById('toggleEditMode');
        
        if (this.isEditMode) {
            // Store a copy of current data for editing
            this.editableData = JSON.parse(JSON.stringify(this.currentCVData));
            toggleBtn.innerHTML = '<span>👁️</span> View Mode';
            toggleBtn.classList.add('btn-edit-active');
            this.renderEditablePreview();
        } else {
            // Exit edit mode without saving
            toggleBtn.innerHTML = '<span>✏️</span> Edit CV';
            toggleBtn.classList.remove('btn-edit-active');
            this.editableData = null;
            this.refreshCVPreview();
        }
    }

    renderEditablePreview() {
        const preview = document.getElementById('cvPreview');
        const html = this.generateEditableFormHTML(this.editableData);
        preview.innerHTML = `
            <div class="cv-edit-form">
                <div class="edit-mode-header">
                    <h3>📝 Edit Mode - Make Changes Below</h3>
                    <div class="edit-actions">
                        <button class="btn btn-secondary" onclick="window.cvApp.cancelEdit()">Cancel</button>
                        <button class="btn btn-primary" onclick="window.cvApp.saveEditedCV()">
                            <span>💾</span> Save Changes
                        </button>
                    </div>
                </div>
                ${html}
            </div>
        `;
    }

    generateEditableFormHTML(cvData) {
        const canonicalCandidate = cvData.candidate || {};
        const canonicalLocation = canonicalCandidate.currentLocation || {};
        const profile = cvData.header || cvData.personal_details || {
            full_name: canonicalCandidate.fullName || '',
            current_title: canonicalCandidate.currentDesignation || canonicalCandidate.designation || '',
            location: canonicalLocation.fullAddress || [canonicalLocation.city, canonicalLocation.country].filter(Boolean).join(', '),
            total_experience: canonicalCandidate.totalExperienceYears || '',
            current_organization: canonicalCandidate.currentOrganization || '',
            email: canonicalCandidate.email || '',
            phone: canonicalCandidate.phoneNumber || '',
            linkedin: cvData.personalDetails?.linkedinUrl || ''
        };
        const summary = cvData.summary || { professional_summary: canonicalCandidate.summary || '' };
        const skills = cvData.skills || {};
        const education = cvData.education || [];
        const workExperience = cvData.work_experience || [];
        const projectExperience = (() => {
            const candidates = [
                cvData.project_experience,
                cvData.projectExperience,
                cvData.projects,
                cvData.experience?.projects,
                cvData.experience?.project_experience,
                cvData.experience?.projectExperience,
            ];
            for (const candidate of candidates) {
                if (Array.isArray(candidate) && candidate.length > 0) {
                    return candidate;
                }
            }
            return [];
        })();

        const canonicalUnmapped = this.currentCanonicalCV?.unmappedData || cvData.unmappedData || {};
        
        let html = '<form id="cvEditForm" class="cv-edit-sections">';
        
        // Personal Details Section - ENHANCED with ALL missing fields and better data mapping
        html += `
            <div class="edit-section">
                <h3 class="section-title">📋 Personal Details</h3>
                <div class="form-grid">
                    <div class="form-group required">
                        <label for="edit_full_name">Full Name *</label>
                        <input type="text" id="edit_full_name" class="form-control" 
                               value="${this.escapeHtml(profile.full_name || '')}" required>
                    </div>
                    <div class="form-group">
                        <label for="edit_portal_id">Portal ID / Employee ID</label>
                        <input type="text" id="edit_portal_id" class="form-control" 
                               value="${this.escapeHtml(profile.portal_id || profile.employee_id || '')}"
                               placeholder="e.g., EMP123456 or your portal ID">
                        <small class="form-help">Your company portal ID or employee ID for export</small>
                    </div>
                    <div class="form-group required">
                        <label for="edit_current_title">Current Title *</label>
                        <input type="text" id="edit_current_title" class="form-control" 
                               value="${this.escapeHtml(profile.current_title || '')}" required>
                    </div>
                    <div class="form-group required">
                        <label for="edit_location">Location *</label>
                        <input type="text" id="edit_location" class="form-control" 
                               value="${this.escapeHtml(profile.location || '')}" 
                               placeholder="e.g., New York, USA or Bangalore, India" required
                               autocomplete="off">
                        <small class="form-help" style="color: #059669; font-weight: 500;">
                            ✓ Enter your city and country (e.g., "San Francisco, USA" or "Mumbai, India")
                        </small>
                    </div>
                    <div class="form-group">
                        <label for="edit_total_experience">Total Experience (years)</label>
                        <input type="number" id="edit_total_experience" class="form-control" 
                               value="${this.extractTotalExperienceValue(profile, cvData)}" min="0" step="0.5"
                               placeholder="e.g., 5.5">
                        <small class="form-help">Your total years of professional experience</small>
                    </div>
                    <div class="form-group">
                        <label for="edit_current_organization">Current Organization</label>
                        <input type="text" id="edit_current_organization" class="form-control" 
                               value="${this.escapeHtml(profile.current_organization || '')}"
                               placeholder="e.g., Microsoft, Google, NTT DATA">
                    </div>
                    <div class="form-group">
                        <label for="edit_email">Email</label>
                        <input type="email" id="edit_email" class="form-control" 
                               value="${this.escapeHtml(profile.email || '')}"
                               placeholder="your.email@company.com">
                    </div>
                    <div class="form-group">
                        <label for="edit_phone">Phone Number</label>
                        <input type="tel" id="edit_phone" class="form-control" 
                               value="${this.escapeHtml(profile.phone || profile.contact_number || '')}"
                               placeholder="e.g., +1-555-123-4567 or +91-9876543210">
                        <small class="form-help">Include country code for international format</small>
                    </div>
                    <div class="form-group">
                        <label for="edit_linkedin">LinkedIn</label>
                        <input type="url" id="edit_linkedin" class="form-control" 
                               value="${this.escapeHtml(profile.linkedin || '')}"
                               placeholder="https://linkedin.com/in/yourprofile">
                    </div>
                </div>
            </div>
        `;

        // Summary Section
        const summaryText = this.extractSummaryText(summary);
        html += `
            <div class="edit-section">
                <h3 class="section-title">📝 Professional Summary</h3>
                <div class="form-group required">
                    <label for="edit_summary">Summary *</label>
                    <textarea id="edit_summary" class="form-control" rows="5" required
                              placeholder="Write a compelling professional summary...">${this.escapeHtml(summaryText || '')}</textarea>
                    <small class="form-help">Describe your professional background, key strengths, and career objectives.</small>
                </div>
                <div class="form-group">
                    <label for="edit_target_role">Target Role</label>
                    <input type="text" id="edit_target_role" class="form-control" 
                           value="${this.escapeHtml(summary.target_role || cvData.target_role || '')}"
                           placeholder="e.g., Senior Software Engineer, Data Scientist">
                </div>
            </div>
        `;

        // Skills Section - ENHANCED with better secondary skills handling and multiple field mapping
        const primarySkills = Array.isArray(skills.primary_skills) ? skills.primary_skills : 
                     Array.isArray(skills.primarySkills) ? skills.primarySkills :
                             Array.isArray(skills) ? skills : [];
        const secondarySkills = skills.secondary_skills || skills.secondarySkills || cvData.secondary_skills || cvData.secondarySkills ||
                       cvData.skills?.secondary_skills || cvData.skills?.secondarySkills || [];
        const toolsPlatforms = skills.tools_and_platforms || skills.toolsAndPlatforms || cvData.tools_and_platforms || cvData.toolsAndPlatforms ||
                              cvData.ai_frameworks || cvData.cloud_platforms || [];
        const domainExpertise = (skills.domain_expertise
            || skills.domainExpertise
            || skills.domains
            || cvData.domain_expertise
            || cvData.domainExpertise
            || cvData.domains
            || cvData.experience?.domainExperience
            || cvData.experience?.domain_expertise
            || cvData.experience?.domainExpertise
            || cvData.experience?.domains
            || []);
        
        html += `
            <div class="edit-section">
                <h3 class="section-title">💡 Skills & Expertise</h3>
                <div class="form-group required">
                    <label for="edit_primary_skills">Primary Skills *</label>
                    <textarea id="edit_primary_skills" class="form-control" rows="3" required
                              placeholder="Enter skills separated by commas">${this.escapeHtml(primarySkills.join(', '))}</textarea>
                    <small class="form-help">Your core technical skills (e.g., Python, JavaScript, AWS, Machine Learning)</small>
                </div>
                <div class="form-group">
                    <label for="edit_secondary_skills">Secondary Skills</label>
                    <textarea id="edit_secondary_skills" class="form-control" rows="2"
                              placeholder="Enter skills separated by commas">${this.escapeHtml(secondarySkills.join(', '))}</textarea>
                    <small class="form-help">Additional skills and competencies (e.g., Project Management, Agile, DevOps)</small>
                </div>
                <div class="form-group">
                    <label for="edit_tools_platforms">Tools & Platforms</label>
                    <textarea id="edit_tools_platforms" class="form-control" rows="2"
                              placeholder="Enter tools separated by commas">${this.escapeHtml(toolsPlatforms.join(', '))}</textarea>
                    <small class="form-help">Software tools, platforms, and frameworks you use</small>
                </div>
                <div class="form-group">
                    <label for="edit_domain_expertise">Domain Expertise</label>
                    <textarea id="edit_domain_expertise" class="form-control" rows="2"
                              placeholder="Enter domains separated by commas">${this.escapeHtml(domainExpertise.join(', '))}</textarea>
                    <small class="form-help">Business domains or industries (e.g., Healthcare, Finance, E-commerce)</small>
                </div>
            </div>
        `;

        // Education Section - NEW ADDITION
        html += this.generateEducationEditSection(education);
        
        // Project Experience Section - NEW ADDITION
        html += this.generateProjectExperienceEditSection(projectExperience);

        // Others Section - captured unmapped details from canonical pipeline
        html += this.generateOthersEditSection(canonicalUnmapped);

        html += '</form>';
        html += '<p class="form-note"><strong>Note:</strong> Fields marked with * are required for CV validation. Other sections help improve the completeness of your CV.</p>';
        
        return html;
    }

    generateEducationEditSection(education) {
        const educationArray = Array.isArray(education) ? education : (education ? [education] : []);
        // Always show at least one blank entry
        const entries = educationArray.length > 0 ? educationArray : [{}];

        let html = `
            <div class="edit-section" id="education-edit-section">
                <h3 class="section-title">🎓 Education</h3>
                <div id="education-entries">
        `;

        entries.forEach((edu, idx) => {
            html += this._generateEducationEntryHTML(edu, idx);
        });

        html += `
                </div>
                <button type="button" class="btn btn-secondary" 
                        style="margin-top:8px;" 
                        onclick="window.cvApp.addEducationEntry()">+ Add Education</button>
            </div>
        `;
        return html;
    }

    _generateEducationEntryHTML(edu, idx) {
        return `
            <div class="education-entry form-grid" data-edu-index="${idx}" style="border:1px solid #e5e7eb;border-radius:6px;padding:12px;margin-bottom:10px;">
                <div style="grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;">
                    <strong>Entry ${idx + 1}</strong>
                    ${idx > 0 ? `<button type="button" class="btn btn-sm" style="background:#fee2e2;color:#dc2626;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;" onclick="window.cvApp.removeEducationEntry(${idx})">Remove</button>` : ''}
                </div>
                <div class="form-group">
                    <label for="edit_degree_${idx}">Degree/Qualification *</label>
                    <input type="text" id="edit_degree_${idx}" class="form-control" 
                           value="${this.escapeHtml(edu.degree || edu.qualification || '')}"
                           placeholder="e.g., Bachelor of Engineering, MBA">
                </div>
                <div class="form-group">
                    <label for="edit_institution_${idx}">Institution/University *</label>
                    <input type="text" id="edit_institution_${idx}" class="form-control" 
                           value="${this.escapeHtml(edu.institution || edu.university || edu.college || '')}"
                           placeholder="e.g., MIT, Stanford University">
                </div>
                <div class="form-group">
                    <label for="edit_university_${idx}">Affiliating University</label>
                    <input type="text" id="edit_university_${idx}" class="form-control" 
                           value="${this.escapeHtml(edu.university || '')}"
                           placeholder="e.g., Telangana University">
                </div>
                <div class="form-group">
                    <label for="edit_graduation_year_${idx}">Graduation Year</label>
                    <input type="number" id="edit_graduation_year_${idx}" class="form-control" 
                           value="${edu.year || edu.graduation_year || edu.year_of_completion || ''}" 
                           min="1970" max="2030" placeholder="e.g., 2020">
                </div>
                <div class="form-group">
                    <label for="edit_grade_${idx}">Grade/Percentage</label>
                    <input type="text" id="edit_grade_${idx}" class="form-control" 
                           value="${this.escapeHtml(edu.grade || edu.percentage || edu.gpa || '')}"
                           placeholder="e.g., 8.5 CGPA, 85%, First Class">
                </div>
            </div>
        `;
    }

    addEducationEntry() {
        const container = document.getElementById('education-entries');
        if (!container) return;
        const idx = container.querySelectorAll('.education-entry').length;
        const div = document.createElement('div');
        div.innerHTML = this._generateEducationEntryHTML({}, idx);
        container.appendChild(div.firstElementChild);
    }

    removeEducationEntry(idx) {
        const entry = document.querySelector(`[data-edu-index="${idx}"]`);
        if (entry) entry.remove();
        // Re-index remaining entries
        const entries = document.querySelectorAll('.education-entry');
        entries.forEach((el, i) => {
            el.setAttribute('data-edu-index', i);
            el.querySelector('strong').textContent = `Entry ${i + 1}`;
        });
    }

    _collectEducationFromForm() {
        const entries = document.querySelectorAll('.education-entry');
        const result = [];
        entries.forEach((entry) => {
            const degree = entry.querySelector('[id^="edit_degree_"]')?.value?.trim() || '';
            const institution = entry.querySelector('[id^="edit_institution_"]')?.value?.trim() || '';
            const university = entry.querySelector('[id^="edit_university_"]')?.value?.trim() || '';
            const year = entry.querySelector('[id^="edit_graduation_year_"]')?.value?.trim() || '';
            const grade = entry.querySelector('[id^="edit_grade_"]')?.value?.trim() || '';
            if (degree || institution || year) {
                result.push({
                    degree, qualification: degree,
                    institution, university: university || institution,
                    college: institution,
                    year: year ? parseInt(year) : null,
                    graduation_year: year ? parseInt(year) : null,
                    year_of_completion: year ? parseInt(year) : null,
                    grade, percentage: grade, gpa: grade
                });
            }
        });
        return result;
    }

    generateProjectExperienceEditSection(projectExperience) {
        const projectArray = Array.isArray(projectExperience) ? projectExperience : (projectExperience ? [projectExperience] : []);
        const entries = projectArray.length > 0 ? projectArray : [{}];

        let html = `
            <div class="edit-section" id="projects-edit-section">
                <h3 class="section-title">🚀 Project Experience</h3>
                <div id="project-entries">
        `;

        entries.forEach((proj, idx) => {
            html += this._generateProjectEntryHTML(proj, idx);
        });

        html += `
                </div>
                <button type="button" class="btn btn-secondary" 
                        style="margin-top:8px;"
                        onclick="window.cvApp.addProjectEntry()">+ Add Project</button>
            </div>
        `;
        return html;
    }

    _generateProjectEntryHTML(proj, idx) {
        const techs = (proj.technologies || proj.technologies_used || proj.toolsUsed || []).join(', ');
        const responsibilities = (proj.responsibilities || []).join('\n');
        const roleValue = proj.role || proj.designation || proj.role_title || proj.position || '';
        const durationValue = proj.duration || (proj.durationFrom && proj.durationTo ? `${proj.durationFrom} to ${proj.durationTo}` : (proj.durationFrom || proj.durationTo || ''));
        return `
            <div class="project-entry form-grid" data-proj-index="${idx}" style="border:1px solid #e5e7eb;border-radius:6px;padding:12px;margin-bottom:10px;">
                <div style="grid-column:1/-1;display:flex;justify-content:space-between;align-items:center;">
                    <strong>Project ${idx + 1}</strong>
                    ${idx > 0 ? `<button type="button" class="btn btn-sm" style="background:#fee2e2;color:#dc2626;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;" onclick="window.cvApp.removeProjectEntry(${idx})">Remove</button>` : ''}
                </div>
                <div class="form-group">
                    <label for="edit_project_name_${idx}">Project Name</label>
                    <input type="text" id="edit_project_name_${idx}" class="form-control" 
                           value="${this.escapeHtml(proj.project_name || proj.projectName || proj.name || '')}"
                           placeholder="e.g., E-commerce Platform, Data Analytics Dashboard">
                </div>
                <div class="form-group">
                    <label for="edit_client_${idx}">Client/Organization</label>
                    <input type="text" id="edit_client_${idx}" class="form-control" 
                           value="${this.escapeHtml(proj.client || proj.client_name || proj.clientName || '')}"
                           placeholder="e.g., Microsoft, Internal Project">
                </div>
                <div class="form-group">
                    <label for="edit_project_role_${idx}">Your Role *</label>
                    <input type="text" id="edit_project_role_${idx}" class="form-control" 
                           value="${this.escapeHtml(roleValue)}"
                           placeholder="e.g., Lead Developer, Technical Architect">
                </div>
                <div class="form-group">
                    <label for="edit_project_duration_${idx}">Duration</label>
                    <input type="text" id="edit_project_duration_${idx}" class="form-control" 
                           value="${this.escapeHtml(durationValue)}"
                           placeholder="e.g., Jan 2022 to Jun 2022">
                </div>
                <div class="form-group">
                    <label for="edit_project_technologies_${idx}">Technologies Used</label>
                    <textarea id="edit_project_technologies_${idx}" class="form-control" rows="2"
                              placeholder="Enter technologies separated by commas">${this.escapeHtml(techs)}</textarea>
                </div>
                <div class="form-group" style="grid-column:1/-1;">
                    <label for="edit_project_description_${idx}">Project Description</label>
                    <textarea id="edit_project_description_${idx}" class="form-control" rows="3"
                              placeholder="Describe the project and your key contributions">${this.escapeHtml(proj.description || proj.project_description || proj.projectDescription || '')}</textarea>
                </div>
                <div class="form-group" style="grid-column:1/-1;">
                    <label for="edit_project_responsibilities_${idx}">Responsibilities (one per line)</label>
                    <textarea id="edit_project_responsibilities_${idx}" class="form-control" rows="4"
                              placeholder="• Developed REST APIs&#10;• Integrated Azure services">${this.escapeHtml(responsibilities)}</textarea>
                </div>
            </div>
        `;
    }

    addProjectEntry() {
        const container = document.getElementById('project-entries');
        if (!container) return;
        const idx = container.querySelectorAll('.project-entry').length;
        const div = document.createElement('div');
        div.innerHTML = this._generateProjectEntryHTML({}, idx);
        container.appendChild(div.firstElementChild);
    }

    removeProjectEntry(idx) {
        const entry = document.querySelector(`[data-proj-index="${idx}"]`);
        if (entry) entry.remove();
        const entries = document.querySelectorAll('.project-entry');
        entries.forEach((el, i) => {
            el.setAttribute('data-proj-index', i);
            el.querySelector('strong').textContent = `Project ${i + 1}`;
        });
    }

    _collectProjectsFromForm() {
        const entries = document.querySelectorAll('.project-entry');
        const result = [];
        entries.forEach((entry) => {
            const idx = entry.getAttribute('data-proj-index');
            const existingProjects = Array.isArray(this.currentCVData?.project_experience) ? this.currentCVData.project_experience : [];
            const existing = existingProjects[idx] || {};
            const name = entry.querySelector('[id^="edit_project_name_"]')?.value?.trim() || '';
            const client = entry.querySelector('[id^="edit_client_"]')?.value?.trim() || '';
            const roleInput = entry.querySelector('[id^="edit_project_role_"]')?.value?.trim() || '';
            const role = roleInput || existing.role || existing.designation || existing.role_title || existing.position || '';
            const duration = entry.querySelector('[id^="edit_project_duration_"]')?.value?.trim() || '';
            const techText = entry.querySelector('[id^="edit_project_technologies_"]')?.value?.trim() || '';
            const desc = entry.querySelector('[id^="edit_project_description_"]')?.value?.trim() || '';
            const respText = entry.querySelector('[id^="edit_project_responsibilities_"]')?.value?.trim() || '';
            const technologies = techText ? techText.split(',').map(s => s.trim()).filter(Boolean) : [];
            const responsibilities = respText ? respText.split('\n').map(s => s.replace(/^[•\-\*]\s*/, '').trim()).filter(Boolean) : [];
            if (name || role || desc) {
                result.push({
                    project_name: name, name,
                    client, client_name: client,
                    role, duration,
                    technologies, technologies_used: technologies,
                    description: desc, project_description: desc,
                    responsibilities,
                    outcomes: []
                });
            }
        });
        return result;
    }

    flattenUnmappedEntries(unmappedData) {
        const entries = [];
        if (!unmappedData || typeof unmappedData !== 'object') return entries;

        Object.entries(unmappedData).forEach(([source, bucket]) => {
            if (!bucket || typeof bucket !== 'object') return;
            Object.entries(bucket).forEach(([key, value]) => {
                const asText = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
                if (!asText || !String(asText).trim()) return;
                entries.push({ source, key, valueText: asText });
            });
        });

        return entries;
    }

    inferTargetPathFromUnmappedKey(source, key, valueText = '') {
        const normalizedSource = String(source || '').toLowerCase();
        const normalizedKey = String(key || '')
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, '');
        const normalizedValue = String(valueText || '').toLowerCase();

        const directMap = {
            portal_id: 'candidate.portalId',
            employee_id: 'candidate.portalId',
            emp_id: 'candidate.portalId',
            email: 'candidate.email',
            email_id: 'candidate.email',
            mail: 'candidate.email',
            phone: 'candidate.phoneNumber',
            phone_number: 'candidate.phoneNumber',
            contact_number: 'candidate.phoneNumber',
            mobile: 'candidate.phoneNumber',
            linkedin: 'personalDetails.linkedinUrl',
            linkedin_url: 'personalDetails.linkedinUrl',
            current_title: 'candidate.currentDesignation',
            designation: 'candidate.currentDesignation',
            current_designation: 'candidate.currentDesignation',
            current_organization: 'candidate.currentOrganization',
            company: 'candidate.currentOrganization',
            summary: 'candidate.summary',
            professional_summary: 'candidate.summary',
            primary_skills: 'skills.primarySkills',
            secondary_skills: 'skills.secondarySkills',
            domain_expertise: 'experience.domainExperience',
            domains: 'experience.domainExperience',
        };

        if (directMap[normalizedKey]) {
            return directMap[normalizedKey];
        }

        if (normalizedKey.includes('skill')) {
            if (normalizedKey.includes('secondary')) return 'skills.secondarySkills';
            return 'skills.primarySkills';
        }

        if (normalizedKey.includes('domain') || normalizedKey.includes('industry')) {
            return 'experience.domainExperience';
        }

        if (normalizedKey.includes('linkedin')) {
            return 'personalDetails.linkedinUrl';
        }

        if (normalizedKey.includes('mail') || normalizedValue.includes('@')) {
            return 'candidate.email';
        }

        if (normalizedKey.includes('phone') || normalizedKey.includes('mobile') || normalizedKey.includes('contact')) {
            return 'candidate.phoneNumber';
        }

        if (normalizedKey.includes('portal') || normalizedKey.includes('employee')) {
            return 'candidate.portalId';
        }

        if (normalizedKey.includes('role') || normalizedKey.includes('title') || normalizedKey.includes('designation')) {
            return 'candidate.currentDesignation';
        }

        if (normalizedKey.includes('organization') || normalizedKey.includes('company') || normalizedKey.includes('employer')) {
            return 'candidate.currentOrganization';
        }

        if (normalizedSource.includes('questionnaire') && (normalizedKey.includes('profile') || normalizedKey.includes('summary'))) {
            return 'candidate.summary';
        }

        return '';
    }

    generateOthersEditSection(unmappedData) {
        const entries = this.flattenUnmappedEntries(unmappedData);
        if (entries.length === 0) {
            return `
                <div class="edit-section" id="others-edit-section">
                    <h3 class="section-title">🧩 Others (Unmapped Details)</h3>
                    <p class="form-help">No unmapped details found for this CV.</p>
                </div>
            `;
        }

        const suggestedTargets = [
            'candidate.portalId',
            'candidate.phoneNumber',
            'candidate.email',
            'candidate.currentDesignation',
            'candidate.currentOrganization',
            'candidate.summary',
            'skills.primarySkills',
            'skills.secondarySkills',
            'experience.domainExperience',
            'personalDetails.linkedinUrl',
        ];

        let html = `
            <div class="edit-section" id="others-edit-section">
                <h3 class="section-title">🧩 Others (Unmapped Details)</h3>
                <p class="form-help">These details were captured but not auto-mapped. Optionally map them below.</p>
                <div style="display:flex;justify-content:flex-end;gap:8px;margin:8px 0 14px;">
                    <button type="button" class="btn btn-secondary" onclick="window.cvApp.resetOthersIncludes()">
                        ↺ Reset Includes
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="window.cvApp.applySuggestedOthersMappings()">
                        ✨ Apply Suggested Mappings
                    </button>
                </div>
                <datalist id="others-target-suggestions">
                    ${suggestedTargets.map((t) => `<option value="${this.escapeHtml(t)}"></option>`).join('')}
                </datalist>
                <div id="others-mapping-entries">
        `;

        entries.forEach((entry, idx) => {
            const suggestedTarget = this.inferTargetPathFromUnmappedKey(entry.source, entry.key, entry.valueText);
            html += `
                <div class="others-mapping-row" data-others-index="${idx}" style="border:1px solid #e5e7eb;border-radius:6px;padding:12px;margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                        <strong>${this.escapeHtml(entry.source)} / ${this.escapeHtml(entry.key)}</strong>
                        <label style="display:flex;align-items:center;gap:6px;">
                            <input type="checkbox" id="others_include_${idx}" checked>
                            Include
                        </label>
                    </div>
                    <div class="form-group">
                        <label for="others_target_${idx}">Map To Canonical Field</label>
                        <input type="text" id="others_target_${idx}" class="form-control" list="others-target-suggestions"
                               value="${this.escapeHtml(suggestedTarget)}"
                               placeholder="e.g., candidate.portalId or skills.primarySkills">
                        ${suggestedTarget
                            ? `<small class="form-help">Suggested mapping: ${this.escapeHtml(suggestedTarget)}</small>`
                            : '<small class="form-help">No automatic suggestion. Choose a canonical path if you want to map this value.</small>'}
                    </div>
                    <div class="form-group">
                        <label for="others_value_${idx}">Captured Value</label>
                        <textarea id="others_value_${idx}" class="form-control" rows="3">${this.escapeHtml(entry.valueText)}</textarea>
                    </div>
                    <input type="hidden" id="others_source_${idx}" value="${this.escapeHtml(entry.source)}">
                    <input type="hidden" id="others_key_${idx}" value="${this.escapeHtml(entry.key)}">
                </div>
            `;
        });

        html += '</div></div>';
        return html;
    }

    applySuggestedOthersMappings() {
        const rows = document.querySelectorAll('.others-mapping-row');
        if (!rows.length) {
            this.showNotification('No Others rows available to map.', 'info');
            return;
        }

        let applied = 0;
        let skipped = 0;

        rows.forEach((row) => {
            const idx = row.getAttribute('data-others-index');
            const source = document.getElementById(`others_source_${idx}`)?.value || '';
            const key = document.getElementById(`others_key_${idx}`)?.value || '';
            const valueText = document.getElementById(`others_value_${idx}`)?.value || '';
            const targetInput = document.getElementById(`others_target_${idx}`);
            const includeInput = document.getElementById(`others_include_${idx}`);

            if (!targetInput || !includeInput) {
                skipped += 1;
                return;
            }

            const suggested = this.inferTargetPathFromUnmappedKey(source, key, valueText);
            if (suggested) {
                targetInput.value = suggested;
                includeInput.checked = true;
                applied += 1;
            } else {
                includeInput.checked = false;
                skipped += 1;
            }
        });

        this.showNotification(
            `Applied ${applied} suggested mapping(s). ${skipped} row(s) left unmapped and excluded.`,
            applied > 0 ? 'success' : 'info'
        );
    }

    resetOthersIncludes() {
        const rows = document.querySelectorAll('.others-mapping-row');
        if (!rows.length) {
            this.showNotification('No Others rows available to reset.', 'info');
            return;
        }

        let resetCount = 0;
        rows.forEach((row) => {
            const idx = row.getAttribute('data-others-index');
            const includeInput = document.getElementById(`others_include_${idx}`);
            if (!includeInput) return;
            includeInput.checked = true;
            resetCount += 1;
        });

        this.showNotification(`Reset includes for ${resetCount} row(s).`, 'success');
    }

    _collectOthersMappingsFromForm() {
        const rows = document.querySelectorAll('.others-mapping-row');
        const mappings = [];
        rows.forEach((row) => {
            const idx = row.getAttribute('data-others-index');
            const include = document.getElementById(`others_include_${idx}`)?.checked;
            if (!include) return;

            const source = document.getElementById(`others_source_${idx}`)?.value || '';
            const key = document.getElementById(`others_key_${idx}`)?.value || '';
            const targetPath = document.getElementById(`others_target_${idx}`)?.value?.trim() || '';
            const value = document.getElementById(`others_value_${idx}`)?.value?.trim() || '';

            if (!value) return;
            mappings.push({
                source,
                key,
                target_path: targetPath,
                value,
            });
        });
        return mappings;
    }

    extractTotalExperienceValue(profile, cvData) {
        // Try multiple sources for total experience value
        let experienceValue = profile.total_experience || 
                             cvData.personal_details?.total_experience || 
                             profile.total_experience_years;
        
        // Handle different formats (string vs number)
        if (typeof experienceValue === 'string') {
            // Extract number from strings like "5 years" or "5.5"
            const match = experienceValue.match(/(\d+(?:\.\d+)?)/);
            if (match) {
                return match[1];
            }
        }
        
        return experienceValue || '';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    cancelEdit() {
        this.isEditMode = false;
        this.editableData = null;
        const toggleBtn = document.getElementById('toggleEditMode');
        toggleBtn.innerHTML = '<span>✏️</span> Edit CV';
        toggleBtn.classList.remove('btn-edit-active');
        this.refreshCVPreview();
        this.showNotification('Edit cancelled', 'info');
    }

    async saveEditedCV() {
        // Prevent multiple simultaneous saves
        if (this._isSaving) {
            console.log('Save already in progress, ignoring duplicate call');
            return;
        }
        this._isSaving = true;
        
        const originalBtnText = '<span>💾</span> Save Changes';
        let saveButton = null;
        
        // Helper function to find and cache the button reference
        const findButton = () => {
            if (!saveButton || !document.body.contains(saveButton)) {
                saveButton = document.querySelector('.edit-actions .btn-primary') || 
                            document.querySelector('.cv-edit-form .btn-primary') ||
                            document.querySelector('button[onclick*="saveEditedCV"]');
            }
            return saveButton;
        };
        
        // Helper function to restore button state
        const restoreButton = () => {
            const btn = findButton();
            if (btn && document.body.contains(btn)) {
                btn.innerHTML = originalBtnText;
                btn.disabled = false;
                btn.style.pointerEvents = 'auto';
                btn.style.opacity = '1';
                btn.classList.remove('btn-loading');
            }
            this._isSaving = false;
        };
        
        // Helper function to set loading state
        const setLoadingState = () => {
            const btn = findButton();
            if (btn) {
                btn.innerHTML = '<span>⏳</span> Saving...';
                btn.disabled = true;
                btn.style.pointerEvents = 'none';
                btn.style.opacity = '0.6';
                btn.classList.add('btn-loading');
                return true;
            } else {
                console.warn('Save button not found in DOM');
                this._isSaving = false;
                return false;
            }
        };
        
        try {
            // Show loading state
            if (!setLoadingState()) {
                this.showNotification('❌ Cannot find save button', 'error');
                return;
            }

            // Auto-create session if missing
            if (!this.currentSessionId) {
                this.showNotification('Creating session...', 'info');
                try {
                    await this.createSession();
                    if (!this.currentSessionId) {
                        restoreButton();
                        throw new Error('Failed to create session');
                    }
                } catch (error) {
                    restoreButton();
                    this.showNotification('❌ Failed to create session: ' + error.message, 'error');
                    return;
                }
            }

            // Collect form data with validation - ENHANCED with ALL new fields
            const fullName = document.getElementById('edit_full_name')?.value?.trim() || '';
            const portalId = document.getElementById('edit_portal_id')?.value?.trim() || '';
            const currentTitle = document.getElementById('edit_current_title')?.value?.trim() || '';
            const location = document.getElementById('edit_location')?.value?.trim() || '';
            const totalExperience = document.getElementById('edit_total_experience')?.value?.trim() || '';
            const currentOrganization = document.getElementById('edit_current_organization')?.value?.trim() || '';
            const email = document.getElementById('edit_email')?.value?.trim() || '';
            const phone = document.getElementById('edit_phone')?.value?.trim() || '';
            const linkedin = document.getElementById('edit_linkedin')?.value?.trim() || '';
            const summary = document.getElementById('edit_summary')?.value?.trim() || '';
            const targetRole = document.getElementById('edit_target_role')?.value?.trim() || '';

            // Skills data
            const primarySkillsText = document.getElementById('edit_primary_skills')?.value?.trim() || '';
            const secondarySkillsText = document.getElementById('edit_secondary_skills')?.value?.trim() || '';
            const toolsPlatformsText = document.getElementById('edit_tools_platforms')?.value?.trim() || '';
            const domainExpertiseText = document.getElementById('edit_domain_expertise')?.value?.trim() || '';

            // Education data — collect all entries from indexed form fields
            const educationData = this._collectEducationFromForm();

            // Project data — collect all entries from indexed form fields
            const projectData = this._collectProjectsFromForm();
            const othersMappings = this._collectOthersMappingsFromForm();

            const updatedData = {
                personal_details: {
                    full_name: fullName,
                    portal_id: portalId || null,
                    employee_id: portalId || null, // Map to both fields for backend compatibility
                    current_title: currentTitle,
                    location: location,
                    total_experience: totalExperience ? parseFloat(totalExperience) : null,
                    current_organization: currentOrganization || null,
                    email: email || null,
                    phone: phone || null,
                    contact_number: phone || null, // Map to both fields for backend compatibility
                    linkedin: linkedin || null,
                },
                summary: {
                    professional_summary: summary,
                    target_role: targetRole || null,
                },
                skills: {
                    primary_skills: primarySkillsText.split(',').map(s => s.trim()).filter(Boolean),
                    secondary_skills: secondarySkillsText.split(',').map(s => s.trim()).filter(Boolean),
                    tools_and_platforms: toolsPlatformsText.split(',').map(s => s.trim()).filter(Boolean),
                    domain_expertise: domainExpertiseText.split(',').map(s => s.trim()).filter(Boolean),
                },
                // Enhanced education mapping - use all collected entries
                education: educationData.length > 0
                    ? educationData
                    : this.mergeEducationData(this.currentCVData?.education || [], {}),
                // Enhanced project mapping - use all collected entries
                project_experience: projectData.length > 0
                    ? projectData
                    : this.mergeProjectData(this.currentCVData?.project_experience || [], {}),
                // Preserve other sections with proper mapping to backend schema
                work_experience: this.mapWorkExperience(this.currentCVData?.work_experience || []),
                certifications: this.mapCertifications(this.currentCVData?.certifications || []),
                // Preserve additional extracted data fields that might be missing
                ai_frameworks: this.currentCVData?.ai_frameworks || [],
                cloud_platforms: this.currentCVData?.cloud_platforms || [],
                operating_systems: this.currentCVData?.operating_systems || [],
                databases: this.currentCVData?.databases || [],
                employment: this.currentCVData?.employment || {},
                // Also include direct fields for export service field mapping
                secondary_skills: secondarySkillsText.split(',').map(s => s.trim()).filter(Boolean),
                tools_and_platforms: toolsPlatformsText.split(',').map(s => s.trim()).filter(Boolean),
                domain_expertise: domainExpertiseText.split(',').map(s => s.trim()).filter(Boolean),
                target_role: targetRole || null,
                schema_version: '1.0',
                // Include header for backward compatibility with export templates
                header: {
                    full_name: fullName,
                    portal_id: portalId || null,
                    employee_id: portalId || null,
                    current_title: currentTitle,
                    location: location,
                    total_experience: totalExperience || null,
                    current_organization: currentOrganization || null,
                    email: email || null,
                    phone: phone || null,
                    contact_number: phone || null,
                    linkedin: linkedin || null,
                    grade: this.currentCVData?.header?.grade || null
                },
                _others_mappings: othersMappings,
            };

            // Enhanced validation with format checks
            const validationResult = this.validateCVData(updatedData);
            
            if (!validationResult.isValid) {
                // ALWAYS restore button on validation failure
                restoreButton();
                
                // Highlight missing fields with detailed feedback
                this.highlightInvalidFields(validationResult.fieldErrors);
                
                // Show detailed error message
                const errorMessage = `⚠️ Please fix the following issues:\n\n${validationResult.errors.join('\n')}\n\n${validationResult.suggestions.join('\n')}`;
                this.showNotification(errorMessage, 'error');
                
                // Scroll to first invalid field
                if (validationResult.fieldErrors.length > 0) {
                    const firstField = document.getElementById(validationResult.fieldErrors[0].fieldId);
                    if (firstField) {
                        firstField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        firstField.focus();
                    }
                }
                return;
            }

            // Save to backend
            const response = await this.request(`${this.apiBase}/cv/review/${this.currentSessionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cv_data: updatedData })
            });

            if (!response.ok) {
                // ALWAYS restore button on backend error
                restoreButton();
                
                // Enhanced error handling for backend errors
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                const backendError = errorData.detail || errorData.message || 'Failed to save changes';
                
                // Show user-friendly error message
                this.showNotification(`❌ Server Error: ${backendError}\n\nPlease check all required fields and try again.`, 'error');
                console.error('Backend validation error:', errorData);
                return;
            }

            const data = await response.json();
            
            // Update current CV data
            this.currentCVData = this.getPreferredCVData(data, updatedData);
            this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
            
            // Show validation results if present
            if (data.validation) {
                this.displayValidationFeedback(data.validation);
                this.updateReviewStatusBadge(data.review_status);
                this.updateExportButtonState(data.review_status, data.can_export);
            }

            const hasValidationIssues = (data.can_export === false)
                || (Array.isArray(data.validation?.issues) && data.validation.issues.length > 0)
                || (Array.isArray(data.validation?.errors) && data.validation.errors.length > 0);

            if (hasValidationIssues) {
                // Keep edit mode active so user can continue fixing fields.
                this.showNotification('⚠ Changes saved, but some required fields are still missing. Please update highlighted fields.', 'error');
                this.ensureEditableSectionsForValidationIssues(data.validation || {});
                restoreButton();
                return;
            }

            // Show success notification immediately
            this.showNotification('✓ Changes saved successfully!', 'success');
            
            // Exit edit mode only when validation is clean
            this.isEditMode = false;
            this.editableData = null;
            const toggleBtn = document.getElementById('toggleEditMode');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<span>✏️</span> Edit CV';
                toggleBtn.classList.remove('btn-edit-active');
            }
            
            // Refresh preview (this will remove the edit form and button from DOM)
            await this.refreshCVPreview();
            
            // Reset the saving flag after everything completes
            this._isSaving = false;
        } catch (error) {
            console.error('Save error:', error);
            // ALWAYS restore button on any error
            restoreButton();
            this.showNotification('❌ Failed to save changes: ' + error.message, 'error');
        } finally {
            // Ensure saving flag is always reset
            this._isSaving = false;
        }
    }

    validateCVData(cvData) {
        const errors = [];
        const suggestions = [];
        const fieldErrors = [];

        // Validate Full Name
        if (!cvData.personal_details.full_name) {
            errors.push('❌ Full Name is required');
            suggestions.push('💡 Enter your complete name (First and Last name)');
            fieldErrors.push({ fieldId: 'edit_full_name', message: 'Required field' });
        } else if (cvData.personal_details.full_name.length < 3) {
            errors.push('❌ Full Name must be at least 3 characters');
            fieldErrors.push({ fieldId: 'edit_full_name', message: 'Too short' });
        }

        // Validate Current Title
        if (!cvData.personal_details.current_title) {
            errors.push('❌ Current Title is required');
            suggestions.push('💡 Enter your job title (e.g., "Senior Software Engineer")');
            fieldErrors.push({ fieldId: 'edit_current_title', message: 'Required field' });
        }

        // Validate Location with format check
        if (!cvData.personal_details.location) {
            errors.push('❌ Location is required');
            suggestions.push('💡 Enter in format: "City, Country" (e.g., "Bangalore, India" or "New York, USA")');
            fieldErrors.push({ fieldId: 'edit_location', message: 'Required field' });
        } else if (!cvData.personal_details.location.includes(',')) {
            errors.push('⚠️ Location format should be "City, Country"');
            suggestions.push('💡 Example: "Mumbai, India" or "London, UK"');
            fieldErrors.push({ fieldId: 'edit_location', message: 'Format: City, Country' });
        } else if (cvData.personal_details.location.length < 5) {
            errors.push('❌ Location seems too short');
            fieldErrors.push({ fieldId: 'edit_location', message: 'Enter full location' });
        }

        // Validate Professional Summary
        if (!cvData.summary.professional_summary) {
            errors.push('❌ Professional Summary is required');
            suggestions.push('💡 Write a brief summary of your professional experience');
            fieldErrors.push({ fieldId: 'edit_summary', message: 'Required field' });
        } else if (cvData.summary.professional_summary.length < 50) {
            errors.push('⚠️ Professional Summary should be at least 50 characters');
            suggestions.push('💡 Provide more detail about your background and expertise');
            fieldErrors.push({ fieldId: 'edit_summary', message: 'Too brief' });
        }

        // Validate Primary Skills
        if (cvData.skills.primary_skills.length === 0) {
            errors.push('❌ At least one Primary Skill is required');
            suggestions.push('💡 Add your key technical skills (e.g., "Python, AWS, Docker")');
            fieldErrors.push({ fieldId: 'edit_primary_skills', message: 'Required field' });
        }

        return {
            isValid: errors.length === 0,
            errors: errors,
            suggestions: suggestions,
            fieldErrors: fieldErrors
        };
    }

    highlightInvalidFields(fieldErrors) {
        // Highlight all invalid fields with visual feedback
        fieldErrors.forEach(error => {
            const field = document.getElementById(error.fieldId);
            if (field) {
                field.style.border = '2px solid #dc2626';
                field.style.backgroundColor = '#fef2f2';
                
                // Add error message below the field
                const existingError = field.parentElement.querySelector('.field-error-message');
                if (existingError) {
                    existingError.remove();
                }
                
                const errorMsg = document.createElement('small');
                errorMsg.className = 'field-error-message';
                errorMsg.style.cssText = 'color: #dc2626; display: block; margin-top: 4px; font-weight: 500;';
                errorMsg.textContent = `⚠ ${error.message}`;
                field.parentElement.appendChild(errorMsg);
                
                // Remove highlight after user starts typing
                field.addEventListener('input', function clearHighlight() {
                    field.style.border = '';
                    field.style.backgroundColor = '';
                    if (errorMsg.parentElement) {
                        errorMsg.remove();
                    }
                    field.removeEventListener('input', clearHighlight);
                }, { once: true });
            }
        });
    }

    mergeEducationData(existingEducation, editedEducation) {
        // If we have edited education data, use it to update the first entry or create new one
        if (editedEducation.degree || editedEducation.institution || editedEducation.year || editedEducation.grade) {
            const updatedEducation = [...existingEducation];
            
            // Update first education entry or create new one
            if (updatedEducation.length > 0) {
                updatedEducation[0] = {
                    ...updatedEducation[0],
                    degree: editedEducation.degree || updatedEducation[0].degree || '',
                    qualification: editedEducation.degree || updatedEducation[0].qualification || '',
                    institution: editedEducation.institution || updatedEducation[0].institution || '',
                    university: editedEducation.institution || updatedEducation[0].university || '',
                    college: editedEducation.institution || updatedEducation[0].college || '',
                    year: editedEducation.year || updatedEducation[0].year || null,
                    graduation_year: editedEducation.graduation_year || updatedEducation[0].graduation_year || null,
                    year_of_completion: editedEducation.year || updatedEducation[0].year_of_completion || null,
                    grade: editedEducation.grade || updatedEducation[0].grade || '',
                    percentage: editedEducation.grade || updatedEducation[0].percentage || '',
                    gpa: editedEducation.grade || updatedEducation[0].gpa || ''
                };
            } else {
                // Create new education entry
                updatedEducation.push({
                    degree: editedEducation.degree || '',
                    qualification: editedEducation.degree || '',
                    institution: editedEducation.institution || '',
                    university: editedEducation.institution || '',
                    year: editedEducation.year || null,
                    graduation_year: editedEducation.graduation_year || null,
                    grade: editedEducation.grade || '',
                    percentage: editedEducation.grade || ''
                });
            }
            
            return updatedEducation;
        }
        
        // Return existing education if no edits
        return existingEducation;
    }

    mergeProjectData(existingProjects, editedProject) {
        // If we have edited project data, use it to update the first entry or create new one
        if (editedProject.project_name || editedProject.client || editedProject.role || 
            editedProject.duration || editedProject.technologies.length > 0 || editedProject.description) {
            
            const updatedProjects = [...existingProjects];
            
            // Update first project entry or create new one
            if (updatedProjects.length > 0) {
                updatedProjects[0] = {
                    ...updatedProjects[0],
                    project_name: editedProject.project_name || updatedProjects[0].project_name || '',
                    name: editedProject.name || updatedProjects[0].name || '',
                    client: editedProject.client || updatedProjects[0].client || '',
                    client_name: editedProject.client_name || updatedProjects[0].client_name || '',
                    role: editedProject.role || updatedProjects[0].role || '',
                    duration: editedProject.duration || updatedProjects[0].duration || '',
                    technologies: editedProject.technologies.length > 0 ? editedProject.technologies : (updatedProjects[0].technologies || []),
                    technologies_used: editedProject.technologies_used.length > 0 ? editedProject.technologies_used : (updatedProjects[0].technologies_used || []),
                    description: editedProject.description || updatedProjects[0].description || '',
                    project_description: editedProject.project_description || updatedProjects[0].project_description || '',
                    responsibilities: updatedProjects[0].responsibilities || [],
                    outcomes: updatedProjects[0].outcomes || []
                };
            } else {
                // Create new project entry
                updatedProjects.push({
                    project_name: editedProject.project_name || '',
                    name: editedProject.name || '',
                    client: editedProject.client || '',
                    client_name: editedProject.client_name || '',
                    role: editedProject.role || '',
                    duration: editedProject.duration || '',
                    technologies: editedProject.technologies || [],
                    technologies_used: editedProject.technologies_used || [],
                    description: editedProject.description || '',
                    project_description: editedProject.project_description || '',
                    responsibilities: [],
                    outcomes: []
                });
            }
            
            return updatedProjects;
        }
        
        // Return existing projects if no edits
        return existingProjects;
    }

    async refreshCVPreview() {
        const preview = document.getElementById('cvPreview');
        
        if (!this.currentSessionId) {
            preview.innerHTML = `
                <div class="preview-placeholder">
                    <p>Your CV data will appear here as you build it</p>
                    <p>Upload a document, record audio, or start chatting to begin</p>
                </div>
            `;
            return;
        }

        try {
            const response = await this.request(`${this.apiBase}/preview/${this.currentSessionId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('DEBUG: Full Preview API response:', JSON.stringify(data, null, 2));
            this.currentCanonicalCV = data.canonical_cv || this.currentCanonicalCV;
            
            // Update review status badge if present in response
            if (data.review_status) {
                this.updateReviewStatusBadge(data.review_status);
            }

            // Update export button state if validation result is present
            if (data.validation_result) {
                this.updateExportButtonState(data.review_status, data.validation_result);
            }
            
            // Try multiple data sources in order of preference
            let cvDataToDisplay = null;
            
            // Option 1: Use cv_data directly if available (most complete)
            if (data.cv_data && Object.keys(data.cv_data).length > 0) {
                console.log('Using data.cv_data');
                cvDataToDisplay = data.cv_data;
            }
            // Option 2: Use preview field
            else if (data.preview && Object.keys(data.preview).length > 0) {
                console.log('Using data.preview');
                cvDataToDisplay = data.preview;
            }
            // Option 3: Use canonical source if returned by newer APIs
            else if (data.canonical_cv && Object.keys(data.canonical_cv).length > 0) {
                console.log('Using data.canonical_cv');
                cvDataToDisplay = data.canonical_cv;
            }
            // Option 4: Fallback to local data
            else if (this.currentCVData && Object.keys(this.currentCVData).length > 0) {
                console.log('Using local currentCVData as fallback');
                cvDataToDisplay = this.currentCVData;
            }
            
            if (cvDataToDisplay) {
                // Store the current CV data
                this.currentCVData = cvDataToDisplay;
                
                // Debug: Log project_experience specifically
                if (cvDataToDisplay.project_experience) {
                    console.log('DEBUG: Found project_experience:', cvDataToDisplay.project_experience);
                } else {
                    console.warn('DEBUG: No project_experience in CV data');
                }
                
                const html = this.generateCVHTML(cvDataToDisplay);
                
                // Check if we generated any meaningful HTML
                if (html && html !== '<p>No CV data available</p>') {
                    preview.innerHTML = `<div class="cv-data">${html}</div>`;
                } else {
                    // Fallback: show raw data if HTML generation failed
                    preview.innerHTML = `
                        <div class="preview-placeholder">
                            <p>⚠️ CV data exists but couldn't be formatted properly.</p>
                            <p>Try clicking "Save & Validate" to refresh the data.</p>
                            <details style="margin-top: 10px;">
                                <summary style="cursor: pointer; color: #5a67d8;">Show Raw Data</summary>
                                <pre style="background: #f3f4f6; padding: 10px; border-radius: 4px; overflow: auto; max-height: 300px;">${JSON.stringify(cvDataToDisplay, null, 2)}</pre>
                            </details>
                        </div>
                    `;
                }
            } else {
                preview.innerHTML = `
                    <div class="preview-placeholder">
                        <p>No preview data available yet</p>
                        <p>Upload a document, record audio, or start chatting to build your CV</p>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error fetching preview:', error);
            
            // Try to show local data if API fails
            if (this.currentCVData && Object.keys(this.currentCVData).length > 0) {
                console.warn('Preview API failed, using local currentCVData as fallback');
                const html = this.generateCVHTML(this.currentCVData);
                preview.innerHTML = `<div class="cv-data">${html}</div>`;
                this.showNotification('⚠️ Using cached CV data. Some information may be outdated.', 'info');
            } else {
                preview.innerHTML = `
                    <div class="preview-placeholder">
                        <p>❌ Error loading preview: ${error.message}</p>
                        <p>Please check your connection and try again.</p>
                        <button class="btn btn-primary" onclick="window.cvApp.refreshCVPreview()" style="margin-top: 10px;">
                            🔄 Retry
                        </button>
                    </div>
                `;
            }
        }
    }

    generateCVHTML(cvData) {
        let html = '';

        const splitTextItems = (text) => {
            return String(text || '')
                .replace(/\r\n/g, '\n')
                .split(/\n|,/)
                .map(item => item.replace(/^[-*\u2022]\s*/, '').trim())
                .filter(Boolean);
        };

        const normalizeList = (value, preferredKeys = []) => {
            const toTextItems = (item) => {
                if (item === null || item === undefined) return [];
                if (typeof item === 'string' || typeof item === 'number') {
                    return splitTextItems(String(item));
                }
                if (Array.isArray(item)) {
                    return item.flatMap(entry => toTextItems(entry));
                }
                if (typeof item === 'object') {
                    for (const key of preferredKeys) {
                        const candidate = item[key];
                        const extracted = toTextItems(candidate);
                        if (extracted.length > 0) {
                            return extracted;
                        }
                    }

                    const fallbackKeys = ['value', 'label', 'name', 'title', 'domain', 'industry', 'certification_name', 'certification'];
                    for (const key of fallbackKeys) {
                        if (key in item) {
                            const extracted = toTextItems(item[key]);
                            if (extracted.length > 0) {
                                return extracted;
                            }
                        }
                    }

                    return Object.values(item).flatMap(entry => toTextItems(entry));
                }
                return [];
            };

            const seen = new Set();
            const normalized = toTextItems(value).filter(item => {
                const key = item.toLowerCase();
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
            return normalized;
        };

        const sanitizeLocation = (value) => {
            const raw = String(value || '').trim();
            if (!raw) return '';
            const lowered = raw.toLowerCase().replace(/^[\s,.;:-]+|[\s,.;:-]+$/g, '');
            const invalidValues = new Set(['and', 'na', 'n/a', 'none', 'null', 'undefined', 'unknown', 'not available']);
            const cleaned = lowered
                .replace(/^and\s+/i, '')
                .replace(/^is\s+/i, '')
                .replace(/^in\s+/i, '')
                .trim();
            if (invalidValues.has(cleaned)) return '';

            const parts = raw
                .split(',')
                .map(part => part.trim())
                .filter(Boolean)
                .filter(part => !invalidValues.has(part.toLowerCase()));

            return parts.length > 0 ? parts.join(', ') : '';
        };

        const sanitizeSecondarySkills = (skills) => {
            const noiseMarkers = [
                'operating system',
                'operating systems',
                'database',
                'databases',
                'domain',
                'tools and platforms',
                'tool and platform',
            ];

            const cleaned = [];
            normalizeList(skills).forEach(skill => {
                const text = String(skill || '').trim();
                if (!text) return;
                const lowered = text.toLowerCase();
                if (noiseMarkers.some(marker => lowered.includes(marker))) return;
                if (!cleaned.includes(text)) cleaned.push(text);
            });

            return cleaned;
        };

        const sanitizeCurrentTitle = (value) => {
            const raw = String(value || '').replace(/\s+/g, ' ').trim();
            if (!raw) return '';
            const cleaned = raw
                .replace(/^(experience|current\s+role|role)\s*[:\-]?\s*/i, '')
                .replace(/\s+/g, ' ')
                .trim();

            const invalid = new Set(['experience', 'current role', 'role', 'project experience', 'summary', 'skills']);
            return invalid.has(cleaned.toLowerCase()) ? '' : cleaned;
        };

        // Header
        const profile = cvData.header || cvData.personal_details || {};
        if (profile) {
            const safeLocation = sanitizeLocation(profile.location);
            const safeCurrentTitle = sanitizeCurrentTitle(profile.current_title);
            const portalId = profile.portal_id || profile.employee_id || cvData.portal_id || cvData.employee_id || '';
            html += '<div class="cv-header">';
            if (profile.full_name) html += `<h1>${profile.full_name}</h1>`;
            if (safeCurrentTitle) html += `<h2>${safeCurrentTitle}</h2>`;
            if (profile.current_organization) html += `<p><strong>Organization:</strong> ${profile.current_organization}</p>`;
            if (profile.total_experience) html += `<p><strong>Experience:</strong> ${profile.total_experience} years</p>`;
            if (profile.grade) html += `<p><strong>Current Grade:</strong> ${profile.grade}</p>`;
            if (profile.target_role) html += `<p><strong>Target Role:</strong> ${profile.target_role}</p>`;
            if (portalId) html += `<p><strong>Portal ID:</strong> ${portalId}</p>`;
            if (profile.email) html += `<p><strong>Email:</strong> ${profile.email}</p>`;
            if (safeLocation) html += `<p><strong>Location:</strong> ${safeLocation}</p>`;
            html += '</div>';
        }

        // Summary
        const summaryValue = cvData.summary?.professional_summary
            ?? cvData.summary?.summary
            ?? cvData.summary;

        const summaryText = this.extractSummaryText(summaryValue).trim();
        const summaryLines = this.normalizeSummaryLines(summaryText);
        if (summaryLines.length > 0) {
            html += `<h3>Professional Summary</h3>`;
            if (summaryLines.length === 1) {
                html += `<p>${this.escapeHtml(summaryLines[0])}</p>`;
            } else {
                html += '<ul>';
                summaryLines.forEach(line => {
                    html += `<li>${this.escapeHtml(line)}</li>`;
                });
                html += '</ul>';
            }
        }

        // Skills
        const skills = Array.isArray(cvData.skills)
            ? normalizeList(cvData.skills)
            : normalizeList(cvData.skills?.primary_skills || []);
        if (skills && skills.length > 0) {
            html += `<h3>Primary Skills</h3><ul>`;
            skills.forEach(skill => html += `<li>${skill}</li>`);
            html += `</ul>`;
        }

        // Secondary Skills
        const secondarySkills = sanitizeSecondarySkills(
            cvData.skills?.secondary_skills || cvData.secondary_skills || []
        );
        if (secondarySkills && secondarySkills.length > 0) {
            html += `<h3>Secondary Skills</h3><ul>`;
            secondarySkills.forEach(skill => html += `<li>${skill}</li>`);
            html += `</ul>`;
        }

        // Work Experience
        if (cvData.work_experience && cvData.work_experience.length > 0) {
            html += `<h3>Work Experience</h3>`;
            cvData.work_experience.forEach(exp => {
                html += `<div class="experience-item">`;
                const position = exp.position || exp.designation;
                const company = exp.company || exp.organization;
                const duration = exp.duration || ((exp.start_date || exp.end_date) ? `${exp.start_date || ''}${(exp.start_date && exp.end_date) ? ' - ' : ''}${exp.end_date || ''}` : '');
                const description = exp.description || normalizeList(exp.responsibilities || []).join('. ');
                if (position) html += `<h4>${position}</h4>`;
                if (company) html += `<p><strong>${company}</strong></p>`;
                if (duration) html += `<p>${duration}</p>`;
                if (description) html += `<p>${description}</p>`;
                html += `</div>`;
            });
        }

        // Project Experience
        const projectExperience = (() => {
            const candidates = [
                cvData.project_experience,
                cvData.projectExperience,
                cvData.projects,
                cvData.experience?.projects,
                cvData.experience?.project_experience,
                cvData.experience?.projectExperience,
            ];
            for (const candidate of candidates) {
                if (Array.isArray(candidate) && candidate.length > 0) {
                    return candidate;
                }
            }
            return [];
        })();

        if (projectExperience.length > 0) {
            html += `<h3>Project Experience</h3>`;
            projectExperience.forEach(proj => {
                html += `<div class="project-item">`;
                
                // Handle multiple field name variations for project name
                const projectName = proj.project_name || proj.projectName || proj.name || proj.title;
                if (projectName) html += `<h4>${projectName}</h4>`;
                
                // Handle multiple field name variations for client
                const clientName = proj.client || proj.client_name || proj.clientName;
                if (clientName) html += `<p><strong>Client:</strong> ${clientName}</p>`;
                
                // Display role if available
                const role = proj.role || proj.designation || proj.role_title || proj.position;
                if (role) html += `<p><strong>Role:</strong> ${role}</p>`;
                
                // Display duration if available
                const duration = proj.duration || (proj.durationFrom && proj.durationTo ? `${proj.durationFrom} to ${proj.durationTo}` : (proj.durationFrom || proj.durationTo || ''));
                if (duration) html += `<p><strong>Duration:</strong> ${duration}</p>`;
                
                // Display team size if available
                const teamSize = proj.team_size || proj.teamSize;
                if (teamSize) html += `<p><strong>Team Size:</strong> ${teamSize}</p>`;
                
                // Handle multiple field name variations for technologies
                const technologies = normalizeList(
                    proj.technologies_used || proj.technologies || proj.toolsUsed || proj.environment || [],
                    ['name', 'label', 'value', 'title']
                );
                if (technologies.length > 0) {
                    html += `<p><strong>Technologies:</strong> ${technologies.join(', ')}</p>`;
                }
                
                // Handle multiple field name variations for description
                const description = proj.project_description || proj.projectDescription || proj.description;
                if (description) html += `<p>${description}</p>`;
                
                // Display responsibilities if available
                const responsibilities = normalizeList(proj.responsibilities || [], ['description', 'value', 'title']);
                if (responsibilities.length > 0) {
                    html += `<p><strong>Responsibilities:</strong></p><ul>`;
                    responsibilities.forEach(resp => html += `<li>${resp}</li>`);
                    html += `</ul>`;
                }
                
                // Display outcomes/achievements if available
                const outcomes = normalizeList(proj.outcomes || proj.achievements || [], ['description', 'value', 'title']);
                if (outcomes.length > 0) {
                    html += `<p><strong>Outcomes:</strong></p><ul>`;
                    outcomes.forEach(outcome => html += `<li>${outcome}</li>`);
                    html += `</ul>`;
                }
                
                html += `</div>`;
            });
        }

        // Education
        const educationEntries = Array.isArray(cvData.education)
            ? cvData.education
            : cvData.education
                ? [cvData.education]
                : [];
        if (educationEntries.length > 0) {
            html += `<h3>Education</h3>`;
            educationEntries.forEach(edu => {
                html += `<div class="education-item">`;
                if (typeof edu === 'string') {
                    html += `<p>${edu}</p>`;
                } else {
                    const qualification = edu.qualification || edu.degree || edu.title || '';
                    if (qualification) html += `<h4>${qualification}</h4>`;
                    if (edu.specialization) html += `<p><strong>Specialization:</strong> ${edu.specialization}</p>`;
                    if (edu.college) html += `<p><strong>College:</strong> ${edu.college}</p>`;
                    if (edu.institution) html += `<p><strong>Institution:</strong> ${edu.institution}</p>`;
                    if (edu.university) html += `<p><strong>University:</strong> ${edu.university}</p>`;
                    if (edu.year_of_passing) html += `<p><strong>Year:</strong> ${edu.year_of_passing}</p>`;
                    if (edu.year) html += `<p><strong>Year:</strong> ${edu.year}</p>`;
                    if (edu.percentage) html += `<p><strong>Score:</strong> ${edu.percentage}</p>`;
                    if (edu.grade) html += `<p><strong>Grade:</strong> ${edu.grade}</p>`;
                }
                html += `</div>`;
            });
        }

        // Technical Details
        if (cvData.cloud_platforms && cvData.cloud_platforms.length > 0) {
            html += `<h3>Cloud Platforms</h3><ul>`;
            cvData.cloud_platforms.forEach(platform => html += `<li>${platform}</li>`);
            html += `</ul>`;
        }

        if (cvData.databases && cvData.databases.length > 0) {
            html += `<h3>Databases</h3><ul>`;
            cvData.databases.forEach(db => html += `<li>${db}</li>`);
            html += `</ul>`;
        }

        const toolsPlatforms = normalizeList(
            cvData.skills?.tools_and_platforms
                || cvData.skills?.toolsAndPlatforms
                || cvData.skills?.platforms
                || cvData.tools_and_platforms
                || cvData.toolsAndPlatforms
                || cvData.platforms
                || []
        );
        if (toolsPlatforms && toolsPlatforms.length > 0) {
            html += `<h3>Tools, Platforms & Operating Systems</h3><ul>`;
            toolsPlatforms.forEach(item => html += `<li>${item}</li>`);
            html += `</ul>`;
        }

        const domainExpertise = normalizeList(
            cvData.domain_expertise
                || cvData.domainExpertise
                || cvData.domains
                || cvData.skills?.domain_expertise
                || cvData.skills?.domainExpertise
                || cvData.skills?.domains
                || cvData.experience?.domainExperience
                || cvData.experience?.domain_expertise
                || cvData.experience?.domainExpertise
                || cvData.experience?.domains
                || cvData.experience?.industriesWorked
                || cvData.industries_worked
                || cvData.industriesWorked
                || [],
            ['domain', 'industry', 'sector', 'name', 'value', 'label']
        );
        if (domainExpertise.length > 0) {
            html += `<h3>Domain Expertise</h3><ul>`;
            domainExpertise.forEach(domain => html += `<li>${domain}</li>`);
            html += `</ul>`;
        }

        // Certifications
        const certifications = normalizeList(
            cvData.certifications || cvData.certifications_and_trainings || [],
            ['certification_name', 'name', 'certification', 'title', 'course', 'value', 'label']
        );
        if (certifications.length > 0) {
            html += `<h3>Certifications</h3><ul>`;
            certifications.forEach(cert => html += `<li>${cert}</li>`);
            html += `</ul>`;
        }

        // Languages
        const languages = normalizeList(cvData.languages || [], ['language', 'name', 'value', 'label']);
        if (languages.length > 0) {
            html += `<h3>Languages</h3><ul>`;
            languages.forEach(lang => html += `<li>${lang}</li>`);
            html += `</ul>`;
        }

        return html || '<p>No CV data available</p>';
    }

    showExportModal() {
        if (!this.currentCVData || Object.keys(this.currentCVData).length === 0) {
            this.showNotification('No CV data to export. Please build your CV first.', 'error');
            return;
        }
        
        // Check if export button is disabled (validation not passed)
        const exportBtn = document.getElementById('exportCV');
        if (exportBtn && exportBtn.disabled) {
            this.showNotification('Please validate your CV before exporting. Click "Save & Validate" first.', 'error');
            return;
        }
        
        const modal = document.getElementById('exportModal');
        if (modal) {
            modal.style.display = 'flex';
            // Add a small delay to trigger animation
            setTimeout(() => {
                modal.classList.add('show');
            }, 10);
        }
    }

    hideExportModal() {
        const modal = document.getElementById('exportModal');
        if (modal) {
            modal.classList.remove('show');
            // Wait for animation to complete before hiding
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
        }
    }

    async exportCV(format) {
        if (!this.currentCVData) {
            this.showNotification('No CV data to export', 'error');
            return;
        }

        // Double-check validation status before export
        const exportBtn = document.getElementById('exportCV');
        if (exportBtn.disabled) {
            this.showNotification('Please validate your CV before exporting.', 'error');
            this.hideExportModal();
            return;
        }

        try {
            if (format === 'json') {
                this.downloadJSON(this.currentCVData, 'cv-data.json');
                this.hideExportModal();
                this.showNotification('CV exported as JSON successfully!', 'success');
                return;
            }

            // For PDF/DOCX, we would need export endpoints
            const response = await this.request(`${this.apiBase}/export/${format}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cv_data: this.currentCVData,
                    session_id: this.currentSessionId
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `cv.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                this.hideExportModal();
                this.showNotification(`CV exported as ${format.toUpperCase()} successfully!`, 'success');
            } else {
                throw new Error(`Export failed: ${response.statusText}`);
            }
        } catch (error) {
            this.showNotification('Export failed: ' + error.message, 'error');
        }
    }

    downloadJSON(data, filename) {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    resetButtonStates() {
        // Reset edit mode to false
        this.isEditMode = false;
        this.editableData = null;
        
        // Reset toggle button to "Edit CV"
        const toggleBtn = document.getElementById('toggleEditMode');
        if (toggleBtn) {
            toggleBtn.innerHTML = '<span>✏️</span> Edit CV';
            toggleBtn.classList.remove('btn-edit-active');
        }
        
        // Reset export button to disabled (requires validation)
        const exportBtn = document.getElementById('exportCV');
        if (exportBtn) {
            exportBtn.disabled = true;
            exportBtn.title = '💾 Click "Save & Validate" first';
            exportBtn.classList.add('btn-disabled');
        }
        
        // Hide validation feedback panel
        const feedbackPanel = document.getElementById('validationFeedback');
        if (feedbackPanel) {
            feedbackPanel.style.display = 'none';
        }
        
        // Reset review status badge
        const reviewBadge = document.getElementById('reviewStatusBadge');
        if (reviewBadge) {
            reviewBadge.style.display = 'none';
        }
    }

    initializeTooltips() {
        // Add helpful tooltips to guide users through the Human-in-the-Loop workflow
        const tooltips = {
            'saveAndValidate': '💾 Validate your CV data and check for missing required fields',
            'toggleEditMode': '✏️ Switch to edit mode to manually update CV fields',
            'exportCV': '📥 Export your validated CV (requires successful validation first)',
            'refreshPreview': '🔄 Refresh the CV preview to see latest changes'
        };

        Object.keys(tooltips).forEach(btnId => {
            const btn = document.getElementById(btnId);
            if (btn && !btn.title) {
                btn.title = tooltips[btnId];
            }
        });
    }

    // Utility Methods
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    updateSessionDisplay(sessionId) {
        document.getElementById('sessionId').value = sessionId;
        document.getElementById('currentSession').innerHTML = `
            <div class="session-info">
                <strong>Active Session:</strong> ${sessionId}
                <br><small>Session created and data will be automatically saved</small>
            </div>
        `;
        this.updateStatus('sessionStatus', sessionId, 'text-success');
        this.updateStatus('lastUpdate', new Date().toLocaleTimeString(), '');
    }

    updateStatus(elementId, value, className = '') {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
            if (className) {
                element.className = `status-value ${className}`;
            }
        }
    }

    showNotification(message, type = 'info') {
        // Create a simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#dc2626' : '#5a67d8'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1001;
            max-width: 300px;
            animation: slideIn 0.3s ease-out;
        `;
        notification.textContent = message;

        // Add CSS animation
        if (!document.getElementById('notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }

    showProgress(elementId, message) {
        const progressBar = document.getElementById(elementId);
        if (progressBar) {
            progressBar.style.display = 'block';
            progressBar.setAttribute('data-message', message);
        }
    }

    hideProgress(elementId) {
        const progressBar = document.getElementById(elementId);
        if (progressBar) {
            progressBar.style.display = 'none';
            setTimeout(() => {
                progressBar.removeAttribute('data-message');
            }, 300);
        }
    }

    showResult(elementId, message, type) {
        const resultArea = document.getElementById(elementId);
        if (resultArea) {
            resultArea.textContent = message;
            resultArea.className = `result-area ${type}`;
            resultArea.style.display = 'block';
        }
    }
}

// Expose the application class for browser-based tests and instantiate normally in production
window.CVBuilderApp = CVBuilderApp;

document.addEventListener('DOMContentLoaded', () => {
    window.cvApp = new CVBuilderApp();
});
