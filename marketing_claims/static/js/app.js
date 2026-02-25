/* ============================================================
   Marketing Claims Product Truth Evaluation Suite
   Main Application JavaScript
   ============================================================ */

const App = {
    products: [],
    results: null,
    statistics: null,

    init() {
        this.setupUpload();
        this.setupTabs();
        this.setupConfigPanel();
        this.setupEventListeners();
    },

    /* ----------------------------------------------------------
       Upload handling (PapaParse)
       ---------------------------------------------------------- */
    setupUpload() {
        const zone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('csv-file-input');

        zone.addEventListener('click', () => fileInput.click());
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) this.parseCSV(file);
        });
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.parseCSV(file);
        });
    },

    parseCSV(file) {
        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                if (results.errors.length > 0) {
                    this.showToast(`CSV parse errors: ${results.errors[0].message}`, 'error');
                    return;
                }
                this.products = results.data.map(row => ({
                    upc: (row.upc || row.UPC || '').trim(),
                    product_name: (row.product_name || row['Product Name'] || row.name || '').trim(),
                    marketing_claims: (row.marketing_claims || row['Marketing Claims'] || row.claims || '').trim(),
                })).filter(p => p.product_name || p.upc);

                this.renderProductsTable();
                this.showToast(`Loaded ${this.products.length} products`, 'success');
                document.getElementById('products-section').style.display = 'block';
            },
            error: (err) => {
                this.showToast(`CSV error: ${err.message}`, 'error');
            }
        });
    },

    renderProductsTable() {
        const tbody = document.getElementById('products-tbody');
        tbody.innerHTML = '';
        this.products.forEach((p, i) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${i + 1}</td>
                <td>${this.escapeHtml(p.upc)}</td>
                <td>${this.escapeHtml(p.product_name)}</td>
                <td title="${this.escapeHtml(p.marketing_claims)}">${this.escapeHtml(p.marketing_claims.substring(0, 120))}${p.marketing_claims.length > 120 ? '...' : ''}</td>
                <td><button class="btn btn-sm btn-secondary" onclick="App.removeProduct(${i})">Remove</button></td>
            `;
            tbody.appendChild(tr);
        });
        document.getElementById('product-count').textContent = this.products.length;
    },

    removeProduct(index) {
        this.products.splice(index, 1);
        this.renderProductsTable();
    },

    /* ----------------------------------------------------------
       Sample data loader
       ---------------------------------------------------------- */
    async loadSampleData() {
        try {
            const resp = await fetch('/api/sample-data');
            const data = await resp.json();
            if (data.products) {
                this.products = data.products;
                this.renderProductsTable();
                document.getElementById('products-section').style.display = 'block';
                this.showToast(`Loaded ${this.products.length} sample products`, 'success');
            }
        } catch (err) {
            this.showToast(`Failed to load sample data: ${err.message}`, 'error');
        }
    },

    /* ----------------------------------------------------------
       Evaluation
       ---------------------------------------------------------- */
    async runEvaluation() {
        if (this.products.length === 0) {
            this.showToast('No products loaded. Upload a CSV or load sample data.', 'error');
            return;
        }

        const llmProvider = document.getElementById('llm-provider').value;
        const llmApiKey = document.getElementById('llm-api-key').value.trim();
        const enrichmentToken = document.getElementById('enrichment-token').value.trim();
        const enrichmentUrl = document.getElementById('enrichment-url').value.trim();
        const customPrompt = document.getElementById('evaluation-prompt').value.trim();

        if (!llmApiKey) {
            this.showToast('Please enter your LLM API key', 'error');
            return;
        }

        this.showProgress(true);
        this.updateProgress('Evaluating products...', `0 / ${this.products.length}`);

        try {
            const resp = await fetch('/api/evaluate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    products: this.products,
                    llm_provider: llmProvider,
                    llm_api_key: llmApiKey,
                    enrichment_auth_token: enrichmentToken,
                    enrichment_base_url: enrichmentUrl || undefined,
                    evaluation_prompt: customPrompt || undefined,
                }),
            });

            const data = await resp.json();
            if (data.error) {
                this.showToast(data.error, 'error');
                this.showProgress(false);
                return;
            }

            this.results = data.results;
            this.statistics = data.statistics;
            this.renderResults();
            this.renderStatistics();
            this.renderCharts();
            document.getElementById('results-section').style.display = 'block';
            document.getElementById('charts-section').style.display = 'block';
            this.showToast('Evaluation complete!', 'success');
        } catch (err) {
            this.showToast(`Evaluation failed: ${err.message}`, 'error');
        } finally {
            this.showProgress(false);
        }
    },

    /* ----------------------------------------------------------
       Render results table
       ---------------------------------------------------------- */
    renderResults() {
        const tbody = document.getElementById('results-tbody');
        tbody.innerHTML = '';

        this.results.forEach((r, i) => {
            const analysis = r.analysis || {};
            const verdict = analysis.overall_verdict || (r.llm_error ? 'ERROR' : 'N/A');
            const report = analysis.report_card || {};
            const grade = report.overall_grade || '-';
            const improvement = analysis.marketing_improvement_suggestions || {};
            const conv = improvement.conversion_impact_assessment || {};
            const boost = conv.estimated_conversion_boost_percent || 0;

            const badgeClass = verdict === 'VALID' ? 'badge-valid'
                             : verdict === 'INVALID' ? 'badge-invalid'
                             : verdict === 'PARTIALLY_VALID' ? 'badge-partial'
                             : 'badge-error';

            const gradeClass = `grade-${grade}`;

            const tr = document.createElement('tr');
            tr.className = 'expandable';
            tr.onclick = () => this.toggleDetail(i);
            tr.innerHTML = `
                <td><span class="expand-icon" id="expand-icon-${i}">&#9654;</span> ${i + 1}</td>
                <td>${this.escapeHtml(r.product_name)}</td>
                <td><span class="badge ${badgeClass}">${verdict}</span></td>
                <td><span class="${gradeClass}" style="font-size:18px;font-weight:800">${grade}</span></td>
                <td>+${boost}%</td>
                <td>${r.llm_error ? '<span class="badge badge-error">Error</span>' : (analysis.claims_analysis || []).length + ' claims'}</td>
            `;
            tbody.appendChild(tr);

            // Detail row
            const detailTr = document.createElement('tr');
            detailTr.id = `detail-${i}`;
            detailTr.style.display = 'none';
            detailTr.innerHTML = `<td colspan="6">${this.renderDetailPanel(r)}</td>`;
            tbody.appendChild(detailTr);
        });
    },

    toggleDetail(index) {
        const row = document.getElementById(`detail-${index}`);
        const icon = document.getElementById(`expand-icon-${index}`);
        if (row.style.display === 'none') {
            row.style.display = 'table-row';
            icon.classList.add('open');
        } else {
            row.style.display = 'none';
            icon.classList.remove('open');
        }
    },

    renderDetailPanel(result) {
        const analysis = result.analysis;
        if (!analysis) {
            return `<div class="result-detail">
                <p><strong>Error:</strong> ${this.escapeHtml(result.llm_error || 'No analysis available')}</p>
                ${result.enrichment_error ? `<p><strong>Enrichment:</strong> ${this.escapeHtml(result.enrichment_error)}</p>` : ''}
            </div>`;
        }

        const claims = analysis.claims_analysis || [];
        const report = analysis.report_card || {};
        const improvement = analysis.marketing_improvement_suggestions || {};
        const truth = analysis.product_truth_summary || {};

        let html = '<div class="result-detail">';

        // Report card
        html += '<div class="grid-4" style="margin-bottom:16px">';
        ['ingredient_accuracy', 'regulatory_compliance', 'claim_substantiation', 'consumer_transparency'].forEach(key => {
            const g = report[key] || '-';
            const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            html += `<div class="grade-card card"><div class="grade-letter grade-${g}">${g}</div><div class="grade-label">${label}</div></div>`;
        });
        html += '</div>';

        // Claims list
        html += '<h4 style="margin-bottom:8px;font-size:14px;font-weight:600">Claims Analysis</h4>';
        claims.forEach(claim => {
            const vclass = (claim.verdict || '').toLowerCase().replace(/_/g, '-');
            const sclass = `severity-${(claim.severity || '').toLowerCase()}`;
            html += `
                <div class="claim-item ${vclass}">
                    <div class="claim-text">
                        <span class="badge ${claim.verdict === 'VALID' ? 'badge-valid' : claim.verdict === 'INVALID' ? 'badge-invalid' : 'badge-partial'}">${claim.verdict}</span>
                        <span class="${sclass}" style="margin-left:8px;font-size:11px">${claim.severity}</span>
                        &mdash; ${this.escapeHtml(claim.original_claim)}
                    </div>
                    <div class="claim-reasoning">${this.escapeHtml(claim.reasoning || '')}</div>
                    ${claim.suggested_improvement ? `<div class="claim-suggestion"><strong>Suggested:</strong> ${this.escapeHtml(claim.suggested_improvement)}</div>` : ''}
                </div>`;
        });

        // Improved claims
        if (improvement.improved_claims_text) {
            html += `<div style="margin-top:16px;padding:12px;background:#EFF6FF;border-radius:8px">
                <h4 style="font-size:14px;font-weight:600;margin-bottom:8px">Improved Marketing Claims</h4>
                <p style="font-size:13px">${this.escapeHtml(improvement.improved_claims_text)}</p>
            </div>`;
        }

        // Conversion boost
        const conv = improvement.conversion_impact_assessment || {};
        if (conv.estimated_conversion_boost_percent) {
            const pct = Math.min(conv.estimated_conversion_boost_percent, 100);
            html += `<div style="margin-top:12px">
                <h4 style="font-size:14px;font-weight:600;margin-bottom:8px">Estimated Conversion Boost</h4>
                <div class="boost-meter">
                    <div class="boost-bar"><div class="boost-bar-fill" style="width:${pct}%"></div></div>
                    <div class="boost-value">+${conv.estimated_conversion_boost_percent}%</div>
                </div>
                <p style="font-size:13px;color:#6B7280;margin-top:6px">${this.escapeHtml(conv.reasoning || '')}</p>
            </div>`;
        }

        // Product truth summary
        if (truth.key_ingredients && truth.key_ingredients.length) {
            html += `<div style="margin-top:12px">
                <h4 style="font-size:14px;font-weight:600;margin-bottom:4px">Key Ingredients</h4>
                <p style="font-size:13px">${truth.key_ingredients.map(i => this.escapeHtml(i)).join(', ')}</p>
            </div>`;
        }

        html += '</div>';
        return html;
    },

    /* ----------------------------------------------------------
       Statistics summary
       ---------------------------------------------------------- */
    renderStatistics() {
        if (!this.statistics) return;
        const s = this.statistics;

        document.getElementById('stat-total').textContent = s.total_products;
        document.getElementById('stat-valid').textContent = s.verdicts.VALID || 0;
        document.getElementById('stat-invalid').textContent = s.verdicts.INVALID || 0;
        document.getElementById('stat-partial').textContent = s.verdicts.PARTIALLY_VALID || 0;
        document.getElementById('stat-boost').textContent = `+${s.average_conversion_boost}%`;
        document.getElementById('stat-claims').textContent = s.total_claims_evaluated;
    },

    /* ----------------------------------------------------------
       Charts & Visualizations
       ---------------------------------------------------------- */
    renderCharts() {
        if (!this.statistics) return;
        this.renderPieChart();
        this.renderNetworkView();
        this.renderWordClouds();
        this.renderBiasChart();
        this.renderReportCardChart();
    },

    renderPieChart() {
        const ctx = document.getElementById('pie-chart').getContext('2d');
        const cats = this.statistics.claim_categories;
        const labels = Object.keys(cats);
        const values = Object.values(cats);

        const colors = [
            '#2563EB', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
            '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#84CC16',
        ];

        if (window._pieChart) window._pieChart.destroy();
        window._pieChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#fff',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { font: { size: 12, family: "'Inter', sans-serif" } } },
                    title: { display: true, text: 'Claims by Category', font: { size: 14, weight: 600 } },
                }
            }
        });
    },

    renderNetworkView() {
        const container = document.getElementById('network-chart');
        container.innerHTML = '';

        const links = this.statistics.ingredient_claim_links;
        if (!links || links.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="title">No ingredient-claim links available</div><div class="desc">Enrichment data needed for network visualization</div></div>';
            return;
        }

        // Build nodes and links for a simple force-directed graph using SVG
        const nodes = new Map();
        const edges = [];

        links.forEach(link => {
            if (!nodes.has(link.source)) nodes.set(link.source, { id: link.source, type: 'ingredient' });
            if (!nodes.has(link.target)) nodes.set(link.target, { id: link.target, type: 'claim' });
            edges.push({ source: link.source, target: link.target });
        });

        const nodeArr = Array.from(nodes.values());
        const width = container.clientWidth || 600;
        const height = 400;

        // Simple layout: ingredients on left, claims on right
        const ingredients = nodeArr.filter(n => n.type === 'ingredient');
        const claims = nodeArr.filter(n => n.type === 'claim');

        ingredients.forEach((n, i) => {
            n.x = 120;
            n.y = 40 + (i * (height - 80) / Math.max(ingredients.length - 1, 1));
        });
        claims.forEach((n, i) => {
            n.x = width - 120;
            n.y = 40 + (i * (height - 80) / Math.max(claims.length - 1, 1));
        });

        let svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`;

        // Draw edges
        edges.forEach(e => {
            const s = nodes.get(e.source);
            const t = nodes.get(e.target);
            svg += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#D1D5DB" stroke-width="1.5"/>`;
        });

        // Draw nodes
        nodeArr.forEach(n => {
            const color = n.type === 'ingredient' ? '#10B981' : '#2563EB';
            const r = n.type === 'ingredient' ? 6 : 8;
            svg += `<circle cx="${n.x}" cy="${n.y}" r="${r}" fill="${color}" stroke="#fff" stroke-width="2"/>`;

            const anchor = n.type === 'ingredient' ? 'end' : 'start';
            const dx = n.type === 'ingredient' ? -12 : 12;
            const label = n.id.length > 20 ? n.id.substring(0, 18) + '...' : n.id;
            svg += `<text x="${n.x + dx}" y="${n.y + 4}" text-anchor="${anchor}" font-size="11" font-family="Inter, sans-serif" fill="#374151">${this.escapeHtml(label)}</text>`;
        });

        // Legend
        svg += `<circle cx="20" cy="${height - 20}" r="5" fill="#10B981"/><text x="30" y="${height - 16}" font-size="11" fill="#6B7280">Ingredient</text>`;
        svg += `<circle cx="120" cy="${height - 20}" r="5" fill="#2563EB"/><text x="130" y="${height - 16}" font-size="11" fill="#6B7280">Claim Type</text>`;

        svg += '</svg>';
        container.innerHTML = svg;
    },

    renderWordClouds() {
        this.renderWordCloud('wordcloud-valid', this.statistics.valid_claim_words, '#10B981');
        this.renderWordCloud('wordcloud-invalid', this.statistics.invalid_claim_words, '#EF4444');
    },

    renderWordCloud(containerId, words, baseColor) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '';

        const entries = Object.entries(words || {}).slice(0, 30);
        if (entries.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="desc">No data yet</div></div>';
            return;
        }

        const maxCount = Math.max(...entries.map(e => e[1]));
        const minSize = 12;
        const maxSize = 36;

        let html = '<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:center;padding:16px">';
        entries.forEach(([word, count]) => {
            const size = minSize + ((count / maxCount) * (maxSize - minSize));
            const opacity = 0.4 + (count / maxCount) * 0.6;
            html += `<span style="font-size:${size}px;font-weight:${count > maxCount / 2 ? 700 : 400};color:${baseColor};opacity:${opacity};padding:2px 4px">${this.escapeHtml(word)}</span>`;
        });
        html += '</div>';
        container.innerHTML = html;
    },

    renderBiasChart() {
        const ctx = document.getElementById('bias-chart');
        if (!ctx) return;

        if (!this.results || this.results.length === 0) return;

        const labels = [];
        const validCounts = [];
        const invalidCounts = [];

        this.results.forEach(r => {
            const analysis = r.analysis;
            if (!analysis) return;
            const name = r.product_name.length > 25 ? r.product_name.substring(0, 23) + '...' : r.product_name;
            labels.push(name);
            const claims = analysis.claims_analysis || [];
            validCounts.push(claims.filter(c => c.verdict === 'VALID').length);
            invalidCounts.push(claims.filter(c => c.verdict !== 'VALID').length);
        });

        if (window._biasChart) window._biasChart.destroy();
        window._biasChart = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Valid Claims', data: validCounts, backgroundColor: '#10B981' },
                    { label: 'Invalid/Other Claims', data: invalidCounts, backgroundColor: '#EF4444' },
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Claim Validity by Product', font: { size: 14, weight: 600 } },
                    legend: { labels: { font: { size: 12 } } },
                },
                scales: {
                    x: { stacked: true, ticks: { font: { size: 10 }, maxRotation: 45 } },
                    y: { stacked: true, beginAtZero: true, title: { display: true, text: 'Number of Claims' } },
                }
            }
        });
    },

    renderReportCardChart() {
        const ctx = document.getElementById('reportcard-chart');
        if (!ctx) return;

        if (!this.results || this.results.length === 0) return;

        const gradeToNum = { 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0 };
        const categories = ['ingredient_accuracy', 'regulatory_compliance', 'claim_substantiation', 'consumer_transparency'];
        const categoryLabels = categories.map(c => c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));

        const avgScores = categories.map(cat => {
            let sum = 0, count = 0;
            this.results.forEach(r => {
                const report = (r.analysis || {}).report_card || {};
                const grade = report[cat];
                if (grade && gradeToNum[grade] !== undefined) {
                    sum += gradeToNum[grade];
                    count++;
                }
            });
            return count ? sum / count : 0;
        });

        if (window._reportChart) window._reportChart.destroy();
        window._reportChart = new Chart(ctx.getContext('2d'), {
            type: 'radar',
            data: {
                labels: categoryLabels,
                datasets: [{
                    label: 'Average Score',
                    data: avgScores,
                    backgroundColor: 'rgba(37, 99, 235, 0.15)',
                    borderColor: '#2563EB',
                    borderWidth: 2,
                    pointBackgroundColor: '#2563EB',
                    pointRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Product Truth Report Card', font: { size: 14, weight: 600 } },
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 4,
                        ticks: {
                            stepSize: 1,
                            callback: (v) => ['F', 'D', 'C', 'B', 'A'][v] || '',
                        },
                        pointLabels: { font: { size: 11 } },
                    }
                }
            }
        });
    },

    /* ----------------------------------------------------------
       Download improved claims
       ---------------------------------------------------------- */
    async downloadImproved() {
        if (!this.results) {
            this.showToast('No results to download', 'error');
            return;
        }

        try {
            const resp = await fetch('/api/download-improved', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ results: this.results }),
            });

            if (!resp.ok) {
                this.showToast('Download failed', 'error');
                return;
            }

            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'improved_marketing_claims.csv';
            a.click();
            URL.revokeObjectURL(url);
            this.showToast('Download started', 'success');
        } catch (err) {
            this.showToast(`Download error: ${err.message}`, 'error');
        }
    },

    /* ----------------------------------------------------------
       UI helpers
       ---------------------------------------------------------- */
    setupTabs() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const group = tab.closest('.tabs').dataset.group;
                document.querySelectorAll(`.tabs[data-group="${group}"] .tab`).forEach(t => t.classList.remove('active'));
                document.querySelectorAll(`.tab-content[data-group="${group}"]`).forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                const target = document.getElementById(tab.dataset.target);
                if (target) target.classList.add('active');
            });
        });
    },

    setupConfigPanel() {
        document.querySelectorAll('.panel-header').forEach(header => {
            header.addEventListener('click', () => {
                const body = header.nextElementSibling;
                body.classList.toggle('collapsed');
                const chevron = header.querySelector('.chevron');
                if (chevron) chevron.textContent = body.classList.contains('collapsed') ? '&#9654;' : '&#9660;';
            });
        });
    },

    setupEventListeners() {
        // Prompt character count
        const promptEl = document.getElementById('evaluation-prompt');
        if (promptEl) {
            const counter = document.getElementById('prompt-char-count');
            promptEl.addEventListener('input', () => {
                if (counter) counter.textContent = `${promptEl.value.length} chars`;
            });
        }
    },

    showProgress(show) {
        const overlay = document.getElementById('progress-overlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    },

    updateProgress(text, sub) {
        document.getElementById('progress-text').textContent = text;
        document.getElementById('progress-sub').textContent = sub;
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity .3s';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    resetPrompt() {
        fetch('/api/prompt')
            .then(r => r.json())
            .then(data => {
                document.getElementById('evaluation-prompt').value = data.prompt;
                this.showToast('Prompt reset to default', 'info');
            });
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());
