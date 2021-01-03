import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import requests

intents = discord.Intents.default()
intents.members = True
load_dotenv()

def admin_req():
    def predicate(ctx):
        return ctx.message.author.id == 466602373679415307
    return commands.check(predicate)

class AenBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix = "!", intents=intents)
        self.TOKEN = os.getenv("DISCORD_TOKEN")
        self.ASS_GUILD = int(os.getenv("ASS_GUILD") or 0)
        self.TWITCH_ID = os.getenv("TWITCH_ID")
        self.stream_check = Path("last_stream_check.txt").resolve()
        self.twitch_games = ["The%20Kingdom%20of%20Loathing"]
        self.dt_format = "%Y-%m-%d %H:%M:%S.%f%z"
        self.iso8601 = "%Y-%m-%dT%H:%M:%S%z"

    def convert_level_to_stat(self, level):
        if level > 255 or level < 1:
            level = 255
        a = level**2
        b = level*2
        mainstat = (a - b) + 5
        c = (level - 1)**2
        substats = (c + 4)**2
        return mainstat, substats

    def convert_stat_to_level(self, mainstat):
        if mainstat < 5:
            return 1, mainstat**2
        if mainstat > 64520:
            return 255, 4162830400
        a = mainstat - 4
        a = math.sqrt(a)
        level = 1 + int(a)
        substats = mainstat**2
        return level, substats

    def convert_substats_to_level(self, substats):
        if substats < 1:
            return 1, 1
        if substats > 4162830400:
            return 255, 64520
        mainstat = math.sqrt(substats)
        level, substats = self.convert_stat_to_level(mainstat)
        return level, mainstat

    async def get_broadcasts(self, twitch_game):
        twitch_headers = {"Accept": "application/vnd.twitchtv.v5+json", "Client-ID": self.TWITCH_ID}
        twitch_request = requests.get(f"https://api.twitch.tv/kraken/streams/?game={twitch_game}", headers=twitch_headers)
        try:
            twitch_json = twitch_request.json()
            return twitch_json["streams"]
        except (json.JSONDecodeError, KeyError):
            return False

    def parse_date(self, date_string, parser):
        return datetime.strptime(date_string, parser)

    async def on_ready(self):
        print(f"{self.user} is connected to the following guilds:\n")
        for guild in self.guilds:
            print(f"{guild.name}(id: {guild.id})")
        self.announce_streams.start()

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            return

        # Pronouns
        if payload.message_id == 741480863543591014:
            guild = self.get_guild(payload.guild_id)
            member = payload.member
            they = discord.utils.get(guild.roles, id=741479573337800706)
            she = discord.utils.get(guild.roles, id=741479514902757416)
            he = discord.utils.get(guild.roles, id=741479366319538226)
            if payload.emoji.name == "🇹":
                await member.add_roles(they)
                print(f"Assigning they to {member.name}")
            if payload.emoji.name == "♀️":
                await member.add_roles(she)
                print(f"Assigning she to {member.name}")
            if payload.emoji.name == "♂️":
                await member.add_roles(he)
                print(f"Assigning he to {member.name}")
            return

        # Listener/No Alerts
        if payload.message_id == 743250513755242548:
            guild = self.get_guild(payload.guild_id)
            member = payload.member
            listener = discord.utils.get(guild.roles, id=466622497991688202)
            no_alerts = discord.utils.get(guild.roles, id=512522219574919179)
            if payload.emoji.name == "👂":
                await member.add_roles(listener)
                await member.remove_roles(no_alerts)
                print(f"Assigning Listener role to {member.name}")
            if payload.emoji.name == "🚫":
                await member.add_roles(no_alerts)
                await member.remove_roles(listener)
                print(f"Assigning No Alerts role to {member.name}")
            return

        # LFGames
        if payload.message_id == 754473416316289105:
            guild = self.get_guild(payload.guild_id)
            member = payload.member
            LFGames = discord.utils.get(guild.roles, id=754473984661258391)
            if payload.emoji.name == "✅":
                await member.add_roles(LFGames)
                print(f"Assigning LFGames role to {member.name}")
            return

    async def on_raw_reaction_remove(self, payload):
        if payload.user_id == self.user.id:
            return

        # Pronouns
        if payload.message_id == 741480863543591014:
            guild = self.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            they = discord.utils.get(guild.roles, id=741479573337800706)
            she = discord.utils.get(guild.roles, id=741479514902757416)
            he = discord.utils.get(guild.roles, id=741479366319538226)
            if payload.emoji.name == "🇹":
                await member.remove_roles(they)
                print(f"Removing they/them role from {member.name}")
            if payload.emoji.name == "♀️":
                await member.remove_roles(she)
                print(f"Removing she/her role from {member.name}")
            if payload.emoji.name == "♂️":
                await member.remove_roles(he)
                print(f"Removing he/him role from {member.name}")
            return
        
        # LFGames
        if payload.message_id == 754473416316289105:
            guild = self.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            LFGames = discord.utils.get(guild.roles, id=754473984661258391)
            if payload.emoji.name == "✅":
                await member.remove_roles(LFGames)
                print(f"Removing LFGames role from {member.name}")
            return

    async def on_member_join(self, member):
        guild = member.guild
        if guild.id == self.ASS_GUILD:
            Listener = discord.utils.get(guild.roles, id=466622497991688202)
            await member.add_roles(Listener)
        return
    
    @tasks.loop(seconds=180)
    async def announce_streams(self):
        #channel = client.get_channel(740999949084524567) # bot testing
        channel = self.get_channel(578739919040675840) # streams and broadcasting
        with open(self.stream_check, "r") as lsc:
            last_loop_time = lsc.readline().rstrip()
            last_loop_time = self.parse_date(last_loop_time, self.dt_format)
        no_streams = True
        for twitch_game in self.twitch_games:
            streams = await self.get_broadcasts(twitch_game)
            if not streams:
                print("The JSON returned blank. Skipping this request.")
                continue
            sorted_streams = sorted(streams, key=lambda stream: self.parse_date(stream["created_at"], self.iso8601))
            for stream in sorted_streams:
                formatted_twitch_time = self.parse_date(stream["created_at"], self.iso8601)
                if formatted_twitch_time > last_loop_time:
                    chan = stream["channel"]
                    print(stream["channel"])
                    print(chan["game"].lower())
                    if ((chan["display_name"].lower() == "aenimuskol") and (chan["game"].lower() == "the kingdom of loathing")) or ((chan["display_name"].lower() == "arsawyer84") and (chan["game"].lower() == "the kingdom of loathing")):
                        announcements = self.get_channel(466605739838930959)
                        await announcements.send(f'`{chan["display_name"]}` is broadcasting Kingdom of Loathing-related things LIVE right now at {chan["url"]} !')
                    else:
                        await channel.send(f'`{chan["display_name"]}` is broadcasting {chan["game"]} at {chan["url"]} !')
                    print(f"Stream start: {stream['created_at']}; Last check: {last_loop_time}")
                    no_streams = False
        if no_streams:
            print("No new streams.")
        else:
            with open(self.stream_check, "w") as lsc:
                lsc.write(str(datetime.now(timezone.utc)))

bot = AenBot()

@admin_req()
@bot.command()
async def close(ctx):
    print("Good Night")
    await bot.close()
    return

@bot.command()
async def item(ctx):
    cmd = ctx.message.content.lower().split()
    drop_rate = cmd[1]
    if "." in drop_rate:
        try:
            drop_rate = float(drop_rate)
        except ValueError:
            await ctx.channel.send(f"That didn't seem to be the right syntax. Try !item x, where x is the drop rate of the item you wish to query.")
            return
    else:
        try:
            drop_rate = int(drop_rate)
        except ValueError:
            await ctx.channel.send(f"That didn't seem to be the right syntax. Try !item x, where x is the drop rate of the item you wish to query.")
            return
    if drop_rate == 0 or drop_rate < 0.1:
        drop_rate = 0.1
    if drop_rate >= 100:
        await ctx.channel.send(f"You do not need any bonus item drop% to guarantee an item with a drop rate of 100.")
        return
    modifier = (100/drop_rate) - 1
    modifier = modifier * 100
    await ctx.channel.send(f"To guarantee an item that has a drop rate of {drop_rate}, you would require {math.ceil(modifier)} total item drop%.")
    return

@bot.command()
async def level(ctx):
    cmd = ctx.message.content.lower().split()
    level = cmd[1]
    try:
        level = int(level)
    except ValueError:
        await ctx.channel.send(f"That didn't seem to be the right syntax. Try !level x, where x is the level you wish to query.")
        return
    if level <= 1:
        await ctx.channel.send(f"Level 1 requires 0 Mainstat (probably).")
        return
    if level > 255:
        level = 255
    mainstat, substats = bot.convert_level_to_stat(level)
    mainstat = int(mainstat)
    substats = int(substats)
    await ctx.channel.send(f"Level {level} requires {mainstat:,} total Mainstat or {substats:,} total Substats.")
    return

@bot.command()
async def stat(ctx):
    cmd = ctx.message.content.lower().split()
    current_mainstat = cmd[1]
    try:
        current_mainstat = int(current_mainstat)
    except ValueError:
        await ctx.channel.send(f"That didn't seem to be the right syntax. Try !stat x, where x is the mainstat you wish to query.")
        return

    if current_mainstat < 1:
        current_mainstat = 1
    level, main_to_substats = bot.convert_stat_to_level(current_mainstat)
    new_mainstat, level_to_substats = bot.convert_level_to_stat(level + 1)
    additional_mainstat_for_next_level = new_mainstat - current_mainstat
    additional_substat_for_next_level = level_to_substats - main_to_substats

    additional_mainstat_for_next_level = int(additional_mainstat_for_next_level)
    additional_substat_for_next_level = int(additional_substat_for_next_level)
    if level == 255:
        await ctx.channel.send(f"{current_mainstat:,} Mainstat or {main_to_substats:,} Substat reaches the max Level of {level:,}.")
    else:
        await ctx.channel.send(f"{current_mainstat:,} Mainstat or {main_to_substats:,} Substat reaches Level {level:,} and requires {additional_mainstat_for_next_level:,} Mainstat or {additional_substat_for_next_level:,} Substats for Level {level + 1}.")
    return

@bot.command()
async def substats(ctx):
    cmd = ctx.message.content.lower().split()
    try:
        substats = int(cmd[1])
    except ValueError:
        await ctx.channel.send(f"That didn't seem to be the right syntax. Try !substat x, where x is the substat you wish to query.")
        return

    if substats < 1:
        substats = 1
    elif substats >= 4162830400:
        await ctx.channel.send(f"4162830400 Substats is the max Mainstat of 64520, which is also the max Level of 255.")
        return

    if len(cmd) == 3:
        try:
            current_mainstat = int(cmd[2])
        except ValueError:
            await ctx.channel.send(f"That didn't seem to be the right syntax. Try !substat x y, where x is the substat you wish to query, and y is your current mainstat.")
            return
        
        if current_mainstat < 1:
            current_mainstat = 1
        elif current_mainstat >= 64520:
            await ctx.channel.send(f"64520 is max Mainstat, which is also the max Level of 255.")
            return
        
        current_level, current_substats = bot.convert_stat_to_level(current_mainstat)
        mainstat_for_next_level, substats_for_next_level = bot.convert_level_to_stat(current_level + 1)
        total_substats = current_substats + substats
        new_level, new_mainstat = bot.convert_substats_to_level(total_substats)
        if new_level > 255 or new_mainstat > 64520:
            await ctx.channel.send(f"{substats:,} Substats at {current_mainstat:,} Mainstat reaches the max of 64520 Mainstat, which is the max Level of 255.")
            return
        additional_mainstat_for_next_level = mainstat_for_next_level - new_mainstat
        additional_substats_for_next_level = substats_for_next_level - total_substats

        new_mainstat = int(new_mainstat)
        additional_mainstat_for_next_level = int(additional_mainstat_for_next_level)
        additional_substats_for_next_level = int(additional_substats_for_next_level)

        if new_level == 255:
            await ctx.channel.send(f"{substats:,} Substats at {current_mainstat:,} Mainstat reaches {new_mainstat:,} Mainstat, which is the max Level of {new_level:,}.")
        elif current_level == new_level:
            await ctx.channel.send(f"{substats:,} Substats at {current_mainstat:,} Mainstat reaches {new_mainstat:,} Mainstat, which is Level {new_level:,}. Level {current_level + 1:,} would require an additional {additional_mainstat_for_next_level:,} Mainstat or {additional_substats_for_next_level:,} Substats.")
        else:
            await ctx.channel.send(f"{substats:,} Substats at {current_mainstat:,} Mainstat reaches {new_mainstat:,} Mainstat, which is Level {new_level:,}.")
        return

    level, mainstat = bot.convert_substats_to_level(substats)
    mainstat_for_next_level, substats_for_next_level = bot.convert_level_to_stat(level + 1)
    additional_mainstat_for_next_level = mainstat_for_next_level - mainstat
    additional_substats_for_next_level = substats_for_next_level - substats

    additional_mainstat_for_next_level = int(additional_mainstat_for_next_level)
    additional_substats_for_next_level = int(additional_substats_for_next_level)
    mainstat = int(mainstat)
    if level == 255:
        await ctx.channel.send(f"{substats:,} Substats reaches {mainstat:,} Mainstat, which is the max Level of {level:,}.")
    else:
        await ctx.channel.send(f"{substats:,} Substats reaches {mainstat:,} Mainstat, which is Level {level:,}. Level {level + 1:,} would require an additional {additional_mainstat_for_next_level:,} Mainstat or {additional_substats_for_next_level:,} Substats.")
    return

bot.run(bot.TOKEN)