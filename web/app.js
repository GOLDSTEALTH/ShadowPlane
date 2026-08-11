/**
 * app.js — ShadowPlane Web Dashboard (Event-Driven)
 * ==================================================
 * Connects to the /ws WebSocket endpoint on page load.
 * Listens for incoming job payloads, log events, timeline
 * steps, diff events, and completion signals.
 *
 * No manual trigger button — everything is driven by
 * GitHub webhook events received by the backend.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ---------------------------------------------------------------
    // Theme Toggle
    // ---------------------------------------------------------------
    const themeToggleBtn = document.getElementById('theme-toggle');
    const moonIcon = document.getElementById('moon-icon');
    const sunIcon = document.getElementById('sun-icon');
    const root = document.documentElement;

    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {
        const currentTheme = root.getAttribute('data-theme');
        setTheme(currentTheme === 'dark' ? 'light' : 'dark');
    });

    function setTheme(theme) {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        moonIcon.style.display = theme === 'dark' ? 'block' : 'none';
        sunIcon.style.display = theme === 'dark' ? 'none' : 'block';
    }

    // ---------------------------------------------------------------
    // DOM references
    // ---------------------------------------------------------------
    const terminalOutput = document.getElementById('terminal-output');
    const diffViewer = document.getElementById('diff-viewer');
    const wsDot = document.getElementById('ws-status-dot');
    const wsText = document.getElementById('ws-status-text');
    const queueDepth = document.getElementById('queue-depth');

    // Webhook Monitor
    const jobPlaceholder = document.getElementById('job-placeholder');
    const jobDetails = document.getElementById('job-details');
    const jobRepo = document.getElementById('job-repo');
    const jobBranch = document.getElementById('job-branch');
    const jobPr = document.getElementById('job-pr');
    const jobSender = document.getElementById('job-sender');
    const jobStatus = document.getElementById('job-status');

    // Timeline
    const steps = {
        'preflight': document.getElementById('step-preflight'),
        'attempt1': document.getElementById('step-attempt1'),
        'analysis': document.getElementById('step-analysis'),
        'attempt2': document.getElementById('step-attempt2'),
        'success': document.getElementById('step-success'),
    };

    // ---------------------------------------------------------------
    // UI helpers
    // ---------------------------------------------------------------
    function resetUI() {
        terminalOutput.innerHTML = '';
        diffViewer.innerHTML = `
            <div class="diff-placeholder">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="m9 15 2 2 4-4"></path></svg>
                <p>No patches applied yet.<br>Wait for a failure analysis.</p>
            </div>
        `;
        Object.values(steps).forEach(el => {
            el.className = 'timeline-step';
        });
    }

    function appendLog(text, type = 'info') {
        const span = document.createElement('span');
        span.className = `log-${type}`;
        span.textContent = text + '\n';
        terminalOutput.appendChild(span);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    function renderDiff(patchMsg, originalStr, patchedStr) {
        diffViewer.innerHTML = `<h4 style="margin-bottom: 0.5rem; color: var(--accent-primary)">Auto-Repair Applied</h4>`;

        const originalLines = originalStr.split('\n');
        const patchedLines = patchedStr.split('\n');
        const maxLen = Math.max(originalLines.length, patchedLines.length);
        let diffHtml = '';

        for (let i = 0; i < maxLen; i++) {
            const o = originalLines[i] || '';
            const p = patchedLines[i] || '';

            if (o !== p) {
                if (o) diffHtml += `<div class="diff-line removed">- ${escapeHtml(o)}</div>`;
                if (p) diffHtml += `<div class="diff-line added">+ ${escapeHtml(p)}</div>`;
            } else {
                diffHtml += `<div class="diff-line context">  ${escapeHtml(o)}</div>`;
            }
        }

        diffViewer.innerHTML += diffHtml;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function updateTimeline(stepName) {
        Object.values(steps).forEach(el => el.classList.remove('active'));
        if (steps[stepName]) {
            steps[stepName].classList.add('active');
            // Mark all preceding steps as completed
            let markCompleted = true;
            for (const key in steps) {
                if (key === stepName) {
                    markCompleted = false;
                    continue;
                }
                if (markCompleted) {
                    steps[key].classList.add('completed');
                }
            }
        }
    }

    // ---------------------------------------------------------------
    // WebSocket connection with auto-reconnect
    // ---------------------------------------------------------------
    let ws = null;
    let reconnectTimer = null;
    const RECONNECT_DELAY_MS = 3000;

    function connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${protocol}://${window.location.host}/ws`;

        ws = new WebSocket(url);

        ws.onopen = () => {
            wsDot.className = 'dot active';
            wsText.textContent = 'Connected';
            appendLog('[WS] Connected to ShadowPlane Gateway.', 'success');
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }
        };

        ws.onclose = () => {
            wsDot.className = 'dot';
            wsText.textContent = 'Disconnected';
            appendLog('[WS] Disconnected. Reconnecting in 3s...', 'warn');
            scheduleReconnect();
        };

        ws.onerror = () => {
            wsDot.className = 'dot error';
            wsText.textContent = 'Error';
        };

        ws.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
                return;
            }

            switch (data.type) {
                case 'job':
                    // New job incoming from a webhook
                    resetUI();
                    jobPlaceholder.style.display = 'none';
                    jobDetails.style.display = 'flex';
                    jobRepo.textContent = data.repo || '—';
                    jobBranch.textContent = data.branch || '—';
                    jobPr.textContent = `#${data.pr_number}` || '—';
                    jobSender.textContent = data.sender || '—';
                    jobStatus.textContent = 'Processing...';
                    jobStatus.className = 'job-status processing';
                    appendLog(`[WEBHOOK] New job: PR #${data.pr_number} on ${data.repo}@${data.branch} by ${data.sender}`, 'info');
                    break;

                case 'queue':
                    queueDepth.textContent = data.depth || 0;
                    break;

                case 'log':
                    appendLog(data.content, data.level || 'info');
                    break;

                case 'step':
                    updateTimeline(data.step);
                    break;

                case 'diff':
                    renderDiff(data.message, data.original, data.patched);
                    break;

                case 'done':
                    steps['success'].classList.add('active', 'completed');
                    appendLog('\n[OK] ShadowPlane Verification Passed.', 'success');
                    jobStatus.textContent = 'Verified';
                    jobStatus.className = 'job-status success';
                    break;

                case 'error':
                    appendLog('\n[FAIL] Verification Failed.', 'error');
                    jobStatus.textContent = 'Failed';
                    jobStatus.className = 'job-status error';
                    break;

                default:
                    console.log('Unknown event type:', data.type);
            }
        };
    }

    function scheduleReconnect() {
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connect();
            }, RECONNECT_DELAY_MS);
        }
    }

    // Start the WebSocket connection immediately on page load
    connect();
});
