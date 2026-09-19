/**
 * Step 1 — Resume Profile Highlights
 * Renders the active (latest) resume profile from the DB as an interactive
 * dashboard: profile hero, categorized skill chips, experience bullet
 * timeline, preferred roles/locations, and a profile-JSON sync control that
 * keeps ai-service/resume_profile.json + resume_experience.json fresh for the
 * Python compute scripts.
 */
document.addEventListener('DOMContentLoaded', () => {
    const heroSection = document.getElementById('profileHighlightsSection');
    const heroCard = document.getElementById('profileHero');
    const btnSyncProfile = document.getElementById('btnSyncProfile');
    const btnLoadHighlights = document.getElementById('btnLoadHighlights');
    const syncStatus = document.getElementById('profileSyncStatus');

    const toastContainer = document.getElementById('toast-container');
    function showToast(msg, type = 'info', duration = 4000) {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = msg;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    function safeParseJson(data) {
        if (!data) return {};
        let parsed = data;
        while (typeof parsed === 'string') {
            try { parsed = JSON.parse(parsed); } catch (e) { break; }
        }
        return parsed && typeof parsed === 'object' ? parsed : {};
    }

    function esc(s) {
        const div = document.createElement('div');
        div.textContent = s == null ? '' : String(s);
        return div.innerHTML;
    }

    // ---- Skill categorization (presentation only; does not affect scoring) ----
    const SKILL_GROUPS = [
        { key: 'core',     label: '⚙️ Core Backend',   match: ['java', 'spring boot', 'spring', 'spring security', 'spring mvc', 'spring cloud', 'microservices', 'rest api', 'rest apis', 'restful', 'hibernate', 'jpa', 'jdbc', 'agile', 'scrum'] },
        { key: 'database', label: '🗄️ Databases',      match: ['sql', 'postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'nosql', 'elasticsearch'] },
        { key: 'cloud',    label: '☁️ Cloud & DevOps', match: ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'ci/cd', 'cicd', 'git', 'github', 'maven', 'gradle', 'terraform', 'github actions', 'lambda', 'ec2', 's3', 'rds'] },
        { key: 'ai',       label: '🤖 AI & Tooling',   match: ['python', 'ollama', 'pgvector', 'apache tika', 'sentence-transformers', 'fastapi', 'langchain', 'postman', 'api testing'] },
    ];
    const GROUP_STYLES = { core: 'tag-core', database: 'tag-db', cloud: 'tag-cloud', ai: 'tag-ai' };

    function categorizeSkills(skills) {
        const groups = { core: [], database: [], cloud: [], ai: [], other: [] };
        (skills || []).forEach(raw => {
            const s = String(raw).trim();
            const lower = s.toLowerCase();
            const group = SKILL_GROUPS.find(g => g.match.some(m => lower === m || lower.includes(m)));
            groups[group ? group.key : 'other'].push(s);
        });
        return groups;
    }

    function chipRow(label, items, chipClass) {
        if (!items || items.length === 0) return '';
        return `
            <div class="skill-group">
                <h5>${label} <span class="badge-count badge-count-sm">${items.length}</span></h5>
                <div class="tags-container">
                    ${items.map(i => `<span class="tag ${chipClass || ''}">${esc(i)}</span>`).join('')}
                </div>
            </div>`;
    }

    function toBullets(description) {
        if (!description) return [];
        let lines = String(description).split(/\r?\n/)
            .map(l => l.replace(/^\s*[-•*\d.)]+\s*/, '').trim())
            .filter(l => l.length > 0);
        if (lines.length <= 1 && lines[0] && lines[0].length > 200) {
            // Single long blob: split into sentence bullets for readability
            lines = lines[0].split(/(?<=\.)\s+(?=[A-Z])/).map(s => s.trim()).filter(Boolean);
        }
        return lines;
    }

    function renderHero(parsed, meta) {
        const name = parsed.name || 'Unknown Candidate';
        const role = parsed.current_role || 'Software Engineer';
        const yoe = parsed.experience_years != null ? parsed.experience_years : (meta.experienceYears || 0);

        const metaChips = [];
        if (parsed.email) metaChips.push(`<a class="profile-chip" href="mailto:${esc(parsed.email)}">✉️ ${esc(parsed.email)}</a>`);
        if (parsed.phone) metaChips.push(`<span class="profile-chip">📞 ${esc(parsed.phone)}</span>`);
        if (parsed.current_location) metaChips.push(`<span class="profile-chip">📍 ${esc(parsed.current_location)}</span>`);
        if (parsed.linkedin_url) {
            const url = parsed.linkedin_url.startsWith('http') ? parsed.linkedin_url : 'https://' + parsed.linkedin_url;
            metaChips.push(`<a class="profile-chip" href="${esc(url)}" target="_blank">🔗 LinkedIn</a>`);
        }
        if (parsed.github_url) {
            const url = parsed.github_url.startsWith('http') ? parsed.github_url : 'https://' + parsed.github_url;
            metaChips.push(`<a class="profile-chip" href="${esc(url)}" target="_blank">🐙 GitHub</a>`);
        }

        heroCard.innerHTML = `
            <div class="profile-hero-top">
                <div class="profile-avatar">${esc(name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase())}</div>
                <div class="profile-id">
                    <h3 class="profile-name">${esc(name)}</h3>
                    <p class="profile-role">${esc(role)}</p>
                    <div class="profile-meta">${metaChips.join('')}</div>
                </div>
                <div class="profile-stats">
                    <div class="stat-box"><span class="stat-value">${yoe}</span><span class="stat-label">Years Exp.</span></div>
                    <div class="stat-box"><span class="stat-value">${(parsed.skills || []).length}</span><span class="stat-label">Skills</span></div>
                    <div class="stat-box"><span class="stat-value">${(parsed.experience || []).length}</span><span class="stat-label">Roles</span></div>
                </div>
            </div>
            ${parsed.summary ? `<p class="profile-summary">${esc(parsed.summary)}</p>` : ''}
            <div class="profile-source-line">
                <span class="badge-active">● Active Profile</span>
                <span class="text-small text-muted">Source: ${esc(meta.fileName || 'resume')} · Parsed ${esc(meta.createdAt || '')} · DB id ${esc(String(meta.id || '').substring(0, 8))}</span>
            </div>
        `;
    }

    function renderSkills(parsed) {
        const container = document.getElementById('profileSkills');
        if (!container) return;
        const groups = categorizeSkills(parsed.skills);
        let html = chipRow(SKILL_GROUPS[0].label, groups.core, GROUP_STYLES.core)
                 + chipRow(SKILL_GROUPS[1].label, groups.database, GROUP_STYLES.database)
                 + chipRow(SKILL_GROUPS[2].label, groups.cloud, GROUP_STYLES.cloud)
                 + chipRow(SKILL_GROUPS[3].label, groups.ai, GROUP_STYLES.ai)
                 + chipRow('🧩 Other', groups.other, '');
        if (!html) html = '<p class="text-muted text-small">No skills detected.</p>';
        container.innerHTML = html;
    }

    function renderExperience(parsed) {
        const container = document.getElementById('profileExperience');
        if (!container) return;
        const exps = parsed.experience || [];
        if (exps.length === 0) {
            container.innerHTML = '<p class="text-muted text-small">No experience entries parsed.</p>';
            return;
        }
        container.innerHTML = exps.map(exp => {
            const bullets = toBullets(exp.description);
            const bulletsHtml = bullets.length > 0
                ? `<ul class="exp-bullets">${bullets.map(b => `<li>${esc(b)}</li>`).join('')}</ul>`
                : '';
            return `
                <li class="exp-entry">
                    <div class="exp-entry-header">
                        <div>
                            <div class="exp-title">${esc(exp.role || 'Role')} <span class="text-muted">@ ${esc(exp.company || 'Company')}</span></div>
                            <div class="exp-company">${esc(exp.duration || '')}</div>
                        </div>
                    </div>
                    ${bulletsHtml}
                </li>`;
        }).join('');
    }

    function renderTargets(parsed) {
        const rolesEl = document.getElementById('profilePreferredRoles');
        const locsEl = document.getElementById('profilePreferredLocations');
        if (rolesEl) {
            rolesEl.innerHTML = (parsed.preferred_roles || []).map(r => `<span class="tag tag-role">🎯 ${esc(r)}</span>`).join('')
                || '<span class="text-muted text-small">None captured</span>';
        }
        if (locsEl) {
            locsEl.innerHTML = (parsed.preferred_locations || []).map(l => `<span class="tag tag-loc">📍 ${esc(l)}</span>`).join('')
                || '<span class="text-muted text-small">None captured</span>';
        }
    }

    function renderProfile(payload) {
        const parsed = safeParseJson(payload.parsed);
        if (!heroSection) return;
        heroSection.classList.remove('hidden');
        renderHero(parsed, payload);
        renderSkills(parsed);
        renderExperience(parsed);
        renderTargets(parsed);
        syncStatus.textContent = `Loaded ${payload.fileName || ''} — synced to JSON on upload`;
    }

    function loadActiveProfile() {
        fetch('/api/resume/profile/current')
            .then(res => {
                if (res.status === 204) { showEmptyState(); return null; }
                if (!res.ok) throw new Error('Failed to load profile');
                return res.json();
            })
            .then(data => { if (data) renderProfile(data); })
            .catch(err => {
                console.error(err);
                showEmptyState();
            });
    }

    function showEmptyState() {
        if (!heroSection || !heroCard) return;
        heroSection.classList.remove('hidden');
        heroCard.innerHTML = `
            <div class="profile-empty">
                <span class="upload-icon">📭</span>
                <h3>No active resume profile</h3>
                <p class="text-muted">Upload a resume below — it will be parsed, stored in PostgreSQL, and synced to <code>ai-service/resume_profile.json</code> for the Python pipeline.</p>
            </div>`;
        syncStatus.textContent = '';
    }

    if (btnSyncProfile) {
        btnSyncProfile.addEventListener('click', () => {
            btnSyncProfile.disabled = true;
            btnSyncProfile.textContent = '⟳ Syncing...';
            fetch('/api/resume/sync-files', { method: 'POST' })
                .then(res => {
                    if (!res.ok) throw new Error('Sync failed');
                    return res.json();
                })
                .then(data => {
                    showToast(`Profile JSON synced (${data.fileName})`, 'success');
                    syncStatus.textContent = `Last sync: ${new Date(data.syncedAt).toLocaleString()}`;
                })
                .catch(err => {
                    console.error(err);
                    showToast('Failed to sync profile JSON (is a resume uploaded?)', 'error');
                })
                .finally(() => {
                    btnSyncProfile.disabled = false;
                    btnSyncProfile.textContent = '⟳ Sync Profile JSON';
                });
        });
    }

    if (btnLoadHighlights) {
        btnLoadHighlights.addEventListener('click', loadActiveProfile);
    }

    // Refresh highlights right after a new upload completes (fired by app.js)
    window.addEventListener('resume:uploaded', () => loadActiveProfile());

    // Initial load
    loadActiveProfile();
});
