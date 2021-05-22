import discord
from dotenv import load_dotenv
import os
from discord.ext import commands
from mojang import MojangAPI
from mcstatus import MinecraftServer
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
server_ip = os.getenv('SERVER_IP')
typie_id = os.getenv('TYPIE_ID')

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


# prints welcome message when connected to Discord
@bot.event
async def on_ready():
    print('Online')


# checks to see who is currently playing on the server
@bot.command(name='whoson',
             help='Checks who is on the server.')
async def whos_on(ctx):
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
async def server(ctx):
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
    thumb_url = "https://i1.wp.com/www.craftycreations.net/wp-content/uploads/2019/08/Grass-Block-e1566147655539.png" \
                "?fit=500%2C500&ssl=1 "
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
        embed.set_thumbnail(url=thumb_url)

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


# gets stats from the server
# @bot.command(name='stats', help='Shows some stats for the server.')
# async def player_stats(ctx, message):
# parse files in saves folder

# gets player data from the server
# https://github.com/twoolie/NBT

bot.run(TOKEN)
