from dotenv import load_dotenv
import os
import json
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("cam", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

admin_id = 1889545520  # Change to your Telegram ID
data_file = "data.json"
pending_state = {}
users = set()

# JSON loading and saving
def load_data():
    if not os.path.exists(data_file):
        return {
            "channels": [],
            "buttons": [],
            "instruction": "",
            "verify_message": "",
            "verify_button_text": "",
            "verify_button_url": ""
        }
    with open(data_file, "r") as f:
        return json.load(f)

def save_data(data):
    with open(data_file, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# Check if user joined all channels
async def has_joined_required(user_id):
    for ch in data.get("channels", []):
        try:
            member = await app.get_chat_member(ch, user_id)
            if member.status not in [enums.ChatMemberStatus.MEMBER, enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]:
                return False
        except:
            return False
    return True

# /start handler
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    user_id = message.from_user.id
    users.add(user_id)

    keyboard = [[InlineKeyboardButton(btn["text"], url=btn["url"])] for btn in data.get("buttons", [])]
    keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="verify")])
    markup = InlineKeyboardMarkup(keyboard)

    instruction_text = data.get("instruction", "Welcome!")
    instruction_photo = data.get("instruction_photo")  # file_id of the image

    if instruction_photo:
        sent = await message.reply_photo(instruction_photo, caption=instruction_text, reply_markup=markup)
    else:
        sent = await message.reply(instruction_text, reply_markup=markup)

    await asyncio.sleep(1800)
    await sent.delete()

# Admin panel
@app.on_message(filters.command("panel") & filters.private & filters.user(admin_id))
async def panel(client, message: Message):
    kb = [
        [InlineKeyboardButton("➕ Set Instruction", callback_data="set_instruction")],
        [InlineKeyboardButton("➕ Add Button", callback_data="add_button")],
        [InlineKeyboardButton("📝 Set Post-Verify Message", callback_data="set_verify_msg")],
        [InlineKeyboardButton("🔗 Set Post-Verify Button", callback_data="set_verify_btn")],
        [InlineKeyboardButton("🗑 Reset Buttons", callback_data="reset_buttons")],
        [InlineKeyboardButton("🗑️ Reset Channels", callback_data="reset_channels")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    await message.reply("Admin Panel", reply_markup=InlineKeyboardMarkup(kb))

# Add forwarded channel
@app.on_message(filters.forwarded & filters.private & filters.user(admin_id))
async def add_channel(client, message: Message):
    chat_id = message.forward_from_chat.id
    if chat_id not in data["channels"]:
        data["channels"].append(chat_id)
        save_data(data)
        await message.reply(f"✅ Channel {chat_id} added.")

# Callback: Set instruction
@app.on_callback_query(filters.regex("set_instruction"))
async def set_instruction_cb(client, cb):
    await cb.message.edit("✍️ Send the new instruction message.")
    pending_state[cb.from_user.id] = "set_instruction"

# Callback: Add button
@app.on_callback_query(filters.regex("add_button"))
async def add_button_cb(client, cb):
    await cb.message.edit("✍️ Send the button **text**.")
    pending_state[cb.from_user.id] = "add_button_text"

@app.on_callback_query(filters.regex("reset_buttons"))
async def reset_buttons_cb(client, cb):
    data["buttons"] = []
    save_data(data)
    await cb.message.edit("✅ All buttons have been reset. You can now add new ones.")

@app.on_callback_query(filters.regex("reset_channels"))
async def reset_channels_cb(client, cb):
    data["channels"] = []
    save_data(data)
    await cb.answer(
        "✅ All force-join channels have been erased.\n\n📤 Forward a message from the new channel(s) to register them again.",
        show_alert=True
    )

@app.on_callback_query(filters.regex("broadcast"))
async def broadcast_cb(client, cb):
    await cb.message.edit("📢 Send the broadcast message.")
    pending_state[cb.from_user.id] = "broadcast"

@app.on_callback_query(filters.regex("stats"))
async def stats_cb(client, cb):
    await cb.message.reply(f"👥 Total users: {len(users)}")

# New: Set post-verification message
@app.on_callback_query(filters.regex("set_verify_msg"))
async def set_verify_msg_cb(client, cb):
    await cb.message.edit("✍️ Send the post-verification message text.")
    pending_state[cb.from_user.id] = "set_verify_msg"

# New: Set post-verification button
@app.on_callback_query(filters.regex("set_verify_btn"))
async def set_verify_btn_cb(client, cb):
    await cb.message.edit("🔤 Send the button text (e.g., 'Access Now').")
    pending_state[cb.from_user.id] = "verify_btn_text"

# Admin message state handling
@app.on_message(filters.private & filters.user(admin_id))
async def admin_reply_handler(client, message: Message):
    user_id = message.from_user.id
    state = pending_state.get(user_id)

    if not state:
        return

    if state == "set_instruction":
        if message.photo:
            data["instruction_photo"] = message.photo[-1].file_id
            data["instruction"] = message.caption or ""
        else:
            data["instruction_photo"] = None
            data["instruction"] = message.text

        save_data(data)
        await message.reply("✅ Instruction updated.")
        pending_state.pop(user_id)

    elif state == "add_button_text":
        pending_state[user_id] = {"step": "awaiting_url", "text": message.text}
        await message.reply("🔗 Now send the button URL.")

    elif isinstance(state, dict) and state.get("step") == "awaiting_url":
        data["buttons"].append({"text": state["text"], "url": message.text})
        save_data(data)
        await message.reply("✅ Button added.")
        pending_state.pop(user_id)

    elif state == "set_verify_msg":
        data["verify_message"] = message.text
        save_data(data)
        await message.reply("✅ Post-verification message set.")
        pending_state.pop(user_id)

    elif state == "verify_btn_text":
        pending_state[user_id] = {"step": "awaiting_verify_url", "text": message.text}
        await message.reply("🔗 Now send the button URL.")

    elif isinstance(state, dict) and state.get("step") == "awaiting_verify_url":
        data["verify_button_text"] = state["text"]
        data["verify_button_url"] = message.text
        save_data(data)
        await message.reply("✅ Post-verification button set.")
        pending_state.pop(user_id)

    elif state == "broadcast":
        count = 0
        for uid in users:
            try:
                await client.send_message(uid, message.text)
                count += 1
            except:
                continue
        await message.reply(f"📣 Broadcast sent to {count} users.")
        pending_state.pop(user_id)

# Verify button
@app.on_callback_query(filters.regex("verify"))
async def verify_callback(client, callback_query):
    user_id = callback_query.from_user.id
    if await has_joined_required(user_id):
        msg = data.get("verify_message", "✅ You are verified!")
        btn_text = data.get("verify_button_text")
        btn_url = data.get("verify_button_url")

        keyboard = None
        if btn_text and btn_url:
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(btn_text, url=btn_url)]])

        await callback_query.message.edit(msg, reply_markup=keyboard)
        await callback_query.answer("✅ You're verified!", show_alert=True)
    else:
        await callback_query.answer("❌ You must join the required channel(s) first.", show_alert=True)
        keyboard = [[InlineKeyboardButton(btn["text"], url=btn["url"])] for btn in data.get("buttons", [])]
        keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="verify")])
        await callback_query.message.edit(
            "Please join the required channel(s) and press Verify again.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

app.run()
