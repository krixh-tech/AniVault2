from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# check subscription (dummy for now)
async def check_subscription(user_id):
    return True


# register user (dummy function)
async def register_user(user_id):
    return True


# force sub text
FORCE_SUB_TEXT = "Please join the channel to use this bot."


# build episodes keyboard
def build_episodes_keyboard(episodes):
    buttons = []
    for ep in episodes:
        buttons.append([InlineKeyboardButton(f"Episode {ep}", callback_data=f"ep_{ep}")])
    return InlineKeyboardMarkup(buttons)


# build quality keyboard
def build_quality_keyboard():
    buttons = [
        [InlineKeyboardButton("360p", callback_data="q_360")],
        [InlineKeyboardButton("480p", callback_data="q_480")],
        [InlineKeyboardButton("720p", callback_data="q_720")],
        [InlineKeyboardButton("1080p", callback_data="q_1080")]
    ]
    return InlineKeyboardMarkup(buttons)


# truncate long text
def truncate(text, length=100):
    if len(text) > length:
        return text[:length] + "..."
    return text


# safe delete message
async def safe_delete(message):
    try:
        await message.delete()
    except:
        pass
