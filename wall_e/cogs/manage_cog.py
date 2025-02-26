import asyncio
import datetime
import re

import discord
from discord.ext import commands
from wall_e_models.models import CommandStat

from utilities.embed import embed, WallEColour
from utilities.file_uploading import start_file_uploading
from utilities.setup_logger import Loggers, print_wall_e_exception


class ManageCog(commands.Cog):

    def __init__(self, bot, config, bot_channel_manager):
        log_info = Loggers.get_logger(logger_name="ManageCog")
        self.logger = log_info[0]
        self.debug_log_file_absolute_path = log_info[1]
        self.error_log_file_absolute_path = log_info[2]
        self.logger.info("[ManageCog __init__()] initializing the TestCog")
        if config.get_config_value('basic_config', 'ENVIRONMENT') == 'TEST':
            bot.add_check(self.check_text_command_test_environment)
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
                self.logger, self.guild, self.bot, self.config, self.debug_log_file_absolute_path, "manage_cog_debug"
            )

    @commands.Cog.listener(name="on_ready")
    async def upload_error_logs(self):
        if self.config.get_config_value('basic_config', 'ENVIRONMENT') != 'TEST':
            while self.guild is None:
                await asyncio.sleep(2)
            await start_file_uploading(
                self.logger, self.guild, self.bot, self.config, self.error_log_file_absolute_path, "manage_cog_error"
            )

    @commands.Cog.listener(name="on_ready")
    async def create_main_channel(self):
        """
        this command is used by the TEST guild to create the channel from which this TEST container
         will process commands
        :return:
        """
        while self.guild is None:
            await asyncio.sleep(2)
        self.logger.info(f"[ManageCog on_ready()] acquired {len(self.guild.channels)} channels")
        if self.config.get_config_value("basic_config", "ENVIRONMENT") == 'TEST':
            self.logger.info("[ManageCog on_ready()] ENVIRONMENT detected to be 'TEST' ENVIRONMENT")
            await self.bot_channel_manager.create_or_get_channel_id(
                self.logger, self.guild, self.config.get_config_value('basic_config', 'ENVIRONMENT'),
                "general_channel"
            )

    @commands.command(brief="returns which branch the user is testing")
    @commands.has_role("Bot_manager")
    async def debuginfo(self, ctx):
        self.logger.info(f"[ManageCog debuginfo()] debuginfo command detected from {ctx.message.author}")
        if self.config.get_config_value("basic_config", "ENVIRONMENT") == 'TEST':
            await ctx.send(
                '```You are testing the latest commit of branch or pull request: '
                f'{self.config.get_config_value("basic_config", "BRANCH_NAME")}```'
            )
        return

    def check_text_command_test_environment(self, ctx):
        """
        this check is used by the TEST guild to ensure that each TEST container will only process incoming
         text commands that originate from channels that match the name of their branch
        :param ctx: the ctx object that is part of command parameters that are not slash commands
        :return:
        """
        if self.config.get_config_value('basic_config', 'ENVIRONMENT') != 'TEST':
            return True
        correct_test_guild_text_channel = (
            ctx.message.guild is not None and
            (ctx.channel.name == f"{self.config.get_config_value('basic_config', 'BRANCH_NAME').lower()}_bot_channel"
             or
             ctx.channel.name == self.config.get_config_value('basic_config', 'BRANCH_NAME').lower())
        )
        return correct_test_guild_text_channel

    @commands.Cog.listener()
    async def on_command(self, ctx):
        """
        Function that gets called whenever a text commmand gets called, being use for data gathering purposes
        :param ctx: the ctx object that is part of command parameters that are not slash commands
        :return:
        """
        if self.check_text_command_test_environment(ctx) and self.config.enabled("database_config", option="ENABLED"):
            await CommandStat.save_command_stat(CommandStat(
                epoch_time=datetime.datetime.now().timestamp(), channel_name=ctx.channel,
                command=ctx.command, invoked_with=ctx.invoked_with,
                invoked_subcommand=ctx.invoked_subcommand
            ))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Function that gets called when the script cant understand the command that the user invoked
        :param ctx: the ctx object that is part of command parameters that are not slash commands
        :param error: the error that was encountered
        :return:
        """
        if self.check_text_command_test_environment(ctx):
            if isinstance(error, commands.MissingRequiredArgument):
                e_obj = await embed(
                    self.logger,
                    ctx=ctx,
                    author=self.config.get_config_value('bot_profile', 'BOT_NAME'),
                    avatar=self.config.get_config_value('bot_profile', 'BOT_AVATAR'),
                    description=f"Missing argument: {error.param}"
                )
                if e_obj is not False:
                    await ctx.send(embed=e_obj)
            elif isinstance(error, commands.errors.CommandNotFound):
                return
            elif isinstance(error, discord.ext.commands.errors.MissingAnyRole):
                self.logger.error(f"{ctx.author} tried to run command {ctx.command}")
                await ctx.channel.send(
                    "You do not have adequate permission to run this command, incident will be reported"
                )
            elif isinstance(error, commands.errors.ArgumentParsingError):
                description = (
                    f"Uh-oh, seem like you have entered a badly formed string and wound up with error:"
                    f"\n'{error.args[0]}'\n\n[Technical Details link if you care to look]"
                    f"(https://discordpy.readthedocs.io/en/latest/ext/commands/api.html?"
                    f"highlight=argumentparsingerror#exceptions)\n\n"
                    f"**You have 20 seconds to copy your input to do a retry before "
                    f"I ensure it is wiped from the channel**"
                )
                error_type = f"{type(error)}"[8:-2]
                embed_obj = await embed(
                    logger=ctx.cog.logger, ctx=ctx, title=f"Error {error_type} encountered",
                    description=description, colour=WallEColour.ERROR
                )
                if embed_obj is not False:
                    message = await ctx.channel.send(
                        embed=embed_obj
                    )
                    await asyncio.sleep(20)
                    try:
                        await ctx.message.delete()
                    except discord.errors.NotFound:
                        pass
                    try:
                        await message.delete()
                    except discord.errors.NotFound:
                        pass
            else:
                # only prints out an error to the log if the string that was entered doesnt contain just "."
                pattern = r'[^\.]'
                if re.search(pattern, f"{error}"[9:-14]):
                    if type(error) is discord.ext.commands.errors.CheckFailure:
                        self.logger.warning(
                            f"[ManageCog on_command_error()] user {ctx.author} "
                            "probably tried to access a command they arent supposed to"
                        )
                    else:
                        print_wall_e_exception(error, error.__traceback__, error_logger=self.logger.error)
