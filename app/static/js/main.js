// --- TRIMESTER SELECTION ---
const getSelectedTrimester = () => {
    return document.querySelector('input[name="trimester"]:checked').value;
};

// --- CHART INITIALIZERS ---
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
            plugins: {
                legend: { labels: { color: '#117964' } }
            },
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

    // Simulate only system metrics for demo
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
        // DO NOT push demo fitness data!
    }, 2000);
});

// --- FITNESS CHART UPDATE WITH REAL DATA ---
function updateFitnessTrend(realFitnessScore) {
    const time = new Date().toLocaleTimeString();
    if (!fitnessTrendChart) return;
    if (fitnessTrendChart.data.labels.length > 10) {
        fitnessTrendChart.data.labels.shift();
        fitnessTrendChart.data.datasets[0].data.shift();
    }
    fitnessTrendChart.data.labels.push(time);
    fitnessTrendChart.data.datasets[0].data.push(realFitnessScore);
    fitnessTrendChart.update();

    document.getElementById('fitnessInterpretation').innerHTML = getFitnessInterpretation(realFitnessScore);
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

// --- SCHEDULE GENERATION LOGIC (REAL DATA!) ---
document.addEventListener('DOMContentLoaded', function () {
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

            // UI: Disable button, show spinner
            this.disabled = true;
            this.innerHTML = 'Processing... <span class="spinner-border spinner-border-sm"></span>';

            try {
                // 1. Generate schedule and get metrics (assume JSON with metrics is returned)
                const response = await fetch('/generate_schedule', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error("Failed to generate schedule!");

                // If backend returns JSON metrics (not file) directly:
                const metrics = await response.json();

                // Update fitness chart with the REAL value
                updateFitnessTrend(metrics.fitnessScore);

                // Update the metrics panel/cards as well:
                showMetrics(metrics);

                // Optionally, download Excel and/or JSON file if you want:
                // If you get a file instead, you'll need a separate fetch for metrics!

                this.innerHTML = "Generate Schedule";
            } catch (e) {
                alert("Error: " + e.message);
                this.innerHTML = "Generate Schedule";
            }
            this.disabled = false;
        });
    }
});

// --- METRICS CARD UPDATE ---
function showMetrics(metrics) {
    document.getElementById('fitnessScore').textContent = metrics.fitnessScore + '%';
    document.getElementById('conflictsCount').textContent = metrics.conflicts;
    document.getElementById('hardConstraints').textContent = metrics.hard + '%';
    document.getElementById('softConstraints').textContent = metrics.soft + '%';
    document.getElementById('genTime').textContent = metrics.time + 's';
}

// --- SMOOTH SCROLL FOR NAVBAR LINK ---
document.addEventListener('DOMContentLoaded', function () {
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
});

// --- DRAG & DROP FILE UPLOAD LOGIC ---
document.addEventListener("DOMContentLoaded", function () {
    const dropArea = document.getElementById("fileDropArea");
    const fileInput = document.getElementById("datasetUpload");
    const fileNameDisplay = document.getElementById("fileNameDisplay");

    if (!dropArea || !fileInput) return;

    dropArea.addEventListener('click', () => fileInput.click());
    dropArea.addEventListener('dragover', function (e) {
        e.preventDefault();
        dropArea.classList.add('dragover');
    });
    dropArea.addEventListener('dragleave', function (e) {
        dropArea.classList.remove('dragover');
    });
    dropArea.addEventListener('drop', function (e) {
        e.preventDefault();
        dropArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            showFileName(fileInput.files[0]);
        }
    });
    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            showFileName(fileInput.files[0]);
        } else if (fileNameDisplay) {
            fileNameDisplay.textContent = "";
        }
    });

    function showFileName(file) {
        if (fileNameDisplay)
            fileNameDisplay.textContent = "Selected: " + file.name;
    }
});

document.querySelectorAll('.aitu-menu-items a').forEach(link => {
    link.addEventListener('click', () => {
        document.getElementById('aitu-menu-toggle').checked = false;
    });
});
