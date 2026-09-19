document.addEventListener('DOMContentLoaded', () => {
    const jobSearchForm = document.getElementById('jobSearchForm');
    const keywordInput = document.getElementById('keywordInput');
    const locationInput = document.getElementById('locationInput');
    const platformSelect = document.getElementById('platformSelect');
    const recencySelect = document.getElementById('recencySelect');
    const btnScrapeJobs = document.getElementById('btnScrapeJobs');
    const scrapingLoader = document.getElementById('scrapingLoader');
    const jobsGrid = document.getElementById('jobsGrid');
    const noJobsNotice = document.getElementById('noJobsNotice');
    const jobsCountBadge = document.getElementById('jobsCountBadge');
    const totalPlatformBadge = document.getElementById('totalPlatformBadge');
    const btnScrapeByResume = document.getElementById('btnScrapeByResume');
    const resumeSelect = document.getElementById('resumeSelect');
    const btnScrapeJobSpy = document.getElementById('btnScrapeJobSpy');

    const toastContainer = document.getElementById('toast-container');
    function showToast(msg, type = 'info') {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = msg;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ---- Scraped Jobs Explorer: search_location > search_term > platform > jobs ----
    const browseState = { location: null, term: null, platform: null };
    const browseLocations = document.getElementById('browseLocations');
    const browseTerms = document.getElementById('browseTerms');
    const browsePlatforms = document.getElementById('browsePlatforms');
    const browseJobsWrap = document.getElementById('browseJobsWrap');
    const browseJobsBody = document.getElementById('browseJobsBody');
    const browseBreadcrumb = document.getElementById('browseBreadcrumb');
    const originChips = document.getElementById('originChips');
    const jobsFilterInput = document.getElementById('jobsFilterInput');
    const jobsFilterCount = document.getElementById('jobsFilterCount');
    const btnRankJobs = document.getElementById('btnRankJobs');
    const rankToggle = document.getElementById('rankToggle');
    let currentJobs = [];
    let rankMode = false;

    function currentResumeId() {
        const matchSel = document.getElementById('matchProfileSelect');
        if (matchSel && matchSel.value) return matchSel.value;
        const sel = document.getElementById('resumeSelect');
        return (sel && sel.value) ? sel.value : null;
    }

    // Profile picker for ranking: canonical text by default, uploaded resumes as overrides
    (function initMatchProfileSelect() {
        const matchSel = document.getElementById('matchProfileSelect');
        if (!matchSel) return;
        fetch('/api/resume')
            .then(res => res.ok ? res.json() : [])
            .then(resumes => {
                (resumes || []).forEach(r => {
                    const opt = document.createElement('option');
                    opt.value = r.id;
                    opt.textContent = `📄 ${r.fileName} (${r.experienceYears != null ? r.experienceYears : '?'} yrs)`;
                    matchSel.appendChild(opt);
                });
            })
            .catch(() => {});
    })();

    // Short city codes expand to portal location text (state codes match as comma-tokens)
    const LOCATION_ALIASES = {
        'ggn':      { cities: ['gurugram', 'gurgaon'], codes: ['hr'] },
        'gurgaon':  { cities: ['gurugram', 'gurgaon'], codes: ['hr'] },
        'blr':      { cities: ['bengaluru', 'bangalore'], codes: ['ka'] },
        'bangalore':{ cities: ['bengaluru', 'bangalore'], codes: ['ka'] },
        'hyd':      { cities: ['hyderabad'], codes: ['ts'] },
        'pune':     { cities: ['pune'], codes: ['mh'] },
        'noida':    { cities: ['noida'], codes: ['up'] },
        'ncr':      { cities: ['delhi', 'ncr'], codes: ['dl'] },
        'delhi':    { cities: ['delhi'], codes: ['dl'] },
        'chennai':  { cities: ['chennai'], codes: ['tn'] },
        'remote':   { cities: ['remote'], codes: [] }
    };

    function jobLocationHay(job) {
        return ((job.location || '') + ' | ' + (job.searchLocation || '')).toLowerCase();
    }

    function jobMatchesLocationFilter(job, rawTerm) {
        const t = (rawTerm || '').trim().toLowerCase();
        if (!t) return true;
        const hay = jobLocationHay(job);
        const alias = LOCATION_ALIASES[t];
        if (alias) {
            if (alias.cities.some(c => hay.includes(c))) return true;
            const tokens = hay.split(/[|,]/).map(s => s.trim());
            if (alias.codes.some(code => tokens.includes(code))) return true;
            return false;
        }
        return hay.includes(t);
    }

    function renderOriginChips() {
        if (!originChips) return;
        const counts = {};
        currentJobs.forEach(item => {
            const job = item.job || item;
            const o = job.searchLocation || '(unknown)';
            counts[o] = (counts[o] || 0) + 1;
        });
        const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
        const parts = [`<button class="chip-btn${jobsFilterInput && jobsFilterInput.value.trim() === '' ? ' active' : ''}" data-origin="">All ${currentJobs.length}</button>`];
        entries.forEach(([origin, count]) => {
            parts.push(`<button class="chip-btn${jobsFilterInput && jobsFilterInput.value.trim().toLowerCase() === origin.toLowerCase() ? ' active' : ''}" data-origin="${esc(origin)}">${esc(origin)} · ${count}</button>`);
        });
        originChips.innerHTML = parts.join('');
        originChips.querySelectorAll('.chip-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (jobsFilterInput) jobsFilterInput.value = btn.getAttribute('data-origin');
                applyJobFilter();
            });
        });
    }

    function applyJobFilter() {
        if (!browseJobsBody) return;
        const term = jobsFilterInput ? jobsFilterInput.value : '';
        const shown = currentJobs.filter(item => jobMatchesLocationFilter(item.job || item, term));
        browseJobsBody.innerHTML = '';
        shown.forEach(item => {
            const job = item.job || item;
            const match = item.match || null;
            const tr = document.createElement('tr');
            const shortId = job.id ? String(job.id).slice(0, 8) : '';
            const remoteBadge = job.isRemote ? ` <span class="tag tag-remote" title="Portal is_remote flag = true">🏠 Remote</span>` : '';
            let matchHtml = '';
            if (match) {
                const labelClass = 'match-' + String(match.label || '').toLowerCase();
                const rankTag = match.rank ? `#${match.rank} ` : '';
                const reasons = (match.reasons || []).map(r => `<li>${esc(r)}</li>`).join('');
                const overlap = (match.skillOverlap || []).slice(0, 8).map(s => `<span class="tag tag-skill">${esc(s)}</span>`).join(' ');
                matchHtml = `<br/><span class="match-badge ${labelClass}" title="semantic ${match.semantic} · skill ${match.skill} · exp ${match.exp} · domain ${match.domain}">${rankTag}${match.score} · ${esc(match.label)}</span>`
                    + (reasons ? `<ul class="match-reasons">${reasons}</ul>` : '')
                    + (overlap ? `<div class="match-skills">${overlap}</div>` : '');
            }
            const originNote = (job.searchLocation && browseState.location === 'Remote' && job.searchLocation !== 'Remote')
                ? `<br/><span class="text-small text-muted" title="Query that found this job">origin: ${esc(job.searchLocation)}</span>` : '';
            tr.innerHTML = `
                <td><a href="/jobs/${esc(job.id)}" class="text-link"><strong>${esc(job.title)}</strong></a>${remoteBadge}<br/><span class="text-small text-muted">${esc(job.companyName)} · #${esc(shortId)}</span>${matchHtml}</td>
                <td class="text-small">${esc(job.location)}${originNote}</td>
                <td class="text-small">${job.jobUrl ? `<a href="${esc(job.jobUrl)}" target="_blank" class="text-link">posting ↗</a>` : ''}${job.jobUrlDirect ? `<br/><a href="${esc(job.jobUrlDirect)}" target="_blank" class="text-link">direct ↗</a>` : ''}</td>
                <td class="text-small">${esc(formatDate(job.postedAt))}</td>
                <td class="text-small">${esc(job.jobType)}${job.jobLevel ? ' · ' + esc(job.jobLevel) : ''}${job.jobFunction ? '<br/>' + esc(job.jobFunction) : ''}</td>
                <td class="text-small">${esc(job.emails)}</td>`;
            browseJobsBody.appendChild(tr);
        });
        if (jobsFilterCount) {
            jobsFilterCount.textContent = term.trim() ? `${shown.length} of ${currentJobs.length} jobs match` : `${currentJobs.length} jobs`;
        }
        renderOriginChips();
        if (!shown.length) {
            browseJobsBody.innerHTML = '<tr><td colspan="6" class="text-small text-muted">No jobs match this location filter.</td></tr>';
        }
    }

    if (jobsFilterInput) {
        jobsFilterInput.addEventListener('input', () => {
            applyJobFilter();
            try {
                const saved = JSON.parse(sessionStorage.getItem('jobsExplorer') || '{}');
                saved.filter = jobsFilterInput.value;
                sessionStorage.setItem('jobsExplorer', JSON.stringify(saved));
            } catch (e) { /* ignore */ }
        });
    }

    let pendingFilter = null;

    async function loadJobs(location, term, platform) {
        browseState.location = location; browseState.term = term; browseState.platform = platform;
        renderBreadcrumb(); showLevel('jobs');
        if (jobsFilterInput) jobsFilterInput.value = pendingFilter != null ? pendingFilter : '';
        pendingFilter = null;
        browseJobsBody.innerHTML = '<tr><td colspan="6" class="text-small text-muted">Loading jobs…</td></tr>';
        try {
            const base = rankMode ? '/api/jobs/browse/list-ranked' : '/api/jobs/browse/list';
            let url = base + '?searchLocation=' + encodeURIComponent(location) + '&searchTerm=' + encodeURIComponent(term) + '&platform=' + encodeURIComponent(platform);
            const rid = currentResumeId();
            if (rankMode && rid) url += '&resumeId=' + encodeURIComponent(rid);
            const res = await fetch(url);
            if (!res.ok) throw new Error(await res.text());
            currentJobs = await res.json();
            if (rankMode && currentJobs.length && !currentJobs[0].match) {
                showToast('No match scores yet — click "⚡ Rank by my profile" first.', 'info');
            }
            applyJobFilter();
        } catch (e) {
            console.error(e);
            currentJobs = [];
            browseJobsBody.innerHTML = '<tr><td colspan="6" class="text-small text-muted">Failed to load jobs.</td></tr>';
        }
    }

    if (rankToggle) {
        rankToggle.addEventListener('change', () => {
            rankMode = rankToggle.checked;
            if (browseState.platform) loadJobs(browseState.location, browseState.term, browseState.platform);
        });
    }

    if (btnRankJobs) {
        btnRankJobs.addEventListener('click', async () => {
            btnRankJobs.disabled = true;
            const rid = currentResumeId();
            if (importSummary) importSummary.textContent = 'Matching: embedding JDs via pgvector + scoring vs your profile (may take a few minutes on first run)…';
            showToast('⚡ Matching started — embedding JDs and scoring against your profile…', 'info');
            try {
                let url = '/api/jobs/match';
                if (rid) url += '?resumeId=' + encodeURIComponent(rid);
                const res = await fetch(url, { method: 'POST' });
                if (!res.ok) throw new Error(await res.text());
                const s = await res.json();
                if (importSummary) importSummary.textContent = `✅ Ranked ${s.scoredJobs} jobs against your profile (${s.candidateYoe} YOE · source: ${s.profileSource}) · ${s.embeddingsBackfilled} embeddings computed · weights: semantic 44 / skill 28 / exp 17 / domain 11.`;
                showToast(`Ranked ${s.scoredJobs} jobs — best matches now on top.`, 'success');
                rankMode = true;
                if (rankToggle) rankToggle.checked = true;
                if (browseState.platform) loadJobs(browseState.location, browseState.term, browseState.platform);
                else loadLocations();
            } catch (e) {
                console.error(e);
                showToast('Matching failed: ' + e.message, 'error');
                if (importSummary) importSummary.textContent = 'Matching failed. Ensure ai-service is running on port 8000.';
            } finally {
                btnRankJobs.disabled = false;
            }
        });
    }
    const btnImportCsv = document.getElementById('btnImportCsv');
    const importSummary = document.getElementById('importSummary');

    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    function showLevel(which) {
        if (!browseLocations) return;
        browseLocations.classList.toggle('hidden', which !== 'locations');
        browseTerms.classList.toggle('hidden', which !== 'terms');
        browsePlatforms.classList.toggle('hidden', which !== 'platforms');
        browseJobsWrap.classList.toggle('hidden', which !== 'jobs');
    }

    function renderBreadcrumb() {
        if (!browseBreadcrumb) return;
        try {
            sessionStorage.setItem('jobsExplorer', JSON.stringify({
                location: browseState.location,
                term: browseState.term,
                platform: browseState.platform,
                filter: jobsFilterInput ? jobsFilterInput.value : '',
                rankMode: rankMode
            }));
        } catch (e) { /* storage unavailable — ignore */ }
        const parts = [`<a href="#" data-nav="locations">Locations</a>`];
        if (browseState.location) parts.push(`<span> › </span><a href="#" data-nav="terms">${esc(browseState.location)}</a>`);
        if (browseState.term) parts.push(`<span> › </span><a href="#" data-nav="platforms">${esc(browseState.term)}</a>`);
        if (browseState.platform) parts.push(`<span> › </span><span>${esc(browseState.platform)}</span>`);
        browseBreadcrumb.innerHTML = parts.join('');
        browseBreadcrumb.querySelectorAll('a').forEach(a => {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                const nav = a.getAttribute('data-nav');
                if (nav === 'locations') loadLocations();
                else if (nav === 'terms') loadTerms(browseState.location);
                else if (nav === 'platforms') loadPlatforms(browseState.location, browseState.term);
            });
        });
    }

    function countRows(data) {
        return data.map(d => {
            const name = d.name != null ? d.name : d.NAME;
            const cnt = d.cnt != null ? d.cnt : d.CNT;
            return { name, count: cnt };
        });
    }

    async function loadLocations() {
        browseState.location = null; browseState.term = null; browseState.platform = null;
        renderBreadcrumb(); showLevel('locations');
        if (!browseLocations) return;
        browseLocations.innerHTML = '<p class="text-small text-muted">Loading locations…</p>';
        try {
            const res = await fetch('/api/jobs/browse/locations');
            const data = countRows(await res.json());
            if (!data.length) {
                browseLocations.innerHTML = '<p class="text-small text-muted">No imported jobs yet. Click "📥 Import CSV (dedupe)".</p>';
                return;
            }
            browseLocations.innerHTML = '';
            data.forEach(({ name, count }) => {
                const card = document.createElement('button');
                card.className = 'browse-card';
                card.innerHTML = `<span class="browse-card-name">📍 ${esc(name)}</span><span class="badge-count">${esc(count)}</span>`;
                card.addEventListener('click', () => loadTerms(name));
                browseLocations.appendChild(card);
            });
        } catch (e) {
            browseLocations.innerHTML = '<p class="text-small text-muted">Failed to load locations.</p>';
        }
    }

    async function loadTerms(location) {
        browseState.location = location; browseState.term = null; browseState.platform = null;
        renderBreadcrumb(); showLevel('terms');
        browseTerms.innerHTML = '<p class="text-small text-muted">Loading search terms…</p>';
        try {
            const res = await fetch('/api/jobs/browse/terms?searchLocation=' + encodeURIComponent(location));
            const data = countRows(await res.json());
            browseTerms.innerHTML = '';
            data.forEach(({ name, count }) => {
                const row = document.createElement('button');
                row.className = 'browse-row';
                row.innerHTML = `<span>🔎 ${esc(name)}</span><span class="badge-count">${esc(count)}</span>`;
                row.addEventListener('click', () => loadPlatforms(location, name));
                browseTerms.appendChild(row);
            });
        } catch (e) {
            browseTerms.innerHTML = '<p class="text-small text-muted">Failed to load search terms.</p>';
        }
    }

    async function loadPlatforms(location, term) {
        browseState.location = location; browseState.term = term; browseState.platform = null;
        renderBreadcrumb(); showLevel('platforms');
        browsePlatforms.innerHTML = '<p class="text-small text-muted">Loading platforms…</p>';
        try {
            const res = await fetch('/api/jobs/browse/platforms?searchLocation=' + encodeURIComponent(location) + '&searchTerm=' + encodeURIComponent(term));
            const data = countRows(await res.json());
            browsePlatforms.innerHTML = '';
            data.forEach(({ name, count }) => {
                const card = document.createElement('button');
                card.className = 'browse-card';
                card.innerHTML = `<span class="browse-card-name">${esc(name)}</span><span class="badge-count">${esc(count)}</span>`;
                card.addEventListener('click', () => loadJobs(location, term, name));
                browsePlatforms.appendChild(card);
            });
        } catch (e) {
            browsePlatforms.innerHTML = '<p class="text-small text-muted">Failed to load platforms.</p>';
        }
    }

    if (btnImportCsv) {
        btnImportCsv.addEventListener('click', async () => {
            btnImportCsv.disabled = true;
            if (importSummary) importSummary.textContent = 'Importing + deduping by company + title…';
            try {
                const res = await fetch('/api/jobs/import-csv', { method: 'POST' });
                if (!res.ok) throw new Error(await res.text());
                const s = await res.json();
                if (importSummary) importSummary.textContent = `✅ ${s.uniqueJobs} unique jobs (deduped by company + title) · ${s.duplicatesSkipped} duplicates skipped · ${s.newlySaved} newly saved · ${s.alreadyInDb} already in DB${s.backfilledIsRemote ? ' · ' + s.backfilledIsRemote + ' is_remote flags backfilled' : ''} · ${s.totalRows} rows read.`;
                showToast(`Imported ${s.newlySaved} new jobs (${s.uniqueJobs} unique)`, 'success');
                loadLocations();
            } catch (e) {
                console.error(e);
                showToast('CSV import failed: ' + e.message, 'error');
                if (importSummary) importSummary.textContent = 'Import failed. Check backend logs / CSV path.';
            } finally {
                btnImportCsv.disabled = false;
            }
        });
    }

    if (browseLocations) {
        let saved = null;
        try { saved = JSON.parse(sessionStorage.getItem('jobsExplorer') || 'null'); } catch (e) {}
        if (saved && saved.platform) {
            // Restore the exact listing we came from (job detail → Back)
            rankMode = !!saved.rankMode;
            if (rankToggle) rankToggle.checked = rankMode;
            pendingFilter = saved.filter || '';
            (async () => {
                await loadLocations();
                if (browseState.location !== undefined) await loadTerms(saved.location);
                await loadPlatforms(saved.location, saved.term);
                await loadJobs(saved.location, saved.term, saved.platform);
            })();
        } else {
            loadLocations();
        }
    }

    if (jobSearchForm) {
        jobSearchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            triggerScrape();
        });
    }

    if (btnScrapeByResume) {
        btnScrapeByResume.addEventListener('click', () => {
            const resumeId = resumeSelect ? resumeSelect.value : null;
            if (!resumeId) {
                showToast('Please select a resume profile first', 'error');
                return;
            }
            triggerScrapeByResume(resumeId);
        });
    }

    // Platform pill filters
    const pillBtns = document.querySelectorAll('.pill-btn');
    pillBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            pillBtns.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            const platform = this.getAttribute('data-filter');
            filterJobsByPlatform(platform);
        });
    });

    // JobSpy scrape button
    if (btnScrapeJobSpy) {
        btnScrapeJobSpy.addEventListener('click', () => {
            triggerJobSpyScrape();
        });
    }

    function triggerScrape() {
        const rawKw = keywordInput ? keywordInput.value.trim() : 'ALL_MATRIX';
        const keyword = (rawKw === 'ALL_MATRIX') ? '' : rawKw;
        const location = locationInput ? locationInput.value.trim() : '';
        const platform = platformSelect ? platformSelect.value : 'ALL';
        const hoursRecent = recencySelect ? recencySelect.value : '24';

        if (scrapingLoader) scrapingLoader.classList.remove('hidden');
        if (btnScrapeJobs) btnScrapeJobs.disabled = true;

        const params = new URLSearchParams({
            keyword: keyword,
            location: location,
            platform: platform,
            hoursRecent: hoursRecent
        });

        fetch('/api/jobs/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        })
        .then(res => {
            if (!res.ok) throw new Error('Scraping request failed');
            return res.json();
        })
        .then(jobs => {
            showToast(`Scraped & saved ${jobs.length} jobs with real portal dates!`, 'success');
            renderJobs(jobs);
        })
        .catch(err => {
            console.error(err);
            showToast('Failed to scrape job postings.', 'error');
        })
        .finally(() => {
            if (scrapingLoader) scrapingLoader.classList.add('hidden');
            if (btnScrapeJobs) btnScrapeJobs.disabled = false;
        });
    }

    function triggerJobSpyScrape() {
        const rawKw = keywordInput ? keywordInput.value.trim() : 'ALL_MATRIX';
        const keyword = (rawKw === 'ALL_MATRIX') ? '' : rawKw;
        const location = locationInput ? locationInput.value.trim() : '';
        const hoursRecent = recencySelect ? recencySelect.value : '336'; // default 14 days for bulk

        if (scrapingLoader) {
            scrapingLoader.classList.remove('hidden');
            const pText = document.getElementById('scrapingProgressText');
            if (pText) pText.textContent = 'JobSpy fetching 80-100 real JDs across LinkedIn & Indeed (may take 1-2 mins)...';
        }
        if (btnScrapeJobSpy) btnScrapeJobSpy.disabled = true;
        showToast('🔥 Starting deep JobSpy multi-portal scrape. Gathering real JDs...', 'info');

        const params = new URLSearchParams({
            keyword: keyword,
            location: location,
            hoursRecent: hoursRecent
        });

        fetch('/api/jobs/scrape-jobspy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        })
        .then(res => {
            if (!res.ok) throw new Error('JobSpy scraping failed');
            return res.json();
        })
        .then(jobs => {
            showToast(`🔥 JobSpy collected & saved ${jobs.length} jobs with full descriptions!`, 'success');
            renderJobs(jobs);
        })
        .catch(err => {
            console.error(err);
            showToast('JobSpy scrape failed. Ensure Python ai-service is running on port 8000.', 'error');
        })
        .finally(() => {
            if (scrapingLoader) scrapingLoader.classList.add('hidden');
            if (btnScrapeJobSpy) btnScrapeJobSpy.disabled = false;
        });
    }

    function triggerScrapeByResume(resumeId) {
        if (scrapingLoader) scrapingLoader.classList.remove('hidden');

        fetch(`/api/jobs/scrape-by-resume/${resumeId}?hoursRecent=24`, {
            method: 'POST'
        })
        .then(res => {
            if (!res.ok) throw new Error('Resume scrape failed');
            return res.json();
        })
        .then(jobs => {
            showToast(`Multi-query engine scraped ${jobs.length} jobs for your profile!`, 'success');
            renderJobs(jobs);
        })
        .catch(err => {
            console.error(err);
            showToast('Failed to auto-scrape for resume.', 'error');
        })
        .finally(() => {
            if (scrapingLoader) scrapingLoader.classList.add('hidden');
        });
    }

    function renderJobs(jobs) {
        if (!jobsGrid) return;
        jobsGrid.innerHTML = '';

        if (!jobs || jobs.length === 0) {
            if (noJobsNotice) noJobsNotice.classList.remove('hidden');
            if (jobsCountBadge) jobsCountBadge.textContent = '0';
            if (totalPlatformBadge) totalPlatformBadge.textContent = '';
            return;
        }

        if (noJobsNotice) noJobsNotice.classList.add('hidden');
        if (jobsCountBadge) jobsCountBadge.textContent = jobs.length;

        // Check if any job DTO reported totalJobsOnPlatform
        const reportedTotal = jobs.find(j => j.totalJobsOnPlatform != null && j.totalJobsOnPlatform > 0);
        if (reportedTotal && totalPlatformBadge) {
            totalPlatformBadge.textContent = `(out of ${reportedTotal.totalJobsOnPlatform}+ 24h jobs on portal)`;
        } else if (totalPlatformBadge) {
            totalPlatformBadge.textContent = '';
        }

        jobs.forEach(job => {
            const card = document.createElement('div');
            card.className = 'job-card glass-card';
            card.setAttribute('data-platform', job.platform || 'ALL');

            const platformName = job.platform || 'LinkedIn';
            const platformClass = 'platform-' + platformName.toLowerCase();
            const dateStr = formatDate(job.postedAt);

            let skillsHtml = '';
            if (job.skills && Array.isArray(job.skills)) {
                skillsHtml = job.skills.map(s => `<span class="tag">${s}</span>`).join(' ');
            }

            card.innerHTML = `
                <div class="job-card-header">
                    <span class="platform-badge ${platformClass}">${platformName}</span>
                    <span class="job-time">${dateStr}</span>
                </div>
                <h4 class="job-title">${job.title || 'Job Opening'}</h4>
                <div class="job-company">${(job.companyName || 'Company') + ' • ' + (job.location || 'Remote')}</div>
                <div class="job-desc-container">
                    <p class="job-desc text-small text-muted">${job.description || ''}</p>
                </div>
                <div class="job-tags">${skillsHtml}</div>
                <div class="job-card-footer">
                    <span class="salary-text">${job.salaryRange || 'Disclosed on apply'}</span>
                    <a href="${job.jobUrl || '#'}" target="_blank" class="btn-primary-sm">Apply Now ↗</a>
                </div>
            `;
            jobsGrid.appendChild(card);
        });
    }

    function filterJobsByPlatform(platform) {
        const cards = document.querySelectorAll('.job-card');
        let count = 0;
        cards.forEach(card => {
            const cardPlatform = card.getAttribute('data-platform');
            if (platform === 'ALL' || cardPlatform.toLowerCase() === platform.toLowerCase()) {
                card.style.display = 'flex';
                count++;
            } else {
                card.style.display = 'none';
            }
        });
        if (jobsCountBadge) jobsCountBadge.textContent = count;
    }

    function formatDate(dateVal) {
        if (!dateVal) return 'Recently';
        let d;
        if (Array.isArray(dateVal)) {
            d = new Date(dateVal[0], dateVal[1] - 1, dateVal[2], dateVal[3] || 0, dateVal[4] || 0);
        } else {
            d = new Date(dateVal);
        }
        if (isNaN(d.getTime())) return 'Recently';
        return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' });
    }
});
