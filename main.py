import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Declare intents
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True

# Load environment variable
load_dotenv()
token = os.getenv("DISCORD_TOKEN")
if not token:
    print("Error: DISCORD_TOKEN not found in .env file")
    exit(1)

# Configuration file path
CONFIG_FILE = "relay_config.json"
import json
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"channel_id": None, "guild_id": None}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# Define allowed file types and maximum size
ALLOWED_FILE_TYPES = ['png', 'jpg', 'jpeg', 'gif', 'epub']
MAX_FILE_SIZE = 30 * 4000 * 4000  # 30 MB

# Command prefix
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot commands
@bot.command(name="heel")
@commands.is_owner()
async def heel(ctx, channel: discord.TextChannel):
    config = load_config()
    config["channel_id"] = channel.id
    config["guild_id"] = ctx.guild.id
    save_config(config)
    await ctx.send(f"i exist to serve")
    print(f"Relay channel configured: {channel.name, channel.id} in guild {ctx.guild.id}")

# Events
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        await bot.process_commands(message)
        return

    # Only process DMs
    if not isinstance(message.channel, discord.DMChannel):
        await bot.process_commands(message)
        return

    # Load guild and channel config
    config = load_config()
    if config["channel_id"] is None:
        await message.author.send("im not configured yet. please ask the administrator to beat me.")
        return
    try:
        guild = bot.get_guild(config["guild_id"])
        if guild is None:
            await message.author.send("target server not found")
            return
        channel = guild.get_channel(config["channel_id"])
        if channel is None:
            await message.author.send("target channel not found")
            return
        
        # Check bot permissions
        if not channel.permissions_for(guild.me).send_messages:
            print(f'permissions lacking in target channel {config["channel_id"]}')
            await message.author.send("i don't have permission to send messages in target channel. please ask the administrator to beat me.")
            return

        # Omitting the command from the message content
        ctx = await bot.get_context(message)
        content_to_relay = message.content
        if content_to_relay.startswith(bot.command_prefix):
            if ctx.command is None:
                command = content_to_relay.split(" ")[0]
                content_to_relay = content_to_relay[len(command):].strip()

        # Handle attachments
        files = []
        if message.attachments:
            for attachment in message.attachments:
                if validate_attachment(attachment):
                    try:
                        file = await attachment.to_file()
                        files.append(file)
                    except Exception as e:
                        print(f"Error downloading attachment {attachment.filename}: {e}")
                        await message.author.send(f"I encountered an error downloading {attachment.filename}")
                else:
                    await message.author.send(f"Invalid file: {attachment.filename}. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}. Max size: {MAX_FILE_SIZE/1024/1024} MB.")

        # Send to relay channel
        await channel.send(content=content_to_relay, files=files)

        # Confirm to sender
        await message.author.send("your message has been relayed.")

    except Exception as e:
        print(f"Error relaying message: {e}")
        await message.author.send(f"error relaying message: {str(e)}")
    await bot.process_commands(message)

# File validation    
def validate_attachment(attachment):
    file_extension = attachment.filename.split('.')[-1].lower()
    if file_extension not in ALLOWED_FILE_TYPES:
        return False
    if attachment.size > MAX_FILE_SIZE:
        return False
    return True 

bot.run(token)
