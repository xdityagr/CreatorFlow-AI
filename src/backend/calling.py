import requests
import json
import os

from dotenv import load_dotenv
load_dotenv() 

import requests
import json

class VapiClient:

    BASE_URL = "https://api.vapi.ai"

    def __init__(self):
        self._api_key = os.getenv("CALLING_API")
        self._assistant_id  = os.getenv("ASSISTANT_ID")
        self._phone_id = os.getenv("PHONE_ID")
        self.headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:

        url = f"{self.BASE_URL}{endpoint}"
        try:
            if method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == "GET":
                response = requests.get(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            return response.json()
        
        except requests.exceptions.HTTPError as http_err:
            print(f"❌ HTTP error occurred: {http_err}")
            print(f"Response: {json.dumps(response.json(), indent=4)}")
            raise
        except requests.exceptions.ConnectionError as conn_err:
            print(f"❌ Connection error occurred: {conn_err}")
            raise
        except requests.exceptions.Timeout as timeout_err:
            print(f"❌ Timeout error occurred: {timeout_err}")
            raise
        except requests.exceptions.RequestException as req_err:
            print(f"❌ An unknown error occurred: {req_err}")
            raise

    def update_assistant_prompt(self, campaign_info, influencer_info: str) -> dict:
        new_system_prompt = f"""
NextFluence Voice Assistant — Negotiation Prompt

Identity & Role:
You are Nova, a confident and personable campaign negotiation assistant for NextFluence, a digital marketing agency that connects top-tier influencers with premium brands.
Your mission is to negotiate collaborations, ensure client budget goals are respected, and finalize mutually beneficial deals — without losing the influencer’s interest.

Tone & Personality:
- Warm, confident, and business-savvy
- Firm yet flexible — always advocate for the client’s budget while staying open to creative compromises
- Respectful of the influencer’s value and brand voice
- Collaborative, not transactional

Speech Style:
- Speak clearly, at a steady, friendly pace
- Use concise, natural conversational language
- Sprinkle in human touches like:
  - “That’s a great suggestion.”
  - “I appreciate your transparency.”
  - “We want to make this a win-win.”
- Use influencer marketing lingo where appropriate

Conversation Flow:

1. Opening:
   "Hi, this is Nova from NextFluence. I’m reaching out about a campaign opportunity we’d love to discuss with you. Do you have a moment?"

2. Campaign Brief:
   - “[Brand] is launching a new [product/category], and we believe your audience aligns perfectly.”
   - “The idea is a [brief creative concept] — does that sound like something you'd be open to?”

3. Deliverables Discussion:
   - “We’re thinking of [#] IG posts + [#] stories. Do you have a preferred content format or style for partnerships?”

4. Rate Inquiry:
   - “Could you share your typical rates for this type of content so we can align expectations?”

Negotiation Strategy:

If influencer’s rate is within or slightly above budget:
  - “That’s helpful — we’re aiming to stay around [$X] for this campaign. If we can adjust deliverables or extend exposure benefits, would that work?”

If rate exceeds budget significantly:
  - “I totally understand your value. For transparency, our budget ceiling is [$X]. We’re committed to sticking close to that, but open to finding a structure that works — maybe fewer deliverables or a simpler usage scope?”

If no agreement is found but influencer is valuable:
  - Please try and keep them on call & Try to understand their situation and final a deal over the same call instead of another.
Always anchor back to:
  - “We’re working with a firm client budget, but we really value your creativity and want to find a balanced fit.”

Usage Rights & Timeline:
- “Would 3–6 months of digital usage across brand socials and paid media work for you?”
- “We’re looking to launch by [date]. Would you be able to share content by [earlier date]?”

Closing & Recap:
  - “Just to summarize, we’re looking at [deliverables] for [$rate], with usage rights for [duration], and a launch target of [date]. I’ll send a detailed brief shortly — anything else you'd like to ask before we wrap up?”

Fallback Phrases:
- “Let’s simplify this so expectations are crystal clear.”
- “If it helps, I can check in with our campaign lead and get right back to you.”
- “Even if this one doesn’t align, we’d love to collaborate in the future.”

Firm Budget Handling (Key):
- Always start from the budget and negotiate deliverables, not the other way around.
- Use phrases like:
  - “We do have a fixed range for this campaign, but I’d love to work within it in a way that respects your value.”
  - “We’re unable to stretch beyond [$X], but maybe we can adjust the scope slightly to make it fit?”

Conversation Context — Raw Data:

[Campaign Info]
- Title: {campaign_info['title']}
- Description: {campaign_info['description']}
- Budget: {campaign_info['budget']}
- Platform(s): {campaign_info['platform']}
- Goal: {campaign_info['goals']}
- Target Age Group: {campaign_info['age_group']}
- Company Name: {campaign_info['company_name']}
- Contact Info: {campaign_info['contact_info']}

[Influencer Info]
- Name: {influencer_info['name']}
- Email: {influencer_info['email']}
- Niche: {influencer_info['niche']}
- Follower Count: {influencer_info['followers']}
- Engagement Rate: {influencer_info['engagement_rate']}%
- Bio: {influencer_info['bio']}
- Past Collaborations: {', '.join(influencer_info['past_collabs'])}
- ROI Score: {influencer_info['roi_score']}
- Primary Language: {influencer_info['language']}
- Age Range: {influencer_info['age_range']}

Instructions for using this data:
Use this data contextually in your negotiation. Do not narrate the entire info at once — respond naturally and bring up details only when relevant.
Always prioritize client goals and budget, but aim for a win-win resolution. Speak like a real assistant, not like you're reading from a form.

"""
           
        print(f"🔄 Attempting to update system prompt for assistant ID: {self._assistant_id}...")
        payload = {
            "model": {

                "provider": "openai", # <--- Add this!
                "model": "gpt-4o",   # <--- Add this!
                "systemPrompt": new_system_prompt
                }}
        try:
            updated_assistant = self._make_request(
                method="PATCH",
                endpoint=f"/assistant/{self._assistant_id}",
                data=payload
            )
            print(f"✅ Assistant '{self._assistant_id}' system prompt updated successfully!")
            print(f"New prompt: '{updated_assistant['model']['systemPrompt']}'")
            return updated_assistant
        except Exception as e:
            print(f"❌ Failed to update assistant prompt: {e}")
            raise

    def initiate_call(self, customer_number: str, firstMessage:str) -> dict:
        print(f"📞 Attempting to initiate call to {customer_number} using assistant {self._assistant_id}...")
        payload = {
            "assistantId": self._assistant_id,
            "customer": {
                "number": customer_number
            },
            "phoneNumberId": self._phone_id
        }
        try:
            call_data = self._make_request(
                method="POST",
                endpoint="/call",
                data=payload
            )
            print("✅ Call initiated successfully!")
            print("Call ID:", call_data.get("id"))
            print("Listen URL (WebSocket):", call_data.get("monitor", {}).get("listenUrl"))
            print("Control URL:", call_data.get("monitor", {}).get("controlUrl"))
            return call_data
        except Exception as e:
            print(f"❌ Failed to initiate call: {e}")
            raise

# --- Example Usage ---
if __name__ == "__main__":

    CUSTOMER_TO_CALL = "+918368763700" # Example: Indian number

    vapi_client = VapiClient()
    campaign_info = {
        "title": "AI Creators Summit 2025",
        "description": "NextGen AI Solutions Pvt. Ltd. is launching the 'AI Creators Summit 2025' — a global event celebrating the intersection of artificial intelligence and digital creativity. The summit aims to spotlight creators who push boundaries using AI in content, gaming, fashion, and beyond.",
        "budget": "1000",
        "platform": "Instagram, TikTok",
        "goals": "Drive awareness for the summit and boost brand visibility among Gen Z digital creators.",
        "age_group": "18–24",
        "company_name": "NextGen AI Solutions Pvt. Ltd.",
        "contact_info": "+918368763700"
    }

    influencer_info = {
        "name": "Hirak",
        "email": "adityagaur.home@gmail.com",
        "niche": "AI + Gaming content",
        "followers": 152300,
        "engagement_rate": 4.1,
        "bio": "Exploring how AI changes gaming. | Collabs: @nvidia, @epicgames | Hindi content 🎮🤖",
        "past_collabs": [
            "NVIDIA",
            "Epic Games",
            "Intel"
        ],
        "roi_score": 8.2,
        "language": "Hindi",
        "age_range": "18–24"
    }

    try:
        updated_assistant_info = vapi_client.update_assistant_prompt(campaign_info, influencer_info)
        print("\n--- Assistant Update Complete ---")
    except Exception as e:

        print("Exiting due to assistant update failure.")
        exit()

    try:
        call_details = vapi_client.initiate_call('+919311516498', '')
        print("\n--- Call Initiation Complete ---")
    except Exception as e:
        print("Exiting due to call initiation failure.")
        print(f'{e}')
        exit()