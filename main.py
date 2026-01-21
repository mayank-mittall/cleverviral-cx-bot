import os
import re
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

# ============================================
# CONFIGURATION - USING ENVIRONMENT VARIABLES
# ============================================

# Get values from environment variables (secure!)
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CALENDLY_LINK = os.environ.get("CALENDLY_LINK", "https://calendly.com/mayank-cleverviral/30min")
NOTION_FORM_LINK = os.environ.get("NOTION_FORM_LINK", "https://cleverviral.notion.site/2ef95faff36c80a29755e31b12bd5e9a?pvs=105")
HANDOFF_TEAM_MEMBER = os.environ.get("HANDOFF_TEAM_MEMBER", "@Mayank M")

# ============================================
# FAQ KNOWLEDGE BASE
# ============================================

FAQ_RESPONSES = {
    "login": """To access your dashboard:
1. Go to gtm.cleverviral.co
2. Use the email invite we sent
3. Check your inbox for login credentials

If you're having trouble logging in, let me know and I'll help!""",

    "master inbox": """To access and respond to leads via Master Inbox:
1. Login to gtm.cleverviral.co
2. Click 'Master Inbox' in the left menu
3. You'll see all positive replies here
4. Click any conversation to respond directly

The Master Inbox is your central hub for managing all lead responses!""",

    "dashboard": """Your Campaign Dashboard shows:
• Active campaigns and their status
• Reply statistics (positive/neutral/negative)
• Response rates and EPR metrics
• Lead quality insights
• Campaign performance trends

Access it anytime at: gtm.cleverviral.co/dashboard""",

    "positive reply": """Positive replies include:
• 'Yes, interested'
• 'Tell me more'
• 'Let's schedule a call'
• Meeting requests
• Questions about your service
• Requests for case studies or demos

You'll see these in your Master Inbox and get notifications in your live_responses channel!""",

    "how to respond": """To respond to a positive lead:
1. Go to gtm.cleverviral.co and login
2. Navigate to Master Inbox
3. Click on the conversation
4. Type your response
5. Click Send

The system will CC your email so you can continue the conversation from your primary inbox if needed.""",

    "reporting": """You receive updates on:
• Weekly campaign launch updates (Mondays 9am ET)
• Weekly performance summaries (Fridays 5pm ET)
• Monthly detailed reports (1st of month)

All reports are posted right here in Slack, plus you can access live reports in the dashboard anytime!""",

    "campaign performance": """To check campaign performance:
1. Login to gtm.cleverviral.co
2. View the live report link shared in Slack
3. Check the monthly report (shared 1st of each month)

Key metrics include:
• Email sends
• Reply rate
• Positive reply rate (EPR)
• Campaign-specific performance

If you'd like a detailed breakdown, just ask!""",

    "new campaign": """To submit a new campaign idea:
1. Type /new-campaign in this channel
2. Fill out the Notion form with:
   • Target audience/ICP
   • Campaign objectives
   • Messaging direction
   • Timeline expectations

We typically launch new campaigns within 3-5 business days after submission!""",

    "deliverability": """We monitor deliverability closely and take proactive steps:
• Regular inbox infrastructure updates
• AI spam filter optimization
• Bounce rate monitoring
• Reply rate tracking

If you notice any issues with email delivery, we're on it! Our team constantly maintains and optimizes the infrastructure to ensure maximum deliverability.""",

    "response time": """Our typical response times:
• General questions: Within 4 hours (business hours)
• Technical issues: Within 2 hours
• Campaign requests: 3-5 business days
• Urgent matters: Tag us with @team and we'll prioritize!

We're in IST timezone but monitor Slack throughout the day.""",

    "meeting": """To book a meeting with us:
• Just ask to schedule a call in this channel
• Or use our Calendly link: https://calendly.com/mayank-cleverviral/30min
• Pick a time that works for you

We're happy to discuss strategy, performance, or answer any questions!""",

    "negative replies": """We handle negative replies automatically:
• 'Not interested' responses are tracked but not re-engaged
• Unsubscribe requests are honored immediately
• Angry responses are flagged for team review

Negative replies help us refine targeting and messaging over time.""",

    "dnc": """DNC (Do Not Contact) list updates:
• We request updated lists monthly
• Submit your DNC list via the form we send
• We exclude these contacts immediately
• Helps maintain deliverability and reputation

If you have contacts to add to DNC, share them anytime!""",

    "infrastructure": """Our infrastructure includes:
• Multiple email sending platforms
• Regular inbox warmup and rotation
• Private SMTP servers for better control
• AI-optimized messaging for spam filters

We continuously upgrade infrastructure to maintain high deliverability rates.""",

    "channels": """You have access to 2 Slack channels:

1. **[clientname]_cleverviral** (this channel)
   • Team communication
   • Campaign discussions
   • Questions and support
   • Performance updates

2. **[clientname]_live_responses**
   • Real-time positive lead notifications
   • See leads as they come in
   • Quick response monitoring

All updates and notifications happen in these channels!""",

    "help": """I can help you with:
• Login and dashboard access
• Understanding your Master Inbox
• Campaign performance and metrics
• Scheduling calls with the team
• Submitting new campaign ideas (/new-campaign)
• General questions about the process

Just ask your question, and I'll do my best to help! If I can't answer, I'll loop in the team immediately."""
}

# Keywords that trigger calendar sharing
MEETING_KEYWORDS = ["call", "meeting", "schedule", "connect", "talk", "discuss", "zoom", "meet"]

# ============================================
# SLACK BOT SETUP
# ============================================

app = App(token=SLACK_BOT_TOKEN)
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# ============================================
# FEATURE 1: WELCOME MESSAGES
# ============================================

@app.event("member_joined_channel")
def handle_member_joined(event, say, client):
    """Send welcome message when new member joins"""
    
    user_id = event["user"]
    channel_id = event["channel"]
    
    # Get channel info to determine which message to send
    channel_info = client.conversations_info(channel=channel_id)
    channel_name = channel_info["channel"]["name"]
    
    # Get user info for personalization
    user_info = client.users_info(user=user_id)
    user_name = user_info["user"]["real_name"]
    
    # Determine message based on channel type
    if "live_responses" in channel_name:
        message = f"""Hey <@{user_id}>! 👋

Welcome to the **Live Responses** channel!

This is where you'll see all the **positive replies** from your email campaigns in real-time. 

**To respond to leads:**
1. Login to gtm.cleverviral.co
2. Go to "Master Inbox"
3. Click on any conversation to reply

You'll get notifications here whenever someone shows interest! 🎯"""
    
    else:  # Main cleverviral channel
        message = f"""Hey <@{user_id}>! 👋

Welcome to your CleverViral team channel!

**This channel is for:**
• Campaign discussions & feedback
• Sharing copy ideas
• Performance updates
• Questions & support

**Quick links:**
• Dashboard: gtm.cleverviral.co
• Master Inbox: gtm.cleverviral.co/inbox
• New Campaign: Type `/new-campaign`
• Schedule Call: Just ask to connect!

I'm your CX bot - ask me anything! 🤖"""
    
    say(text=message, channel=channel_id)

# ============================================
# FEATURE 2: BASIC FAQ
# ============================================

def find_faq_match(message_text):
    """Check if message matches any FAQ keyword"""
    message_lower = message_text.lower()
    
    # Check each FAQ keyword
    for keyword, response in FAQ_RESPONSES.items():
        if keyword in message_lower:
            return response
    
    return None

# ============================================
# FEATURE 3: CALENDAR SHARING
# ============================================

def should_share_calendar(message_text):
    """Check if message contains meeting-related keywords"""
    message_lower = message_text.lower()
    return any(keyword in message_lower for keyword in MEETING_KEYWORDS)

# ============================================
# FEATURE 4: CAMPAIGN FORM (Slash Command)
# ============================================

@app.command("/new-campaign")
def handle_new_campaign(ack, say, command):
    """Handle /new-campaign slash command"""
    ack()  # Acknowledge the command
    
    user_id = command["user_id"]
    
    message = f"""Hey <@{user_id}>! 🚀

Ready to launch a new campaign? Please fill out this form with your campaign details:

👉 {NOTION_FORM_LINK}

**What we need:**
• Target audience/ICP
• Campaign objectives
• Messaging direction
• Timeline expectations

Once submitted, we'll review and get back to you within 3-5 business days!"""
    
    say(text=message, channel=command["channel_id"])

# ============================================
# FEATURE 5 & 6: MESSAGE HANDLER (FAQ + Handoff)
# ============================================

@app.message(re.compile(".*"))
def handle_message(message, say):
    """Process all channel messages for FAQ and calendar triggers"""
    
    # Ignore bot's own messages
    if message.get("bot_id"):
        return
    
    message_text = message.get("text", "")
    channel_id = message["channel"]
    user_id = message["user"]
    
    # Check for FAQ match first
    faq_response = find_faq_match(message_text)
    if faq_response:
        say(text=faq_response, channel=channel_id)
        return
    
    # Check if should share calendar
    if should_share_calendar(message_text):
        calendar_message = f"""Happy to connect! 📅

Here's my calendar - pick a time that works for you:
{CALENDLY_LINK}

Looking forward to chatting!"""
        say(text=calendar_message, channel=channel_id)
        return
    
    # If message seems like a question but no FAQ match, trigger human handoff
    if "?" in message_text or any(word in message_text.lower() for word in ["help", "issue", "problem", "not working"]):
        handoff_message = f"""Got it! Let me loop in the team to help with that.

{HANDOFF_TEAM_MEMBER} - could you assist <@{user_id}> with their question? 🙏

We'll get back to you ASAP!"""
        say(text=handoff_message, channel=channel_id)

# ============================================
# FLASK ROUTES FOR SLACK EVENTS
# ============================================

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events"""
    return handler.handle(request)

@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handle Slack slash commands"""
    return handler.handle(request)

@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return "Bot is running! 🤖", 200

@flask_app.route("/", methods=["GET"])
def home():
    """Home route"""
    return "CleverViral CX Bot is alive! 🤖✅", 200

# ============================================
# RUN THE BOT
# ============================================

if __name__ == "__main__":
    print("🤖 CleverViral CX Bot is starting...")
    print("✅ Bot is ready and listening for events!")
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)
