(() => {
  const keywordSelect = document.querySelector('#keyword');
  const targetUrl = document.querySelector('#target-url');
  const checkButton = document.querySelector('#check-button');
  const formError = document.querySelector('#form-error');
  const progressList = document.querySelector('#progress-list');
  const indicator = document.querySelector('#job-indicator');
  const captchaNotice = document.querySelector('#captcha-notice');
  const resultCard = document.querySelector('#result-card');
  const resultStatus = document.querySelector('#result-status');
  const checks = [...document.querySelectorAll('[data-check]')];
  const vpnBadge = document.querySelector('#vpn-badge');
  const vpnBadgeText = document.querySelector('#vpn-badge-text');
  const vpnRefreshBtn = document.querySelector('#vpn-badge-refresh');
  const vpnCheck = document.querySelector('[data-check="vpn"]');
  const locationCheck = document.querySelector('[data-check="location"]');
  let pollTimer = null;

  const setError = (message = '') => {
    formError.textContent = message;
    formError.hidden = !message;
  };

  const selectedTarget = () => keywordSelect.selectedOptions[0]?.dataset.targetUrl || '';

  const updateButton = () => {
    const ready = Boolean(keywordSelect.value) && checks.every((item) => item.checked);
    checkButton.disabled = !ready;
  };

  const checkVpn = async () => {
    if (!vpnBadgeText) return;
    vpnBadgeText.textContent = '🔍 Verifying USA VPN connection...';
    vpnBadge.style.background = '#f8fafc';
    vpnBadge.style.borderColor = '#cbd5e1';
    vpnBadge.style.color = '#334155';
    if (vpnRefreshBtn) vpnRefreshBtn.disabled = true;

    try {
      const res = await fetch('/api/vpn-status');
      const data = await res.json();
      if (data.is_usa) {
        vpnBadge.style.background = '#f0fdf4';
        vpnBadge.style.borderColor = '#86efac';
        vpnBadge.style.color = '#166534';
        const loc = [data.city, 'United States'].filter(Boolean).join(', ');
        vpnBadgeText.textContent = `🟢 USA Verified: ${loc} (${data.ip})`;
        if (vpnCheck) vpnCheck.checked = true;
        if (locationCheck) locationCheck.checked = true;
        setError();
      } else {
        vpnBadge.style.background = '#fef2f2';
        vpnBadge.style.borderColor = '#fca5a5';
        vpnBadge.style.color = '#991b1b';
        const detected = [data.city, data.country].filter(Boolean).join(', ') || 'Outside USA';
        vpnBadgeText.textContent = `🔴 VPN Disconnected: Detected in ${detected} (${data.ip || 'No IP'}). Connect ExpressVPN USA!`;
        if (vpnCheck) vpnCheck.checked = false;
        if (locationCheck) locationCheck.checked = false;
        setError(`USA VPN Required! Detected location: ${detected}. Please connect ExpressVPN USA.`);
      }
    } catch (_) {
      vpnBadgeText.textContent = '⚠️ Could not verify IP. Please check internet connection.';
    } finally {
      if (vpnRefreshBtn) vpnRefreshBtn.disabled = false;
      updateButton();
    }
  };

  const showProgress = (messages) => {
    progressList.replaceChildren(...messages.map((message) => {
      const item = document.createElement('li');
      item.textContent = message;
      return item;
    }));
    progressList.scrollTop = progressList.scrollHeight;
  };

  const showResult = (result) => {
    resultCard.hidden = false;
    resultStatus.textContent = result.status || 'Unknown';
    resultStatus.className = 'result-badge';
    if (result.status !== 'FOUND') resultStatus.classList.add(result.status?.includes('Not') ? 'not-found' : 'error');
    document.querySelector('#result-keyword').textContent = result.keyword || '-';
    document.querySelector('#result-target').textContent = result.target_url || '-';
    document.querySelector('#result-position').textContent = result.position || '-';
    document.querySelector('#result-page').textContent = result.google_page || '-';
    document.querySelector('#result-found-url').textContent = result.url_found || '-';
    document.querySelector('#result-result-title').textContent = result.title || '-';
    document.querySelector('#result-datetime').textContent = [result.search_date, result.search_time].filter(Boolean).join(' ') || '-';
  };

  const loadRecentResults = async () => {
    const response = await fetch('/api/results');
    const payload = await response.json();
    const body = document.querySelector('#recent-results');
    body.replaceChildren();
    if (!payload.results.length) {
      const row = document.createElement('tr');
      row.innerHTML = '<td colspan="4" class="empty-cell">No results yet.</td>';
      body.append(row);
      return;
    }
    payload.results.forEach((item) => {
      const row = document.createElement('tr');
      [item.keyword, item.status, item.position || '-', item.search_date || '-'].forEach((value) => {
        const cell = document.createElement('td');
        cell.textContent = value;
        row.append(cell);
      });
      body.append(row);
    });
  };

  const pollStatus = async () => {
    try {
      const response = await fetch('/api/status');
      const status = await response.json();
      showProgress(status.progress || []);
      const captchaMessage = (status.progress || []).some((message) => message.toLowerCase().includes('captcha'));
      captchaNotice.hidden = !captchaMessage;
      indicator.textContent = status.running ? 'Running' : 'Ready';
      indicator.className = `status-dot${status.running ? ' busy' : ''}`;
      if (status.error) setError(status.error);
      if (status.result) showResult(status.result);
      if (!status.running) {
        clearInterval(pollTimer);
        pollTimer = null;
        checkButton.disabled = false;
        updateButton();
        await loadRecentResults();
      }
    } catch (_) {
      setError('The local app could not read the current job status.');
    }
  };

  keywordSelect.addEventListener('change', () => {
    targetUrl.value = selectedTarget();
    setError();
    updateButton();
  });
  checks.forEach((item) => item.addEventListener('change', updateButton));

  checkButton.addEventListener('click', async () => {
    setError();
    resultCard.hidden = true;
    checkButton.disabled = true;
    const checklist = Object.fromEntries(checks.map((item) => [item.dataset.check, item.checked]));
    try {
      const response = await fetch('/api/check', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({keyword: keywordSelect.value, checklist}),
      });
      const payload = await response.json();
      if (!response.ok) {
        setError(payload.error || 'The rank check could not start.');
        updateButton();
        return;
      }
      showProgress(['Starting Chrome']);
      indicator.textContent = 'Running';
      indicator.className = 'status-dot busy';
      pollTimer = setInterval(pollStatus, 1000);
      await pollStatus();
    } catch (_) {
      setError('The local app could not start the rank check.');
      updateButton();
    }
  });

  vpnRefreshBtn?.addEventListener('click', checkVpn);
  targetUrl.value = selectedTarget();
  updateButton();
  loadRecentResults();
  checkVpn();
})();
