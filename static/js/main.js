// static/js/main.js

const getSelectedTrimester = () => document.querySelector('input[name="trimester"]:checked').value;

function createChart(id, label, color) {
    const ctx = document.getElementById(id);
    if (!ctx) return null;
    return new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderColor: color,
                backgroundColor: 'transparent',
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { labels: { color: '#117964' } } },
            scales: {
                x: { ticks: { color: '#117964' } },
                y: { ticks: { color: '#117964' }, beginAtZero: true }
            }
        }
    });
}

let cpuChart, ramChart, memoryChart, fitnessTrendChart;

document.addEventListener('DOMContentLoaded', function () {
    cpuChart = createChart('cpuChart', 'CPU Load', '#117964');
    ramChart = createChart('ramChart', 'RAM Load', '#19be94');
    memoryChart = createChart('memoryChart', 'Memory Load', '#ffc107');
    fitnessTrendChart = createChart('fitnessTrendChart', 'Fitness Score Trend', '#0b96ff');

    setInterval(function () {
        const time = new Date().toLocaleTimeString();
        const pushData = (chart, value) => {
            if (!chart) return;
            if (chart.data.labels.length > 10) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            chart.data.labels.push(time);
            chart.data.datasets[0].data.push(value);
            chart.update();
        };
        pushData(cpuChart, Math.random() * 100);
        pushData(ramChart, Math.random() * 50);
        pushData(memoryChart, 80 + Math.random() * 20);
    }, 2000);

    // Navbar smooth scroll and mobile close
    const link = document.getElementById("generateScheduleLink");
    if (link) {
        link.addEventListener("click", function (e) {
            if (window.location.pathname === "/" || window.location.pathname.endsWith("/index.html")) {
                e.preventDefault();
                const target = document.getElementById("main-content");
                if (target) target.scrollIntoView({ behavior: 'smooth' });
                const menuToggle = document.getElementById('aitu-menu-toggle');
                if (menuToggle) menuToggle.checked = false;
            }
        });
    }
    document.querySelectorAll('.aitu-menu-items a').forEach(link => {
        link.addEventListener('click', () => {
            const toggle = document.getElementById('aitu-menu-toggle');
            if (toggle) toggle.checked = false;
        });
    });

    // File drop and preview
    const dropArea = document.getElementById("fileDropArea");
    const fileInput = document.getElementById("datasetUpload");
    const fileNameDisplay = document.getElementById("fileNameDisplay");
    if (dropArea && fileInput) {
        dropArea.addEventListener('click', () => fileInput.click());
        dropArea.addEventListener('dragover', e => { e.preventDefault(); dropArea.classList.add('dragover'); });
        dropArea.addEventListener('dragleave', e => { dropArea.classList.remove('dragover'); });
        dropArea.addEventListener('drop', e => {
            e.preventDefault();
            dropArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                showFileName(fileInput.files[0]);
            }
        });
        fileInput.addEventListener('change', function () {
            if (fileInput.files.length > 0) showFileName(fileInput.files[0]);
            else if (fileNameDisplay) fileNameDisplay.textContent = "";
        });
        function showFileName(file) {
            if (fileNameDisplay) fileNameDisplay.textContent = "Selected: " + file.name;
        }
    }

    // Download buttons setup
    document.getElementById('downloadExcel').onclick = function (e) {
        e.preventDefault();
        triggerDownload(`/download_excel?trimester=${getSelectedTrimester()}`);
    };
    document.getElementById('downloadJson').onclick = function (e) {
        e.preventDefault();
        triggerDownload(`/download_json?trimester=${getSelectedTrimester()}`);
    };


    // Generate button logic
    const generateBtn = document.getElementById("generateBtn");
    if (generateBtn) {
        generateBtn.addEventListener("click", async function () {
            const trimester = getSelectedTrimester();
            const fileInput = document.getElementById("datasetUpload");
            if (!fileInput.files.length) {
                alert("Please upload your GA Input Excel file first!");
                return;
            }
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('trimester', trimester);
            this.disabled = true;
            this.innerHTML = 'Processing... <span class="spinner-border spinner-border-sm"></span>';
            try {
                const response = await fetch('/generate_schedule', { method: 'POST', body: formData });
                if (!response.ok) throw new Error("Failed to generate schedule!");
                const metrics = await response.json();
                showMetrics(metrics);
                showFitnessProgress(metrics);
                document.getElementById('downloadLinks').style.display = "flex";
                triggerDownload(`/download_excel?trimester=${trimester}`);
                triggerDownload(`/download_json?trimester=${trimester}`);
                this.innerHTML = "Generate Schedule";
            } catch (e) {
                alert("Error: " + e.message);
                this.innerHTML = "Generate Schedule";
            }
            this.disabled = false;
        });
    }
});

function showMetrics(metrics) {
    document.getElementById('fitnessScore').textContent = metrics.fitnessScore + '%';
    document.getElementById('conflictsCount').textContent = metrics.conflicts;
    document.getElementById('hardConstraints').textContent = metrics.hard + '%';
    document.getElementById('softConstraints').textContent = metrics.soft + '%';
    document.getElementById('genTime').textContent = metrics.time + 's';
}

function showFitnessProgress(metrics) {
    if (metrics.fitness_progress) {
        const progressValues = metrics.fitness_progress.map(x => Math.round(10000 / (1 + x), 2));
        fitnessTrendChart.data.labels = metrics.fitness_progress.map((_, i) => "Gen " + (i + 1));
        fitnessTrendChart.data.datasets[0].data = progressValues;
        fitnessTrendChart.update();
    }
}

function triggerDownload(url) {
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function getFitnessInterpretation(score) {
    if (score >= 98) {
        return '🟢 <strong>Excellent schedule!</strong> (Very high fitness, near-perfect constraint satisfaction)';
    } else if (score >= 90) {
        return '🟢 <strong>Good schedule.</strong> (Minor issues, but most constraints are satisfied)';
    } else if (score >= 75) {
        return '🟡 <strong>Average schedule.</strong> (Consider revising input data; some constraints not met)';
    } else {
        return '🔴 <strong>Poor schedule!</strong> (Many conflicts or constraints violated, please check input)';
    }
}

function updateFitnessInterpretation() {
    const fitnessScore = parseFloat(document.getElementById('fitnessScore').textContent);
    const interpretation = getFitnessInterpretation(fitnessScore);
    document.getElementById('fitnessInterpretation').innerHTML = interpretation;
}

document.getElementById('fitnessScore').addEventListener('DOMSubtreeModified', updateFitnessInterpretation);

