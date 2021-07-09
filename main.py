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
async def whos_on(ctx, message=""):
    serv = MinecraftServer(server_ip, 25565)
    status = serv.status()
    print(status.raw)
    if "sample" in status.raw['players'].keys():
        playing = [user['name'] for user in status.raw['players']['sample']]
    else:
        playing = []

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
async def server(ctx, message=""):
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


# gets status from the server
@bot.command(name='status', help='Shows the current status of a player on the server.')
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
    status = serv.status()
    print(status.raw)
    if 'sample' in status.raw['players'].keys():
        playing = [user['name'] for user in status.raw['players']['sample']]
    else:
        playing = []

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


# gets individual player killedby stats
@bot.command(name='killedby', help="Shows what has killed a player.")
async def killed_by(ctx, message):
    # load json file
    uuid = MojangAPI.get_uuid(message)
    p_filename = uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]
    filename = save_location + "stats/" + p_filename + ".json"

    with open(filename) as f:
        kb_stats = json.load(f)['stats']

    if 'minecraft:killed_by' in kb_stats.keys():
        killedby = kb_stats['minecraft:killed_by']

        embed = discord.Embed(
            title="{}'s foes".format(message),
            color=discord.Color.dark_green()
        )

        for mob in killedby:
            embed.add_field(name=mob.split(":")[-1].replace('_', ' '), value=killedby[mob], inline=True)

        await ctx.send(embed=embed)

    else:
        response = "{} hasn't been killed by anything yet. {}. Good job!".format(message, villager_noise())
        await ctx.send(response)


# gets individual player killedby stats
@bot.command(name='kills', help="Shows a player's kills.")
async def kills(ctx, message):
    # load json file
    uuid = MojangAPI.get_uuid(message)
    p_filename = uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]
    filename = save_location + "stats/" + p_filename + ".json"

    with open(filename) as f:
        k_stats = json.load(f)['stats']

    if 'minecraft:killed' in k_stats.keys():
        killed = k_stats['minecraft:killed']

        embed = discord.Embed(
            title="Mobs who fear {}".format(message),
            color=discord.Color.dark_green()
        )

        for mob in killed:
            embed.add_field(name=mob.split(":")[-1].replace('_', ' '), value=killed[mob], inline=True)

        await ctx.send(embed=embed)

    else:
        response = "{} hasn't killed anything yet. {}. Better get on that!".format(message, villager_noise())
        await ctx.send(response)


# gets individual player tools used stats
@bot.command(name='tools', help="Shows all the tools a player as used up.")
async def tools(ctx, message):
    # load json file
    uuid = MojangAPI.get_uuid(message)
    p_filename = uuid[:8] + "-" + uuid[8:12] + "-" + uuid[12:16] + "-" + uuid[16:20] + "-" + uuid[20:]
    filename = save_location + "stats/" + p_filename + ".json"

    with open(filename) as f:
        t_stats = json.load(f)['stats']

    if 'minecraft:broken' in t_stats.keys():
        killed = t_stats['minecraft:broken']

        embed = discord.Embed(
            title="Tools {} has used up".format(message),
            color=discord.Color.dark_green()
        )

        for mob in killed:
            embed.add_field(name=mob.split(":")[-1].replace('_', ' '), value=killed[mob], inline=True)

        await ctx.send(embed=embed)

    else:
        response = "{} hasn't broken anything yet. {}. Work a little harder maybe?".format(message, villager_noise())
        await ctx.send(response)


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


# gets server rankings
@bot.command(name='rankings', help="Shows the current rankings among known players.")
async def rankings(ctx, message=""):
    stats_dict = {"Most jumpy": {},
                  "Most sneaky": {},
                  "Most in a hurry": {},
                  "Most like a fish": {},
                  "Best climber": {},
                  "Most deadly": {},
                  "Most dead": {},
                  "Most dedicated": {},
                  "Longest lived (current life)": {}}

    filename = save_location + "stats/"
    players = []

    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                all_stats = json.load(f)['stats']
                player = MojangAPI.get_username(file.split('.')[0])[0:4]
                players.append(player)

            stats_dict["Most jumpy"][player] = all_stats['minecraft:custom']['minecraft:jump']
            stats_dict["Most sneaky"][player] = all_stats['minecraft:custom']['minecraft:sneak_time']
            stats_dict["Most in a hurry"][player] = all_stats['minecraft:custom']['minecraft:sprint_one_cm']
            stats_dict["Most like a fish"][player] = all_stats['minecraft:custom']['minecraft:swim_one_cm']
            stats_dict["Best climber"][player] = all_stats['minecraft:custom']['minecraft:climb_one_cm']
            stats_dict["Most deadly"][player] = all_stats['minecraft:custom']['minecraft:mob_kills']
            stats_dict["Most dead"][player] = all_stats['minecraft:custom']['minecraft:deaths']
            stats_dict["Most dedicated"][player] = all_stats['minecraft:custom']['minecraft:play_time']
            stats_dict["Longest lived (current life)"][player] = all_stats['minecraft:custom'][
                'minecraft:time_since_death']

    results = {}
    for key in stats_dict.keys():
        ordered_dict = dict(reversed(sorted(stats_dict[key].items(), key=lambda item: item[1])))
        ordered_list = list(ordered_dict.items())
        format_list = []

        for item in ordered_list:
            if key == "Most dedicated" or key == "Longest lived (current life)":
                value = str(datetime.timedelta(seconds=item[1]))
            else:
                value = "{:,}".format(item[1])

            format_list.append(" {}: **{}**".format(item[0], value))
        results_list = " \n".join(format_list)

        results[key] = results_list

    embed = discord.Embed(
        title="Rankings",
        color=discord.Color.dark_green()
    )
    for k in results.keys():
        embed.add_field(name=k + ":", value=results[k], inline=True)
    await ctx.send(embed=embed)


# gets server story achievements
@bot.command(name='story', help="Shows the story achievements for all players.")
async def story(ctx, message=""):
    story_adv = ['Minecraft',
                 'Stone Age',
                 'Getting an Upgrade',
                 'Acquire Hardware',
                 'Suit Up',
                 'Hot Stuff',
                 "Isn't It Iron Pick",
                 'Not Today, Thank You',
                 'Ice Bucket Challenge',
                 'Diamonds!',
                 'We Need to Go Deeper',
                 'Cover Me With Diamonds',
                 'Enchanter',
                 'Zombie Doctor',
                 'Eye Spy',
                 'The End?']

    story_nam = ['story/root',
                 'story/mine_stone',
                 'story/upgrade_tools',
                 'story/smelt_iron',
                 'story/obtain_armor',
                 'story/lava_bucket',
                 'story/iron_tools',
                 'story/deflect_arrow',
                 'story/form_obsidian',
                 'story/mine_diamond',
                 'story/enter_the_nether',
                 'story/shiny_gear',
                 'story/enchant_item',
                 'story/cure_zombie_villager',
                 'story/follow_ender_eye',
                 'story/enter_the_end']

    adv_dict = {}
    for i in story_nam:
        adv_dict[i] = []
    players = []

    filename = save_location + "advancements/"
    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                advance = json.load(f)
            player = MojangAPI.get_username(file.split('.')[0])
            players.append(player)

            for i in range(len(story_nam)):
                if story_nam[i] in [k.split(":")[-1] for k in advance.keys()]:
                    adv_dict[story_nam[i]].append(" {}: :green_circle:".format(player[:4]))
                else:
                    adv_dict[story_nam[i]].append(" {}: :red_circle:".format(player[:4]))

    results = {}
    for i in range(len(story_nam)):
        results_list = " \n".join(adv_dict[story_nam[i]])
        results[story_adv[i]] = results_list

    embed = discord.Embed(
        title="Story Achievements",
        color=discord.Color.dark_green()
    )

    for adv in results.keys():
        embed.add_field(name=adv + ":", value=results[adv], inline=True)

    url = "https://minecraft.fandom.com/wiki/Advancement"
    embed.add_field(name="More information",
                    value="[minecraft.fandom.com/wiki/Advancement]({})".format(url),
                    inline=False)
    await ctx.send(embed=embed)


# gets server nether achievements
@bot.command(name='nether', help="Shows the nether achievements for all players.")
async def nether(ctx, message=""):
    nether_adv = ['Nether',
                  'Return to Sender',
                  'Those Were the Days',
                  'Hidden in the Depths',
                  'Subspace Bubble',
                  'A Terrible Fortress',
                  'Who is Cutting Onions?',
                  'Oh Shiny',
                  'This Boat Has Legs',
                  'Uneasy Alliance',
                  'War Pigs',
                  'Country Lode, Take Me Home',
                  'Cover Me in Debris',
                  'Spooky Scary Skeleton',
                  'Into Fire',
                  'Not Quite "Nine" Lives',
                  'Hot Tourist Destinations',
                  'Withering Heights',
                  'Local Brewery',
                  'Bring Home the Beacon',
                  'A Furious Cocktail',
                  'Beaconator',
                  'How Did We Get Here?']

    nether_nam = ['nether/root',
                  'nether/return_to_sender',
                  'nether/find_bastion',
                  'nether/obtain_ancient_debris',
                  'nether/fast_travel',
                  'nether/find_fortress',
                  'nether/obtain_crying_obsidian',
                  'nether/distract_piglin',
                  'nether/ride_strider',
                  'nether/uneasy_alliance',
                  'nether/loot_bastion',
                  'nether/use_lodestone',
                  'nether/netherite_armor',
                  'nether/get_wither_skull',
                  'nether/obtain_blaze_rod',
                  'nether/charge_respawn_anchor',
                  'nether/explore_nether',
                  'nether/summon_wither',
                  'nether/brew_potion',
                  'nether/create_beacon',
                  'nether/all_potions',
                  'nether/create_full_beacon',
                  'nether/all_effects']

    adv_dict = {}
    for i in nether_nam:
        adv_dict[i] = []
    players = []

    filename = save_location + "advancements/"
    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                advance = json.load(f)
            player = MojangAPI.get_username(file.split('.')[0])
            players.append(player)

            for i in range(len(nether_nam)):
                if nether_nam[i] in [k.split(":")[-1] for k in advance.keys()]:
                    adv_dict[nether_nam[i]].append(" {}: :green_circle:".format(player[:4]))
                else:
                    adv_dict[nether_nam[i]].append(" {}: :red_circle:".format(player[:4]))

    results = {}
    for i in range(len(nether_nam)):
        results_list = " \n".join(adv_dict[nether_nam[i]])
        results[nether_adv[i]] = results_list

    embed = discord.Embed(
        title="Nether Achievements",
        color=discord.Color.dark_green()
    )

    for adv in results.keys():
        embed.add_field(name=adv + ":", value=results[adv], inline=True)

    url = "https://minecraft.fandom.com/wiki/Advancement"
    embed.add_field(name="More information",
                    value="[minecraft.fandom.com/wiki/Advancement]({})".format(url),
                    inline=False)
    await ctx.send(embed=embed)


# gets server the end achievements
@bot.command(name='end', help="Shows the end achievements for all players.")
async def end(ctx, message=""):
    end_adv = ['The End?',
               'Free the End',
               'The Next Generation',
               'Remote Getaway',
               'The End... Again...',
               'You Need a Mint',
               'The City at the End of the Game',
               "Sky's the Limit",
               'Great View From Up Here']

    end_nam = ['end/root',
               'end/kill_dragon',
               'end/dragon_egg',
               'end/enter_end_gateway',
               'end/respawn_dragon',
               'end/dragon_breath',
               'end/find_end_city',
               'end/elytra',
               'end/levitate']

    adv_dict = {}
    for i in end_nam:
        adv_dict[i] = []
    players = []

    filename = save_location + "advancements/"
    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                advance = json.load(f)
            player = MojangAPI.get_username(file.split('.')[0])
            players.append(player)

            for i in range(len(end_nam)):
                if end_nam[i] in [k.split(":")[-1] for k in advance.keys()]:
                    adv_dict[end_nam[i]].append(" {}: :green_circle:".format(player[:4]))
                else:
                    adv_dict[end_nam[i]].append(" {}: :red_circle:".format(player[:4]))

    results = {}
    for i in range(len(end_nam)):
        results_list = " \n".join(adv_dict[end_nam[i]])
        results[end_adv[i]] = results_list

    embed = discord.Embed(
        title="Nether Achievements",
        color=discord.Color.dark_green()
    )

    for adv in results.keys():
        embed.add_field(name=adv + ":", value=results[adv], inline=True)

    url = "https://minecraft.fandom.com/wiki/Advancement"
    embed.add_field(name="More information",
                    value="[minecraft.fandom.com/wiki/Advancement]({})".format(url),
                    inline=False)
    await ctx.send(embed=embed)


# gets server the adventure achievements
@bot.command(name='adventure', help="Shows the adventure achievements for all players.")
async def adventure(ctx, message=""):
    adventure_adv = ['Adventure',
                     'Voluntary Exile',
                     'Is It a Bird?',
                     'Monster Hunter',
                     'What a Deal!',
                     'Sticky Situation',
                     "Ol' Betsy",
                     'Surge Protector',
                     'Light as a Rabbit',
                     'Sweet Dreams',
                     'Hero of the Village',
                     'Is It a Balloon?',
                     'A Throwaway Joke',
                     'Take Aim',
                     'Monsters Hunted',
                     'Postmortal',
                     'Hired Help',
                     'Two Birds, One Arrow',
                     "Who's the Pillager Now?",
                     'Arbalistic',
                     'Adventuring Time',
                     'Is It a Plane?',
                     'Very Very Frightening',
                     'Sniper Duel',
                     'Bullseye']

    adventure_nam = ['adventure/root',
                     'adventure/voluntary_exile',
                     'adventure/spyglass_at_parrot',
                     'adventure/kill_a_mob',
                     'adventure/trade',
                     'adventure/honey_block_slide',
                     'adventure/ol_betsy',
                     'adventure/lightning_rod_with_villager_no_fire',
                     'adventure/walk_on_powder_snow_with_leather_boots',
                     'adventure/sleep_in_bed',
                     'adventure/hero_of_the_village',
                     'adventure/spyglass_at_ghast',
                     'adventure/throw_trident',
                     'adventure/shoot_arrow',
                     'adventure/kill_all_mobs',
                     'adventure/totem_of_undying',
                     'adventure/summon_iron_golem',
                     'adventure/two_birds_one_arrow',
                     'adventure/whos_the_pillager_now',
                     'adventure/arbalistic',
                     'adventure/adventuring_time',
                     'adventure/spyglass_at_dragon',
                     'adventure/very_very_frightening',
                     'adventure/sniper_duel',
                     'adventure/bullseye']

    adv_dict = {}
    for i in adventure_nam:
        adv_dict[i] = []
    players = []

    filename = save_location + "advancements/"
    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                advance = json.load(f)
            player = MojangAPI.get_username(file.split('.')[0])
            players.append(player)

            for i in range(len(adventure_nam)):
                if adventure_nam[i] in [k.split(":")[-1] for k in advance.keys()]:
                    adv_dict[adventure_nam[i]].append(" {}: :green_circle:".format(player[:4]))
                else:
                    adv_dict[adventure_nam[i]].append(" {}: :red_circle:".format(player[:4]))

    results = {}
    for i in range(len(adventure_nam)):
        results_list = " \n".join(adv_dict[adventure_nam[i]])
        results[adventure_adv[i]] = results_list

    embed = discord.Embed(
        title="Nether Achievements",
        color=discord.Color.dark_green()
    )

    for adv in results.keys():
        embed.add_field(name=adv + ":", value=results[adv], inline=True)

    url = "https://minecraft.fandom.com/wiki/Advancement"
    embed.add_field(name="More information",
                    value="[minecraft.fandom.com/wiki/Advancement]({})".format(url),
                    inline=False)
    await ctx.send(embed=embed)


# gets server the husbandry achievements
@bot.command(name='husbandry', help="Shows the husbandry achievements for all players.")
async def husbandry(ctx, message=""):
    husbandry_adv = ['Husbandry',
                     'Bee Our Guest',
                     'The Parrots and the Bats',
                     'Whatever Floats Your Goat!',
                     'Best Friends Forever',
                     'Glow and Behold!',
                     'Fishy Business',
                     'Total Beelocation',
                     'A Seedy Place',
                     'Wax On',
                     'Two by Two',
                     'A Complete Catalogue',
                     'Tactical Fishing',
                     'A Balanced Diet',
                     'Serious Dedication',
                     'Wax Off',
                     'The Cutest Predator',
                     'The Healing Power of Friendship!']

    husbandry_nam = ['husbandry/root',
                     'husbandry/safely_harvest_honey',
                     'husbandry/breed_an_animal',
                     'husbandry/ride_a_boat_with_a_goat',
                     'husbandry/tame_an_animal',
                     'husbandry/make_a_sign_glow',
                     'husbandry/fishy_business',
                     'husbandry/silk_touch_nest',
                     'husbandry/plant_seed',
                     'husbandry/wax_on',
                     'husbandry/bred_all_animals',
                     'husbandry/complete_catalogue',
                     'husbandry/tactical_fishing',
                     'husbandry/balanced_diet',
                     'husbandry/obtain_netherite_hoe',
                     'husbandry/wax_off',
                     'husbandry/axolotl_in_a_bucket',
                     'husbandry/kill_axolotl_target']

    adv_dict = {}
    for i in husbandry_nam:
        adv_dict[i] = []
    players = []

    filename = save_location + "advancements/"
    for file in os.listdir(filename):
        if file.endswith(".json"):
            with open(filename + file) as f:
                advance = json.load(f)
            player = MojangAPI.get_username(file.split('.')[0])
            players.append(player)

            for i in range(len(husbandry_nam)):
                if husbandry_nam[i] in [k.split(":")[-1] for k in advance.keys()]:
                    adv_dict[husbandry_nam[i]].append(" {}: :green_circle:".format(player[:4]))
                else:
                    adv_dict[husbandry_nam[i]].append(" {}: :red_circle:".format(player[:4]))

    results = {}
    for i in range(len(husbandry_nam)):
        results_list = " \n".join(adv_dict[husbandry_nam[i]])
        results[husbandry_adv[i]] = results_list

    embed = discord.Embed(
        title="Nether Achievements",
        color=discord.Color.dark_green()
    )

    for adv in results.keys():
        embed.add_field(name=adv + ":", value=results[adv], inline=True)

    url = "https://minecraft.fandom.com/wiki/Advancement"
    embed.add_field(name="More information",
                    value="[minecraft.fandom.com/wiki/Advancement]({})".format(url),
                    inline=False)

    await ctx.send(embed=embed)


# not working yet


# # checks if bot has any problems
# @bot.command(name='botstatus', help="Checks if Nash as any errors.")
# async def bot_status(ctx):
#     functions = [whos_on, server, who_is, player_status, stats, rankings]
#     results = []
#
#     # get random server player
#     filename = save_location + "stats/"
#     player = random.choice(os.listdir(filename)).split('.')[0]
#
#     for fn in functions:
#         try:
#             fn(ctx, player)
#             results.append('On')
#         except Exception as e:
#             results.append(e)
#
#     embed = discord.Embed(
#         title="Functions",
#         color=discord.Color.dark_green()
#     )
#
#     for i in range(len(functions)):
#         if results[i] == "On":
#             embed.add_field(name=functions[i], value=":green_circle:", inline=True)
#         else:
#             embed.add_field(name=functions[i], value=results[i], inline=True)
#
#     await ctx.send(embed=embed)


bot.run(TOKEN)
