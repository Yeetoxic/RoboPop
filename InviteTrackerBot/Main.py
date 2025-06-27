import discord
from discord import app_commands
from discord.ext import commands
import datetime
import pytz

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
    global race_started, invite_goal, race_start_time, invite_uses

    print(f'Starting Race ({invite_uses})')
    print(f"Received race_start command from {interaction.user} in '{interaction.guild}'")

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
        # Clear existing invites and only store new invites after race start
        invite_uses = {}
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
    global race_started, race_start_time, invite_uses
    if race_started and invite.created_at:
        # Convert race_start_time to an aware datetime with UTC timezone
        aware_race_start_time = race_start_time.replace(tzinfo=datetime.timezone.utc)
        if invite.created_at > aware_race_start_time:
            invite_uses[invite.code] = invite.uses
            print(f'Invite added ({invite_uses})')
            print(f'New Invite Created After Race Start: {invite.code}, by {invite.inviter.mention} at {datetime.datetime.utcnow():.2f}.')

@bot.event
async def on_invite_delete(invite):
    """Remove deleted invites from the tracking list."""
    if invite.code in invite_uses:
        del invite_uses[invite.code]

@bot.event
async def on_member_join(member):
    """Detect which invite was used when a new member joins."""
    global race_started, invite_goal

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
                print(f'Invite used at {datetime.datetime.utcnow():.2f} ({invite_uses})')
                print(f'Invite Used After Race Start: {invite.code}')

                # Check if any invite reached the goal
                if invite.uses >= invite_goal:
                    race_started = False
                    print(f'Final {invite_uses}')
                    print(f'RACE COMPLETE: `{invite.code}` created by {invite.inviter.mention} has reached {invite_goal} uses and won the race!')
                    await guild.system_channel.send(
                        f"@everyone The invite code **`{invite.code}`** created by {invite.inviter.mention} has reached **{invite_goal}** uses first and won the race!"
                    )
                break
            else:
                print(f'Invite that was not included in the competition was used.')
    except discord.Forbidden:
        print("Missing permissions to access invites in the guild.")
    except Exception as e:
        print(f"An error occurred while processing member join: {e}")


@tree.command(name="leader_board", description="Gives the leaderboard of the current race in-progress")
async def leader_board(interaction: discord.Interaction):
    """Generate a detailed leaderboard for the invite race."""
    global invite_uses, race_started, race_start_time

    try:
        if not race_started:
            await interaction.response.send_message("The race is not currently running.", ephemeral=True)
            return

        # Get the current time
        TimeNow = datetime.datetime.now(pytz.timezone('America/Los_Angeles')).strftime("%m/%d/%Y %I:%M:%S %p %Z")
        
        # Make race_start_time offset-aware
        aware_race_start_time = race_start_time.replace(tzinfo=datetime.timezone.utc)

        # Create an embed for the leaderboard
        embed = discord.Embed(
            title="**Invite Race Statistics**",
            description=f"Generated: **`{TimeNow}`**",
            color=0x2de639
        )

        guild = interaction.guild
        invites = await guild.invites()

        # Dictionary to group invites by inviter
        invites_by_user = {}

        # Filter invites created after the race start time
        for invite in invites:
            if invite.created_at and invite.created_at > aware_race_start_time:
                if invite.inviter not in invites_by_user:
                    invites_by_user[invite.inviter] = []
                invites_by_user[invite.inviter].append(invite)

        # Format the embed fields
        for inviter, inviter_invites in invites_by_user.items():
            value = ""
            for invite in inviter_invites:
                value += f"> - Invite code (**`{invite.code}`**) with (**`{invite.uses}`**) uses.\n"

            embed.add_field(name=f"Invite(s) by **`{inviter}`**", value=value, inline=True)

        # Check if no invites were found
        if not invites_by_user:
            embed.add_field(name="No data", value="No valid invites created since the race started.", inline=True)

        embed.set_footer(text="RoboPop Interactive Display Interface (c) Yeetoxic 2025")
        
        # Send the embed to the interaction channel
        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        print("Permission error: Missing permissions to send messages or retrieve invites.")
    except Exception as e:
        print(f"Unexpected error occurred: {e}")



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
bot.run("MTMyNzgzNTcxOTAxMTQwMTc1OQ.GtTiKl.jiHIFFl6db1ZWe5fDV8-9pPN-HoYV_RiituHjo") # <-- This bot token is invalid, I took it down a while ago!
