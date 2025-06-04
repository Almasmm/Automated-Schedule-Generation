// static/js/check.js
document.addEventListener("DOMContentLoaded", function () {
    function setupDropZone(zoneId, inputId, nameId) {
        const dropZone = document.getElementById(zoneId);
        const fileInput = document.getElementById(inputId);
        const fileNameDiv = document.getElementById(nameId);

        if (!dropZone || !fileInput) return;

        // Highlight on dragover
        dropZone.addEventListener("dragover", function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add("dragover");
        });
        // Remove highlight on dragleave
        dropZone.addEventListener("dragleave", function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove("dragover");
        });
        // Handle drop
        dropZone.addEventListener("drop", function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove("dragover");
            const files = e.dataTransfer.files;
            if (files.length) {
                fileInput.files = files;
                if (fileNameDiv) fileNameDiv.textContent = files[0].name;
            }
        });
        // Click to open file dialog
        dropZone.addEventListener("click", function () {
            fileInput.click();
        });
        // Show file name on selection
        fileInput.addEventListener("change", function () {
            if (fileNameDiv)
                fileNameDiv.textContent = fileInput.files.length ? fileInput.files[0].name : "";
        });
    }

    setupDropZone("timetable-zone", "timetable", "timetable-name");
    setupDropZone("gainput-zone", "ga_input", "ga-name");
});
