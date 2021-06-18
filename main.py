import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
from mojang import MojangAPI
from mcstatus import MinecraftServer
import random
from nbt import nbt
import json
import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
server_ip = os.getenv('SERVER_IP')
typie_id = os.getenv('TYPIE_ID')
save_location = os.getenv('SAVE_LOCATION')

# Change only the no_category default string
help_command = commands.DefaultHelpCommand(no_category='Commands')

bot = commands.Bot(command_prefix='-',
                   help_command=help_command)


# returns a random villager noise for messages
def villager_noise():
    noises = ["Herrm",
              "Hurrg",
              "Hmmmn",
              "Huurr",
              "Hrmmm",
              "Huh",
              "Hrng",
              "Hmmr",
              "Hurn"
              ]
    return random.choice(noises)


def format_txt(txt):
    return txt.split(":")[-1].replace("_", " ").capitalize()


# prints welcome message when connected to Discord
@bot.event
async def on_ready():
    print('Online')


# checks to see who is currently playing on the server
@bot.command(name='whoson',
             help='Checks who is on the server.')
async def whos_on(ctx, message):
    serv = MinecraftServer(server_ip, 25565)
    query = serv.query()
    playing = query.players.names

    if len(playing) > 1:
        response = "{} are on right now. {}".format(", ".join(playing), villager_noise())
    elif len(playing) == 1:
        response = "{}. {} is on right now.".format(villager_noise(), playing[0])
    else:
        response = "{}. No one is on right now.".format(villager_noise())
    await ctx.send(response)


# check if the server is running
@bot.command(name='server',
             help='Check to see if the server is running.')
async def server(ctx, message):
    # check if the server is running
    print(server_ip)
    serv = MinecraftServer(server_ip, 25565)
    latency = serv.ping()
    response = "{}. The server IS running with a latency of {} seconds.".format(villager_noise(), latency)
    await ctx.send(response)


# if the server is not running - this should probably be built into the function above
@server.error
async def server_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        await ctx.send("{}. The server is NOT running.".format(villager_noise()))


# look up minecraft user profile
@bot.command(name='whois',
             help='Looks up Minecraft user names.')
async def who_is(ctx, message):
    uuid = MojangAPI.get_uuid(message)

    if uuid:
        namehist = MojangAPI.get_name_history(uuid)
        profile = MojangAPI.get_profile(uuid)

        embed = discord.Embed(
            title="{}'s profile".format(message),
            color=discord.Color.dark_green()
        )
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Skin", value="[Open Skin]({})".format(profile.skin_url), inline=True)
        embed.add_field(name="Information", value="Username Changes:{}".format(len(namehist)), inline=True)

        embed.set_thumbnail(url="https://visage.surgeplay.com/bust/512/{}".format(uuid))
        await ctx.send(embed=embed)

    else:
        await ctx.send("{}. I don't know that player.".format(villager_noise()))


# error handling if user does not exist
@who_is.error
async def who_is_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("{}. You're missing the account name.".format(villager_noise()))


# watch the server log to see if anyone has joined and print message
async def ms_login():
    pass
    channel = bot.get_channel(int(typie_id))
    # monitor server log
    # if someone logs on:
    username = 'Name from Server Log'
    await channel.send("{} logged on. {}".format(username, villager_noise()))


async def ms_death():
    pass
    channel = bot.get_channel(int(typie_id))
    # monitor server log
    # if someone dies:
    username = "Name from server log"
    await channel.sed("{} died.".format(username))


# gets status from the server
@bot.command(name='status', help='Shows the current status of players on the server.')
async def player_status(ctx, message):
    uuid = MojangAPI.get_uuid(message)
    p_filename = uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:] + ".dat"
    player = nbt.NBTFile(save_location + "playerdata/" + p_filename, 'rb')

    # location
    p_loc = "{}: X: {}, Y: {}, Z: {}".format(player['Dimension'].value.split(":")[-1].capitalize(),
                                             int(player['Pos'][0].value),
                                             int(player['Pos'][1].value),
                                             int(player['Pos'][2].value))

    # XP
    p_xp = player['XpLevel'].value

    # Health
    p_health = player['Health'].value / 2
    if p_health.is_integer():
        p_health = int(p_health)

    # hunger
    p_hunger = player['foodLevel'].value / 2
    if p_hunger.is_integer():
        p_hunger = int(p_hunger)

    # holding
    item = player['SelectedItemSlot'].value
    p_item = player['Inventory'][item]['id'].value.split(":")[-1].replace('_', ' ')
    file_item = player['Inventory'][item]['id'].value.split(":")[-1]

    # online
    serv = MinecraftServer(server_ip, 25565)
    query = serv.query()
    playing = query.players.names
    if message in playing:
        p_online = ":green_circle:"
    else:
        p_online = ":red_circle:"

    embed = discord.Embed(
        title="{}'s status".format(message),
        color=discord.Color.dark_green()
    )
    embed.add_field(name="Last known location", value=p_loc, inline=False)
    embed.add_field(name="Last holding", value=p_item, inline=False)
    embed.add_field(name="XP", value=p_xp, inline=True)
    embed.add_field(name="Health", value="{}/10".format(p_health), inline=True)
    embed.add_field(name="Hunger", value="{}/10".format(p_hunger), inline=True)
    embed.add_field(name="Online", value=p_online, inline=False)

    embed.set_thumbnail(url="https://visage.surgeplay.com/bust/512/{}".format(uuid))
    await ctx.send(embed=embed)


# gets individual player stats
@bot.command(name='stats', help="Shows a few of a player's stats.")
async def stats(ctx, message):
    # load json file
    uuid = MojangAPI.get_uuid(message)
    p_filename = uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]
    filename = save_location + "stats/" + p_filename + ".json"

    with open(filename) as f:
        stats_dict = json.load(f)['stats']

    # get top stats (highest, and most, etc)
    tops = {}
    for key in stats_dict.keys():
        tops[key] = (max(k for k, v in stats_dict[key].items() if v != 0))

    embed = discord.Embed(
        title="{}'s stats".format(message),
        color=discord.Color.dark_green()
    )

    if "minecraft:used" in tops.keys():
        embed.add_field(name="Most used item:", value=format_txt(tops["minecraft:used"]), inline=False)
    else:
        embed.add_field(name="Most used item:", value="Nothing yet!", inline=False)

    if "minecraft:mob_kills" in stats_dict['minecraft:custom'].keys():
        embed.add_field(name="Total mobs killed:",
                        value=stats_dict['minecraft:custom']['minecraft:mob_kills'],
                        inline=True)
    else:
        embed.add_field(name="Total mobs killed:",
                        value="0",
                        inline=True)

    if "minecraft:killed" in stats_dict['minecraft:custom'].keys():
        most_mobs = format_txt(tops["minecraft:killed"]) + " - " + str(
            stats_dict['minecraft:killed'][tops['minecraft:killed']])
        embed.add_field(name="Most killed mob:", value=most_mobs, inline=True)
    else:
        embed.add_field(name="Most killed mob:", value="Nothing yet!", inline=True)

    if "minecraft:damage_dealt" in stats_dict['minecraft:custom'].keys():
        embed.add_field(name="Damage dealt:",
                        value=stats_dict['minecraft:custom']['minecraft:damage_dealt'],
                        inline=True)
    else:
        embed.add_field(name="Damage dealt:",
                        value="0",
                        inline=True)

    if "minecraft:deaths" in stats_dict['minecraft:custom'].keys():
        embed.add_field(name="Total deaths:", value=stats_dict['minecraft:custom']['minecraft:deaths'], inline=True)
    else:
        embed.add_field(name="Total deaths:", value="0", inline=True)

    if "minecraft:killed_by" in stats_dict['minecraft:custom'].keys():
        killed_most = format_txt(tops["minecraft:killed_by"]) + ' - ' + str(
            stats_dict['minecraft:custom'][tops['minecraft:killed_by']])
        embed.add_field(name="Killed most by:", value=killed_most, inline=True)
    else:
        embed.add_field(name="Killed most by:", value="Nothing yet!", inline=True)

    if "minecraft:damage_taken" in stats_dict['minecraft:custom'].keys():
        embed.add_field(name="Damage taken:",
                        value=stats_dict['minecraft:custom']['minecraft:damage_taken'],
                        inline=True)
    else:
        embed.add_field(name="Damage taken:",
                        value="0",
                        inline=True)

    if "minecraft:time_since_death" in stats_dict['minecraft:custom'].keys():
        s = stats_dict['minecraft:custom']['minecraft:time_since_death']
        embed.add_field(name="Time since last death:",
                        value=str(datetime.timedelta(seconds=s)),
                        inline=False)
    else:
        embed.add_field(name="Time since last death:",
                        value="No deaths yet!",
                        inline=False)

    embed.set_thumbnail(url="https://visage.surgeplay.com/bust/512/{}".format(uuid))
    await ctx.send(embed=embed)


# gets individual player stats
@bot.command(name='rankings', help="Shows the current rankings among known players.")
async def rankings(ctx, message):
    stats_dict = {"jumpy": {},
                  "sneaky": {},
                  "hurry": {},
                  "fish": {},
                  "climber": {},
                  "deadly": {},
                  "deaths": {},
                  "dedicated": {},
                  "lived": {}}

    filename = save_location + "stats/"
    players = []

    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                all_stats = json.load(f)['stats']
                player = MojangAPI.get_username(file.split('.')[0])
                players.append(player)

            stats_dict["jumpy"][player] = all_stats['minecraft:custom']['minecraft:jump']
            stats_dict["sneaky"][player] = all_stats['minecraft:custom']['minecraft:sneak_time']
            stats_dict["hurry"][player] = all_stats['minecraft:custom']['minecraft:sprint_one_cm']
            stats_dict["fish"][player] = all_stats['minecraft:custom']['minecraft:swim_one_cm']
            stats_dict["climber"][player] = all_stats['minecraft:custom']['minecraft:climb_one_cm']
            stats_dict["deadly"][player] = all_stats['minecraft:custom']['minecraft:mob_kills']
            stats_dict["deaths"][player] = all_stats['minecraft:custom']['minecraft:deaths']
            stats_dict["dedicated"][player] = all_stats['minecraft:custom']['minecraft:play_one_minute']
            stats_dict["lived"][player] = all_stats['minecraft:custom']['minecraft:time_since_death']

    results = {}
    for key in stats_dict.keys():
        ordered_dict = dict(reversed(sorted(stats_dict[key].items(), key=lambda item: item[1])))
        ordered_list = list(ordered_dict.items())
        format_list = []
        print(ordered_list)
        for item in ordered_list:
            if key == "dedicated" or key == "lived":
                value = str(datetime.timedelta(seconds=item[1]))
            else:
                value = "{:,}".format(item[1])

            format_list.append("{}: **{}**".format(item[0], value))
        results_list = " \n ".join(format_list)
        print(results_list)
        results[key] = results_list

    print(results)

    embed = discord.Embed(
        title="Players: {}".format(', '.join(players)),
        color=discord.Color.dark_green()
    )
    embed.add_field(name="Most jumpy:", value=results['jumpy'], inline=True)
    embed.add_field(name="Most sneaky:", value=results['sneaky'], inline=True)
    embed.add_field(name="Most in a hurry:", value=results['hurry'], inline=True)
    embed.add_field(name="Most like a fish:", value=results['fish'], inline=True)
    embed.add_field(name="Best climber:", value=results['climber'], inline=True)
    embed.add_field(name="Most deadly:", value=results['deadly'], inline=True)
    embed.add_field(name="Most dead:", value=results['deaths'], inline=True)
    embed.add_field(name="Most dedicated:", value=results['dedicated'], inline=True)
    embed.add_field(name="Longest lived (current life):", value=results['lived'], inline=True)

    await ctx.send(embed=embed)


# checks if bot has any problems
@bot.command(name='botstatus', help="Checks if Nash as any errors.")
async def bot_status(ctx):
    functions = [whos_on, server, who_is, player_status, stats, rankings]
    results = []

    for fn in functions:
        try:
            fn(ctx, "chipuha")
            results.append('On')
        except Exception as e:
            results.append(e)

    embed = discord.Embed(
        title="Functions",
        color=discord.Color.dark_green()
    )

    for i in range(len(functions)):
        if results[i] =="On":
            embed.add_field(name=functions[i], value=":green_circle:", inline=True)
        else:
            embed.add_field(name=functions[i], value=results[i], inline=True)

    await ctx.send(embed=embed)


bot.run(TOKEN)
