from emailEngine import EmailFollowUpSystem
import os
import time
import threading
import logging
from aiengine import MasterLLM
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class emailHandler:
    def __init__(self):
        EMAIL_CONFIG = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'imap_server': 'imap.gmail.com',
        'imap_port': 993,
        'email_address': os.getenv("GMAIL_USER"),  # Replace with your email
        'password': os.getenv("GMAIL_PASS") # Replace with your app password
        }       
        self.check_delay = 30
        self.llm = MasterLLM()
        
        self.engine = EmailFollowUpSystem(**EMAIL_CONFIG)
        self.engine.register_reply_callback(self._replied)
        
    def update_check_delay(self, delay):
        self.check_delay = delay

    def initiateMailing(self):
        threading.Thread(target=self.initiate_mailing_thread, daemon=True).start()

    def initiate_mailing_thread(self):
        self.engine.start_monitoring()

        try:
            while True:
                pending_count = len(self.engine.get_pending_emails())
                if pending_count > 0:
                    logger.info(f"Currently tracking {pending_count} emails for follow-up")
                else:
                    logger.info("No emails currently being tracked for follow-up.")
                time.sleep(self.check_delay)  # Don't sleep only when count is 0
        except KeyboardInterrupt:
            logger.info("Ctrl+C detected. Shutting down email system...")
            self.engine.stop_monitoring()
            print("Main program exiting.")
    def send_followup(self, to, subject, body,  followup_timeout=24):
        self.engine.send_with_followup(to_email=to, subject=subject, message=body, timeout_hours=followup_timeout)
    
    def _replied(self, sender_email, subject, body, original_sent_info):
        print('User replied, processing with llm now. ')
        self.llm.feature_checkInfluencerContact(subject, body)



e = emailHandler()
e.initiateMailing()
e.send_followup(
        to='adityagaur.home@gmail.com', # Replace with a test email you can reply from
        subject='Important Meeting Request - Test',
        body='Hello,\n\nI would like to schedule a meeting with you next week. Please let me know your availability.\n\nBest regards',
        followup_timeout=0.001 
    )
            


#             """
#     This function will be called when a reply is detected.
#     It acts as the "signal" receiver.
#     """
#     print("\n" + "="*50)
#     print(f"🎉 REPLY SIGNAL RECEIVED! 🎉")
#     print(f"From: {sender_email}")
#     print(f"Subject: {subject}") # Print the received subject
#     print(f"Body snippet:\n{body[:200]}...") # Print first 200 chars of the received body
#     print(f"Original email sent info: {original_sent_info['to_email']}, {original_sent_info['subject']}")
#     print("="*50 + "\n")

#     # Example: Decide whether to follow up further or not
#     # In a real application, you might analyze the 'body' to make this decision.
#     if "thanks" in body.lower() or "got it" in body.lower():
#         print("Reply indicates acknowledgement. No further follow-up needed for this conversation.")
#         # The system will automatically stop tracking this email, as a reply was detected.
#     else:
#         print("Reply received, but further action might be needed based on content.")
#         # If the reply is incomplete, you might want to manually re-add it or trigger
#         # a new task based on its content, *outside* the automatic follow-up logic.


# def my_reply_handler(sender_email, subject, body, original_sent_info):
#     """
#     This function will be called when a reply is detected.
#     It acts as the "signal" receiver.
#     """
#     print("\n" + "="*50)
#     print(f"🎉 REPLY SIGNAL RECEIVED! 🎉")
#     print(f"From: {sender_email}")
#     print(f"Subject: {subject}") # Print the received subject
#     print(f"Body snippet:\n{body[:200]}...") # Print first 200 chars of the received body
#     print(f"Original email sent info: {original_sent_info['to_email']}, {original_sent_info['subject']}")
#     print("="*50 + "\n")

#     # Example: Decide whether to follow up further or not
#     # In a real application, you might analyze the 'body' to make this decision.
#     if "thanks" in body.lower() or "got it" in body.lower():
#         print("Reply indicates acknowledgement. No further follow-up needed for this conversation.")
#         # The system will automatically stop tracking this email, as a reply was detected.
#     else:
#         print("Reply received, but further action might be needed based on content.")
#         # If the reply is incomplete, you might want to manually re-add it or trigger
#         # a new task based on its content, *outside* the automatic follow-up logic.


# def main():

#     {'user':os.getenv("GMAIL_USER"), 'passwd':os.getenv("GMAIL_PASS")}
#     EMAIL_CONFIG = {
#         'smtp_server': 'smtp.gmail.com',
#         'smtp_port': 587,
#         'imap_server': 'imap.gmail.com',
#         'imap_port': 993,
#         'email_address': os.getenv("GMAIL_USER"),  # Replace with your email
#         'password': os.getenv("GMAIL_PASS") # Replace with your app password
#     }
    
#     # Create email system instance
#     email_system = EmailFollowUpSystem(**EMAIL_CONFIG)
    
#     # Register the callback function
#     email_system.register_reply_callback(my_reply_handler)
    
#     # Start monitoring system
#     email_system.start_monitoring()
    
#     # Send an email with follow-up
#     # Set a very short timeout for quick testing (e.g., 0.001 hours = ~3.6 seconds)
#     email_system.send_with_followup(
#         to_email='adityagaur.home@gmail.com', # Replace with a test email you can reply from
#         subject='Important Meeting Request - Test',
#         message='Hello,\n\nI would like to schedule a meeting with you next week. Please let me know your availability.\n\nBest regards',
#         timeout_hours=0.001 
#     )
    




# if __name__ == "__main__":
#     main()