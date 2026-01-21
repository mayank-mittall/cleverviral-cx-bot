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

def is_actual_question(message_text):
    """
    Determine if message is ACTUALLY a question
    Not just a statement with keywords
    """
    message_lower = message_text.lower().strip()
    
    # Must have question mark OR question words
    has_question_mark = "?" in message_text
    
    # Question starter words
    question_starters = [
        "how", "what", "when", "where", "why", "who", "which",
        "can you", "could you", "would you", "do you", "does", "did",
        "is there", "are there", "will you", "have you", "has",
        "am i", "are we", "is it", "should i", "should we"
    ]
    
    starts_with_question = any(message_lower.startswith(starter) for starter in question_starters)
    
    return has_question_mark or starts_with_question

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
        "answer": "You can see reporting in a few ways:\n• Weekly performance summaries posted here every Friday\n• Monthly detailed reports on the 1st of each month\n• Live reports via the Google Sheets link we share\n\nWant access to the live dashboard or need specific numbers? The team can help!",
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
        "answer": "For dashboard access issues:\n• Check your email for the original login credentials\n• Make sure you're using the correct dashboard URL\n• Try resetting your password\n\nThe team can resend credentials or help you get access!",
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
        "answer": "Email send volumes are included in:\n• Weekly summaries (posted Fridays)\n• Monthly reports (1st of month)\n• The live Google Sheets report\n\nWant the current count? The team can pull exact numbers for you!",
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
        "answer": "Low response rates can happen due to several factors:\n• List quality and targeting\n• Messaging and positioning\n• Deliverability issues\n• Industry/timing seasonality\n\nThe team will analyze your specific campaign and identify what to optimize!",
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
        "answer": "New campaigns typically launch within 3-5 business days after strategy is finalized. We'll notify you right here in this channel once it's live!",
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
        "answer": "To respond to positive leads:\n1. Access your Master Inbox via the dashboard\n2. All positive replies are automatically funneled there\n3. Click any conversation to reply directly\n\nYou can also respond from your email when we CC you on replies!",
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
        "answer": "To pause a campaign, just let the team know which specific campaign you'd like to pause. We'll deactivate it within 24 hours and confirm here!",
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
        "answer": "We target based on the ICP established during onboarding. Want to refine targeting or test a new audience? Use the `/new-campaign` command or discuss with the team!",
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
        "answer": "All email copy is written and reviewed by our team. Want to test new messaging or update copy? The team can walk you through the process and implement changes!",
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
        "answer": "We actively monitor deliverability with regular infrastructure updates and optimization. If you're noticing delivery issues, the team will investigate immediately and make adjustments!",
        "category": "deliverability"
    }
]

def find_faq_match(message_text):
    """
    Match message to FAQ - ONLY if it's actually a question
    """
    # First check: Is this even a question?
    if not is_actual_question(message_text):
        return None
    
    message_lower = message_text.lower()
    
    # Check each FAQ's question patterns
    for faq in FAQ_DATABASE:
        for pattern in faq["question_patterns"]:
            # Check if the pattern is in the question
            if pattern in message_lower:
                return {
                    "answer": faq["answer"],
                    "category": faq["category"]
                }
    
    return None

# Meeting keywords
MEETING_KEYWORDS = [
    "call", "meeting", "schedule", "connect", "talk", "discuss",
    "zoom", "meet", "chat", "catch up", "sync", "block time",
    "block a time", "find time", "available", "free time", "calendly",
    "book", "booking", "appointment", "slot", "when can we", "can we meet",
    "let's talk", "get on a call", "hop on", "quick call", "quick chat"
]

# ============================================
# WELCOME MESSAGES
# ============================================

@bot.event("member_joined_channel")
def welcome_message(event, say):
    user_id = event["user"]
    channel_id = event["channel"]
    
    if is_internal_team_member(user_id):
        return
    
    try:
        channel_info = bot.client.conversations_info(channel=channel_id)
        if not channel_info["ok"]:
            return
        channel_name = channel_info["channel"]["name"]
    except Exception as e:
        print(f"Error fetching channel info: {e}")
        return
    
    if "live_responses" in channel_name or "live-responses" in channel_name:
        text = (
            f"Welcome <@{user_id}>! 👋\n\n"
            f"This channel is for **real-time notifications** of all positive replies from your campaigns. "
            f"You can respond to leads via your Master Inbox."
        )
    else:
        calendly_link = format_link(CALENDLY_LINK, "book a call")
        text = (
            f"Welcome <@{user_id}>! 👋\n\n"
            f"This is your primary communication channel with the CleverViral team. "
            f"We'll discuss strategy, share updates, and collaborate on campaigns here.\n\n"
            f"**Quick actions:**\n"
            f"• To suggest a new campaign: `/new-campaign`\n"
            f"• To {calendly_link} with the team\n\n"
            f"I'm your CX bot - ask me anything! 🤖"
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
    
    # CRITICAL: Only proceed if this is actually a question
    if not is_actual_question(message_text):
        print(f"Not a question, ignoring: {message_text[:50]}")
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
    
    # Check for meeting keywords FIRST
    message_lower = message_text.lower()
    if any(keyword in message_lower for keyword in MEETING_KEYWORDS):
        calendly_link = format_link(CALENDLY_LINK, "here")
        text = (
            f"Got it <@{user_id}>! 📅\n\n"
            f"You can book a time {calendly_link}. Looping in <@{team_member_id}> as well!"
        )
        
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
        
        text = (
            f"{answer}\n\n"
            f"Looping in <@{team_member_id}> to provide any additional details! 👍"
        )
        
        try:
            client.reactions_remove(channel=channel_id, timestamp=message_ts, name="hourglass_flowing_sand")
            client.reactions_add(channel=channel_id, timestamp=message_ts, name="white_check_mark")
        except:
            pass
        
        say(text=text, thread_ts=thread_ts)
        return
    
    # No FAQ match - escalate
    text = (
        f"Got it <@{user_id}>! 👍\n\n"
        f"Looping in <@{team_member_id}> to answer this one."
    )
    
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
    
    form_link = format_link(NOTION_FORM_LINK, "this campaign form")
    text = (
        f"Hey <@{user_id}>! 🚀\n\n"
        f"Great idea! Please fill out {form_link} with your campaign details. "
        f"We'll review and get back to you within 3-5 business days!"
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
    return "Bot is running! 🤖", 200

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
    print("🤖 CleverViral CX Bot is starting...")
    print("✅ Bot is ready and listening for events!")
    
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
