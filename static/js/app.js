/**
 * LinkedIn Post Generator - SPA Application
 */

// ========================================
// State Management
// ========================================

const state = {
    currentTab: 'generate',
    currentProfile: null,
    profiles: [],
    currentPdf: null,
    currentAnalysis: null, // Stores the content analysis
    generatedPost: null,
    selectedImageId: null,
    selectedQuotes: [], // Quotes selected by user to focus on
    history: [],
    currentStatus: null, // 'uploading', 'processing', 'summarizing', 'generating'
    advancedOptionsOpen: false,
    inputType: 'pdf' // 'pdf' or 'url'
};

// ========================================
// API Client
// ========================================

const API = {
    baseUrl: '/api',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include', // Include cookies for session auth
            ...options
        };

        // Remove Content-Type for FormData
        if (options.body instanceof FormData) {
            delete config.headers['Content-Type'];
        }

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Unauthorized - redirect to login
                state.isAuthenticated = false;
                App.showLoginModal();
                throw new Error('Please login to continue');
            }
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Request failed' }));
                throw new Error(error.error || error.detail || 'Request failed');
            }

            if (response.status === 204) return null;
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    // Profiles
    async getProfiles() {
        return this.request('/profiles/');
    },

    async createProfile(data) {
        return this.request('/profiles/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateProfile(id, data) {
        return this.request(`/profiles/${id}/`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    async addSamplePost(profileId, data) {
        return this.request(`/profiles/${profileId}/add_sample_post/`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async deleteSamplePost(profileId, postId) {
        return this.request(`/profiles/${profileId}/sample-posts/${postId}/`, {
            method: 'DELETE'
        });
    },

    // PDFs
    async uploadPdf(file, profileId = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (profileId) formData.append('profile_id', profileId);

        return this.request('/pdfs/', {
            method: 'POST',
            body: formData
        });
    },

    async submitUrl(url, profileId = null) {
        return this.request('/submit-url/', {
            method: 'POST',
            body: JSON.stringify({
                url: url,
                profile_id: profileId
            })
        });
    },

    async getPdfImages(pdfId) {
        return this.request(`/pdfs/${pdfId}/images/`);
    },

    // Content Analysis
    async analyzeContent(pdfId, customInstructions = '') {
        return this.request('/analyze/', {
            method: 'POST',
            body: JSON.stringify({
                pdf_id: pdfId,
                custom_instructions: customInstructions
            })
        });
    },

    // Post Generation
    async generatePost(pdfId, profileId, options = {}) {
        return this.request('/generate/', {
            method: 'POST',
            body: JSON.stringify({
                pdf_id: pdfId,
                profile_id: profileId,
                generate_image: options.generateImage || false,
                use_extracted_image: options.useExtractedImage !== false,
                custom_instructions: options.customInstructions || '',
                tone_preference: options.tonePreference || 'professional',
                post_length_preference: options.postLengthPreference || 'medium',
                include_emojis: options.includeEmojis !== false,
                include_hashtags: options.includeHashtags !== false,
                include_source_link: options.includeSourceLink || false
            })
        });
    },

    async regeneratePost(postId, options = {}) {
        return this.request(`/regenerate/${postId}/`, {
            method: 'POST',
            body: JSON.stringify(options)
        });
    },

    async refinePost(postId, refinementPrompt) {
        return this.request(`/refine/${postId}/`, {
            method: 'POST',
            body: JSON.stringify({
                refinement_prompt: refinementPrompt
            })
        });
    },

    // History
    async getHistory() {
        return this.request('/posts/');
    },

    // Prompts (for transparency page)
    async getPrompts() {
        return this.request('/prompts/');
    },

    // Authentication
    async register(username, email, password, name) {
        return this.request('/auth/register/', {
            method: 'POST',
            body: JSON.stringify({ username, email, password, name })
        });
    },

    async login(username, password) {
        return this.request('/auth/login/', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },

    async logout() {
        return this.request('/auth/logout/', {
            method: 'POST'
        });
    },

    async checkAuth() {
        return this.request('/auth/check/');
    },

    async getCurrentUser() {
        return this.request('/auth/current-user/');
    }
};

// ========================================
// UI Components
// ========================================

const UI = {
    // Toast notifications
    showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.success}</span>
            <span class="toast-message">${message}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    // Tab switching
    switchTab(tabName) {
        state.currentTab = tabName;

        // Update nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabName}-tab`);
        });

        // Load data for specific tabs
        if (tabName === 'profile') {
            this.loadProfileData();
        } else if (tabName === 'history') {
            this.loadHistory();
        } else if (tabName === 'prompts') {
            this.loadPrompts();
        }
    },

    // Profile dropdown
    async updateProfileDropdown() {
        const select = document.getElementById('profile-select');
        select.innerHTML = '<option value="">Default Style</option>';

        state.profiles.forEach(profile => {
            const option = document.createElement('option');
            option.value = profile.id;
            option.textContent = profile.name;
            select.appendChild(option);
        });

        if (state.currentProfile) {
            select.value = state.currentProfile.id;
        }
    },

    // Load profile data into form
    async loadProfileData() {
        if (state.profiles.length === 0) {
            await App.loadProfiles();
        }

        const profile = state.profiles[0];
        if (profile) {
            state.currentProfile = profile;
            document.getElementById('profile-name').value = profile.name || '';
            document.getElementById('profile-headline').value = profile.headline || '';
            document.getElementById('profile-industry').value = profile.industry || '';
            document.getElementById('profile-tone').value = profile.tone_preference || 'professional';
            document.getElementById('profile-length').value = profile.post_length_preference || 'medium';
            document.getElementById('profile-emojis').checked = profile.include_emojis !== false;
            document.getElementById('profile-hashtags').checked = profile.include_hashtags !== false;
            document.getElementById('profile-custom-instructions').value = profile.custom_instructions || '';

            this.renderSamplePosts(profile.sample_posts || []);
        }
    },

    // Render sample posts
    renderSamplePosts(posts) {
        const container = document.getElementById('sample-posts-list');
        
        if (!posts || posts.length === 0) {
            container.innerHTML = '<p class="empty-state">No sample posts yet. Add some to help the AI learn your style!</p>';
            return;
        }

        container.innerHTML = posts.map(post => `
            <div class="sample-post-card" data-id="${post.id}">
                <p>${this.escapeHtml(post.content)}</p>
                ${post.engagement_notes ? `<div class="notes">${this.escapeHtml(post.engagement_notes)}</div>` : ''}
                <button class="btn-icon delete-btn" onclick="App.deleteSamplePost('${post.id}')">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </button>
            </div>
        `).join('');
    },

    // Render extracted images
    renderExtractedImages(images) {
        const container = document.getElementById('extracted-images');
        const grid = document.getElementById('image-grid');

        if (!images || images.length === 0) {
            container.style.display = 'none';
            return;
        }

        // Sort by relevance score descending
        const sortedImages = [...images].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));

        grid.innerHTML = sortedImages.map(img => {
            const isFigure = img.is_figure;
            const hasCaption = img.caption && img.caption.trim().length > 0;
            const captionText = hasCaption ? this.truncateText(img.caption, 50) : '';
            
            return `
                <div class="image-thumb ${state.selectedImageId === img.id ? 'selected' : ''} ${isFigure ? 'is-figure' : ''}" 
                     data-id="${img.id}"
                     data-url="${img.image_url}"
                     data-page="${img.page_number}"
                     data-caption="${this.escapeHtml(img.caption || '')}">
                    <img src="${img.image_url}" alt="Page ${img.page_number}">
                    ${isFigure ? '<div class="figure-badge">📊 Figure</div>' : ''}
                    ${hasCaption ? `<div class="image-caption">${this.escapeHtml(captionText)}</div>` : ''}
                    <div class="expand-icon">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <path d="M2 6V2h4M14 6V2h-4M2 10v4h4M14 10v4h-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                </div>
            `;
        }).join('');

        // Add click handlers for selection and modal
        grid.querySelectorAll('.image-thumb').forEach(thumb => {
            thumb.addEventListener('click', (e) => {
                const id = thumb.dataset.id;
                const url = thumb.dataset.url;
                const page = thumb.dataset.page;
                const caption = thumb.dataset.caption;
                
                // If clicking on expand icon or double-click, open modal
                if (e.target.closest('.expand-icon') || e.detail === 2) {
                    const title = caption ? caption : `Page ${page}`;
                    UI.openImageModal(url, title);
                } else {
                    // Single click selects the image
                    App.selectImage(id);
                }
            });
        });

        container.style.display = 'block';
    },
    
    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    // Open image modal
    openImageModal(imageUrl, title = 'Image Preview') {
        const modal = document.getElementById('image-modal');
        const modalImage = document.getElementById('modal-image');
        const modalTitle = document.getElementById('modal-title');
        
        modalImage.src = imageUrl;
        modalTitle.textContent = title;
        modal.classList.add('active');
        
        // Store current image URL for copy/download
        modal.dataset.currentImageUrl = imageUrl;
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    },

    // Close image modal
    closeImageModal() {
        const modal = document.getElementById('image-modal');
        modal.classList.remove('active');
        document.body.style.overflow = '';
    },

    // Copy image to clipboard
    async copyImageToClipboard() {
        const modal = document.getElementById('image-modal');
        const imageUrl = modal.dataset.currentImageUrl;
        const copyBtn = document.getElementById('copy-image-btn');
        const originalHTML = copyBtn.innerHTML;
        
        // Show loading state
        copyBtn.disabled = true;
        copyBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" class="spin">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4 31.4" stroke-linecap="round"/>
            </svg>
            Copying...
        `;
        
        try {
            // Fetch the image
            const response = await fetch(imageUrl);
            const blob = await response.blob();
            
            // Try to copy as image
            if (navigator.clipboard && navigator.clipboard.write) {
                const item = new ClipboardItem({ [blob.type]: blob });
                await navigator.clipboard.write([item]);
                this.showCopySuccess(copyBtn, originalHTML);
            } else {
                // Fallback: copy image URL
                await navigator.clipboard.writeText(imageUrl);
                this.showCopySuccess(copyBtn, originalHTML, 'URL Copied!');
            }
        } catch (error) {
            console.error('Failed to copy image:', error);
            // Fallback: try to copy URL
            try {
                await navigator.clipboard.writeText(imageUrl);
                this.showCopySuccess(copyBtn, originalHTML, 'URL Copied!');
            } catch (e) {
                this.showCopyError(copyBtn, originalHTML);
            }
        }
    },
    
    // Show copy success animation
    showCopySuccess(btn, originalHTML, message = 'Copied!') {
        btn.classList.add('copy-success');
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            ${message}
        `;
        
        setTimeout(() => {
            btn.classList.remove('copy-success');
            btn.innerHTML = originalHTML;
            btn.disabled = false;
        }, 2000);
    },
    
    // Show copy error animation
    showCopyError(btn, originalHTML) {
        btn.classList.add('copy-error');
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Failed
        `;
        this.showToast('Failed to copy image. Try right-click > Copy Image.', 'error');
        
        setTimeout(() => {
            btn.classList.remove('copy-error');
            btn.innerHTML = originalHTML;
            btn.disabled = false;
        }, 2000);
    },

    // Download image
    downloadImage() {
        const modal = document.getElementById('image-modal');
        const imageUrl = modal.dataset.currentImageUrl;
        const title = document.getElementById('modal-title').textContent;
        
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = `${title.replace(/\s+/g, '_')}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showToast('Image downloaded!', 'success');
    },

    // Render content analysis
    renderAnalysis(analysis) {
        const container = document.getElementById('content-analysis');
        const analyzeBtn = document.getElementById('analyze-btn');
        
        if (!analysis) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        analyzeBtn.style.display = 'none';
        
        // Core Finding
        const coreFinding = document.getElementById('analysis-core-finding');
        coreFinding.textContent = analysis.core_finding || 'No core finding available';
        
        // Document Sections Breakdown
        const sectionsContainer = document.getElementById('analysis-sections');
        if (analysis.document_sections && Array.isArray(analysis.document_sections)) {
            sectionsContainer.innerHTML = analysis.document_sections.map((section, i) => `
                <div class="doc-section-card" data-section="${i}">
                    <div class="doc-section-header" onclick="UI.toggleDocSection(${i})">
                        <div class="doc-section-title">
                            <span class="doc-section-number">${i + 1}</span>
                            <h5>${this.escapeHtml(section.section_title || `Section ${i + 1}`)}</h5>
                        </div>
                        <svg class="doc-section-toggle" width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <div class="doc-section-body" id="doc-section-body-${i}">
                        <p class="doc-section-summary">${this.escapeHtml(section.summary || '')}</p>
                        ${section.key_details && section.key_details.length > 0 ? `
                            <ul class="doc-section-details">
                                ${section.key_details.map(detail => `<li>${this.escapeHtml(detail)}</li>`).join('')}
                            </ul>
                        ` : ''}
                    </div>
                </div>
            `).join('');
            
            // Expand first section by default
            if (analysis.document_sections.length > 0) {
                this.toggleDocSection(0);
            }
        } else {
            sectionsContainer.innerHTML = '<p class="no-data">No section breakdown available</p>';
        }
        
        // Key Data Points
        const dataPointsList = document.getElementById('analysis-data-points');
        if (analysis.key_data_points && Array.isArray(analysis.key_data_points)) {
            dataPointsList.innerHTML = analysis.key_data_points.map((dp, i) => {
                if (typeof dp === 'string') {
                    return `<div class="data-point"><div class="data-point-finding">${this.escapeHtml(dp)}</div></div>`;
                }
                return `
                    <div class="data-point">
                        <div class="data-point-finding">${this.escapeHtml(dp.finding || dp)}</div>
                        ${dp.context ? `<div class="data-point-context">📊 ${this.escapeHtml(dp.context)}</div>` : ''}
                        ${dp.limitations ? `<div class="data-point-limitations">⚠️ ${this.escapeHtml(dp.limitations)}</div>` : ''}
                    </div>
                `;
            }).join('');
        } else {
            dataPointsList.innerHTML = '<p class="no-data">No data points extracted</p>';
        }
        
        // Executive Implications
        const implicationsGrid = document.getElementById('analysis-implications');
        if (analysis.executive_implications) {
            const impl = analysis.executive_implications;
            implicationsGrid.innerHTML = `
                ${impl.financial ? `
                    <div class="implication-card">
                        <h5>💰 Financial</h5>
                        <p>${this.escapeHtml(impl.financial)}</p>
                    </div>
                ` : ''}
                ${impl.operational ? `
                    <div class="implication-card">
                        <h5>⚙️ Operational</h5>
                        <p>${this.escapeHtml(impl.operational)}</p>
                    </div>
                ` : ''}
                ${impl.timeline ? `
                    <div class="implication-card">
                        <h5>⏱️ Timeline</h5>
                        <p>${this.escapeHtml(impl.timeline)}</p>
                    </div>
                ` : ''}
                ${impl.risks ? `
                    <div class="implication-card">
                        <h5>⚠️ Risks</h5>
                        <p>${this.escapeHtml(impl.risks)}</p>
                    </div>
                ` : ''}
            `;
        } else {
            implicationsGrid.innerHTML = '<p class="no-data">No implications available</p>';
        }
        
        // Quotable Facts
        const quotesList = document.getElementById('analysis-quotes');
        if (analysis.quotable_facts && Array.isArray(analysis.quotable_facts)) {
            quotesList.innerHTML = analysis.quotable_facts.map((quote, i) => `
                <div class="quote-item" data-quote="${this.escapeHtml(quote)}">
                    <span class="quote-number">${i + 1}</span>
                    <span class="quote-text">${this.escapeHtml(quote)}</span>
                </div>
            `).join('');
            
            // Add click handlers for quote selection
            quotesList.querySelectorAll('.quote-item').forEach(item => {
                item.addEventListener('click', () => {
                    item.classList.toggle('selected');
                    const quote = item.dataset.quote;
                    if (item.classList.contains('selected')) {
                        if (!state.selectedQuotes.includes(quote)) {
                            state.selectedQuotes.push(quote);
                        }
                    } else {
                        state.selectedQuotes = state.selectedQuotes.filter(q => q !== quote);
                    }
                    this.updateCustomInstructionsHint();
                });
            });
        } else {
            quotesList.innerHTML = '<p class="no-data">No quotable facts extracted</p>';
        }
        
        // Methodology
        const methodologySection = document.getElementById('analysis-methodology');
        if (analysis.methodology) {
            const meth = analysis.methodology;
            methodologySection.innerHTML = `
                ${meth.approach ? `
                    <div class="methodology-item">
                        <strong>Approach</strong>
                        <p>${this.escapeHtml(meth.approach)}</p>
                    </div>
                ` : ''}
                ${meth.credibility ? `
                    <div class="methodology-item">
                        <strong>Credibility</strong>
                        <p>${this.escapeHtml(meth.credibility)}</p>
                    </div>
                ` : ''}
                ${meth.limitations ? `
                    <div class="methodology-item">
                        <strong>Limitations</strong>
                        <p>${this.escapeHtml(meth.limitations)}</p>
                    </div>
                ` : ''}
                ${meth.prior_work ? `
                    <div class="methodology-item">
                        <strong>Prior Work</strong>
                        <p>${this.escapeHtml(meth.prior_work)}</p>
                    </div>
                ` : ''}
            `;
        }
        
        // Show the custom instructions section
        document.getElementById('custom-instructions-section').style.display = 'block';
        document.getElementById('generate-btn').disabled = false;
    },
    
    updateCustomInstructionsHint() {
        const textarea = document.getElementById('custom-instructions');
        if (state.selectedQuotes.length > 0 && !textarea.value.trim()) {
            textarea.placeholder = `${state.selectedQuotes.length} fact(s) selected. Add instructions like "Focus on these selected points" or leave blank to include all insights.`;
        } else {
            textarea.placeholder = "Add your angle or perspective... e.g., 'Focus on practical applications for startups' or 'Highlight the implications for healthcare'";
        }
    },
    
    toggleDocSection(index) {
        const header = document.querySelector(`.doc-section-card[data-section="${index}"] .doc-section-header`);
        const body = document.getElementById(`doc-section-body-${index}`);
        const toggle = document.querySelector(`.doc-section-card[data-section="${index}"] .doc-section-toggle`);
        
        if (body && header && toggle) {
            const isExpanded = body.classList.contains('expanded');
            if (isExpanded) {
                body.classList.remove('expanded');
                header.classList.remove('expanded');
                toggle.classList.remove('expanded');
            } else {
                body.classList.add('expanded');
                header.classList.add('expanded');
                toggle.classList.add('expanded');
            }
        }
    },

    // Render LinkedIn post preview
    renderPostPreview(post) {
        const preview = document.getElementById('linkedin-preview');
        const actions = document.getElementById('post-actions');
        const summarySection = document.getElementById('summary-section');
        const summaryContent = document.getElementById('summary-content');

        if (!post) {
            preview.innerHTML = `
                <div class="preview-placeholder">
                    <div class="placeholder-icon">✨</div>
                    <p>Your generated post will appear here</p>
                    <p class="hint">Upload a paper and click Generate</p>
                </div>
            `;
            actions.style.display = 'none';
            summarySection.style.display = 'none';
            document.getElementById('refine-section').style.display = 'none';
            return;
        }

        const profileName = state.currentProfile?.name || 'You';
        const profileHeadline = state.currentProfile?.headline || 'Professional';
        const initials = profileName.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

        let imageHtml = '';
        if (post.selected_image_data?.image_url) {
            imageHtml = `<div class="post-image"><img src="${post.selected_image_data.image_url}" alt="Post image"></div>`;
        } else if (post.generated_image_url) {
            imageHtml = `<div class="post-image"><img src="${post.generated_image_url}" alt="AI generated image"></div>`;
        }

        preview.innerHTML = `
            <div class="post-preview">
                <div class="post-header">
                    <div class="post-avatar">${initials}</div>
                    <div class="post-meta">
                        <h4>${this.escapeHtml(profileName)}</h4>
                        <p>${this.escapeHtml(profileHeadline)}</p>
                    </div>
                </div>
                <div class="post-content">${this.escapeHtml(post.post_content)}</div>
                ${imageHtml}
            </div>
        `;

        actions.style.display = 'flex';
        
        // Show refine section
        document.getElementById('refine-section').style.display = 'block';
        document.getElementById('refine-input').value = ''; // Clear previous input

        // Render summary
        if (post.summary) {
            try {
                const summary = JSON.parse(post.summary);
                summaryContent.innerHTML = `
                    <p><strong>Summary:</strong> ${this.escapeHtml(summary.brief_summary || '')}</p>
                    ${summary.key_findings ? `
                        <p><strong>Key Findings:</strong></p>
                        <ul>
                            ${summary.key_findings.map(f => `<li>${this.escapeHtml(f)}</li>`).join('')}
                        </ul>
                    ` : ''}
                    ${summary.implications ? `<p><strong>Implications:</strong> ${this.escapeHtml(summary.implications)}</p>` : ''}
                    ${summary.surprising_insight ? `<p><strong>Interesting Insight:</strong> ${this.escapeHtml(summary.surprising_insight)}</p>` : ''}
                `;
            } catch {
                summaryContent.innerHTML = `<p>${this.escapeHtml(post.summary)}</p>`;
            }
            summarySection.style.display = 'block';
        }
    },

    // Render history
    renderHistory(posts) {
        const container = document.getElementById('history-list');

        if (!posts || posts.length === 0) {
            container.innerHTML = '<p class="empty-state">No posts generated yet. Upload a paper to get started!</p>';
            return;
        }

        container.innerHTML = posts.map(post => `
            <div class="history-card" data-id="${post.id}">
                <div class="history-card-header">
                    <h3>${this.escapeHtml(post.pdf_title || 'Untitled Paper')}</h3>
                    <time>${new Date(post.created_at).toLocaleDateString()}</time>
                </div>
                <div class="history-card-content">${this.escapeHtml(post.post_content)}</div>
                <div class="history-card-actions">
                    <button class="btn-secondary" onclick="App.copyPost('${post.id}')">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <rect x="5" y="5" width="9" height="9" rx="2" stroke="currentColor" stroke-width="1.5"/>
                            <path d="M11 5V3a2 2 0 00-2-2H3a2 2 0 00-2 2v6a2 2 0 002 2h2" stroke="currentColor" stroke-width="1.5"/>
                        </svg>
                        Copy
                    </button>
                    <button class="btn-secondary" onclick="App.viewPost('${post.id}')">
                        View Details
                    </button>
                </div>
            </div>
        `).join('');
    },

    // Load history
    async loadHistory() {
        try {
            const posts = await API.getHistory();
            state.history = posts;
            this.renderHistory(posts);
        } catch (error) {
            console.error('Error loading history:', error);
            this.showToast('Failed to load history', 'error');
        }
    },

    // Load and render prompts
    async loadPrompts() {
        try {
            const data = await API.getPrompts();
            this.renderPrompts(data);
        } catch (error) {
            console.error('Error loading prompts:', error);
            document.getElementById('prompts-list').innerHTML = 
                '<p class="empty-state">Failed to load prompts. Please refresh the page.</p>';
        }
    },

    // Render prompts
    renderPrompts(data) {
        const container = document.getElementById('prompts-list');
        const providerEl = document.getElementById('current-provider');
        
        // Update provider name
        if (providerEl) {
            providerEl.textContent = `${data.provider.charAt(0).toUpperCase() + data.provider.slice(1)} (${data.model})`;
        }

        container.innerHTML = data.prompts.map(prompt => `
            <div class="prompt-card">
                <div class="prompt-card-header">
                    <h3>
                        ${this.getPromptIcon(prompt.id)} ${this.escapeHtml(prompt.name)}
                    </h3>
                    <span class="prompt-badge">${prompt.id}</span>
                </div>
                <div class="prompt-card-body">
                    <p class="prompt-description">${this.escapeHtml(prompt.description)}</p>
                    
                    <div class="prompt-section">
                        <div class="prompt-section-label">System Prompt</div>
                        <div class="prompt-content">${this.escapeHtml(prompt.system_prompt)}</div>
                    </div>
                    
                    <div class="prompt-section">
                        <div class="prompt-section-label">User Prompt Template</div>
                        <div class="prompt-content">${this.highlightVariables(this.escapeHtml(prompt.user_prompt_template))}</div>
                    </div>
                    
                    <div class="prompt-variables">
                        <h4>Variables used:</h4>
                        <div class="variable-list">
                            ${prompt.variables.map(v => `<span class="variable-tag">{${this.escapeHtml(v)}}</span>`).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },

    // Get icon for prompt type
    getPromptIcon(id) {
        const icons = {
            'summarize': '📊',
            'generate': '✍️',
            'refine': '✏️'
        };
        return icons[id] || '📝';
    },

    // Highlight variables in prompt templates
    highlightVariables(text) {
        return text.replace(/\{([^}]+)\}/g, '<span class="variable">{$1}</span>');
    },

    // Helper: Escape HTML
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Set loading state
    setLoading(isLoading) {
        const btn = document.getElementById('generate-btn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoader = btn.querySelector('.btn-loader');

        btn.disabled = isLoading;
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnLoader.style.display = isLoading ? 'inline-flex' : 'none';
    },

    // Status indicator management
    showStatus() {
        document.getElementById('status-indicator').style.display = 'block';
        this.resetStatusSteps();
    },

    hideStatus() {
        document.getElementById('status-indicator').style.display = 'none';
    },

    resetStatusSteps() {
        document.querySelectorAll('.status-step').forEach(step => {
            step.classList.remove('pending', 'active', 'done');
            step.classList.add('pending');
        });
        document.querySelectorAll('.status-connector').forEach(conn => {
            conn.classList.remove('done');
        });
    },

    setStatusStep(stepName, status, message = '') {
        const steps = ['upload', 'process', 'analyze', 'generate'];
        const stepIndex = steps.indexOf(stepName);
        
        steps.forEach((step, index) => {
            const stepEl = document.querySelector(`.status-step[data-step="${step}"]`);
            const connectors = document.querySelectorAll('.status-connector');
            
            stepEl.classList.remove('pending', 'active', 'done');
            
            if (index < stepIndex) {
                stepEl.classList.add('done');
                if (connectors[index]) connectors[index].classList.add('done');
            } else if (index === stepIndex) {
                stepEl.classList.add(status);
                if (status === 'done' && connectors[index]) {
                    connectors[index].classList.add('done');
                }
            } else {
                stepEl.classList.add('pending');
            }
        });

        if (message) {
            document.getElementById('status-message').textContent = message;
        }
    },

    // Toggle advanced options
    toggleAdvancedOptions() {
        const panel = document.getElementById('advanced-options');
        const btn = document.getElementById('toggle-options-btn');
        state.advancedOptionsOpen = !state.advancedOptionsOpen;
        
        panel.style.display = state.advancedOptionsOpen ? 'block' : 'none';
        btn.classList.toggle('expanded', state.advancedOptionsOpen);
    },

    // Update authentication UI
    updateAuthUI(authData) {
        const loginBtn = document.getElementById('login-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const userInfo = document.getElementById('user-info');

        if (authData && authData.is_authenticated !== false) {
            loginBtn.style.display = 'none';
            logoutBtn.style.display = 'inline-block';
            userInfo.style.display = 'inline-block';
            userInfo.textContent = authData.user?.username || authData.profile?.name || 'User';
        } else {
            loginBtn.style.display = 'inline-block';
            logoutBtn.style.display = 'none';
            userInfo.style.display = 'none';
        }
    }
};

// ========================================
// Application Logic
// ========================================

const App = {
    async init() {
        this.bindEvents();
        // Check authentication first
        await this.checkAuthentication();
        if (state.isAuthenticated) {
            await this.loadProfiles();
            UI.updateProfileDropdown();
        } else {
            this.showLoginModal();
        }
    },

    bindEvents() {
        // Tab navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => UI.switchTab(tab.dataset.tab));
        });

        // Input type toggle (PDF vs URL)
        document.querySelectorAll('.input-type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.dataset.type;
                this.switchInputType(type);
            });
        });

        // File upload
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');

        uploadZone.addEventListener('click', () => fileInput.click());
        
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type === 'application/pdf') {
                this.handleFileUpload(file);
            } else {
                UI.showToast('Please upload a PDF file', 'error');
            }
        });

        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.handleFileUpload(file);
        });

        // URL fetch
        document.getElementById('fetch-url-btn').addEventListener('click', () => {
            this.handleUrlSubmit();
        });

        // URL input enter key
        document.getElementById('url-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.handleUrlSubmit();
            }
        });

        // Clear PDF
        document.getElementById('clear-pdf').addEventListener('click', () => {
            this.clearPdf();
        });

        // Analyze content
        document.getElementById('analyze-btn').addEventListener('click', () => {
            this.analyzeContent();
        });
        
        // Collapse analysis
        document.getElementById('collapse-analysis').addEventListener('click', () => {
            const content = document.getElementById('analysis-content');
            const btn = document.getElementById('collapse-analysis');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
            btn.classList.toggle('collapsed');
        });
        
        // Toggle methodology section
        document.getElementById('toggle-methodology').addEventListener('click', () => {
            const content = document.getElementById('analysis-methodology');
            const btn = document.getElementById('toggle-methodology');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
            btn.classList.toggle('open');
        });

        // Generate post
        document.getElementById('generate-btn').addEventListener('click', () => {
            this.generatePost();
        });

        // Copy post
        document.getElementById('copy-btn').addEventListener('click', () => {
            this.copyCurrentPost();
        });

        // Regenerate post
        document.getElementById('regenerate-btn').addEventListener('click', () => {
            this.regeneratePost();
        });

        // Profile form
        document.getElementById('profile-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveProfile();
        });

        // Add sample post
        document.getElementById('add-sample-btn').addEventListener('click', () => {
            this.addSamplePost();
        });

        // Profile selector
        document.getElementById('profile-select').addEventListener('change', (e) => {
            const profileId = e.target.value;
            state.currentProfile = state.profiles.find(p => p.id === profileId) || null;
            
            // If a profile is selected, update the generation options to match
            if (state.currentProfile) {
                document.getElementById('gen-tone').value = state.currentProfile.tone_preference || 'professional';
                document.getElementById('gen-length').value = state.currentProfile.post_length_preference || 'medium';
                document.getElementById('gen-emojis').checked = state.currentProfile.include_emojis !== false;
                document.getElementById('gen-hashtags').checked = state.currentProfile.include_hashtags !== false;
                
                // Pre-fill custom instructions from profile if the field is empty
                const customInstructionsField = document.getElementById('custom-instructions');
                if (!customInstructionsField.value.trim() && state.currentProfile.custom_instructions) {
                    customInstructionsField.value = state.currentProfile.custom_instructions;
                }
            }
        });

        // Advanced options toggle
        document.getElementById('toggle-options-btn').addEventListener('click', () => {
            UI.toggleAdvancedOptions();
        });

        // Refine post
        document.getElementById('refine-btn').addEventListener('click', () => {
            this.refinePost();
        });

        // Suggestion chips
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const suggestion = chip.dataset.suggestion;
                document.getElementById('refine-input').value = suggestion;
                // Optionally auto-submit
                // this.refinePost();
            });
        });

        // Allow Enter key to submit refinement (Shift+Enter for newline)
        document.getElementById('refine-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.refinePost();
            }
        });

        // Image modal events
        document.getElementById('modal-close').addEventListener('click', () => {
            UI.closeImageModal();
        });

        document.getElementById('modal-backdrop').addEventListener('click', () => {
            UI.closeImageModal();
        });

        document.getElementById('copy-image-btn').addEventListener('click', () => {
            UI.copyImageToClipboard();
        });

        document.getElementById('download-image-btn').addEventListener('click', () => {
            UI.downloadImage();
        });

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                UI.closeImageModal();
                App.hideLoginModal();
            }
        });

        // Authentication events
        document.getElementById('login-btn').addEventListener('click', () => {
            App.showLoginModal();
        });

        document.getElementById('logout-btn').addEventListener('click', () => {
            this.logout();
        });

        document.getElementById('auth-modal-close').addEventListener('click', () => {
            App.hideLoginModal();
        });

        document.getElementById('auth-modal-backdrop').addEventListener('click', () => {
            App.hideLoginModal();
        });

        // Auth tab switching
        document.querySelectorAll('.auth-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;
                document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(`${tabName}-form`).classList.add('active');
                document.getElementById('auth-modal-title').textContent = tabName === 'login' ? 'Login' : 'Register';
                document.getElementById(`${tabName}-error`).textContent = '';
            });
        });

        // Login form
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleLogin();
        });

        // Register form
        document.getElementById('register-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleRegister();
        });
    },

    async handleLogin() {
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        const errorEl = document.getElementById('login-error');

        if (!username || !password) {
            errorEl.textContent = 'Please enter username and password';
            return;
        }

        try {
            const result = await API.login(username, password);
            state.isAuthenticated = true;
            state.currentUser = result.user;
            UI.updateAuthUI(result);
            App.hideLoginModal();
            await this.loadProfiles();
            UI.updateProfileDropdown();
            UI.showToast('Login successful!', 'success');
        } catch (error) {
            errorEl.textContent = error.message || 'Login failed';
        }
    },

    async handleRegister() {
        const username = document.getElementById('register-username').value.trim();
        const email = document.getElementById('register-email').value.trim();
        const name = document.getElementById('register-name').value.trim();
        const password = document.getElementById('register-password').value;
        const errorEl = document.getElementById('register-error');

        if (!username || !password) {
            errorEl.textContent = 'Username and password are required';
            return;
        }

        if (password.length < 8) {
            errorEl.textContent = 'Password must be at least 8 characters';
            return;
        }

        try {
            const result = await API.register(username, email, password, name);
            state.isAuthenticated = true;
            state.currentUser = result.user;
            UI.updateAuthUI(result);
            App.hideLoginModal();
            await this.loadProfiles();
            UI.updateProfileDropdown();
            UI.showToast('Registration successful!', 'success');
        } catch (error) {
            errorEl.textContent = error.message || 'Registration failed';
        }
    },

    async logout() {
        try {
            await API.logout();
            state.isAuthenticated = false;
            state.currentUser = null;
            state.profiles = [];
            state.currentProfile = null;
            UI.updateAuthUI(null);
            UI.showToast('Logged out successfully', 'success');
            App.showLoginModal();
        } catch (error) {
            UI.showToast('Logout failed', 'error');
        }
    },

    async loadProfiles() {
        try {
            state.profiles = await API.getProfiles();
            if (state.profiles.length > 0) {
                state.currentProfile = state.profiles[0];
                
                // Pre-fill custom instructions from profile
                const customInstructionsField = document.getElementById('custom-instructions');
                if (customInstructionsField && state.currentProfile.custom_instructions) {
                    customInstructionsField.value = state.currentProfile.custom_instructions;
                }
                
                // Also pre-fill generation options
                const genTone = document.getElementById('gen-tone');
                const genLength = document.getElementById('gen-length');
                const genEmojis = document.getElementById('gen-emojis');
                const genHashtags = document.getElementById('gen-hashtags');
                
                if (genTone) genTone.value = state.currentProfile.tone_preference || 'professional';
                if (genLength) genLength.value = state.currentProfile.post_length_preference || 'medium';
                if (genEmojis) genEmojis.checked = state.currentProfile.include_emojis !== false;
                if (genHashtags) genHashtags.checked = state.currentProfile.include_hashtags !== false;
            }
        } catch (error) {
            console.error('Error loading profiles:', error);
        }
    },

    switchInputType(type) {
        state.inputType = type;
        
        // Update toggle buttons
        document.querySelectorAll('.input-type-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });
        
        // Show/hide appropriate input zone
        const uploadZone = document.getElementById('upload-zone');
        const urlZone = document.getElementById('url-input-zone');
        const pdfInfo = document.getElementById('pdf-info');
        
        // Only toggle if no content is loaded
        if (!state.currentPdf) {
            if (type === 'pdf') {
                uploadZone.style.display = 'block';
                urlZone.style.display = 'none';
            } else {
                uploadZone.style.display = 'none';
                urlZone.style.display = 'block';
            }
        }
    },

    async handleFileUpload(file) {
        const uploadZone = document.getElementById('upload-zone');
        const pdfInfo = document.getElementById('pdf-info');
        const analyzeBtn = document.getElementById('analyze-btn');

        uploadZone.classList.add('loading');
        
        // Show status indicator
        UI.showStatus();
        UI.setStatusStep('upload', 'active', 'Uploading your PDF...');

        try {
            // Simulate upload progress
            await new Promise(r => setTimeout(r, 300));
            UI.setStatusStep('upload', 'done', 'Extracting text and images...');
            UI.setStatusStep('process', 'active', 'Processing PDF content...');

            const pdf = await API.uploadPdf(file, state.currentProfile?.id);
            state.currentPdf = pdf;
            state.currentAnalysis = null; // Reset analysis

            // Update UI
            document.getElementById('content-icon').textContent = '📄';
            document.getElementById('pdf-title').textContent = pdf.title || 'Untitled Paper';
            document.getElementById('pdf-authors').textContent = pdf.authors || 'Unknown authors';
            document.getElementById('pdf-filename').textContent = pdf.original_filename;

            uploadZone.style.display = 'none';
            document.getElementById('url-input-zone').style.display = 'none';
            pdfInfo.style.display = 'flex';
            
            // Enable analyze button (not generate yet)
            analyzeBtn.disabled = false;
            analyzeBtn.style.display = 'flex';
            document.getElementById('generate-btn').disabled = true;
            document.getElementById('content-analysis').style.display = 'none';
            document.getElementById('custom-instructions-section').style.display = 'none';

            // Load extracted images
            if (pdf.extracted_images && pdf.extracted_images.length > 0) {
                UI.renderExtractedImages(pdf.extracted_images);
                state.selectedImageId = pdf.extracted_images[0]?.id;
            }

            UI.setStatusStep('process', 'done', 'PDF ready! Click "Analyze Content" to see insights.');
            UI.showToast('PDF processed successfully!', 'success');
            
            // Hide status after a moment
            setTimeout(() => UI.hideStatus(), 2000);
        } catch (error) {
            UI.showToast(error.message || 'Failed to upload PDF', 'error');
            UI.hideStatus();
        } finally {
            uploadZone.classList.remove('loading');
        }
    },

    async handleUrlSubmit() {
        const urlInput = document.getElementById('url-input');
        const fetchBtn = document.getElementById('fetch-url-btn');
        const btnText = fetchBtn.querySelector('.btn-text');
        const btnLoading = fetchBtn.querySelector('.btn-loading');
        const analyzeBtn = document.getElementById('analyze-btn');
        const url = urlInput.value.trim();

        if (!url) {
            UI.showToast('Please enter a URL', 'error');
            return;
        }

        // Show loading state
        btnText.style.display = 'none';
        btnLoading.style.display = 'flex';
        fetchBtn.disabled = true;
        
        UI.showStatus();
        UI.setStatusStep('upload', 'active', 'Fetching article...');

        try {
            await new Promise(r => setTimeout(r, 300));
            UI.setStatusStep('upload', 'done', 'Extracting content...');
            UI.setStatusStep('process', 'active', 'Processing article content...');

            const content = await API.submitUrl(url, state.currentProfile?.id);
            state.currentPdf = content;
            state.currentAnalysis = null; // Reset analysis

            // Update UI
            document.getElementById('content-icon').textContent = '🔗';
            document.getElementById('pdf-title').textContent = content.title || 'Untitled Article';
            document.getElementById('pdf-authors').textContent = content.authors || content.domain || 'Unknown source';
            document.getElementById('pdf-filename').textContent = content.domain || new URL(url).hostname;

            document.getElementById('upload-zone').style.display = 'none';
            document.getElementById('url-input-zone').style.display = 'none';
            document.getElementById('pdf-info').style.display = 'flex';
            
            // Enable analyze button (not generate yet)
            analyzeBtn.disabled = false;
            analyzeBtn.style.display = 'flex';
            document.getElementById('generate-btn').disabled = true;
            document.getElementById('content-analysis').style.display = 'none';
            document.getElementById('custom-instructions-section').style.display = 'none';

            // Hide extracted images for URL content (no images extracted)
            document.getElementById('extracted-images').style.display = 'none';

            UI.setStatusStep('process', 'done', 'Article ready! Click "Analyze Content" to see insights.');
            UI.showToast('Article fetched successfully!', 'success');
            
            setTimeout(() => UI.hideStatus(), 2000);
        } catch (error) {
            UI.showToast(error.message || 'Failed to fetch URL', 'error');
            UI.hideStatus();
        } finally {
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            fetchBtn.disabled = false;
        }
    },

    async analyzeContent() {
        if (!state.currentPdf) {
            UI.showToast('Please upload content first', 'error');
            return;
        }

        const analyzeBtn = document.getElementById('analyze-btn');
        const originalText = analyzeBtn.innerHTML;
        
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = `
            <svg class="spin" width="20" height="20" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-dasharray="31.4 31.4" stroke-linecap="round"/>
            </svg>
            <span>Analyzing...</span>
        `;
        
        UI.showStatus();
        UI.setStatusStep('analyze', 'active', 'Analyzing content with AI...');

        try {
            const result = await API.analyzeContent(state.currentPdf.id);
            state.currentAnalysis = result.analysis;
            state.selectedQuotes = []; // Reset selected quotes
            
            UI.setStatusStep('analyze', 'done', 'Analysis complete! Review the insights below.');
            UI.renderAnalysis(result.analysis);
            UI.showToast('Analysis complete!', 'success');
            
            setTimeout(() => UI.hideStatus(), 2000);
        } catch (error) {
            UI.showToast(error.message || 'Failed to analyze content', 'error');
            UI.hideStatus();
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = originalText;
        }
    },

    clearPdf() {
        state.currentPdf = null;
        state.currentAnalysis = null;
        state.selectedImageId = null;
        state.selectedQuotes = [];
        state.generatedPost = null;

        // Show appropriate input based on current type
        if (state.inputType === 'pdf') {
            document.getElementById('upload-zone').style.display = 'block';
            document.getElementById('url-input-zone').style.display = 'none';
        } else {
            document.getElementById('upload-zone').style.display = 'none';
            document.getElementById('url-input-zone').style.display = 'block';
        }
        
        document.getElementById('pdf-info').style.display = 'none';
        document.getElementById('extracted-images').style.display = 'none';
        document.getElementById('content-analysis').style.display = 'none';
        document.getElementById('custom-instructions-section').style.display = 'none';
        document.getElementById('analyze-btn').disabled = true;
        document.getElementById('analyze-btn').style.display = 'flex';
        document.getElementById('analyze-btn').innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>Analyze Content</span>
        `;
        document.getElementById('generate-btn').disabled = true;
        document.getElementById('file-input').value = '';
        document.getElementById('url-input').value = '';
        document.getElementById('custom-instructions').value = '';

        UI.renderPostPreview(null);
    },

    selectImage(imageId) {
        state.selectedImageId = imageId;
        document.querySelectorAll('.image-thumb').forEach(thumb => {
            thumb.classList.toggle('selected', thumb.dataset.id === imageId);
        });
    },

    async generatePost() {
        if (!state.currentPdf) {
            UI.showToast('Please upload content first', 'error');
            return;
        }
        
        if (!state.currentAnalysis) {
            UI.showToast('Please analyze the content first', 'error');
            return;
        }

        UI.setLoading(true);
        UI.showStatus();
        UI.setStatusStep('analyze', 'done', 'Analysis complete');
        UI.setStatusStep('generate', 'active', 'Writing your LinkedIn post...');

        try {
            // Gather all generation options
            let customInstructions = document.getElementById('custom-instructions').value.trim();
            
            // If user selected quotes, add them to instructions
            if (state.selectedQuotes.length > 0 && !customInstructions) {
                customInstructions = `Focus on these key facts: ${state.selectedQuotes.join('; ')}`;
            } else if (state.selectedQuotes.length > 0) {
                customInstructions += ` Especially emphasize: ${state.selectedQuotes.join('; ')}`;
            }
            
            const options = {
                useExtractedImage: document.getElementById('use-extracted-image').checked,
                generateImage: document.getElementById('generate-ai-image').checked,
                customInstructions: customInstructions,
                tonePreference: document.getElementById('gen-tone').value,
                postLengthPreference: document.getElementById('gen-length').value,
                includeEmojis: document.getElementById('gen-emojis').checked,
                includeHashtags: document.getElementById('gen-hashtags').checked,
                includeSourceLink: document.getElementById('include-source-link').checked
            };

            const post = await API.generatePost(
                state.currentPdf.id,
                state.currentProfile?.id,
                options
            );

            state.generatedPost = post;
            
            UI.setStatusStep('generate', 'done', 'Post generated successfully!');
            UI.renderPostPreview(post);
            UI.showToast('Post generated successfully!', 'success');
            
            // Hide status after success
            setTimeout(() => UI.hideStatus(), 1500);
        } catch (error) {
            UI.showToast(error.message || 'Failed to generate post', 'error');
            UI.hideStatus();
        } finally {
            UI.setLoading(false);
        }
    },

    async regeneratePost() {
        if (!state.generatedPost) {
            UI.showToast('No post to regenerate', 'error');
            return;
        }

        UI.setLoading(true);
        UI.showToast('Regenerating post...', 'success');

        try {
            const post = await API.regeneratePost(state.generatedPost.id);
            state.generatedPost = post;
            UI.renderPostPreview(post);
            UI.showToast('Post regenerated!', 'success');
        } catch (error) {
            UI.showToast(error.message || 'Failed to regenerate post', 'error');
        } finally {
            UI.setLoading(false);
        }
    },

    async refinePost() {
        if (!state.generatedPost) {
            UI.showToast('No post to refine', 'error');
            return;
        }

        const refinementPrompt = document.getElementById('refine-input').value.trim();
        if (!refinementPrompt) {
            UI.showToast('Please enter how you want to refine the post', 'error');
            return;
        }

        // Set loading state on refine button
        const refineBtn = document.getElementById('refine-btn');
        const btnText = refineBtn.querySelector('.btn-text');
        const btnLoader = refineBtn.querySelector('.btn-loader');
        
        refineBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-flex';

        UI.showToast('Refining your post...', 'success');

        try {
            const post = await API.refinePost(state.generatedPost.id, refinementPrompt);
            state.generatedPost = post;
            UI.renderPostPreview(post);
            document.getElementById('refine-input').value = ''; // Clear input after success
            UI.showToast('Post refined!', 'success');
        } catch (error) {
            UI.showToast(error.message || 'Failed to refine post', 'error');
        } finally {
            refineBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    },

    copyCurrentPost() {
        if (!state.generatedPost) return;

        navigator.clipboard.writeText(state.generatedPost.post_content)
            .then(() => UI.showToast('Post copied to clipboard!', 'success'))
            .catch(() => UI.showToast('Failed to copy post', 'error'));
    },

    copyPost(postId) {
        const post = state.history.find(p => p.id === postId);
        if (post) {
            navigator.clipboard.writeText(post.post_content)
                .then(() => UI.showToast('Post copied to clipboard!', 'success'))
                .catch(() => UI.showToast('Failed to copy post', 'error'));
        }
    },

    viewPost(postId) {
        const post = state.history.find(p => p.id === postId);
        if (post) {
            state.generatedPost = post;
            UI.renderPostPreview(post);
            UI.switchTab('generate');
        }
    },

    async saveProfile() {
        const profileData = {
            name: document.getElementById('profile-name').value,
            headline: document.getElementById('profile-headline').value,
            industry: document.getElementById('profile-industry').value,
            tone_preference: document.getElementById('profile-tone').value,
            post_length_preference: document.getElementById('profile-length').value,
            include_emojis: document.getElementById('profile-emojis').checked,
            include_hashtags: document.getElementById('profile-hashtags').checked,
            custom_instructions: document.getElementById('profile-custom-instructions').value.trim()
        };

        try {
            let profile;
            if (state.currentProfile) {
                profile = await API.updateProfile(state.currentProfile.id, profileData);
                UI.showToast('Profile updated!', 'success');
            } else {
                profile = await API.createProfile(profileData);
                UI.showToast('Profile created!', 'success');
            }

            state.currentProfile = profile;
            await this.loadProfiles();
            UI.updateProfileDropdown();
            UI.loadProfileData();
        } catch (error) {
            UI.showToast(error.message || 'Failed to save profile', 'error');
        }
    },

    async addSamplePost() {
        const content = document.getElementById('sample-post-input').value.trim();
        const notes = document.getElementById('sample-post-notes').value.trim();

        if (!content) {
            UI.showToast('Please enter a sample post', 'error');
            return;
        }

        if (!state.currentProfile) {
            UI.showToast('Please save your profile first', 'error');
            return;
        }

        try {
            await API.addSamplePost(state.currentProfile.id, {
                content,
                engagement_notes: notes
            });

            document.getElementById('sample-post-input').value = '';
            document.getElementById('sample-post-notes').value = '';

            // Reload profile to get updated sample posts
            await this.loadProfiles();
            state.currentProfile = state.profiles.find(p => p.id === state.currentProfile.id);
            UI.renderSamplePosts(state.currentProfile?.sample_posts || []);
            
            UI.showToast('Sample post added!', 'success');
        } catch (error) {
            UI.showToast(error.message || 'Failed to add sample post', 'error');
        }
    },

    async deleteSamplePost(postId) {
        if (!state.currentProfile) return;

        try {
            await API.deleteSamplePost(state.currentProfile.id, postId);
            
            // Reload profile
            await this.loadProfiles();
            state.currentProfile = state.profiles.find(p => p.id === state.currentProfile.id);
            UI.renderSamplePosts(state.currentProfile?.sample_posts || []);
            
            UI.showToast('Sample post deleted', 'success');
        } catch (error) {
            UI.showToast(error.message || 'Failed to delete sample post', 'error');
        }
    }
};

// ========================================
// Initialize App
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    App.init();
});

