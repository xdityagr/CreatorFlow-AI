import smtplib
import imaplib
import email
import time
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import threading
import logging
from email.utils import make_msgid, parsedate_to_datetime
import pytz 
import re 
from .aiengine import MasterLLM

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailFollowUpSystem:
    def __init__(self, smtp_server, smtp_port, imap_server, imap_port, email_address, password):
        """
        Initialize the email follow-up system
        
        Args:
            smtp_server: SMTP server address (e.g., 'smtp.gmail.com')
            smtp_port: SMTP port (e.g., 587 for TLS)
            imap_server: IMAP server address (e.g., 'imap.gmail.com')
            imap_port: IMAP port (e.g., 993 for SSL)
            email_address: Your email address
            password: Your email password or app password
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email_address = email_address
        self.password = password
        self.pending_emails = {}  # Store pending follow-ups
        self.running = False
        self.monitor_thread = None
        self.reply_callback = None # To store the callback function for replies
        
    def register_reply_callback(self, callback_func):
        """
        Register a callback function to be called when a reply is received.
        The callback function should accept (sender_email, subject, body, original_sent_info) as arguments.
        """
        if callable(callback_func):
            self.reply_callback = callback_func
            logger.info("Reply callback function registered.")
        else:
            logger.error("Provided callback is not callable.")

    def _extract_email_body(self, email_message):
        """Extracts the plain text body from an email message."""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                ctype = part.get_content_type()
                cdisposition = part.get('Content-Disposition')

                # Look for plain text parts that are not attachments
                if ctype == 'text/plain' and 'attachment' not in (cdisposition or ''):
                    try:
                        charset = part.get_content_charset()
                        body = part.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
                        break # Found the plain text body, no need to look further
                    except Exception as e:
                        logger.warning(f"Error decoding email part: {e}")
        else:
            # Not a multipart email, assume it's plain text
            try:
                charset = email_message.get_content_charset()
                body = email_message.get_payload(decode=True).decode(charset or 'utf-8', errors='ignore')
            except Exception as e:
                logger.warning(f"Error decoding single-part email: {e}")
        
        # Clean up common reply prefixes/signatures
        body = re.split(r'On .* wrote:|-----Original Message-----|From:.*Sent:.*To:.*Subject:|\[Quoted text hidden\]', body, 1)[0].strip()
        return body

    def send_email(self, to_email, subject, message, is_followup=False, in_reply_to_mid=None):
        """Send an email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_email
            
            message_id = make_msgid(domain=self.email_address.split('@')[1]) # Use sender's domain
            msg['Message-ID'] = message_id

            if is_followup:
                msg['Subject'] = f"Follow-up: {subject}"
                follow_up_text = f"\n\n--- Follow-up ---\nThis is a follow-up to my previous email. Please let me know if you received this.\n\n"
                message = follow_up_text + message
                if in_reply_to_mid:
                    msg['In-Reply-To'] = in_reply_to_mid
                    msg['References'] = in_reply_to_mid 
            else:
                msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_address, self.password)
            
            text = msg.as_string()
            server.sendmail(self.email_address, to_email, text)
            server.quit()
            print('sent')
            
            logger.info(f"Email sent to {to_email} - Subject: {subject}")
            return True, message_id
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False, None
    
    def check_for_reply(self, to_email, original_subject, sent_time_utc, original_message_id):
        """
        Check if there's a reply from the recipient.
        Returns (True, subject, body) if a reply is found, otherwise (False, None, None).
        """
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            mail.select('inbox')
            
            search_criteria = f'(FROM "{to_email}")'
            result, data = mail.search(None, search_criteria)
            
            logger.info(f"Searching for replies from {to_email} after {sent_time_utc} (Original Message-ID: {original_message_id})")
            
            if result == 'OK' and data[0]:
                email_ids = data[0].split()
                logger.info(f"Found {len(email_ids)} total emails from {to_email}")
            
                
                for email_id in reversed(email_ids):
                    try:
                        result, msg_data = mail.fetch(email_id, '(RFC822)')
                        if result == 'OK':
                            email_message = email.message_from_bytes(msg_data[0][1])
                            
                            date_header = email_message.get('Date')
                            if date_header:
                                try:
                                    email_date = parsedate_to_datetime(date_header)
                                    if email_date.tzinfo is None:
                                        email_date = pytz.utc.localize(email_date) 
                                    else:
                                        email_date = email_date.astimezone(pytz.utc)

                                    logger.debug(f"Parsed email date (UTC): {email_date}") # Changed to debug
                                    
                                except Exception as e:
                                    logger.error(f"Date parsing error for email {email_id}: {e}")
                                    continue
                            else:
                                logger.debug(f"Skipping email {email_id} - No Date header found.") # Changed to debug
                                continue
                            
                            subject_header = email_message.get('Subject', '')
                            try:
                                decoded_subject = decode_header(subject_header)
                                subject = ''
                                for part, encoding in decoded_subject:
                                    if isinstance(part, bytes):
                                        subject += part.decode(encoding or 'utf-8', errors='ignore')
                                    else:
                                        subject += str(part)
                            except:
                                subject = str(subject_header)
                            
                            logger.info(f"Checking email - Date: {email_date}, Subject: {subject}")
                            
                            if email_date > sent_time_utc: 
                                logger.info(f"✅ Found email AFTER sent time from {to_email}: {subject}")
                                
                                in_reply_to = email_message.get('In-Reply-To', '')
                                references = email_message.get('References', '')
                                
                                is_reply = False
                                if original_message_id:

                                    if original_message_id in in_reply_to.split() or original_message_id in references.split():
                                        is_reply = True
                                        logger.info(f"🎉 REPLY DETECTED (Message-ID header) from {to_email}: {subject}")
                                    else:
                                        logger.info(f"Message-ID '{original_message_id}' not found in In-Reply-To or References headers.")

                                if not is_reply: # Only do subject fallback if Message-ID didn't match
                                    subject_lower = subject.lower()
                                    original_lower = original_subject.lower()
                                    
                                    clean_subject = subject_lower
                                    for prefix in ['re:', 'fwd:', 'fw:']:
                                        if clean_subject.startswith(prefix):
                                            clean_subject = clean_subject[len(prefix):].strip()
                                    
                                    if ('re:' in subject_lower and original_lower in clean_subject) or \
                                       (original_lower in clean_subject and len(clean_subject) >= len(original_lower) * 0.7):
                                        is_reply = True
                                        logger.info(f"🎉 REPLY DETECTED (Subject fallback) from {to_email}: {subject}")

                                if is_reply:
                                    reply_body = self._extract_email_body(email_message)
                                    mail.close()
                                    mail.logout()
                                    return True, subject, reply_body
                                else:
                                    logger.info(f"❌ Not a reply to our specific email - no matching Message-ID or strong subject correlation.")
                            else:
                                logger.info(f"⏰ Email {email_id} is older than or same as our sent time ({email_date} vs {sent_time_utc}) - skipping for further check.")

                    except Exception as e:
                        logger.error(f"Error processing email {email_id}: {str(e)}")
                        continue
            else:
                logger.info(f"No emails found from {to_email} matching search criteria.")
            
            mail.close()
            mail.logout()
            return False, None, None
            
        except Exception as e:
            logger.error(f"Failed to check for reply from {to_email}: {str(e)}")
            return False, None, None
    
    def send_with_followup(self, to_email, subject, message, timeout_hours=24):
        """
        Send an email and schedule a follow-up if no reply is received
        
        Args:
            to_email: Recipient's email address
            subject: Email subject
            message: Email message
            timeout_hours: Hours to wait before sending follow-up (default: 24)
        """
        print('sending...')
        success, message_id = self.send_email(to_email, subject, message)
        if success:
            sent_time_utc = datetime.datetime.now(pytz.utc)
            
            email_key = f"{to_email}_{subject}_{sent_time_utc.timestamp()}"
            self.pending_emails[email_key] = {
                'to_email': to_email,
                'subject': subject,
                'message': message,
                'sent_time_utc': sent_time_utc,
                'timeout_hours': timeout_hours,
                'followup_sent': False,
                'original_message_id': message_id
            }
            
            logger.info(f"Email scheduled for follow-up tracking: {to_email} (Sent UTC: {sent_time_utc})")
            return True
        return False
    
    def monitor_replies(self):
        """Monitor for replies and send follow-ups as needed"""
        while self.running:
            current_time_utc = datetime.datetime.now(pytz.utc)
            emails_to_remove = []
            
            # Make a copy of keys to iterate over, allowing dictionary modification
            for email_key in list(self.pending_emails.keys()):
                email_info = self.pending_emails.get(email_key)
                if not email_info: # If item was removed by another iteration
                    continue

                to_email = email_info['to_email']
                subject = email_info['subject']
                message = email_info['message']
                sent_time_utc = email_info['sent_time_utc']
                timeout_hours = email_info['timeout_hours']
                followup_sent = email_info['followup_sent']
                original_message_id = email_info.get('original_message_id')
                
                # 1. Check for reply
                # CORRECTED LINE: Assign the returned values
                is_reply_found, reply_subject, reply_body = self.check_for_reply(to_email, subject, sent_time_utc, original_message_id)
                
                if is_reply_found:
                    logger.info(f"🎉 Reply received from {to_email} for: {subject}")
                    
                    # Call the registered callback if it exists
                    if self.reply_callback:
                        try:
                            self.reply_callback(to_email, reply_subject, reply_body, email_info)
                        except Exception as cb_e:
                            logger.error(f"Error in reply callback: {cb_e}")
                    
                    emails_to_remove.append(email_key) # Remove from tracking after reply
                    continue
                
                # 2. If no reply, check timeout for follow-up
                time_diff = current_time_utc - sent_time_utc
                
                if time_diff.total_seconds() >= timeout_hours * 3600:
                    if not followup_sent:
                        logger.info(f"Timeout reached for {to_email} - {subject}. Sending follow-up.")
                        success, new_message_id = self.send_email(to_email, subject, message, is_followup=True, in_reply_to_mid=original_message_id)
                        if success:
                            logger.info(f"Follow-up sent to {to_email} for: {subject}")
                            # Update details for next check
                            self.pending_emails[email_key]['followup_sent'] = True
                            self.pending_emails[email_key]['sent_time_utc'] = current_time_utc 
                            self.pending_emails[email_key]['original_message_id'] = new_message_id 
                        else:
                            logger.warning(f"Failed to send follow-up to {to_email}. Removing from tracking.")
                            emails_to_remove.append(email_key)
                    else:
                        # If follow-up was sent, and still no reply after another 'timeout_hours' period
                        if time_diff.total_seconds() >= (timeout_hours * 2) * 3600:  # e.g., 2 * 24 hours
                            logger.info(f"No reply received from {to_email} after follow-up period. Removing from tracking.")
                            emails_to_remove.append(email_key)
            
            for email_key in emails_to_remove:
                if email_key in self.pending_emails:
                    del self.pending_emails[email_key]
            
            time.sleep(30) # Check every 30 seconds

    def start_monitoring(self):
        """Start the email monitoring system in a separate thread"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_replies, name="EmailMonitorThread")
            self.monitor_thread.daemon = True # Allows program to exit even if thread is running
            self.monitor_thread.start()
            logger.info("Email monitoring system started")
        else:
            logger.info("Email monitoring system is already running.")
    
    def stop_monitoring(self):
        """Stop the email monitoring system"""
        if self.running:
            logger.info("Stopping email monitoring system...")
            self.running = False
            if self.monitor_thread and self.monitor_thread.is_alive():
                # Give a short time for the thread to gracefully shut down
                self.monitor_thread.join(timeout=5) 
                if self.monitor_thread.is_alive():
                    logger.warning("Email monitoring thread did not terminate gracefully.")
            logger.info("Email monitoring system stopped.")
        else:
            logger.info("Email monitoring system is not running.")
    
    def get_pending_emails(self):
        """Get list of emails pending follow-up (for external status checks)"""
        # Return a copy to prevent modification issues while iterating
        return list(self.pending_emails.values()) 

llm =MasterLLM()
def my_reply_handler(sender_email, subject, body, original_sent_info):
    """
    This function will be called when a reply is detected.
    It acts as the "signal" receiver.
    """
    print("\n" + "="*50)
    print(f"🎉 REPLY SIGNAL RECEIVED! 🎉")
    print(f"From: {sender_email}")
    print(f"Subject: {subject}") # Print the received subject
    print(f"Body snippet:\n{body[:200]}...") # Print first 200 chars of the received body
    print(f"Original email sent info: {original_sent_info['to_email']}, {original_sent_info['subject']}")
    print("="*50 + "\n")
    print('User replied, processing with llm now. ')
    llm.feature_checkInfluencerContact(subject, body)
    

def main():
    # Configuration for Gmail (you'll need to use app passwords for Gmail)
    EMAIL_CONFIG = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'imap_server': 'imap.gmail.com',
        'imap_port': 993,
        'email_address': 'nextfluence.ai@gmail.com',  # Replace with your email
        'password': 'rhsc moao ccgs dahr'  # Replace with your app password
    }
    
    # Create email system instance
    email_system = EmailFollowUpSystem(**EMAIL_CONFIG)
    
    # Register the callback function
    email_system.register_reply_callback(my_reply_handler)
    
    # Start monitoring system
    email_system.start_monitoring()
    

    email_system.send_with_followup(
        to_email='adityagaur.home@gmail.com', # Replace with a test email you can reply from
        subject='Important Meeting Request - Test',
        message='Hello,\n\nI would like to schedule a meeting with you next week. Please let me know your availability.\n\nBest regards',
        timeout_hours=24
    )
    
    # Keep the program running in the main thread
    try:
        while True:
            # You can check pending emails from here too, for UI updates or other logic
            pending_count = len(email_system.get_pending_emails())
            if pending_count > 0:
                logger.info(f"Currently tracking {pending_count} emails for follow-up")
            else:
                logger.info("No emails currently being tracked for follow-up.")
            time.sleep(10) # Check status every 10 seconds
    except KeyboardInterrupt:
        logger.info("Ctrl+C detected. Shutting down email system...")
        email_system.stop_monitoring() # Call stop_monitoring for graceful shutdown
        print("Main program exiting.")


if __name__ == "__main__":
    main()
