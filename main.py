import os
import re
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify

# ============================================
# CONFIGURATION
# ============================================

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
CALENDLY_LINK = os.environ.get("CALENDLY_LINK", "https://calendly.com/mayank-cleverviral/30min")
NOTION_FORM_LINK = os.environ.get("NOTION_FORM_LINK", "https://cleverviral.notion.site/2ef95faff36c80a29755e31b12bd5e9a?pvs=105")

# Team member IDs
TEAM_MEMBERS = {
    "hassan": "U04Q9SG853P",
    "rish": "U046PBV7QBT",
    "sahil": "U07RMKN25MY",
    "chetan": "U06RX4KQ8LX",
    "suraj": "U04UR5DBFGT",
}

INTERNAL_TEAM_IDS = list(TEAM_MEMBERS.values())
DEFAULT_HANDOFF = TEAM_MEMBERS["hassan"]

# ============================================
# INITIALIZATION
# ============================================

bot = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

app = Flask(__name__)
handler = SlackRequestHandler(bot)
handled_threads = set()

# ============================================
# QUESTION TYPE ROUTING
# ============================================

QUESTION_ROUTING = {
    "campaigns": {
        "team_member": TEAM_MEMBERS["hassan"],
        "keywords": ["campaign", "send", "sending", "performance", "report", "results", "metrics", "epr", "positive reply", "reply rate", "statistics", "stats"]
    },
    "copy": {
        "team_member": TEAM_MEMBERS["rish"],
        "keywords": ["copy", "copywriting", "messaging", "email copy", "subject line", "strategy", "approach", "angle", "value prop"]
    },
    "targeting": {
        "team_member": TEAM_MEMBERS["sahil"],
        "keywords": ["data", "targeting", "audience", "icp", "leads", "list", "contacts", "prospects"]
    },
    "deliverability": {
        "team_member": TEAM_MEMBERS["chetan"],
        "keywords": ["deliverability", "inbox", "spam", "email signature", "bounce", "sender", "domain", "infrastructure"]
    },
    "automation": {
        "team_member": TEAM_MEMBERS["suraj"],
        "keywords": ["automation", "autoresponder", "auto reply", "cc", "forward", "clever responder", "automated"]
    }
}

def detect_question_type(message_text):
    """Detect question type for routing"""
    message_lower = message_text.lower()
    
    for category, config in QUESTION_ROUTING.items():
        if any(keyword in message_lower for keyword in config["keywords"]):
            return config["team_member"], category
    
    return DEFAULT_HANDOFF, "general"

# ============================================
# HELPER FUNCTIONS
# ============================================

def is_internal_team_member(user_id):
    return user_id in INTERNAL_TEAM_IDS

def format_link(url, text):
    return f"<{url}|{text}>"

def has_team_replied_in_thread(channel_id, thread_ts):
    try:
        result = bot.client.conversations_replies(channel=channel_id, ts=thread_ts)
        if not result["ok"]:
            return False
        
        messages = result.get("messages", [])
        for msg in messages[1:]:
            user_id = msg.get("user")
            if user_id and is_internal_team_member(user_id):
                return True
        return False
    except Exception as e:
        print(f"Error checking thread replies: {e}")
        return False

def get_thread_key(channel_id, thread_ts):
    return f"{channel_id}:{thread_ts}"

def is_needs_response(message_text):
    """
    Determine if message needs a response
    Includes: questions, complaints, concerns, requests
    Excludes: short acknowledgments, thanks, casual chat
    """
    message_lower = message_text.lower().strip()
    
    # Short acknowledgments that don't need responses
    short_acks = [
        "thanks", "thank you", "ty", "thx",
        "ok", "okay", "k",
        "got it", "sounds good", "perfect", "great", "nice",
        "yes", "no", "yep", "nope", "sure"
    ]
    
    # If message is just a short acknowledgment, don't respond
    if message_lower in short_acks:
        return False
    
    # If very short (under 10 chars) and no question mark, probably not meaningful
    if len(message_text) < 10 and "?" not in message_text:
        return False
    
    # Questions - always respond
    has_question_mark = "?" in message_text
    question_starters = [
        "how", "what", "when", "where", "why", "who", "which",
        "can you", "could you", "would you", "do you", "does", "did",
        "is there", "are there", "will you", "have you", "has",
        "am i", "are we", "is it", "should i", "should we", "can we", "can i"
    ]
    starts_with_question = any(message_lower.startswith(starter) for starter in question_starters)
    
    # Complaints/concerns - always respond
    concern_words = [
        "bad", "terrible", "awful", "trash", "horrible", "poor",
        "not working", "broken", "issue", "problem", "concerned",
        "worried", "disappointing", "disappointed", "frustrated",
        "low", "down", "dropping", "declined", "worse"
    ]
    has_concern = any(word in message_lower for word in concern_words)
    
    # Requests - always respond
    request_phrases = [
        "need to", "want to", "would like", "can we", "could we",
        "let's", "we should", "please", "help"
    ]
    has_request = any(phrase in message_lower for phrase in request_phrases)
    
    return has_question_mark or starts_with_question or has_concern or has_request

# ============================================
# FAQ RESPONSES - ACTUAL QUESTIONS ONLY
# ============================================

FAQ_DATABASE = [
    {
        "question_patterns": [
            "how can i see reporting",
            "how do i see the report",
            "where is the report",
            "how can i check performance",
            "how do i check the numbers",
            "where can i see results",
            "how to see campaign performance",
            "where are the metrics"
        ],
        "answer": "You can see reporting in a few ways:\n• Weekly summaries posted here every Friday\n• Monthly reports on the 1st of each month\n• Live reports via the Google Sheets link we share\n\nWant specific numbers? The team can pull exact data.",
        "category": "campaigns"
    },
    {
        "question_patterns": [
            "can't login",
            "cannot login",
            "can't access dashboard",
            "login not working",
            "how do i login",
            "how to access dashboard",
            "forgot password",
            "need login credentials",
            "dashboard login"
        ],
        "answer": "For dashboard access:\n• Check your email for login credentials\n• Make sure you're using the correct URL\n• Try resetting your password\n\nThe team can resend credentials or help you get in.",
        "category": "general"
    },
    {
        "question_patterns": [
            "how many emails sent",
            "how many emails have we sent",
            "what's the email volume",
            "total emails sent",
            "email send count",
            "how many sent this month"
        ],
        "answer": "Email volumes are in:\n• Weekly summaries (Fridays)\n• Monthly reports (1st of month)\n• Live Google Sheets report\n\nWant the current count? Team can pull exact numbers.",
        "category": "campaigns"
    },
    {
        "question_patterns": [
            "why so low",
            "why are results low",
            "why only few responses",
            "why not more replies",
            "response rate low",
            "why so few positives"
        ],
        "answer": "Low response rates can happen due to:\n• List quality and targeting\n• Messaging fit\n• Deliverability issues\n• Timing/seasonality\n\nThe team will analyze your campaign and identify what to optimize.",
        "category": "campaigns"
    },
    {
        "question_patterns": [
            "when will campaign launch",
            "when does it go live",
            "when will we start",
            "launch timeline",
            "when will it begin",
            "how long until launch"
        ],
        "answer": "New campaigns typically launch within 3-5 business days after strategy is finalized. We'll notify you here once it's live.",
        "category": "campaigns"
    },
    {
        "question_patterns": [
            "how do i respond to leads",
            "how to reply to leads",
            "where do i respond",
            "how to answer positive replies",
            "where is master inbox",
            "how to access inbox"
        ],
        "answer": "To respond to leads:\n1. Access Master Inbox via dashboard\n2. All positive replies show up there\n3. Click any conversation to reply\n\nYou can also respond from your email when we CC you.",
        "category": "campaigns"
    },
    {
        "question_patterns": [
            "can we pause",
            "how to stop campaign",
            "need to pause",
            "can we turn off",
            "stop sending",
            "deactivate campaign"
        ],
        "answer": "To pause a campaign, let the team know which one. We'll deactivate it within 24 hours and confirm here.",
        "category": "campaigns"
    },
    {
        "question_patterns": [
            "can we change targeting",
            "who are we targeting",
            "can we target different audience",
            "change the icp",
            "target different people",
            "who should we reach"
        ],
        "answer": "We target based on the ICP from onboarding. Want to refine targeting or test a new audience? Use `/new-campaign` or discuss with the team.",
        "category": "targeting"
    },
    {
        "question_patterns": [
            "can we change the copy",
            "update the messaging",
            "change email copy",
            "new message",
            "different copy",
            "revise the emails"
        ],
        "answer": "All copy is written and reviewed by our team. Want to test new messaging? The team can walk you through the process and implement changes.",
        "category": "copy"
    },
    {
        "question_patterns": [
            "emails going to spam",
            "landing in spam",
            "deliverability issue",
            "not landing in inbox",
            "emails not delivered",
            "spam folder"
        ],
        "answer": "We actively monitor deliverability with regular infrastructure updates. If you're seeing delivery issues, the team will investigate and make adjustments.",
        "category": "deliverability"
    }
]

def find_faq_match(message_text):
    """Match message to FAQ - ONLY if it needs a response"""
    if not is_needs_response(message_text):
        return None
    
    message_lower = message_text.lower()
    
    for faq in FAQ_DATABASE:
        for pattern in faq["question_patterns"]:
            if pattern in message_lower:
                return {
                    "answer": faq["answer"],
                    "category": faq["category"]
                }
    
    return None

# Meeting keywords - EXPANDED for better matching
MEETING_KEYWORDS = [
    # Core meeting words
    "call", "meeting", "schedule", "connect", "talk", "discuss",
    "zoom", "meet", "chat", "catch up", "sync",
    
    # Time blocking phrases
    "block time", "block a time", "block some time", "grab time", 
    "grab some time", "find time", "find a time", "find some time",
    "carve out time", "set aside time",
    
    # Availability
    "available", "free time", "when are you free", "when can we",
    
    # Booking/scheduling
    "book", "booking", "appointment", "slot", "calendly",
    
    # Action phrases  
    "can we meet", "let's talk", "get on a call", "hop on", 
    "quick call", "quick chat", "quick sync", "touch base"
]

# ============================================
# ONBOARDING COMMANDS (MANUAL, TEAM ONLY)
# ============================================

@bot.command("/pip-onboard")
def handle_onboard_main(ack, say, command):
    """Team uses this to send main channel welcome"""
    ack()
    
    # Only team members can use this
    user_id = command["user_id"]
    if not is_internal_team_member(user_id):
        say("This command is only available to the CleverViral team.", ephemeral=True)
        return
    
    calendly_link = format_link(CALENDLY_LINK, "book a call")
    text = (
        f"Welcome.\n\n"
        f"This is your primary channel with the CleverViral team. "
        f"We'll discuss strategy, share updates, and collaborate on campaigns here.\n\n"
        f"**Quick actions:**\n"
        f"• Need a new campaign? Use `/new-campaign`\n"
        f"• Want to {calendly_link} with the team\n\n"
        f"I'm Pip. Ask me anything you need."
    )
    
    say(text=text)

@bot.command("/pip-onboard-live")
def handle_onboard_live(ack, say, command):
    """Team uses this to send live_responses welcome"""
    ack()
    
    # Only team members can use this
    user_id = command["user_id"]
    if not is_internal_team_member(user_id):
        say("This command is only available to the CleverViral team.", ephemeral=True)
        return
    
    text = (
        f"Welcome.\n\n"
        f"This channel shows real-time notifications of positive replies from your campaigns. "
        f"You can respond to leads via your Master Inbox (accessible from your dashboard).\n\n"
        f"We'll notify you here whenever someone shows interest."
    )
    
    say(text=text)

# ============================================
# MESSAGE HANDLER
# ============================================

@bot.message(".*")
def handle_message(message, say, client):
    """Handle messages - only respond to ACTUAL questions"""
    
    if "bot_id" in message:
        return
    
    user_id = message.get("user")
    message_text = message.get("text", "")
    message_ts = message.get("ts")
    channel_id = message.get("channel")
    thread_ts = message.get("thread_ts", message_ts)
    
    # Ignore internal team
    if is_internal_team_member(user_id):
        print(f"Ignoring message from team member: {user_id}")
        return
    
    # Check if thread already handled
    thread_key = get_thread_key(channel_id, thread_ts)
    if thread_key in handled_threads:
        print(f"Thread already handled: {thread_key}")
        return
    
    # Check if team already replied in thread
    if thread_ts != message_ts:
        if has_team_replied_in_thread(channel_id, thread_ts):
            print(f"Team already replied in thread: {thread_key}")
            handled_threads.add(thread_key)
            return
    
    # CRITICAL: Only proceed if this needs a response
    if not is_needs_response(message_text):
        print(f"Doesn't need response, ignoring: {message_text[:50]}")
        return
    
    # React with hourglass
    try:
        client.reactions_add(
            channel=channel_id,
            timestamp=message_ts,
            name="hourglass_flowing_sand"
        )
    except Exception as e:
        print(f"Error adding reaction: {e}")
    
    handled_threads.add(thread_key)
    
    # Detect question type for routing
    team_member_id, question_category = detect_question_type(message_text)
    
    # Check for meeting keywords FIRST (before FAQ)
    message_lower = message_text.lower()
    
    # Better keyword matching - check if ANY keyword is in message
    is_meeting_request = False
    for keyword in MEETING_KEYWORDS:
        if keyword in message_lower:
            is_meeting_request = True
            break
    
    if is_meeting_request:
        calendly_link = format_link(CALENDLY_LINK, "here")
        text = f"Hey <@{user_id}>, grab a time {calendly_link}. Looping in <@{team_member_id}> as well."
        
        try:
            client.reactions_remove(channel=channel_id, timestamp=message_ts, name="hourglass_flowing_sand")
            client.reactions_add(channel=channel_id, timestamp=message_ts, name="white_check_mark")
        except:
            pass
        
        say(text=text, thread_ts=thread_ts)
        return
    
    # Check for FAQ match
    faq_match = find_faq_match(message_text)
    if faq_match:
        answer = faq_match.get("answer", "")
        faq_category = faq_match.get("category", "general")
        
        # Get appropriate team member based on FAQ category
        if faq_category != "general":
            for cat_name, cat_config in QUESTION_ROUTING.items():
                if cat_name == faq_category:
                    team_member_id = cat_config["team_member"]
                    break
        
        text = f"Hey <@{user_id}>,\n\n{answer}\n\nLooping in <@{team_member_id}> on this one."
        
        try:
            client.reactions_remove(channel=channel_id, timestamp=message_ts, name="hourglass_flowing_sand")
            client.reactions_add(channel=channel_id, timestamp=message_ts, name="white_check_mark")
        except:
            pass
        
        say(text=text, thread_ts=thread_ts)
        return
    
    # No FAQ match - escalate
    text = f"Hey <@{user_id}>, looping in <@{team_member_id}> on this one."
    
    try:
        client.reactions_remove(channel=channel_id, timestamp=message_ts, name="hourglass_flowing_sand")
        client.reactions_add(channel=channel_id, timestamp=message_ts, name="eyes")
    except:
        pass
    
    say(text=text, thread_ts=thread_ts)

# ============================================
# SLASH COMMANDS
# ============================================

@bot.command("/new-campaign")
def handle_new_campaign(ack, body, say):
    ack()
    user_id = body["user_id"]
    
    form_link = format_link(NOTION_FORM_LINK, "this brief form")
    text = (
        f"Sounds like a start of a great idea. To make sure we capture all the necessary details, "
        f"please fill out {form_link}. We'll review and get back to you within 3-5 business days."
    )
    say(text=text)

# ============================================
# N8N WEBHOOK
# ============================================

@app.route("/n8n/transcript-summary", methods=["POST"])
def n8n_transcript_summary():
    data = request.json
    
    if not data or "summary" not in data or "channel" not in data:
        return jsonify({"status": "error", "message": "Invalid payload"}), 400
    
    summary = data["summary"]
    target_channel = data["channel"]
    
    try:
        bot.client.chat_postMessage(
            channel=target_channel,
            text=f"📞 **Call Summary**\n\n{summary}"
        )
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error posting to Slack: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================
# FLASK ROUTES
# ============================================

@app.route("/health", methods=["GET"])
def health_check():
    return "Pip is running 🐦", 200

@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)

# ============================================
# STARTUP
# ============================================

if __name__ == "__main__":
    print("🐦 Pip is starting...")
    print("✅ Pip is ready")
    
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
