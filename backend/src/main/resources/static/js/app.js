document.addEventListener('DOMContentLoaded', () => {
    // Toast Notification System
    const toastContainer = document.getElementById('toast-container');
    
    function showToast(message, type = 'info') {
        if (!toastContainer) return;
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // Dropzone functionality
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const parsedDataSection = document.getElementById('parsedDataSection');

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
            
            setTimeout(() => {
                uploadProgress.classList.add('hidden');
                displayParsedData(data.parsedData);
            }, 1000);
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
        
        // Sometimes the JSON string might need parsing if it comes back as string from API
        const parsed = typeof data === 'string' ? JSON.parse(data) : data;
        
        document.getElementById('pName').textContent = parsed.name || 'N/A';
        document.getElementById('pEmail').textContent = parsed.email || 'N/A';
        document.getElementById('pPhone').textContent = parsed.phone || 'N/A';
        document.getElementById('pRole').textContent = parsed.current_role || 'N/A';
        document.getElementById('pExp').textContent = parsed.experience_years || '0';
        document.getElementById('pSummary').textContent = parsed.summary || 'No summary available.';
        
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
        
        parsedDataSection.classList.remove('hidden');
    }

    // View buttons for existing resumes
    const viewButtons = document.querySelectorAll('.view-btn');
    viewButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            showToast('Fetching parsed data...', 'info');
            
            fetch(`/api/resume/${id}`)
            .then(res => res.json())
            .then(data => {
                // Dropzone hide, show parsed data
                if(dropzone) dropzone.classList.add('hidden');
                displayParsedData(data.parsedData);
                // Scroll to parsed data
                parsedDataSection.scrollIntoView({ behavior: 'smooth' });
            })
            .catch(err => {
                showToast('Failed to load resume details.', 'error');
                console.error(err);
            });
        });
    });
});
