document.addEventListener('DOMContentLoaded', function() {
    // --- Influencer Search Page Filtering (No changes here, copied for completeness) ---
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            const campaignId = this.dataset.campaignId;
            const niche = document.getElementById('filter-niche').value;
            const minFollowers = document.getElementById('filter-min-followers').value;
            const minRoi = document.getElementById('filter-min-roi').value;
            const minEngagement = document.getElementById('filter-min-engagement').value;

            let queryParams = [];
            if (niche) {
                queryParams.push(`niche=${encodeURIComponent(niche)}`);
            }
            if (minFollowers) {
                queryParams.push(`min_followers=${encodeURIComponent(minFollowers)}`);
            }
            if (minRoi) {
                queryParams.push(`min_roi=${encodeURIComponent(minRoi)}`);
            }
            if (minEngagement) {
                queryParams.push(`min_engagement=${encodeURIComponent(minEngagement)}`);
            }

            const currentUrl = window.location.pathname;

            const newUrl = `${currentUrl.split('?')[0]}?${queryParams.join('&')}`;
            window.location.href = newUrl;
        });
    }

    // --- AI Negotiation Page: Start Negotiation Button ---
    const startNegotiationBtn = document.getElementById('start-negotiation-btn');
    if (startNegotiationBtn) {
        startNegotiationBtn.addEventListener('click', function() {
            const influencerId = startNegotiationBtn.dataset.influencerId; // Get from data attribute
            const campaignId = startNegotiationBtn.dataset.campaignId;   // Get from data attribute
            const negotiationProgressSteps = document.getElementById('negotiation-progress-steps');
            const negotiationSummaryContent = document.getElementById('negotiation-summary-content');

            // Clear previous messages
            if (negotiationProgressSteps) negotiationProgressSteps.innerHTML = '';
            if (negotiationSummaryContent) negotiationSummaryContent.innerHTML = '';

            // Add loading indicator
            if (negotiationProgressSteps) {
                negotiationProgressSteps.innerHTML = '<p class="text-info"><div class="spinner-border spinner-border-sm me-2" role="status"><span class="visually-hidden">Loading...</span></div>Initiating negotiation process...</p>';
            }
            startNegotiationBtn.disabled = true; // Disable button during negotiation
            startNegotiationBtn.textContent = 'Negotiation in Progress...';
            startNegotiationBtn.classList.remove('btn-primary');
            startNegotiationBtn.classList.add('btn-secondary');


            fetch('/api/start_negotiation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ influencer_id: influencerId, campaign_id: campaignId }),
            })
            .then(response => response.json())
            .then(data => {
                if (['initiated', 'email_sent', 'call_initiated', 'negotiation_complete'].includes(data.status)) {
                    if (negotiationProgressSteps) {
                        negotiationProgressSteps.innerHTML = ''; // Clear initial message

                        let stepIndex = 0;
                        const interval = setInterval(() => {
                            if (stepIndex < data.steps.length) {
                                // Add progress step with a little animation/styling
                                const p = document.createElement('p');
                                p.classList.add('fade-in'); // Add fade-in class for animation
                                p.textContent = data.steps[stepIndex];
                                negotiationProgressSteps.appendChild(p);
                                negotiationProgressSteps.scrollTop = negotiationProgressSteps.scrollHeight; // Scroll to bottom
                                stepIndex++;
                            } else {
                                clearInterval(interval);
                                clearInterval(intervalId);
                                intervalId = setInterval(() => pollNegotiationStatus(influencerId, campaignId), 3000);

                            }
                        }, 1500); // Simulate delay between steps (1.5 seconds)
                    }
                } else {
                    if (negotiationProgressSteps) {
                        negotiationProgressSteps.innerHTML = `<p class="text-danger">Error: ${data.message}</p>`;
                    }
                    if (negotiationSummaryContent) {
                         negotiationSummaryContent.innerHTML = `
                            <h4 class="text-danger mb-3">Negotiation Failed</h4>
                            <p><strong>Status:</strong> <span class="text-danger fw-bold">An error occurred or negotiation failed.</span></p>
                        `;
                    }
                    startNegotiationBtn.disabled = false;
                    startNegotiationBtn.textContent = 'Start AI Negotiation (Failed)';
                    startNegotiationBtn.classList.remove('btn-secondary');
                    startNegotiationBtn.classList.add('btn-danger');
                }
            })
            .catch((error) => {
                console.error('Fetch Error:', error);
                if (negotiationProgressSteps) {
                    negotiationProgressSteps.innerHTML = '<p class="text-danger">An error occurred during negotiation (check console).</p>';
                }
                if (negotiationSummaryContent) {
                    negotiationSummaryContent.innerHTML = `
                        <h4 class="text-danger mb-3">Negotiation Error</h4>
                        <p><strong>Status:</strong> <span class="text-danger fw-bold">Network error or API issue.</span></p>
                    `;
                }
                startNegotiationBtn.disabled = false;
                startNegotiationBtn.textContent = 'Start AI Negotiation (Error)';
                startNegotiationBtn.classList.remove('btn-secondary');
                startNegotiationBtn.classList.add('btn-danger');
            });
        });
    }
});
