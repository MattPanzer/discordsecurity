import discord
import asyncio
import json
from discord.ext import commands

TOKEN = "MTM0NTg0NTIzOTU2NjQzODQ5MQ.GXJS8p.pqj3zOG_SYs0x388evyX8sp-G_DWQ3sXUKkkLs"
GUILD_ID = 1345842312592359545
THRESHOLD = 3  # Numero massimo di azioni consentite in un breve periodo
TIME_FRAME = 10  # Tempo in secondi

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

actions = {}

async def backup_server():
    guild = bot.get_guild(GUILD_ID)
    if guild:
        data = {
            "roles": [role.name for role in guild.roles],
            "categories": {category.name: category.id for category in guild.categories},
            "channels": [{"name": channel.name, "category": channel.category.name if channel.category else None} for channel in guild.channels]
        }
        with open("backup.json", "w") as f:
            json.dump(data, f, indent=4)

async def restore_server():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    try:
        with open("backup.json", "r") as f:
            data = json.load(f)
        
        # Ripristina i ruoli mancanti
        existing_roles = {role.name for role in guild.roles}
        for role_name in data["roles"]:
            if role_name not in existing_roles:
                await guild.create_role(name=role_name)
                print(f"Creato ruolo: {role_name}")
        
        # Ripristina le categorie mancanti
        existing_categories = {category.name for category in guild.categories}
        category_map = {}
        for category_name in data["categories"]:
            if category_name not in existing_categories:
                category = await guild.create_category(name=category_name)
                category_map[category_name] = category.id
                print(f"Creata categoria: {category_name}")
            else:
                category_map[category_name] = next(c.id for c in guild.categories if c.name == category_name)
        
        # Ripristina i canali mancanti
        existing_channels = {channel.name for channel in guild.channels}
        for channel_data in data["channels"]:
            channel_name = channel_data["name"]
            category_name = channel_data["category"]
            if channel_name not in existing_channels:
                category = discord.utils.get(guild.categories, id=category_map.get(category_name)) if category_name else None
                await guild.create_text_channel(name=channel_name, category=category)
                print(f"Creato canale: {channel_name} in categoria {category_name if category_name else 'Nessuna'}")
    except Exception as e:
        print(f"Errore nel ripristino: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user} è online e protegge il server!")
    await backup_server()
    bot.loop.create_task(backup_loop())

async def backup_loop():
    while True:
        await backup_server()
        await asyncio.sleep(3600)  # Backup ogni ora

@bot.command()
async def restore(ctx):
    await restore_server()
    await ctx.send("Ripristino completato!")

async def monitor_actions(user_id, guild):
    if user_id not in actions:
        actions[user_id] = 0
    actions[user_id] += 1
    await asyncio.sleep(TIME_FRAME)
    actions[user_id] -= 1
    if actions[user_id] > THRESHOLD:
        user = guild.get_member(user_id)
        if user:
            await guild.ban(user, reason="Possibile raid - troppe modifiche a canali/ruoli")
            del actions[user_id]

async def get_audit_log_entry(guild, action):
    async for entry in guild.audit_logs(limit=1, action=action):
        return entry
    return None

@bot.event
async def on_guild_channel_create(channel):
    guild = channel.guild
    entry = await get_audit_log_entry(guild, discord.AuditLogAction.channel_create)
    if entry:
        await monitor_actions(entry.user.id, guild)

@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    entry = await get_audit_log_entry(guild, discord.AuditLogAction.channel_delete)
    if entry:
        await monitor_actions(entry.user.id, guild)

@bot.event
async def on_guild_role_create(role):
    guild = role.guild
    entry = await get_audit_log_entry(guild, discord.AuditLogAction.role_create)
    if entry:
        await monitor_actions(entry.user.id, guild)

@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    entry = await get_audit_log_entry(guild, discord.AuditLogAction.role_delete)
    if entry:
        await monitor_actions(entry.user.id, guild)

bot.run(TOKEN)
