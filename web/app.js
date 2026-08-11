document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle Logic
    const themeToggleBtn = document.getElementById('theme-toggle');
    const moonIcon = document.getElementById('moon-icon');
    const sunIcon = document.getElementById('sun-icon');
    const root = document.documentElement;

    // Check local storage or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);

    themeToggleBtn.addEventListener('click', () => {
        const currentTheme = root.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    });

    function setTheme(theme) {
        root.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (theme === 'dark') {
            moonIcon.style.display = 'block';
            sunIcon.style.display = 'none';
        } else {
            moonIcon.style.display = 'none';
            sunIcon.style.display = 'block';
        }
    }

    // SSE and UI Logic
    const btnTrigger = document.getElementById('btn-trigger');
    const terminalOutput = document.getElementById('terminal-output');
    const diffViewer = document.getElementById('diff-viewer');
    const statusDot = document.getElementById('system-status-dot');
    const statusText = document.getElementById('system-status-text');

    const steps = {
        'preflight': document.getElementById('step-preflight'),
        'attempt1': document.getElementById('step-attempt1'),
        'analysis': document.getElementById('step-analysis'),
        'attempt2': document.getElementById('step-attempt2'),
        'success': document.getElementById('step-success')
    };

    function resetUI() {
        terminalOutput.innerHTML = '';
        diffViewer.innerHTML = `
            <div class="diff-placeholder">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="opacity-50 mb-4"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="m9 15 2 2 4-4"></path></svg>
                <p>No patches applied yet.<br>Wait for a failure analysis.</p>
            </div>
        `;
        Object.values(steps).forEach(el => {
            el.className = 'timeline-step';
        });
        statusDot.className = 'dot active';
        statusText.textContent = 'Verification Running...';
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
        
        // Very basic mock diff rendering for the demo
        const originalLines = originalStr.split('\n');
        const patchedLines = patchedStr.split('\n');

        let diffHtml = '';
        const maxLen = Math.max(originalLines.length, patchedLines.length);
        
        for (let i = 0; i < maxLen; i++) {
            const o = originalLines[i] || '';
            const p = patchedLines[i] || '';
            
            if (o !== p) {
                if (o) diffHtml += `<div class="diff-line removed">- ${o}</div>`;
                if (p) diffHtml += `<div class="diff-line added">+ ${p}</div>`;
            } else {
                diffHtml += `<div class="diff-line context">  ${o}</div>`;
            }
        }
        
        diffViewer.innerHTML += diffHtml;
    }

    btnTrigger.addEventListener('click', async () => {
        btnTrigger.disabled = true;
        resetUI();
        
        try {
            // Trigger the backend to start the loop
            const resp = await fetch('/api/start', { method: 'POST' });
            if (!resp.ok) throw new Error('Failed to start run');
            
            // Connect to SSE stream
            const eventSource = new EventSource('/api/stream');
            
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'log') {
                    appendLog(data.content, data.level || 'info');
                } 
                else if (data.type === 'step') {
                    // Update timeline
                    Object.values(steps).forEach(el => el.classList.remove('active'));
                    if (steps[data.step]) {
                        steps[data.step].classList.add('active');
                        // Mark previous steps as completed
                        let markCompleted = true;
                        for (const key in steps) {
                            if (key === data.step) {
                                markCompleted = false;
                                continue;
                            }
                            if (markCompleted) {
                                steps[key].classList.add('completed');
                            }
                        }
                    }
                }
                else if (data.type === 'diff') {
                    renderDiff(data.message, data.original, data.patched);
                }
                else if (data.type === 'done') {
                    eventSource.close();
                    btnTrigger.disabled = false;
                    statusDot.className = 'dot';
                    statusText.textContent = 'System Idle';
                    
                    // Mark success
                    steps['success'].classList.add('active', 'completed');
                    appendLog('\n✅ ShadowPlane Verification Passed.', 'success');
                }
                else if (data.type === 'error') {
                    eventSource.close();
                    btnTrigger.disabled = false;
                    statusDot.className = 'dot error';
                    statusText.textContent = 'System Error';
                    appendLog('\n❌ Verification Failed.', 'error');
                }
            };
            
            eventSource.onerror = (err) => {
                console.error("SSE Error:", err);
                eventSource.close();
                btnTrigger.disabled = false;
                statusDot.className = 'dot error';
                statusText.textContent = 'Connection Error';
            };
            
        } catch (error) {
            appendLog(`Error: ${error.message}`, 'error');
            btnTrigger.disabled = false;
        }
    });
});
