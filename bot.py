import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")

DATA_FILE = "channels.json"

client = OpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

channels = load_data()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="setaichannel", description="Set the channel where the bot will reply to every message with AI")
@app_commands.describe(channel="The channel the bot should watch")
@app_commands.checks.has_permissions(administrator=True)
async def set_ai_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild_id)
    channels[guild_id] = channel.id
    save_data(channels)

    await interaction.response.send_message(
        f"✅ AI reply channel set to {channel.mention}\n"
        f"The bot will now reply to **every message** in that channel.",
        ephemeral=True
    )

@set_ai_channel.error
async def set_ai_channel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)

@bot.tree.command(name="clearaichannel", description="Stop the bot from auto-replying in any channel")
@app_commands.checks.has_permissions(administrator=True)
async def clear_ai_channel(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    if guild_id in channels:
        del channels[guild_id]
        save_data(channels)
        await interaction.response.send_message("✅ AI auto-reply disabled for this server.", ephemeral=True)
    else:
        await interaction.response.send_message("No AI channel was set.", ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if not message.guild:
        return

    guild_id = str(message.guild.id)
    assigned_channel_id = channels.get(guild_id)

    if assigned_channel_id is None or message.channel.id != assigned_channel_id:
        return

    if len(message.content.strip()) < 2:
        return

    async with message.channel.typing():
        try:
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful, witty Discord bot. "
                            "Reply naturally and conversationally. "
                            "Keep responses reasonably short (1-3 paragraphs max) unless asked for more."
                        )
                    },
                    {"role": "user", "content": message.content}
                ],
                max_tokens=500,
                temperature=0.8
            )

            reply = response.choices[0].message.content.strip()

            if len(reply) > 2000:
                reply = reply[:1997] + "..."

            await message.reply(reply, mention_author=False)

        except Exception as e:
            print(f"Matt's AI API Error: `You a bitch`")
            await message.reply(f"Matt's AI API Error: `You a bitch`")

bot.run(DISCORD_TOKEN)