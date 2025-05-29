// Chart.js metrics section
const createChart = (id, label, color) => {
    return new Chart(document.getElementById(id).getContext('2d'), {
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
                legend: {
                    labels: { color: 'white' }
                }
            },
            scales: {
                x: { ticks: { color: 'white' } },
                y: { ticks: { color: 'white' }, beginAtZero: true }
            }
        }
    });
};
const cpuChart = createChart('cpuChart', 'CPU Load', 'orange');
const ramChart = createChart('ramChart', 'RAM Load', 'lightgreen');
const memoryChart = createChart('memoryChart', 'Memory Load', 'skyblue');
const internetChart = createChart('internetChart', 'Internet Load', 'red');

const updateCharts = () => {
    const time = new Date().toLocaleTimeString();
    const pushData = (chart, value) => {
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
    pushData(internetChart, Math.random() * 100);
};
setInterval(updateCharts, 2000);

// Schedule generation logic
document.addEventListener('DOMContentLoaded', function () {
    const generateBtn = document.getElementById("generateBtn");
    if (generateBtn) {
        generateBtn.addEventListener("click", async function () {
            const trimester = document.getElementById("trimester").value;
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
                // 1. Generate schedule and download Excel
                const response = await fetch('/generate_schedule', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error("Failed to generate schedule!");

                // Download the Excel file
                const blob = await response.blob();
                const downloadUrl = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = `timetable_T${trimester}.xlsx`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(downloadUrl);

                // 2. Automatically download the JSON file right after
                const jsonResponse = await fetch(`/download_json?trimester=${trimester}`);
                if (jsonResponse.ok) {
                    const jsonBlob = await jsonResponse.blob();
                    const jsonUrl = URL.createObjectURL(jsonBlob);
                    const a2 = document.createElement("a");
                    a2.href = jsonUrl;
                    a2.download = `timetable_T${trimester}.json`;
                    document.body.appendChild(a2);
                    a2.click();
                    a2.remove();
                    URL.revokeObjectURL(jsonUrl);
                } else {
                    alert("Schedule generated, but JSON file not found!");
                }

                this.innerHTML = "Generate Schedule";
                document.getElementById("afterGenButtons").style.display = "";
            } catch (e) {
                alert("Error: " + e.message);
                this.innerHTML = "Generate Schedule";
            }
            this.disabled = false;
        });
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const link = document.getElementById("generateScheduleLink");
    if (link) {
        link.addEventListener("click", function (e) {
            e.preventDefault();
            const scheduleSection = document.getElementById("main-content");
            if (scheduleSection) {
                scheduleSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
});

