import asyncio

import discord
from discord.ext import commands

from utilities.embed import embed
from utilities.file_uploading import start_file_uploading
from utilities.setup_logger import Loggers


class Mod(commands.Cog):

    def __init__(self, bot, config, bot_channel_manager):
        log_info = Loggers.get_logger(logger_name="Mod")
        self.logger = log_info[0]
        self.debug_log_file_absolute_path = log_info[1]
        self.error_log_file_absolute_path = log_info[2]
        self.bot = bot
        self.config = config
        self.guild = None
        self.bot_channel_manager = bot_channel_manager

    @commands.Cog.listener(name="on_ready")
    async def get_guild(self):
        self.guild = self.bot.guilds[0]

    @commands.Cog.listener(name="on_ready")
    async def upload_debug_logs(self):
        if self.config.get_config_value('basic_config', 'ENVIRONMENT') != 'TEST':
            while self.guild is None:
                await asyncio.sleep(2)
            await start_file_uploading(
                self.logger, self.guild, self.bot, self.config, self.debug_log_file_absolute_path, "mod_debug"
            )

    @commands.Cog.listener(name="on_ready")
    async def upload_error_logs(self):
        if self.config.get_config_value('basic_config', 'ENVIRONMENT') != 'TEST':
            while self.guild is None:
                await asyncio.sleep(2)
            await start_file_uploading(
                self.logger, self.guild, self.bot, self.config, self.error_log_file_absolute_path, "mod_error"
            )

    @commands.command(
        brief="Allows Minions to post embed messages.",
        help=(
            'For odd number of arguments the first arg will be used as description in the embed and the rest as '
            'field title and content.\n'
            'For even number there will be no description.\n\n'
            'Arguments:\n'
            '---[description]: the description of the embed\n'
            '---title: a title in the embed\n'
            '---content; the content that correspond to the above title in the embed\n\n'
            'Example: \n'
            '---.embed "title1" "content1"'
            '---.embed "title1" "content1"\n'
            '---.embed "the description" "title1" "content1"\n'
            '---.embed "title1" "content1" "title2" "content2"\n'
            '---.embed "the description" "title1" "content1" "title2" "content2"\n'
        ),
        usage='["the description"] ["title"] ["corresponding content"]',
        aliases=['em']
    )
    @commands.has_any_role("Minions", "Moderator")
    async def embed(self, ctx, *arg):
        self.logger.info(f'[Mod embed()] embed function detected by user {ctx.message.author}')
        await ctx.message.delete()
        self.logger.info('[Mod embed()] invoking message deleted')

        if not arg:
            self.logger.info("[Mod embed()] no args, so command ended")
            return

        if ctx.message.author not in discord.utils.get(ctx.guild.roles, name="Minions").members:
            self.logger.info('[Mod embed()] unathorized command attempt detected. Being handled.')
            await self.rekt(ctx)
            return

        self.logger.info('[Mod embed()] minion confirmed')
        fields = []
        desc = ''
        arg = list(arg)
        arg_len = len(arg)
        # odd number of args means description plus fields
        if not arg_len % 2 == 0:
            desc = arg[0]
            arg.pop(0)
            arg_len = len(arg)

        i = 0
        while i < arg_len:
            fields.append([arg[i], arg[i + 1]])
            i += 2

        name = ctx.author.nick or ctx.author.name
        e_obj = await embed(
            self.logger, ctx=ctx, description=desc, author=name, avatar=ctx.author.avatar.url,
            content=fields
        )
        if e_obj is not False:
            await ctx.send(embed=e_obj)

    async def rekt(self, ctx):
        self.logger.info('[Mod rekt()] sending troll to unauthorized user')
        lol = '[secret](https://www.youtube.com/watch?v=dQw4w9WgXcQ)'
        e_obj = await embed(
            self.logger,
            ctx=ctx,
            title='Minion Things',
            author=self.config.get_config_value('bot_profile', 'BOT_NAME'),
            avatar=self.config.get_config_value('bot_profile', 'BOT_AVATAR'),
            description=lol
        )
        if e_obj is not False:
            msg = await ctx.send(embed=e_obj)
            await asyncio.sleep(5)
            await msg.delete()
            self.logger.info('[Mod rekt()] troll message deleted')

    @commands.command(
        brief="Posts the warning message in embed format.",
        help=(
            'Arguments:\n'
            '---warning message: message that will be posted in the warning embed in the channel\n\n'
            'Example: \n'
            '---.modspeak warning message\n\n'
        ),
        usage="warning message",
        aliases=['warn'],
    )
    @commands.has_any_role("Minions", "Moderator")
    async def modspeak(self, ctx, *arg):
        self.logger.info(f'[Mod modspeak()] modspeack function detected by minion {ctx.message.author}')
        await ctx.message.delete()
        self.logger.info('[Mod modspeak()] invoking message deleted')

        if not arg:
            self.logger.info("[Mod modspeak()] no args, so command ended")
            return

        if ctx.message.author not in discord.utils.get(ctx.guild.roles, name="Minions").members:
            self.logger.info('[Mod modspeak()] unathorized command attempt detected. Being handled.')
            await self.rekt(ctx)
            return

        msg = ''
        for wrd in arg:
            msg += f'{wrd} '

        e_obj = await embed(
            self.logger, ctx=ctx, title='ATTENTION:', author=ctx.author.display_name,
            avatar=ctx.author.avatar.url, description=msg, footer='Moderator Warning'
        )
        if e_obj is not False:
            await ctx.send(embed=e_obj)
