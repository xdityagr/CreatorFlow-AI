
import os
from google import genai
from google.genai import types

from enum import Enum, auto
import re

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from .calling import VapiClient

from dotenv import load_dotenv
load_dotenv() 

campaign_info = {
    "title":"AI EVENT",
    "description": "An AI event organised by NextGen AI solutions pvt. limited. This event is to bring together ai masters from around the world.",
    "budget":"1000",
    "platform" : "Instagram, Tiktok",
    "goals": "",
    "age_group": "18-24",
    "company_name": "NextGen AI solutions pvt. ltd.", 
    "contact_info":"+918368763700"
    }

influencer_info = {
    "name":"Siddharth",
    "email": "adityagaur.home@gmail.com",
    "niche": "gaming",
    "followers": 144507,
    "engagement_rate": 3.47,
    "bio": "Throw thus another military wall her. | Collab with @nike, @adidas",
    "past_collabs": [
      "Nike",
      "Adidas"
    ],
    "roi_score": 7.25,
    "language": "Hindi",
    "age_range": "18-24"
}

class MasterLLM:
    def __init__(self):
        self._api_token = os.getenv("GEMAPIKEY")
        self.client = genai.Client(api_key=self._api_token)

        self._promptGen_emailprompt = """Consider yourself a professional manager representing a company or team. Write a formal and courteous email to [influencer] to integrate your brand. The tone should be respectful, confident, and clear. The email should reflect leadership, professionalism, and purpose. Include a subject line, appropriate greeting, a concise body with key information or requests, and a professional closing signature."""
        self._promptGen_email = """Consider yourself a professional manager representing a company or team. Write a formal and courteous email to [influencer] to integrate your brand. The tone should be respectful, confident, and clear. The email should reflect leadership, professionalism, and purpose. Include a subject line, appropriate greeting, a concise body with key information or requests, and a professional closing signature."""
        self._promptGen_transcription = """Consider yourself a professional manager representing a company or team. Write a formal and courteous email to [influencer] to integrate your brand. The tone should be respectful, confident, and clear. The email should reflect leadership, professionalism, and purpose. Include a subject line, appropriate greeting, a concise body with key information or requests, and a professional closing signature."""
        self._promptGen_searchFiltering = """Consider yourself a professional manager representing a company or team. Write a formal and courteous email to [influencer] to integrate your brand. The tone should be respectful, confident, and clear. The email should reflect leadership, professionalism, and purpose. Include a subject line, appropriate greeting, a concise body with key information or requests, and a professional closing signature."""


    def _generate_email_prompt(self, influencer_info:dict, campaign_info:dict):
        campaign_title = campaign_info["title"]
        campaign_description = campaign_info["description"]
        campaign_budget = campaign_info["budget"]
        campaign_platforms = campaign_info["platform"]
        campaign_goals = campaign_info["goals"]
        campaign_age_group = campaign_info["age_group"]
        company_name = campaign_info["company_name"]
        company_contact_info = campaign_info["contact_info"]

        influencer_name = influencer_info["name"]
        influencer_email = influencer_info["email"]
        influencer_niche = influencer_info["niche"]
        influencer_followers = influencer_info["followers"]
        influencer_engagement_rate = influencer_info["engagement_rate"]
        influencer_bio = influencer_info["bio"]
        influencer_past_collabs = influencer_info["past_collabs"]
        influencer_roi_score = influencer_info["roi_score"]
        influencer_language = influencer_info["language"]
        influencer_age_range = influencer_info["age_range"]

        prompt = f"""You are an automation bot from NextFluence AI (use this as your name) made for writing emails to influencers with whom a marketing company called '{company_name}' can integrate with. The tone should be respectful, confident, and clear. The email should reflect leadership, professionalism, and purpose. Your respone must include a subject line, appropriate greeting, a concise body with key information or requests, and a professional closing signature. At the end, Your goal is to get the contact number of the influencer for further negotiation & finally a deal. Make use of tags in your response, do not provide response out of these tags. Use <subject> tag and wrap the generated subject in it and use a closing </subject> tag as well. Move to next line use <body> tag for the whole body and end with a </body> tag."""

        content = f"""Write a formal and courteous email to the influencer '{influencer_name}' (Can be a name or a username) to integrate with the marketing campaign. Campaign info is as follows : Campaign name - {campaign_title}, Campaign Description - {campaign_description}, Campaign platforms - {campaign_platforms}, Campaign Goals are - {campaign_goals}, Campaign target age group - {campaign_age_group}, Here is the influencer info you will be writing to : Email - {influencer_email}, Influencer niche(s) - {influencer_niche}, Number of followers - {influencer_followers}, Engagement rate - {influencer_engagement_rate}, Their Bio/Description - {influencer_bio}, Their past bran collaborations - {influencer_past_collabs}, ROI Score - {influencer_roi_score}, Preferred language - {influencer_language}, Their audience's age range - {influencer_age_range}."""
        return prompt , content
    
    def _extract_emailctx(self, response_text):
        subject_match = re.search(r"<subject>(.*?)</subject>", response_text, re.DOTALL)
        body_match = re.search(r"<body>(.*?)</body>", response_text, re.DOTALL)

        subject = subject_match.group(1).strip() if subject_match else ""
        body_raw = body_match.group(1) if body_match else ""

        body = "\n".join(line.lstrip() for line in body_raw.splitlines())   
        return subject, body
    
    def _call(self, system_prompt, content):
        try:
            response = self.client.models.generate_content(
            model="gemini-2.0-flash", 
            config=types.GenerateContentConfig(
            system_instruction=system_prompt),
            contents=content)
            return response, {}
        
        except Exception as e:
            return None, {'Error': f'{e}'}
        
    def generate_email_and_send(self, influencer_info, campaign_info):
        
        system_prompt, info = self._generate_email_prompt(influencer_info, campaign_info)
        resp, err = self._call(system_prompt, info)
        if resp:
            subject, body = self._extract_emailctx(resp.text)
            # retr, err = send_mail({'user':os.getenv("GMAIL_USER"), 'passwd':os.getenv("GMAIL_PASS")}, influencer_info['email'], subject, body)
            # if retr :
            print(f"Mail successfully sent to {influencer_info['email']}")
            return subject, body
            # else:
                # print('Error :', err.get('Error'))    
                # return None, None
            
        else:        
            print('Error :', err.get('Error'))
            return None, None

    def _process_ifc(self, response):
        resp_lower = response.strip().lower()
        
        if resp_lower.startswith('<follow-up-reply>'):
            return '<follow-up-reply>', None
        
        elif resp_lower.startswith('<follow-up-cancel>'):
            return '<follow-up-cancel>', None
            
        elif resp_lower.startswith('<init-call>'):
            # Use regex to find a phone number pattern after <init-call>
            # This regex looks for digits, spaces, hyphens, and plus signs.
            # It's a basic pattern; more robust phone number regex might be needed for production.
            match = re.search(r'<init-call>\s*([\d\s\-\+]+)', resp_lower)
            if match:
                phone_number = match.group(1).strip()
                # Clean up the phone number (remove spaces, hyphens) but keep leading '+'
                phone_number = re.sub(r'[\s\-]', '', phone_number)
                return '<init-call>', phone_number
            else:
            
                return '<error>', "LLM returned <init-call> without a valid phone number."
        
        else:
            # Try to extract the error info if it was explicitly tagged as <error>
            error_match = re.search(r'<error>(.*)</error>', response, re.IGNORECASE | re.DOTALL)
            if error_match:
                return '<error>', error_match.group(1).strip()
            else:
                return '<error>', "Unrecognized LLM response format."

    def feature_checkInfluencerContact(self, subject, body):
        mail = f"""Subject : {subject}
{body}"""
        
        prompt = """You are an automation bot from NextFluence AI (use this as your name) made for analyzing the reply of the client (influencer) to a mail which was sent in order to get their phone number to proceed further negotiation & finally get a deal. You are working for a marketing company called '{company_name}'. You must analyze their reply & give out only a tag as a response, Three case can happen: [1] if their reply is a query & they want to ask something, use tag <follow-up-reply> [2] If they deny the deal, return tag <follow-up-cancel>. [3] If they share their contact info (Their phone number) use tag <init-call> with their correct phone number next to it with contry code (Mostly india).
        Your reponse must contain only 1 tag. The mail will be provided in the content. If none of the cases are met or error occurs, return only an <error> tag with enclosing the error info in it."""


        resp, error = self._call(prompt, mail)
        print(resp)
        if resp : 
            tag, num = self._process_ifc(resp.text)
            print(tag, num)
            print("\n\n\n CHECK OUT THE TAGS ABOVE.")
            if tag == '<init-call>' and num:
                vapi_client = VapiClient()
                try:
                    updated_assistant_info = vapi_client.update_assistant_prompt(campaign_info, influencer_info)
                    print("\n--- Assistant Update Complete ---")
                except Exception as e:

                    print("Exiting due to assistant update failure.")
                    exit()

                try:
                    call_details = vapi_client.initiate_call('+918368763700', '')
                    print("\n--- Call Initiation Complete ---")

                    return True
                except Exception as e:
                    print("Exiting due to call initiation failure.")
                    print(f'{e}')
                    return False
                

        
def send_mail(user_creds, to, subject, body):
    try:
        msg = MIMEMultipart()
        user = user_creds.get('user', None)
        passwd = user_creds.get('passwd', None)
        msg['From'] = user
        msg['To'] = to
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, passwd)
            server.send_message(msg)
        
        return True, {"Status": "Success"}

    except Exception as e: 
        return False, {"Status": f"Error : {e}"}



# m = MasterLLM()
# m.generate_email_and_send(influencer_info, campaign_info)

