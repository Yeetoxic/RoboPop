import discord
from discord import app_commands
from discord.ext import commands
import datetime

# Intents and bot setup
intents = discord.Intents.default()
intents.invites = True
intents.guilds = True
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Dictionary to store invite use counts
invite_uses = {}
race_started = False
race_start_time = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@tree.command(name="race_start", description="Start the invite tracking race with a specific goal.")
@app_commands.describe(goal="Number of invite uses to win the race.")
async def race_start(interaction: discord.Interaction, goal: int):
    """Start the invite tracking race with a specific goal."""
    global race_started, invite_goal, race_start_time

    print(f"Received race_start command from {interaction.user} in {interaction.guild}")
    print(f'Initial Invite List {invite_uses}')

    if not interaction.user.guild_permissions.administrator:
        print("User lacks Administrator permissions.")
        await interaction.response.send_message("You must have Administrator permissions to use this command.", ephemeral=True)
        return

    if race_started:
        print("Race is already in progress.")
        await interaction.response.send_message("The invite race is already in progress!", ephemeral=True)
        return

    if goal <= 0:
        print("Invalid goal provided.")
        await interaction.response.send_message("Please provide a valid positive number for the goal.", ephemeral=True)
        return

    # Get the invites of the server
    guild = interaction.guild
    if guild is None:
        print("Interaction guild is None.")
        await interaction.response.send_message("This command can only be used in a server. Please run this command in a valid server.", ephemeral=True)
        return

    # Verify bot permissions
    bot_member = guild.get_member(bot.user.id)
    if not bot_member.guild_permissions.manage_guild:
        print("Bot lacks Manage Server permissions.")
        await interaction.response.send_message("I need the 'Manage Server' permission to access invites.", ephemeral=True)
        return

    try:
        print("Fetching invites for the guild.")
        invites = await guild.invites()
        for invite in invites:
            invite_uses[invite.code] = invite.uses

        race_started = True
        invite_goal = goal
        race_start_time = datetime.datetime.utcnow()
        print(f"Race started with goal {goal} uses at {race_start_time}.")
        await interaction.response.send_message("Starting invite race...", ephemeral=True)
        await guild.system_channel.send(f"@everyone The invite race has started! First invite to reach {goal} uses wins. **Any invites created starting NOW will count toward this!**")
    except discord.Forbidden:
        print("Forbidden: Missing permission to access invites.")
        await interaction.response.send_message("I don't have permission to access invites. Please ensure I have the 'Manage Server' permission.", ephemeral=True)
    except discord.HTTPException as e:
        print(f"HTTPException occurred: {e}")
        await interaction.response.send_message(f"An error occurred while retrieving invites: {e}", ephemeral=True)
    except Exception as e:
        print(f"Unexpected error: {e}")
        await interaction.response.send_message(f"An unexpected error occurred: {e}", ephemeral=True)

@bot.event
async def on_invite_create(invite):
    """Track new invites."""
    global race_started, race_start_time
    if race_started and invite.created_at:
        # Convert race_start_time to an aware datetime with UTC timezone
        aware_race_start_time = race_start_time.replace(tzinfo=datetime.timezone.utc)
        if invite.created_at > aware_race_start_time:
            invite_uses[invite.code] = invite.uses
            print(f'New Invite Created After Race Start: {invite.code}')

@bot.event
async def on_invite_delete(invite):
    """Remove deleted invites from the tracking list."""
    if invite.code in invite_uses:
        del invite_uses[invite.code]

@bot.event
async def on_member_join(member):
    """Detect which invite was used when a new member joins."""
    global race_started, invite_goal
    print(f'Invite used {invite_uses}')

    if not race_started:
        return

    guild = member.guild
    if guild is None:
        print("Member joined, but guild context is missing.")
        return

    try:
        invites = await guild.invites()

        for invite in invites:
            # Check if invite was created after the race started and was used
            if invite.code in invite_uses and invite_uses.get(invite.code, 0) < invite.uses:
                invite_uses[invite.code] = invite.uses

                # Check if any invite reached the goal
                if invite.uses >= invite_goal:
                    race_started = False
                    print(f'RACE COMPLETE: `{invite.code}` created by {invite.inviter.mention} has reached {invite_goal} uses and won the race!')
                    await guild.system_channel.send(
                        f"@everyone The invite code **`{invite.code}`** created by {invite.inviter.mention} has reached **{invite_goal}** uses first and won the race!"
                    )
                break
    except discord.Forbidden:
        print("Missing permissions to access invites in the guild.")
    except Exception as e:
        print(f"An error occurred while processing member join: {e}")

@tree.command(name="stop_race", description="Stop the invite tracking race.")
async def stop_race(interaction: discord.Interaction):
    """Stop the invite tracking race."""
    global race_started

    if not race_started:
        await interaction.response.send_message("The invite race is not currently running.", ephemeral=True)
        return

    if not interaction.user.guild_permissions.administrator:
        print("User lacks Administrator permissions.")
        await interaction.response.send_message("You must have Administrator permissions to use this command.", ephemeral=True)
        return

    race_started = False
    await interaction.response.send_message("The invite race has been stopped.")

# Run the bot with token
bot.run("MTMyNzgzNTcxOTAxMTQwMTc1OQ.GtTiKl.jiHIFFl6db1ZWe5fDV8-9pPN-HoYV_RiituHjo")
