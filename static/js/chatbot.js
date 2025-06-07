document.addEventListener('DOMContentLoaded', function() {
    const chatbotMessages = document.getElementById('chatbotMessages');
    const chatbotInput = document.getElementById('chatbotInput');
    const btnSendMessage = document.getElementById('btnSendMessage');

    function addMessage(content, isUser = false, isDiseaseInfo = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');

        if (isDiseaseInfo) {
            // Handle structured disease information
            messageDiv.innerHTML = `
                <div class="disease-info">
                    <h4>${content.disease}</h4>
                    <div class="disease-details">
                        <p><strong>Symptoms:</strong> ${content.symptoms || 'Not specified'}</p>
                        <p><strong>Causes:</strong> ${content.causes || 'Not specified'}</p>
                        <p><strong>Treatment:</strong> ${content.treatment || 'Not specified'}</p>
                        <p><strong>Prevention:</strong> ${content.prevention || 'Not specified'}</p>
                    </div>
                    ${content.images && content.images.length > 0 ?
                      `<div class="disease-images">
                        ${content.images.map(img => `<img src="${img}" alt="${content.disease}">`).join('')}
                       </div>` : ''}
                </div>
            `;
        } else if (content.details) {
            // Handle list responses (treatments/preventions)
            messageDiv.innerHTML = `
                <p>${content.answer}</p>
                <ul>
                    ${content.details.map(item => `<li>${item}</li>`).join('')}
                </ul>
            `;
        } else if (content.suggestions) {
            // Handle suggestions
            messageDiv.innerHTML = `
                <p>${content.answer}</p>
                <ul class="suggestions">
                    ${content.suggestions.map(item => `<li>${item}</li>`).join('')}
                </ul>
            `;
        } else if (content.diseases) {
            // Handle disease list
            messageDiv.innerHTML = `
                <p>${content.answer}</p>
                <div class="disease-buttons">
                    ${content.diseases.map(disease =>
                        `<button class="btn btn-small view-disease" data-disease="${disease}">${disease}</button>`
                    ).join('')}
                </div>
            `;
        } else {
            // Simple text message
            const messageContent = document.createElement('p');
            messageContent.textContent = content.answer || content;
            messageDiv.appendChild(messageContent);
        }

        chatbotMessages.appendChild(messageDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        // Add event listeners to any new disease buttons
        messageDiv.querySelectorAll('.view-disease').forEach(button => {
            button.addEventListener('click', function() {
                const diseaseName = this.getAttribute('data-disease');
                fetchDiseaseInfo(diseaseName);
            });
        });
    }

    async function fetchDiseaseInfo(diseaseName) {
        try {
            const response = await fetch(`/disease-info/${diseaseName}`);
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            addMessage({
                type: 'disease_info',
                disease: diseaseName,
                answer: `Information about ${diseaseName}:`,
                ...data
            }, false, true);
        } catch (error) {
            console.error('Error fetching disease info:', error);
            addMessage("Sorry, I couldn't retrieve information about that disease.");
        }
    }

    async function sendMessage() {
        const message = chatbotInput.value.trim();
        if (!message) return;

        // Add user message
        addMessage(message, true);
        chatbotInput.value = '';

        try {
            const response = await fetch('/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Handle different response types
            switch(data.type) {
                case 'disease_info':
                    addMessage(data, false, true);
                    break;
                case 'general_info':
                case 'guidance':
                case 'disease_list':
                    addMessage(data);
                    break;
                default:
                    addMessage(data.answer || "I didn't understand that. Can you rephrase?");
            }
        } catch (error) {
            console.error('Chatbot error:', error);
            addMessage({
                answer: "Sorry, I'm having trouble connecting. Please try again later.",
                type: 'error'
            });
        }
    }

    // Event listeners
    btnSendMessage.addEventListener('click', sendMessage);
    chatbotInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Initial bot greeting
    addMessage({
        type: 'greeting',
        answer: "Hello! I'm your Rice Disease Assistant. Ask me about symptoms, treatments, or prevention for specific rice diseases."
    });
});