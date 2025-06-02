from flask import Flask, render_template, request, redirect, url_for, jsonify
import uuid
import json
import os 
import threading
import time 

from backend.aiengine import MasterLLM
from backend.calling import VapiClient

from backend.emailEngine import EmailFollowUpSystem
import logging 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


app = Flask(__name__)
llm = MasterLLM()
vapi_client = VapiClient()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
EMAIL_ADDRESS = os.getenv("GMAIL_USER", "your_email@example.com") 
EMAIL_PASSWORD = os.getenv("GMAIL_PASS", "your_app_password")   


email_system = EmailFollowUpSystem(
    smtp_server=SMTP_SERVER,
    smtp_port=SMTP_PORT,
    imap_server=IMAP_SERVER,
    imap_port=IMAP_PORT,
    email_address=EMAIL_ADDRESS,
    password=EMAIL_PASSWORD
)

# Global dictionary to store negotiation statuses for frontend polling
negotiation_statuses = {}
negotiation_lock = threading.Lock() # For thread-safe access to negotiation_statuses


def app_reply_handler(from_email, subject, body, email_id):
    logger.info(f"App-integrated Reply received from {from_email}: {subject} (Email ID: {email_id})")

    found_negotiation_key = None
    with negotiation_lock:
        for (inf_id, camp_id), status_data in negotiation_statuses.items():
            if status_data.get('status') == 'email_sent':
                selected_influencer = next((i for i in influencers_data if str(i["id"]) == inf_id), None)
                selected_influencer['email'] = 'adityagaur.home@gmail.com'
                if selected_influencer and selected_influencer['email'].lower() == from_email.lower():
                    found_negotiation_key = (inf_id, camp_id)
                    break
    
    if found_negotiation_key:
        inf_id, camp_id = found_negotiation_key
        selected_influencer = next((i for i in influencers_data if str(i["id"]) == inf_id), None)
        selected_campaign = next((c for c in campaigns if c["id"] == camp_id), None)

        if selected_influencer and selected_campaign:
            try:
                # Use MasterLLM to check for contact info and trigger call
                success = llm.feature_checkInfluencerContact(subject, body)
                    
                result = '+918368763700'
                
                with negotiation_lock:
                    current_steps = negotiation_statuses[found_negotiation_key]['steps']
                    if success:
                        current_steps.append("Influencer's contact information received via email.")
                        current_steps.append("Updating AI assistant for voice negotiation...")
                        current_steps.append("Initiating AI voice call with influencer...")
                        current_steps.append("Call initiated successfully.")
                        current_steps.append("Negotiation in progress... (AI voice call ongoing)")
                        current_steps.append("Monitor call status via Vapi dashboard for real-time updates.")
                        current_steps.append("Negotiation complete. Awaiting contract signing.")
                        
                        negotiation_statuses[found_negotiation_key]['status'] = 'call_initiated'
                        negotiation_statuses[found_negotiation_key]['message'] = 'Call initiated successfully.'
                        negotiation_statuses[found_negotiation_key]['phone_number'] = result # Assuming result contains the phone number
                    else:
                        current_steps.append(f"Failed to extract contact info or initiate call: {result}")
                        negotiation_statuses[found_negotiation_key]['status'] = 'error_during_call_initiation'
                        negotiation_statuses[found_negotiation_key]['message'] = f'Error: {result}'
            except Exception as e:
                logger.error(f"Error in app_reply_handler during call initiation: {e}")
                with negotiation_lock:
                    negotiation_statuses[found_negotiation_key]['status'] = 'error_during_call_initiation'
                    negotiation_statuses[found_negotiation_key]['message'] = f'An unexpected error occurred during call initiation: {e}'
        else:
            logger.warning(f"Could not find matching campaign/influencer for reply from {from_email}")
    else:
        logger.info(f"No active negotiation found for reply from {from_email}.")


email_system.register_reply_callback(app_reply_handler)
# --- End Custom Reply Handler ---


# --- Load Influencer Data from JSON File ---
CREATORS_FILE = 'creators.json'

def load_creators_data():
    try:
        with open(CREATORS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {CREATORS_FILE} not found. Returning empty list.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {CREATORS_FILE}. Returning empty list.")
        return []

influencers_data = load_creators_data()
# --- End Influencer Data Loading ---


# --- Dummy Data for Campaigns (Keep as is, or integrate with a proper DB later) ---
campaigns = []
# --- End Dummy Data ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('campaign_list.html', campaigns=campaigns)

@app.route('/campaign/create', methods=['GET', 'POST'])
def campaign_create():
    if request.method == 'POST':
        new_campaign = {
            "id": str(uuid.uuid4()),
            "title": request.form['title'],
            "description": request.form['description'],
            "budget": request.form['budget'],
            "niche": request.form['niche'],
            "platform": request.form['platform'],
            "company_name": request.form['company_name'],
            "contact_info": request.form['contact_info'],
            "goals": request.form['goal'],
            "age_group": request.form['age_group'],
            "additional_params": request.form.get('additional_params', '')
        }
        campaigns.append(new_campaign)
        print(f"New campaign created: {new_campaign}")
        return redirect(url_for('dashboard'))
    return render_template('campaign_create.html')

@app.route('/influencer/search/<campaign_id>')
def influencer_search(campaign_id):
    selected_campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not selected_campaign:
        return "Campaign not found!", 404

    filter_niche = request.args.get('niche', '').strip().lower()
    filter_min_followers = request.args.get('min_followers', type=int)
    filter_min_roi = request.args.get('min_roi', type=float)
    filter_min_engagement = request.args.get('min_engagement', type=float)

    filtered_influencers = influencers_data

    if filter_niche:
        filtered_influencers = [
            i for i in filtered_influencers
            if filter_niche in i["niche"].lower()
        ]

    if filter_min_followers is not None:
        filtered_influencers = [
            i for i in filtered_influencers
            if i["followers"] >= filter_min_followers
        ]

    if filter_min_roi is not None:
        filtered_influencers = [
            i for i in filtered_influencers
            if i["roi_score"] >= filter_min_roi
        ]

    if filter_min_engagement is not None:
        filtered_influencers = [
            i for i in filtered_influencers
            if i["engagement_rate"] >= filter_min_engagement
        ]

    current_filters = {
        'niche': filter_niche,
        'min_followers': filter_min_followers,
        'min_roi': filter_min_roi,
        'min_engagement': filter_min_engagement
    }

    return render_template('influencer_search.html',
                           influencers=filtered_influencers,
                           campaign=selected_campaign,
                           current_filters=current_filters)

@app.route('/ai_negotiation/<influencer_id>/<campaign_id>')
def ai_negotiation(influencer_id, campaign_id):
    selected_influencer = next((i for i in influencers_data if str(i["id"]) == influencer_id), None)
    selected_campaign = next((c for c in campaigns if c["id"] == campaign_id), None)

    if not selected_influencer or not selected_campaign:
        return "Influencer or Campaign not found!", 404

    print(f"{selected_campaign=}", f"{selected_influencer}")

    return render_template('ai_negotiation.html',
                           influencer=selected_influencer,
                           campaign=selected_campaign)

@app.route('/api/start_negotiation', methods=['POST'])
def start_negotiation():
    data = request.json
    influencer_id = data.get('influencer_id')
    campaign_id = data.get('campaign_id')

    selected_influencer = next((i for i in influencers_data if str(i["id"]) == influencer_id), None)
    selected_influencer['email'] = 'adityagaur.home@gmail.com'

    selected_campaign = next((c for c in campaigns if c["id"] == campaign_id), None)

    if not selected_influencer or not selected_campaign:
        return jsonify({"status": "error", "message": "Influencer or Campaign not found!"}), 404

    negotiation_key = (influencer_id, campaign_id)

    # Initialize negotiation status for this pair
    with negotiation_lock:
        negotiation_statuses[negotiation_key] = {
            "status": "initiated",
            "message": "Negotiation process initiated.",
            "steps": ["Initiating AI negotiation..."],
            "phone_number": None # To store if received
        }

    status = "success"
    message = "Negotiation process initiated."

    try:
        with negotiation_lock:
            current_steps = negotiation_statuses[negotiation_key]['steps']
            current_steps.append("Generating and sending initial outreach email...")

        sub, body = llm.generate_email_and_send(selected_influencer, selected_campaign)
        email_success = False
        email_error = None

        try:
            email_system.send_with_followup(
            to_email='adityagaur.home@gmail.com', # Replace with a test email you can reply from
            subject=sub,
            message=body,
            timeout_hours=24
        )
            email_success=True
        except Exception as e:
            email_error = e

        if email_success:
            with negotiation_lock:
                negotiation_statuses[negotiation_key]['status'] = 'email_sent'
                negotiation_statuses[negotiation_key]['message'] = 'Initial email sent. Monitoring for influencer\'s reply.'
                negotiation_statuses[negotiation_key]['steps'].append(f"Email sent successfully to {selected_influencer['email']}.")
                negotiation_statuses[negotiation_key]['steps'].append("Awaiting influencer's email response... (Monitoring in background)")
            message = "Initial email sent. Monitoring for influencer's reply."
        else:
            with negotiation_lock:
                negotiation_statuses[negotiation_key]['status'] = 'email_send_failed'
                negotiation_statuses[negotiation_key]['message'] = f"Failed to send initial email: {email_error}."
                negotiation_statuses[negotiation_key]['steps'].append(f"Failed to send initial email: {email_error}. Negotiation halted.")
            status = "error"
            message = negotiation_statuses[negotiation_key]['message']

    except Exception as e:
        logger.error(f"Error in start_negotiation: {e}")
        with negotiation_lock:
            negotiation_statuses[negotiation_key]['status'] = 'error'
            negotiation_statuses[negotiation_key]['message'] = f"An unexpected error occurred: {e}"
            negotiation_statuses[negotiation_key]['steps'].append(f"An unexpected error occurred: {e}")
        status = "error"
        message = negotiation_statuses[negotiation_key]['message']

    # Return the current status for the frontend to display immediately
    with negotiation_lock:
        response_data = negotiation_statuses[negotiation_key].copy()
    return jsonify(response_data), 200 if status == "success" else 500

# New endpoint for frontend to poll for negotiation status updates
@app.route('/api/negotiation_status/<influencer_id>/<campaign_id>', methods=['GET'])
def get_negotiation_status(influencer_id, campaign_id):
    negotiation_key = (influencer_id, campaign_id)
    with negotiation_lock:
        status_data = negotiation_statuses.get(negotiation_key, {
            "status": "not_found",
            "message": "Negotiation not initiated or found.",
            "steps": ["Negotiation not found."],
            "phone_number": None
        })
    return jsonify(status_data)


# Function to start email monitoring in a separate thread
def start_email_monitoring():
    logger.info("Starting email monitoring thread...")
    try:
        email_system.start_monitoring()
    except Exception as e:
        logger.error(f"Error starting email monitoring: {e}")


if __name__ == '__main__':
    # Start email monitoring in a separate thread
    monitoring_thread = threading.Thread(target=start_email_monitoring, daemon=True) 
    monitoring_thread.start()

    # Run the Flask app
    app.run(debug=True)
