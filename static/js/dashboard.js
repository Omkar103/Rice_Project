document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadArea = document.getElementById('uploadArea');
    const previewArea = document.getElementById('previewArea');
    const imageUpload = document.getElementById('imageUpload');
    const imagePreview = document.getElementById('imagePreview');
    const btnClosePreview = document.getElementById('btnClosePreview');
    const btnAnalyze = document.getElementById('btnAnalyze');
    const resultArea = document.getElementById('resultArea');
    const resultContent = document.getElementById('resultContent');
    const spinner = document.getElementById('spinner');


    // Event Listeners
    imageUpload.addEventListener('change', handleImageUpload);
    btnRemoveImage.addEventListener('click', resetUpload);
    btnAnalyze.addEventListener('click', analyzeImage);

    // Drag and drop functionality
    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#2e7d32';
        uploadBox.style.backgroundColor = 'rgba(46, 125, 50, 0.05)';
    });

    uploadBox.addEventListener('dragleave', () => {
        uploadBox.style.borderColor = '#ccc';
        uploadBox.style.backgroundColor = 'transparent';
    });

    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#ccc';
        uploadBox.style.backgroundColor = 'transparent';

        if (e.dataTransfer.files.length) {
            imageUpload.files = e.dataTransfer.files;
            handleImageUpload({ target: { files: e.dataTransfer.files } });
        }
    });

    // Functions
    function handleImageUpload(event) {
        const file = event.target.files[0];

        if (!file) return;

        if (!file.type.match('image.*')) {
            alert('Please select an image file (JPEG, PNG)');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            imagePreview.src = e.target.result;
            uploadBox.style.display = 'none';
            previewBox.style.display = 'block';
            resultsBox.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    function resetUpload() {
        imageUpload.value = '';
        imagePreview.src = '#';
        previewBox.style.display = 'none';
        resultsBox.style.display = 'none';
        uploadBox.style.display = 'block';
    }

    async function analyzeImage() {
        if (!imageUpload.files.length) {
            alert('Please select an image first');
            return;
        }

        previewBox.style.display = 'none';
        resultsBox.style.display = 'block';
        resultsContent.style.display = 'none';
        spinner.style.display = 'block';

        const formData = new FormData();
        formData.append('image', imageUpload.files[0]);

        try {
            const response = await fetch('/classify', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Display results
            displayResults(data);

        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
            resetUpload();
        }
    }

    function displayResults(data) {
        spinner.style.display = 'none';
        resultsContent.style.display = 'block';

        document.getElementById('diseaseName').textContent = data.disease || 'Unknown';
        document.getElementById('confidenceValue').textContent = `${Math.round((data.confidence || 0) * 100)}%`;
        document.getElementById('confidenceFill').style.width = `${(data.confidence || 0) * 100}%`;
        document.getElementById('recommendationText').textContent = data.recommendation || 'No recommendation available';
    }
    // Settings functionality
    document.getElementById('dark-mode').addEventListener('change', function() {
        document.body.classList.toggle('dark-mode', this.checked);
        updateSettings({ dark_mode: this.checked });
    });

    document.getElementById('email-notifications').addEventListener('change', function() {
        updateSettings({ notifications: this.checked });
    });

    document.getElementById('language-select').addEventListener('change', function() {
        updateSettings({ language: this.value });
    });

    async function updateSettings(settings) {
        try {
            const response = await fetch('/update-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                throw new Error('Failed to update settings');
            }
        } catch (error) {
            console.error('Error updating settings:', error);
        }
    }

    // Disease info modal
    const modal = document.getElementById('diseaseModal');
    const closeModal = document.querySelector('.close-modal');
    const viewButtons = document.querySelectorAll('.view-details, .view-disease');

    viewButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const diseaseName = this.getAttribute('data-disease');
            try {
                const response = await fetch(`/disease-info/${diseaseName}`);
                const data = await response.json();

                if (data.error) {
                    throw new Error(data.error);
                }

                // Populate modal
                document.getElementById('modalDiseaseName').textContent = diseaseName;
                document.getElementById('modalSymptoms').textContent = data.symptoms || 'Not available';
                document.getElementById('modalCauses').textContent = data.causes || 'Not available';
                document.getElementById('modalTreatment').textContent = data.treatment || 'Not available';
                document.getElementById('modalPrevention').textContent = data.prevention || 'Not available';

                const imagesContainer = document.getElementById('modalImages');
                imagesContainer.innerHTML = '';

                if (data.images && data.images.length) {
                    data.images.forEach(img => {
                        const imgEl = document.createElement('img');
                        imgEl.src = img;
                        imgEl.alt = diseaseName;
                        imagesContainer.appendChild(imgEl);
                    });
                }

                modal.style.display = 'block';
            } catch (error) {
                console.error('Error fetching disease info:', error);
                alert('Could not load disease information');
            }
        });
    });

    closeModal.addEventListener('click', function() {
        modal.style.display = 'none';
    });

    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    // Save result button
    const btnSaveResult = document.getElementById('btnSaveResult');
    if (btnSaveResult) {
        btnSaveResult.addEventListener('click', function() {
            alert('Result saved to your history!');
        });
    }
});