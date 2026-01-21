import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, jsonify

# --- CONFIGURATION ---
# Load environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
CALENDLY_LINK = os.environ.get("CALENDLY_LINK", "https://calendly.com/your-link")
NOTION_FORM_LINK = os.environ.get("NOTION_FORM_LINK", "https://notion.so/your-form")
HANDOFF_TEAM_MEMBER_ID = os.environ.get("HANDOFF_TEAM_MEMBER_ID", "UXXXXXXXX") # Replace with actual Member ID

# --- INITIALIZATION ---

# Initializes your app with your bot token and signing secret
bot = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET
)

# Initialize Flask app
app = Flask(__name__)

# Create a handler for Slack events
handler = SlackRequestHandler(bot)

# --- DATA (FAQs) ---
# Using a simple dictionary for FAQs. For a real-world scenario, you might use a database or a file.
faq_responses = {
    "login": "You can log in to the CleverViral dashboard at gtm.cleverviral.co. You should have received an invite via email to set up your account.",
    "dashboard": "The Campaign Dashboard provides a real-time overview of your campaign performance, including sends, opens, clicks, and replies.",
    "master inbox": "The Master Inbox is where you can view and reply to all positive leads from your campaigns. You can access it via the main dashboard at gtm.cleverviral.co.",
    "campaign launch": "New campaigns are typically launched within 3-5 business days after the strategy is finalized. We will notify you here in the '#[client]_cleverviral' channel once it's live.",
    "reporting": "You will receive weekly performance TL;DRs in this channel every Friday and a detailed monthly report via email at the beginning of each month.",
    "leads": "Positive replies from potential leads are funneled into the Master Inbox. You'll also get a real-time notification in the '#[client]_live_responses' channel for each positive reply.",
    "pause campaign": "To pause a campaign, please let us know which campaign you'd like to pause, and we will deactivate it. Please allow up to 24 hours for this change to take effect.",
    "target audience": "We define the target audience based on the Ideal Customer Profile (ICP) we established during onboarding. If you want to suggest a new audience, feel free to use the `/new-campaign` command.",
    "copywriting": "All email copy is written by our team and goes through a rigorous internal review process. We typically share the copy direction with you before launching a new angle.",
    "billing": "For any questions regarding billing or your subscription, please contact your account manager directly or email billing@cleverviral.co.",
    "meeting": f"Of course! You can book a time with us using this link: {CALENDLY_LINK}",
    "call": f"Happy to connect! Please book a time that works for you here: {CALENDLY_LINK}",
    "schedule": f"Let's find a time. You can view our availability and book a slot here: {CALENDLY_LINK}",
    "connect": f"Sounds good. Please grab a time on our calendar: {CALENDLY_LINK}",
    "idea": f"That's great! To ensure we capture all the details for a new campaign idea, please use the `/new-campaign` command. It will give you a form to fill out."
}

# --- SLACK EVENT HANDLERS ---

# Welcome message for new members
@bot.event("member_joined_channel")
def welcome_message(event, say):
    user_id = event["user"]
    channel_id = event["channel"]
    channel_name = ""

    # Fetch channel info to get the name
    try:
        channel_info = bot.client.conversations_info(channel=channel_id)
        if channel_info["ok"]:
            channel_name = channel_info["channel"]["name"]
    except Exception as e:
        print(f"Error fetching channel info: {e}")
        return

    # Customize message based on the channel
    if "live_responses" in channel_name:
        text = f"Welcome <@{user_id}>! This channel is for real-time notifications of all positive replies from our campaigns. You can monitor lead activity here."
    else:
        text = (
            f"Welcome <@{user_id}>! This is your primary communication channel with the CleverViral team. "
            f"Here we'll discuss strategy, share updates, and collaborate on your campaigns.\n\n"
            f"A few quick links to get you started:\n"
            f"• Access your Dashboard & Master Inbox: https://gtm.cleverviral.co\n"
            f"• To suggest a new campaign, just type `/new-campaign`"
        )
    
    say(text=text)

# Respond to messages containing keywords (FAQs)
@bot.message(".*")
def handle_message(message, say):
    user_message = message["text"].lower()
    
    # Find a matching FAQ keyword
    for keyword, response in faq_responses.items():
        if keyword in user_message:
            say(text=response, thread_ts=message["ts"])
            return # Stop after the first match

    # If no keyword is found, handoff to a human
    # This part is simple now, could be improved with sentiment analysis in V2
    # Avoids replying to its own messages or other bot messages
    if "bot_id" not in message:
        handoff_text = (
            f"I'm not sure how to answer that. Let me loop in the team for you. "
            f"<@{HANDOFF_TEAM_MEMBER_ID}> will get back to you shortly."
        )
        say(text=handoff_text, thread_ts=message["ts"])


# --- SLACK COMMAND HANDLERS ---

@bot.command("/new-campaign")
def handle_new_campaign(ack, body, say):
    ack()
    user_id = body["user_id"]
    text = (
        f"Hi <@{user_id}>! That's great you have a new idea. To make sure we capture all the necessary details, "
        f"please fill out this brief form:\n{NOTION_FORM_LINK}"
    )
    say(text=text)


# --- N8N WEBHOOK ENDPOINT (FOR V1 TRANSCRIPT SUMMARY) ---
# This endpoint will be called by your N8N workflow

@app.route("/n8n/transcript-summary", methods=["POST"])
def n8n_transcript_summary():
    data = request.json
    
    # Ensure data from N8N is valid
    if not data or "summary" not in data or "channel" not in data:
        return jsonify({"status": "error", "message": "Invalid payload. 'summary' and 'channel' are required."}, 400)

    summary = data["summary"]
    target_channel = data["channel"] # e.g., "testclient-cxcleverviral"

    try:
        # Post the summary to the specified Slack channel
        bot.client.chat_postMessage(
            channel=target_channel,
            text=f"📄 Here's a summary of the recent client call:\n\n{summary}"
        )
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Error posting to Slack: {e}")
        return jsonify({"status": "error", "message": f"Failed to post to Slack: {e}"}), 500

# --- FLASK APP ROUTES ---

# Health check endpoint
@app.route("/health", methods=["GET"])
def health_check():
    return "Bot is running! 🤖", 200

# Entry point for all Slack events
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# Entry point for all Slack commands
@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    return handler.handle(request)


# --- APP STARTUP ---
if __name__ == "__main__":
    # The port is important for Render
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
