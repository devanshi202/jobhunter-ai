document.addEventListener('DOMContentLoaded', () => {
    // Toast Notification System
    const toastContainer = document.getElementById('toast-container');
    
    function showToast(message, type = 'info', duration = 4000) {
        if (!toastContainer) return null;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        toastContainer.appendChild(toast);
        
        const timer = setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);

        return toast;
    }

    function formatDate(dateVal) {
        if (!dateVal) return new Date().toLocaleString('en-US', { month: 'short', day: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
        
        let d;
        if (Array.isArray(dateVal)) {
            d = new Date(dateVal[0], dateVal[1] - 1, dateVal[2], dateVal[3] || 0, dateVal[4] || 0, dateVal[5] || 0);
        } else {
            d = new Date(dateVal);
        }

        if (isNaN(d.getTime())) {
            d = new Date();
        }

        return d.toLocaleString('en-US', {
            month: 'short',
            day: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function safeParseJson(data) {
        if (!data) return {};
        let parsed = data;
        while (typeof parsed === 'string') {
            try {
                parsed = JSON.parse(parsed);
            } catch (e) {
                break;
            }
        }
        return parsed && typeof parsed === 'object' ? parsed : {};
    }

    // Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const parsedDataSection = document.getElementById('parsedDataSection');
    const uploadSection = document.getElementById('uploadSection');
    const headerSubtitle = document.getElementById('headerSubtitle');
    const uploadAnotherBtn = document.getElementById('uploadAnotherBtn');

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => dropzone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, () => dropzone.classList.remove('dragover'), false);
        });

        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) handleFiles(files[0]);
        });

        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) handleFiles(this.files[0]);
        });
    }

    if (uploadAnotherBtn) {
        uploadAnotherBtn.addEventListener('click', () => {
            if (parsedDataSection) parsedDataSection.classList.add('hidden');
            if (uploadSection) uploadSection.classList.remove('hidden');
            if (dropzone) dropzone.classList.remove('hidden');
            if (uploadProgress) uploadProgress.classList.add('hidden');
            if (headerSubtitle) headerSubtitle.classList.remove('hidden');
            if (fileInput) fileInput.value = '';
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    function handleFiles(file) {
        // Validate
        if (file.size > 10 * 1024 * 1024) {
            showToast('File too large. Maximum size is 10MB.', 'error');
            return;
        }
        
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext !== 'pdf' && ext !== 'docx') {
            showToast('Only PDF and DOCX files are supported.', 'error');
            return;
        }

        uploadFile(file);
    }

    function uploadFile(file) {
        dropzone.classList.add('hidden');
        uploadProgress.classList.remove('hidden');
        progressFill.style.width = '30%';
        progressText.textContent = '30% - Uploading...';

        const formData = new FormData();
        formData.append('file', file);

        progressFill.style.width = '60%';
        progressText.textContent = '60% - AI is parsing your resume (this takes a moment)...';

        fetch('/api/resume/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) throw new Error('Upload failed');
            progressFill.style.width = '90%';
            return response.json();
        })
        .then(data => {
            progressFill.style.width = '100%';
            progressText.textContent = '100% - Complete!';
            showToast('Resume parsed successfully!', 'success');
            
            // Dynamically add row to table with robust date formatting
            const expYears = data.parsedData ? (data.parsedData.experience_years || 0) : 0;
            const dateStr = formatDate(data.createdAt);
            addResumeToTable(data.id, data.fileName, dateStr, expYears);

            setTimeout(() => {
                uploadProgress.classList.add('hidden');
                displayParsedData(data.parsedData);
                // Notify Step 1 highlights renderer to refresh active profile
                window.dispatchEvent(new CustomEvent('resume:uploaded', { detail: data }));
            }, 500);
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Failed to upload and parse resume.', 'error');
            dropzone.classList.remove('hidden');
            uploadProgress.classList.add('hidden');
        });
    }

    function displayParsedData(data) {
        if (!data) return;
        
        const parsed = safeParseJson(data);
        
        document.getElementById('pName').textContent = parsed.name || 'N/A';
        document.getElementById('pEmail').textContent = parsed.email || 'N/A';
        document.getElementById('pPhone').textContent = parsed.phone || 'N/A';
        document.getElementById('pLocation').textContent = parsed.current_location || 'N/A';
        document.getElementById('pRole').textContent = parsed.current_role || 'N/A';
        document.getElementById('pExp').textContent = parsed.experience_years || '0';
        document.getElementById('pSummary').textContent = parsed.summary || 'No summary available.';

        // Links (LinkedIn & GitHub)
        const linkedinEl = document.getElementById('pLinkedin');
        if (linkedinEl) {
            if (parsed.linkedin_url && parsed.linkedin_url.trim()) {
                const url = parsed.linkedin_url.startsWith('http') ? parsed.linkedin_url : 'https://' + parsed.linkedin_url;
                linkedinEl.href = url;
                linkedinEl.textContent = parsed.linkedin_url;
                linkedinEl.style.pointerEvents = 'auto';
            } else {
                linkedinEl.removeAttribute('href');
                linkedinEl.textContent = 'N/A';
                linkedinEl.style.pointerEvents = 'none';
            }
        }

        const githubEl = document.getElementById('pGithub');
        if (githubEl) {
            if (parsed.github_url && parsed.github_url.trim()) {
                const url = parsed.github_url.startsWith('http') ? parsed.github_url : 'https://' + parsed.github_url;
                githubEl.href = url;
                githubEl.textContent = parsed.github_url;
                githubEl.style.pointerEvents = 'auto';
            } else {
                githubEl.removeAttribute('href');
                githubEl.textContent = 'N/A';
                githubEl.style.pointerEvents = 'none';
            }
        }

        // Skills
        const skillsContainer = document.getElementById('pSkills');
        skillsContainer.innerHTML = '';
        if (parsed.skills && Array.isArray(parsed.skills)) {
            parsed.skills.forEach(skill => {
                const span = document.createElement('span');
                span.className = 'tag';
                span.textContent = skill;
                skillsContainer.appendChild(span);
            });
        }
        
        // Experience
        const expList = document.getElementById('pExperienceList');
        expList.innerHTML = '';
        if (parsed.experience && Array.isArray(parsed.experience)) {
            parsed.experience.forEach(exp => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <div class="exp-title">${exp.role || 'Role'}</div>
                    <div class="exp-company">${exp.company || 'Company'} | ${exp.duration || 'Duration'}</div>
                    <div class="text-small text-muted">${exp.description || ''}</div>
                `;
                expList.appendChild(li);
            });
        }
        
        // Projects
        const projList = document.getElementById('pProjectsList');
        if (projList) {
            projList.innerHTML = '';
            if (parsed.projects && Array.isArray(parsed.projects)) {
                parsed.projects.forEach(proj => {
                    const li = document.createElement('li');
                    const techs = proj.technologies ? proj.technologies.join(', ') : '';
                    li.innerHTML = `
                        <div class="exp-title">${proj.title || 'Project'}</div>
                        <div class="exp-company text-small text-muted">${techs}</div>
                        <div class="text-small">${proj.description || ''}</div>
                    `;
                    projList.appendChild(li);
                });
            }
        }
        
        // Achievements
        const achList = document.getElementById('pAchievementsList');
        if (achList) {
            achList.innerHTML = '';
            if (parsed.achievements && Array.isArray(parsed.achievements)) {
                parsed.achievements.forEach(ach => {
                    const li = document.createElement('li');
                    li.innerHTML = `<div class="text-small">${ach}</div>`;
                    achList.appendChild(li);
                });
            }
        }

        // Targeted Roles
        const rolesContainer = document.getElementById('pPreferredRoles');
        if (rolesContainer) {
            rolesContainer.innerHTML = '';
            if (parsed.preferred_roles && Array.isArray(parsed.preferred_roles)) {
                parsed.preferred_roles.forEach(role => {
                    const span = document.createElement('span');
                    span.className = 'tag';
                    span.textContent = role;
                    rolesContainer.appendChild(span);
                });
            }
        }

        // Preferred Locations
        const locationsContainer = document.getElementById('pPreferredLocations');
        if (locationsContainer) {
            locationsContainer.innerHTML = '';
            if (parsed.preferred_locations && Array.isArray(parsed.preferred_locations)) {
                parsed.preferred_locations.forEach(loc => {
                    const span = document.createElement('span');
                    span.className = 'tag';
                    span.textContent = loc;
                    locationsContainer.appendChild(span);
                });
            }
        }
        
        // Hide upload section & subtitle, show parsed data section
        if (uploadSection) uploadSection.classList.add('hidden');
        if (headerSubtitle) headerSubtitle.classList.add('hidden');
        if (parsedDataSection) {
            parsedDataSection.classList.remove('hidden');
            parsedDataSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    function addResumeToTable(id, fileName, createdAtStr, expYears) {
        const tbody = document.getElementById('resumesTableBody');
        const listSection = document.getElementById('resumesListSection');

        if (listSection && listSection.classList.contains('hidden')) {
            listSection.classList.remove('hidden');
        }

        if (tbody) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${fileName}</td>
                <td>${createdAtStr}</td>
                <td>${expYears} yrs</td>
                <td>
                    <button class="btn-ghost view-btn" data-id="${id}">View Data</button>
                </td>
            `;
            tbody.insertBefore(tr, tbody.firstChild);

            const btn = tr.querySelector('.view-btn');
            if (btn) {
                btn.addEventListener('click', function() {
                    fetchResumeById(id);
                });
            }
        }
    }

    function fetchResumeById(id) {
        const loadingToast = showToast('Fetching parsed data...', 'info', 1000);
        fetch(`/api/resume/${id}`)
        .then(res => {
            if (!res.ok) throw new Error('Failed to fetch');
            return res.json();
        })
        .then(data => {
            if (loadingToast) loadingToast.remove();
            displayParsedData(data.parsedData);
        })
        .catch(err => {
            if (loadingToast) loadingToast.remove();
            showToast('Failed to load resume details.', 'error');
            console.error(err);
        });
    }

    // View buttons for existing resumes
    const viewButtons = document.querySelectorAll('.view-btn');
    viewButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            fetchResumeById(id);
        });
    });

    // Auto-load latest resume profile on page load if one exists in DB
    if (parsedDataSection) {
        fetch('/api/resume/latest')
            .then(res => {
                if (res.status === 200) return res.json();
                return null;
            })
            .then(data => {
                if (data && data.parsedData) {
                    displayParsedData(data.parsedData);
                }
            })
            .catch(err => {
                console.log('No prior resume to auto-load:', err);
            });
    }
});
