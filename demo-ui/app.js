// CV Builder Automation - Comprehensive JavaScript Implementation
class CVBuilderApp {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.currentSessionId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.currentCVData = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkServerStatus();
        this.setupDragAndDrop();
        this.initializeChat();
    }

    bindEvents() {
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
        document.getElementById('exportCV').addEventListener('click', () => this.showExportModal());

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

    initializeChat() {
        this.addChatMessage("Hello! I'm here to help you build your CV. You can upload documents, record audio, or chat with me to build your CV step by step. How would you like to start?", 'bot');
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
            const response = await fetch(`${this.apiBase}/session/start`, {
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
            const response = await fetch(`${this.apiBase}/session/${sessionId}`, {
                method: 'GET'
            });

            if (response.ok) {
                const data = await response.json();
                this.currentSessionId = sessionId;
                this.currentCVData = data.cv_data || {};
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

        if (!file.name.match(/\.(pdf|docx)$/i)) {
            this.showNotification('Please select a PDF or DOCX file', 'error');
            return;
        }

        this.showProgress('uploadProgress', 'Uploading file...');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            if (this.currentSessionId) {
                formData.append('session_id', this.currentSessionId);
            }

            const response = await fetch(`${this.apiBase}/cv/upload`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.currentCVData = data.cv_data || data.parsed_data;
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

        if (!file.type.match(/audio\/.*/)) {
            this.showNotification('Please select an audio file', 'error');
            return;
        }

        await this.processAudio(file);
    }

    async processAudio(audioBlob) {
        this.showProgress('audioProgress', 'Processing audio...');

        try {
            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.webm');
            if (this.currentSessionId) {
                formData.append('session_id', this.currentSessionId);
            }

            const response = await fetch(`${this.apiBase}/speech/transcribe`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.currentCVData = data.cv_data || data.extracted_cv_data;
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
                
                this.showResult('transcriptionResult', resultText, 'success');
                this.refreshCVPreview();
                this.addChatMessage(`I've processed your audio and extracted CV information. Would you like to review the details or add more information?`, 'bot');
                
                document.getElementById('recordingStatus').textContent = '';
            } else {
                throw new Error('Audio processing failed');
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

        this.addChatMessage(message, 'user');
        input.value = '';

        try {
            const response = await fetch(`${this.apiBase}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message, 
                    session_id: this.currentSessionId || 'default-session' 
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.addChatMessage(data.bot || 'No response', 'bot');
                
                if (data.cv_data) {
                    this.currentCVData = data.cv_data;
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

    refreshCVPreview() {
        const preview = document.getElementById('cvPreview');
        
        if (!this.currentCVData || Object.keys(this.currentCVData).length === 0) {
            preview.innerHTML = `
                <div class="preview-placeholder">
                    <p>Your CV data will appear here as you build it</p>
                    <p>Upload a document, record audio, or start chatting to begin</p>
                </div>
            `;
            return;
        }

        const html = this.generateCVHTML(this.currentCVData);
        preview.innerHTML = `<div class="cv-data">${html}</div>`;
    }

    generateCVHTML(cvData) {
        let html = '';

        // Header
        if (cvData.header) {
            html += '<div class="cv-header">';
            if (cvData.header.full_name) html += `<h1>${cvData.header.full_name}</h1>`;
            if (cvData.header.current_title) html += `<h2>${cvData.header.current_title}</h2>`;
            if (cvData.header.email) html += `<p>Email: ${cvData.header.email}</p>`;
            if (cvData.header.contact_number) html += `<p>Phone: ${cvData.header.contact_number}</p>`;
            if (cvData.header.location) html += `<p>Location: ${cvData.header.location}</p>`;
            html += '</div>';
        }

        // Summary
        if (cvData.summary) {
            html += `<h3>Professional Summary</h3><p>${cvData.summary}</p>`;
        }

        // Skills
        if (cvData.skills && cvData.skills.length > 0) {
            html += `<h3>Primary Skills</h3><ul>`;
            cvData.skills.forEach(skill => html += `<li>${skill}</li>`);
            html += `</ul>`;
        }

        // Secondary Skills
        if (cvData.secondary_skills && cvData.secondary_skills.length > 0) {
            html += `<h3>Secondary Skills</h3><ul>`;
            cvData.secondary_skills.forEach(skill => html += `<li>${skill}</li>`);
            html += `</ul>`;
        }

        // Work Experience
        if (cvData.work_experience && cvData.work_experience.length > 0) {
            html += `<h3>Work Experience</h3>`;
            cvData.work_experience.forEach(exp => {
                html += `<div class="experience-item">`;
                if (exp.position) html += `<h4>${exp.position}</h4>`;
                if (exp.company) html += `<p><strong>${exp.company}</strong></p>`;
                if (exp.duration) html += `<p>${exp.duration}</p>`;
                if (exp.description) html += `<p>${exp.description}</p>`;
                html += `</div>`;
            });
        }

        // Project Experience
        if (cvData.project_experience && cvData.project_experience.length > 0) {
            html += `<h3>Project Experience</h3>`;
            cvData.project_experience.forEach(proj => {
                html += `<div class="project-item">`;
                if (proj.project_name) html += `<h4>${proj.project_name}</h4>`;
                if (proj.client) html += `<p><strong>Client:</strong> ${proj.client}</p>`;
                if (proj.technologies_used && proj.technologies_used.length > 0) {
                    html += `<p><strong>Technologies:</strong> ${proj.technologies_used.join(', ')}</p>`;
                }
                if (proj.project_description) html += `<p>${proj.project_description}</p>`;
                if (proj.responsibilities && proj.responsibilities.length > 0) {
                    html += `<p><strong>Responsibilities:</strong></p><ul>`;
                    proj.responsibilities.forEach(resp => html += `<li>${resp}</li>`);
                    html += `</ul>`;
                }
                html += `</div>`;
            });
        }

        // Education
        if (cvData.education && cvData.education.length > 0) {
            html += `<h3>Education</h3>`;
            cvData.education.forEach(edu => {
                html += `<div class="education-item">`;
                if (edu.qualification) html += `<h4>${edu.qualification}</h4>`;
                if (edu.specialization) html += `<p><strong>Specialization:</strong> ${edu.specialization}</p>`;
                if (edu.college) html += `<p><strong>College:</strong> ${edu.college}</p>`;
                if (edu.university) html += `<p><strong>University:</strong> ${edu.university}</p>`;
                if (edu.year_of_passing) html += `<p><strong>Year:</strong> ${edu.year_of_passing}</p>`;
                if (edu.percentage) html += `<p><strong>Score:</strong> ${edu.percentage}</p>`;
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

        if (cvData.domain_expertise && cvData.domain_expertise.length > 0) {
            html += `<h3>Domain Expertise</h3><ul>`;
            cvData.domain_expertise.forEach(domain => html += `<li>${domain}</li>`);
            html += `</ul>`;
        }

        return html || '<p>No CV data available</p>';
    }

    showExportModal() {
        if (!this.currentCVData || Object.keys(this.currentCVData).length === 0) {
            this.showNotification('No CV data to export. Please build your CV first.', 'error');
            return;
        }
        document.getElementById('exportModal').style.display = 'flex';
    }

    hideExportModal() {
        document.getElementById('exportModal').style.display = 'none';
    }

    async exportCV(format) {
        if (!this.currentCVData) {
            this.showNotification('No CV data to export', 'error');
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
            const response = await fetch(`${this.apiBase}/export/${format}`, {
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

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CVBuilderApp();
});
