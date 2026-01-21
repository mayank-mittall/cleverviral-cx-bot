# CleverViral CX Bot

Slack bot for automated client communication and support.

## Required Environment Variables

Set these in your hosting platform (Railway):

```
SLACK_BOT_TOKEN=xoxb-your-token-here
CALENDLY_LINK=https://calendly.com/mayank-cleverviral/30min
NOTION_FORM_LINK=https://cleverviral.notion.site/2ef95faff36c80a29755e31b12bd5e9a?pvs=105
HANDOFF_TEAM_MEMBER=@Mayank M
```

## Deployment

1. Push code to GitHub
2. Connect Railway to GitHub repo
3. Set environment variables in Railway dashboard
4. Deploy!

## Features

- ✅ Welcome messages for new channel members
- ✅ Basic FAQ responses (15 common questions)
- ✅ Calendar link sharing
- ✅ Campaign form sharing via /new-campaign
- ✅ Human handoff for complex questions
