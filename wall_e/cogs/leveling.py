import asyncio
import json

import discord
from discord.ext import commands
from wall_e_models.models import Level, UserPoint

from utilities.embed import embed
from utilities.file_uploading import start_file_uploading
from utilities.paginate import paginate_embed
from utilities.setup_logger import Loggers


class Leveling(commands.Cog):

    def __init__(self, bot, config, bot_channel_manager):
        log_info = Loggers.get_logger(logger_name="Leveling")
        self.logger = log_info[0]
        self.debug_log_file_absolute_path = log_info[1]
        self.error_log_file_absolute_path = log_info[2]
        self.levels_have_been_changed = False
        self.bot = bot
        self.config = config
        self.guild = None
        self.user_points = {}
        self.levels = {}
        self.xp_system_ready = False
        self.council_channel = None
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
                self.logger, self.guild, self.bot, self.config, self.debug_log_file_absolute_path, "leveling_debug"
            )

    @commands.Cog.listener(name="on_ready")
    async def upload_error_logs(self):
        if self.config.get_config_value('basic_config', 'ENVIRONMENT') != 'TEST':
            while self.guild is None:
                await asyncio.sleep(2)
            await start_file_uploading(
                self.logger, self.guild, self.bot, self.config, self.error_log_file_absolute_path, "leveling_error"
            )

    @commands.Cog.listener(name="on_ready")
    async def load_points_into_dict(self):
        """
        Loads the current level info and user points into the self.level and self.user_points dict respectively
        to quicker read access
        :return:
        """
        if self.config.enabled("database_config", option="ENABLED"):
            if not await Level.level_points_have_been_imported():
                self.logger.info("[Leveling load_points_into_dict()] loading levels into DB and dict")
                with open('resources/mee6_levels/levels.json') as f:
                    self.levels = {
                        int(level_number): await Level.create_level(
                            int(level_number),
                            level_info['total_xp_required_for_level'],
                            level_info['xp_needed_to_level_up_to_next_level'],
                            role_name=level_info['role_name'] if 'role_name' in level_info else None,
                        )
                        for (level_number, level_info) in json.load(f).items()
                    }
            elif len(self.levels) == 0:
                self.logger.info("[Leveling load_points_into_dict()] loading level from DB into dict")
                self.levels = await Level.load_to_dict()
            self.logger.info("[Leveling load_points_into_dict()] levels loaded in DB and dict")
            self.user_points = await UserPoint.load_to_dict()
            self.logger.info("[Leveling load_points_into_dict()] UserPoints loaded into dict")
            self.logger.info("[Leveling load_points_into_dict()] XP system ready")
            self.xp_system_ready = True

    # async def load_data_from_mee6_endpoint_and_json(self):
    #     await self.bot.wait_until_ready()
    #     logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] loading XP data")
    #     await Level.clear_all_entries()
    #     await UserPoint.clear_all_entries()
    #
    #     if not await Level.level_points_have_been_imported():
    #         logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] loading levels into DB and dict")
    #         with open('resources/mee6_levels/levels.json') as f:
    #             self.levels = {
    #                 int(level_number): await Level.create_level(
    #                     int(level_number),
    #                     level_info['total_xp_required_for_level'],
    #                     level_info['xp_needed_to_level_up_to_next_level'],
    #                     role_name=level_info['role_name'] if 'role_name' in level_info else None,
    #                 )
    #                 for (level_number, level_info) in json.load(f).items()
    #             }
    #     elif len(self.levels) == 0:
    #         logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] loading level from DB into dict")
    #         self.levels = await Level.load_to_dict()
    #     logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] levels loaded in DB and dict")
    #
    #     if not await UserPoint.user_points_have_been_imported():
    #         logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] loading UserPoints into DB and dict")
    #         page = 0
    #         all_users_loaded = False
    #         while not all_users_loaded:
    #             r = requests.get(
    #                 f"https://mee6.xyz/api/plugins/levels/leaderboard/228761314644852736?page={page}&limit=1000",
    #                 headers={
    #                     'Authorization': self.config.get_config_value('basic_config', 'MEE6_AUTHORIZATION')
    #                 }
    #             )
    #             if r.status_code == 200:
    #                 data = json.loads(r.text)
    #                 if len(data['players']) > 0:
    #                     page += 1
    #                     for player in data['players']:
    #                         # player = {
    #                         #     'avatar': '3fd2cc8fda2a0af3b1a06bb27d5151f0',
    #                         #     'detailed_xp': [
    #                         #         8349,  # how much of the "XP needed to level up" I have so far
    #                         #         11980,  # XP needed to level up
    #                         #         197219  # Total XP I have so far
    #                         #     ],
    #                         #     'discriminator': '6816',
    #                         #     'guild_id': '228761314644852736',
    #                         #     'id': '288148680479997963',
    #                         #     'level': 44,
    #                         #     'message_count': 9858,  # total messages sent
    #                         #     'username': 'modernNeo',
    #                         #     'xp': 197219  # Total XP
    #                         # }
    #                         user_id = int(player['id'])
    #                         message_count = int(player['message_count'])
    #                         level = int(player['level'])
    #                         user_xp = int(player['xp'])
    #                         self.user_points[user_id] = await UserPoint.create_user_point(
    #                             user_id, points=user_xp, message_count=message_count, level=level
    #                         )
    #                 else:
    #                     all_users_loaded = True
    #             elif r.status_code == 429:
    #                 logger.info(
    #                     "[Leveling load_data_from_mee6_endpoint_and_json()] wall_e is currently rate-limited by the"
    #                     " mee6 website. exiting now"
    #                 )
    #                 await asyncio.sleep(120)
    #                 exit(0)
    #             else:
    #                 await asyncio.sleep(120)
    #     elif len(self.user_points) == 0:
    #         logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] loading UserPoints from DB into dict")
    #         self.user_points = await UserPoint.load_to_dict()
    #     logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] UserPoints loaded in DB and dict")
    #     logger.info("[Leveling load_data_from_mee6_endpoint_and_json()] XP data loaded")
    #     self.xp_system_ready = True

    @commands.Cog.listener(name="on_ready")
    async def create_council_channel(self):
        """
        Gets the council_channel that will be used or any mod-relevant messages for Leveling cog class
        :return:
        """
        while self.guild is None:
            await asyncio.sleep(2)
        council_channel_id = await self.bot_channel_manager.create_or_get_channel_id(
            self.logger, self.guild, self.config.get_config_value('basic_config', 'ENVIRONMENT'),
            "leveling"
        )
        self.council_channel = discord.utils.get(
            self.guild.channels, id=council_channel_id
        )

    @commands.Cog.listener(name='on_message')
    async def on_message(self, message):
        """
        called whenever a new message is sent on the guild to potentially increase the user points for
         the message's author
        :param message: the message that was sent that tripped the function call
        :return:
        """
        while self.guild is None:
            await asyncio.sleep(2)
        if not message.author.bot:
            if not self.xp_system_ready:
                return
            message_author_id = message.author.id
            if message_author_id not in self.user_points:
                self.logger.info(
                    f"[Leveling on_message()] could not detect author {message.author}({message_author_id}) "
                    "in the user_points dict"
                )
                self.user_points[message_author_id] = await UserPoint.create_user_point(message_author_id)
            if await self.user_points[message_author_id].increment_points():
                self.logger.info(
                    f"[Leveling on_message()] increased points for {message.author}({message_author_id}) "
                    f" and alerting them that they are in a new level in channel {message.channel}"
                )
                level = self.levels[self.user_points[message_author_id].level_number]
                if level.role_id is not None:
                    role = message.guild.get_role(level.role_id)
                    if role is not None:
                        self.logger.info(
                            f"[Leveling on_message()] the new level {level.number} "
                            f" for user {message.author}({message_author_id}) has the role {role} "
                            f"associated with it. Assigning to user"
                        )
                        await message.author.add_roles(role)
                    else:
                        self.logger.info(
                            f"[Leveling on_message()] the new level {level.number} "
                            f" for user {message.author}({message_author_id}) has an invalid role {role} associated "
                            f"with it. Alerting the council to this "
                        )
                        await self.council_channel.send(
                            "The XP role could not be found. Please call `.remove_level_name <level_number>` "
                            "to confirm that you want the XP roles deleted or re-create the roles:\n\n"
                            "Role Name - Linked XP Level\n"
                            f"{level.role_name} - {level.number}"
                        )

                await message.channel.send(
                    f"<@{message_author_id}> is now **level {level.number}**!"
                )
                self.logger.info(f"[Leveling on_message()] message sent to {message.author}({message_author_id})")

    @commands.Cog.listener(name="on_ready")
    async def ensure_roles_exist_and_have_right_users(self):
        """
        Runs once a day to detect if the levels have been changed and therefore the user's level for their points
        need to be updated
        :return:
        """
        while self.guild is None:
            await asyncio.sleep(2)
        if self.config.enabled("database_config", option="ENABLED"):
            while not self.xp_system_ready or self.council_channel is None:
                await asyncio.sleep(2)
            while True:
                if self.levels_have_been_changed:
                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()] updating user and roles for XP system"
                    )
                    levels_with_a_role = [level for level in self.levels.values() if level.role_name is not None]
                    levels_with_a_role.sort(key=lambda level: level.number)
                    # ordering level roles in an ascending order

                    guild_roles = []
                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()]"
                        f" ensuring that all {len(levels_with_a_role)} XP roles exist"
                    )
                    xp_roles_that_are_missing = {}
                    for level_with_role in levels_with_a_role:
                        role = discord.utils.get(self.guild.roles, name=level_with_role.role_name)
                        if role is not None:
                            guild_roles.append(role)
                            level_with_role.role_id = role.id
                            await level_with_role.async_save()
                        else:
                            xp_roles_that_are_missing[level_with_role.role_name] = level_with_role.number
                    if len(xp_roles_that_are_missing) == 0:
                        self.logger.info(
                            "[Leveling ensure_roles_exist_and_have_right_users()] all"
                            f" {len(levels_with_a_role)} XP roles exist"
                        )
                    else:
                        xp_roles_that_are_missing = [
                            f"{role_name} - {role_number}"
                            for role_name, role_number in xp_roles_that_are_missing.items()
                        ]
                        xp_roles_that_are_missing = "\n".join(xp_roles_that_are_missing)
                        await self.council_channel.send(
                            "The following XP roles could not be found. Please call "
                            "`.remove_level_name <level_number>` to confirm that you want the XP roles deleted or "
                            "re-create the roles:\n\nRole Name - Linked XP Level\n"
                            f"{xp_roles_that_are_missing}"
                        )
                        self.logger.info(
                            "[Leveling ensure_roles_exist_and_have_right_users()]"
                            f" Moderators have been informed that {len(xp_roles_that_are_missing)}"
                            f" XP roles do not exist "
                        )
                    members = await self.guild.fetch_members().flatten()

                    # sorts the members in ascending order by their total cls
                    members_with_points = [member for member in members if member.id in self.user_points]
                    members_with_points.sort(key=lambda member: self.user_points[member.id].points)

                    role_index = 0
                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()] ensuring that members with XP points"
                        " have the right XP roles"
                    )
                    prev_number_of_members_fixed = number_of_members_fixed = 0
                    prev_number_of_members_skipped = number_of_members_skipped = 0
                    number_of_members = len(members_with_points)
                    for member_with_point in members_with_points:
                        while (
                                len(levels_with_a_role) > (role_index + 1) and
                                self.user_points[member_with_point.id].points >=
                                levels_with_a_role[role_index + 1].total_points_required
                        ):
                            role_index += 1
                        number_of_retries = 0
                        successful = False
                        skip = False
                        while not successful and not skip:
                            skip = False
                            successful = False
                            try:
                                number_of_retries += 1
                                await member_with_point.remove_roles(*guild_roles[role_index + 1:])
                                await member_with_point.add_roles(*guild_roles[:role_index + 1])
                                successful = True
                                number_of_retries = 0
                                number_of_members_fixed += 1
                            except Exception as e:
                                self.logger.error(
                                    "[Leveling ensure_roles_exist_and_have_right_users()] encountered "
                                    f"following error when fixing the roles for member {member_with_point}, \n{e}"
                                )
                                if number_of_retries == 5:
                                    self.logger.error(
                                        f"[Leveling ensure_roles_exist_and_have_right_users()] "
                                        f"tried to fix the"
                                        f" permissions for member {member_with_point} 5 times, moving onto "
                                        f"next member"
                                    )
                                    skip = True
                                    number_of_retries = 0
                                    number_of_members_skipped += 1
                                else:
                                    self.logger.error(
                                        "[Leveling ensure_roles_exist_and_have_right_users()] "
                                        "will try again in one minute"
                                    )
                                    await asyncio.sleep(60)
                        if (
                                (prev_number_of_members_skipped != number_of_members_skipped and
                                 number_of_members_skipped % 10 == 0) or
                                (prev_number_of_members_fixed != number_of_members_fixed and
                                 number_of_members_fixed % 10 == 0)
                        ):
                            prev_number_of_members_skipped = number_of_members_skipped
                            prev_number_of_members_fixed = number_of_members_fixed
                            self.logger.info(
                                f"[Leveling ensure_roles_exist_and_have_right_users()] current_progress so far..."
                                f" number_of_members_fixed = {number_of_members_fixed}/{number_of_members} || "
                                f"number_of_members_skipped = {number_of_members_skipped}/{number_of_members}"
                            )
                        await asyncio.sleep(5)

                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()] ensured that the members with XP points"
                        " have the right XP roles")

                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()] ensuring that members without XP points"
                        " don't have any XP roles "
                    )
                    for member_without_points in [member for member in members if member.id not in self.user_points]:
                        try:
                            await member_without_points.remove_roles(*guild_roles)
                        except Exception as e:
                            self.logger.error(
                                "[Leveling ensure_roles_exist_and_have_right_users()] encountered "
                                f"following error when fixing the roles for member {member_without_points}, \n{e}"
                            )
                        await asyncio.sleep(5)
                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()] ensured that members without XP points"
                        " don't have any XP roles "
                    )
                    self.levels_have_been_changed = False
                    self.logger.info(
                        "[Leveling ensure_roles_exist_and_have_right_users()] "
                        "users and role are now updated for XP system"
                    )
                await asyncio.sleep(86400)

    @commands.Cog.listener(name='on_member_join')
    async def re_assign_roles(self, member: discord.Member):
        """
        Set the necessary XP levels to the member that was joined in case they previously were in the guild
        :param member: the member whose join triggered the function call and may need their XP levels re-assigned
        :return:
        """
        if self.config.enabled("database_config", option="ENABLED"):
            if member.id not in self.user_points:
                return
            while not self.xp_system_ready:
                await asyncio.sleep(2)
            self.logger.info(
                f"[Leveling re_assign_roles()] ensuring a {member} with {self.user_points[member.id].points} "
                f"points wil get their roles back if they leave and re-join the guild"
            )

            levels_with_a_role = [
                level for level in self.levels.values()
                if level.role_name is not None and level.total_points_required <= self.user_points[member.id].points
            ]
            self.logger.info(
                f"[Leveling re_assign_roles()] seems user {member} is entitled to the following levels which have"
                f" a role: {levels_with_a_role}"
            )

            guild_roles = [
                member.guild.get_role(self.levels[level_with_role.number].role_id)
                for level_with_role in levels_with_a_role
            ]
            guild_roles = [guild_role for guild_role in guild_roles if guild_role]

            self.logger.info(
                f"[Leveling re_assign_roles()] will get the {guild_roles} roles added back to {member}"
            )
            number_of_retries = 0
            success = False
            while number_of_retries < 5 and success is False:
                try:
                    number_of_retries += 1
                    await member.add_roles(*guild_roles)
                    success = True
                except Exception as e:
                    self.logger.info(
                        f"[Leveling re_assign_roles()] encountered following error when fixing the roles for "
                        f"member {member}, \n{e}"
                    )
                    if number_of_retries < 5:
                        self.logger.info("[Leveling re_assign_roles()] will try again in one minute")
                        await asyncio.sleep(60)
            if success:
                self.logger.info(f"[Leveling re_assign_roles()] XP roles fixed for user {member}")
            else:
                self.logger.error(
                    f"[Leveling re_assign_roles()] could not fix the XP roles for user {member}"
                )

    @commands.command(
        brief="associates an XP level with the role with the specified name",
        help=(
            'associates an existing role with the specified name for the specified level or it renames a '
            'role that is already assigned to the specified level\n\n'
            'Arguments:\n'
            '---level number: the number for the XP level to set\n'
            '---new role name: the name to set for the role associated with the XP level for "level number"\n\n'
            'Example:\n'
            '---.set_level_name 2 "Vim User"\n\n'
        ),
        usage='<level number> "new role name"'
    )
    @commands.has_any_role("Minions", "Moderator")
    async def set_level_name(self, ctx, level_number: int, new_role_name: str):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        self.logger.info(
            f"[Leveling set_level_name()] received request to set name for level {level_number} to {new_role_name}"
        )
        existing_xp_level_with_specified_role_name = [
            level for level in self.levels.values() if level.role_name == new_role_name
        ]
        self.logger.info(
            f"[Leveling set_level_name()] len(existing_xp_level_with_specified_role_name)="
            f"{len(existing_xp_level_with_specified_role_name)}"
        )
        if len(existing_xp_level_with_specified_role_name) > 0:
            await ctx.send(
                f"role {new_role_name} is already in use by level "
                f"{existing_xp_level_with_specified_role_name[0].number}"
            )
            return
        if level_number not in list(self.levels.keys()):
            self.logger.info(f"[Leveling set_level_name()] {level_number} is not valid")
            current_levels = sorted([level.number for level in self.levels.values() if level.role_id is None])
            current_levels = [f"{level}" for level in current_levels]

            current_levels = ", ".join(current_levels)
            await ctx.send(
                f"you specified an incorrect level, the only levels available for setting their names "
                f"are :{current_levels}"
            )
            return
        if self.levels[level_number].role_id is None:
            self.logger.info(f"[Leveling set_level_name()] no role_id detected for level {level_number}")
            # level does not yet have a role associated with it
            role = discord.utils.get(self.guild.roles, name=new_role_name)
            if role is None:
                self.logger.info(
                    f"[Leveling set_level_name()] could not find the role {new_role_name}"
                    f" to associate with {level_number}"
                )
                await ctx.send(f"could not find role {new_role_name}. ")
            else:
                self.logger.info(
                    f"[Leveling set_level_name()] associating level {level_number} with role {new_role_name}"
                )
                await self.levels[level_number].set_level_name(new_role_name, role.id)
                self.levels_have_been_changed = True
                await ctx.send(
                    f"assigned role {new_role_name} for level {level_number}. "
                    f"Will take about 24 hours to apply role to the right people.\n\n"
                    f"Don't forget to correct the role position"
                )

        else:
            self.logger.info(f"[Leveling set_level_name()] role_id detected for level {level_number}")
            role = ctx.guild.get_role(self.levels[level_number].role_id)
            if role is None:
                self.logger.info(
                    f"[Leveling set_level_name()] detected role_id detected for level {level_number} is invalid"
                )
                # the XP level is getting a new role since the role it was associated with was an error
                role = discord.utils.get(self.guild.roles, name=new_role_name)
                if role is None:
                    await ctx.send(f"could not find role {new_role_name}. ")
                else:
                    await self.levels[level_number].set_level_name(new_role_name, role.id)
                    self.logger.info(
                        f"[Leveling set_level_name()] set flag to associate level {level_number} with role"
                        f" {role.name}"
                    )
                    self.levels_have_been_changed = True
                    await ctx.send(
                        f"Associated role {new_role_name} for level {level_number}. "
                        f"Will take about 24 hours to apply role to the right people.\n\n"
                        f"Don't forget to correct the role position"
                    )
            else:
                old_name = role.name
                self.logger.info(
                    f"[Leveling set_level_name()] renaming role {old_name} to {new_role_name} for level"
                    f" {level_number}"
                )
                await role.edit(name=new_role_name)
                await self.levels[level_number].rename_level_name(new_role_name)
                await ctx.send(f"renamed role {old_name} to {new_role_name} for level {level_number}")

    @commands.command(
        brief="unmaps the any role that is currently mapped to the specified level",
        help=(
            'de-associates an existing role with the specified name from the specified level\n\n'
            'Arguments:\n'
            '---level number: the number for the XP level to remove the role association from\n\n'
            'Example:\n'
            '---.remove_level_name 2\n\n'
        ),
        usage='<level number>'
    )
    @commands.has_any_role("Minions", "Moderator")
    async def remove_level_name(self, ctx, level_number: int):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        if self.levels[level_number].role_id is None:
            self.logger.info(
                f"[Leveling remove_level_name()] resetting role info to Null for level {level_number}"
            )
            await self.levels[level_number].remove_role()
            await ctx.send(f"level {level_number} does not have an existing role associated with it")
            return
        role_name = self.levels[level_number].role_name
        await self.levels[level_number].remove_role()
        self.logger.info(
            f"[Leveling remove_level_name()] resetting role info to Null for level {level_number}"
        )
        self.levels_have_been_changed = True
        await ctx.send(
            f"role {role_name} was disassociated from level {level_number}\n\n"
            f"Don't forget to delete the role"
        )

    @commands.command(
        brief="Get the XP rank for first tagged user or calling user",
        help=(
            'Arguments:\n'
            '---[@user] : the tagged user\'s whose rank to return\n\n'
            'Example:\n'
            '---.rank\n'
            '---.rank @user\n\n'
        ),
        usage='[@user]'
    )
    async def rank(self, ctx):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        message_author = ctx.author if len(ctx.message.mentions) == 0 else ctx.message.mentions[0]
        message_author_id = message_author.id
        if message_author_id not in self.user_points:
            await ctx.send("specified user is not being tracked")
            return
        if self.user_points[message_author_id].hidden and message_author_id != ctx.author.id:
            await ctx.send("This user has hidden their score")
            return
        xp_required_to_level_up = await self.user_points[message_author_id].get_xp_needed_to_level_up_to_next_level()

        description = f"""
        {self.user_points[message_author_id].level_up_specific_points} / {xp_required_to_level_up} XP

        Total Messages: {self.user_points[message_author_id].message_count}

        """

        e_obj = await embed(
            self.logger,
            ctx=ctx,
            avatar=message_author.avatar.url,
            author=message_author.name,
            title=f"{message_author.name}'s Stat Card",
            content=[
                (
                    f"Rank # {await self.user_points[message_author_id].get_rank()}",
                    f"Level # {self.user_points[message_author_id].level_number}")
            ],
            description=description
        )
        if e_obj is not None:
            await ctx.send(embed=e_obj)

    @commands.command(
        brief="Shows a list of all the XP levels and their associated roles and whether or not the roles exist"
    )
    @commands.has_any_role("Minions", "Moderator")
    async def levels(self, ctx):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        levels_with_a_role = [level for level in self.levels.values() if level.role_name is not None]
        levels_with_a_role.sort(key=lambda level: level.number)

        levels_with_a_valid_role = []
        levels_with_an_invalid_role = []
        for level_with_role in levels_with_a_role:
            role = discord.utils.get(self.guild.roles, name=level_with_role.role_name)
            if role is not None:
                levels_with_a_valid_role.append(level_with_role)
            else:
                levels_with_an_invalid_role.append(level_with_role)

        descriptions_to_embed = []
        description_to_embed = "\nLevel Number - Level Role\n"
        for (index, level) in enumerate(levels_with_a_valid_role):
            if index % 10 == 0 and index > 0:
                descriptions_to_embed.append(description_to_embed)
                description_to_embed = "\nLevel Number - Level Role\n"
            description_to_embed += f"{level.number} - {level.role_name}\n"
        if description_to_embed != "\nLevel Number - Level Role\n":
            descriptions_to_embed.append(description_to_embed)

        description_to_embed = "\nLevel Number - Invalid Level Role\n"
        for (index, level) in enumerate(levels_with_an_invalid_role):
            if index % 10 == 0 and index > 0:
                descriptions_to_embed.append(description_to_embed)
                description_to_embed = "\nLevel Number - Invalid Level Role\n"
            description_to_embed += f"{level.number} - {level.role_name}\n"
        if description_to_embed != "\nLevel Number - Invalid Level Role\n":
            descriptions_to_embed.append(description_to_embed)

        await paginate_embed(self.logger, self.bot, self.config, descriptions_to_embed, title="Levels", ctx=ctx)

    @commands.command(brief="shows the current leaderboards")
    async def ranks(self, ctx):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        user_points = self.user_points.copy()
        user_points = [
            user_point for user_point in list(user_points.values())
            if (
                (user_point.user_id == ctx.author.id and user_point.hidden) or
                (user_point.user_id != ctx.author.id and not user_point.hidden)
            )
        ]
        user_points.sort(key=lambda x: x.points, reverse=True)
        descriptions_to_embed = []
        description_to_embed = "\nUser - Messages - Experience - Level\n"
        rank = 1
        for (index, user_point) in enumerate(user_points):
            if index % 10 == 0 and index > 0:
                descriptions_to_embed.append(description_to_embed)
                description_to_embed = "\nRank - User - Messages - Experience - Level\n"
            description_to_embed += (
                f"{rank} - <@{user_point.user_id}> - {user_point.message_count} - {user_point.points}"
                f" - {user_point.level_number}\n"
            )
            rank += 1
        if description_to_embed != "\nUser - Messages - Experience - Level\n":
            descriptions_to_embed.append(description_to_embed)
        if len(descriptions_to_embed) == 0:
            await ctx.send("No users currently being tracked")
        else:
            await paginate_embed(self.logger, self.bot, self.config, descriptions_to_embed, ctx=ctx)

    @commands.command(
        brief="Hide a user's ranking from .rank @user and .ranks",
        help=(
            'Arguments:\n'
            '---[@user] : the tagged user\'s whose rank to hide\n\n'
            'Example:\n'
            '---.hide_xp\n'
            '---.hide_xp @user\n\n'
        ),
        usage='[@user]'
    )
    async def hide_xp(self, ctx):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        user_to_hide = ctx.author if len(ctx.message.mentions) == 0 else ctx.message.mentions[0]
        if user_to_hide.id != ctx.author.id:
            user_roles = [
                role.name for role in sorted(ctx.author.roles, key=lambda x: int(x.position), reverse=True)
            ]
            if 'Minions' not in user_roles:
                await ctx.send(
                    "You do not have adequate permission to hide another user's rank, incident will be reported"
                )
                return
        if self.user_points[user_to_hide.id].hidden:
            await ctx.send(
                "You are already hidden" if user_to_hide.id == ctx.author.id else
                f"User {user_to_hide} is already hidden"
            )
        else:
            await self.user_points[user_to_hide.id].hide_xp()
            await ctx.send(
                "You are now hidden" if user_to_hide.id == ctx.author.id else
                f"User {user_to_hide} is now hidden"
            )

    @commands.command(
        brief="Makes a user's ranking visible again in .rank @user and .ranks",
        help=(
            'Arguments:\n'
            '---[@user] : the tagged user\'s whose rank to show\n\n'
            'Example:\n'
            '---.show_xp\n'
            '---.show_xp @user\n\n'
        ),
        usage='[@user]'
    )
    async def show_xp(self, ctx):
        if not self.xp_system_ready:
            await ctx.send("level command is not yet ready...")
            return
        user_to_show = ctx.author if len(ctx.message.mentions) == 0 else ctx.message.mentions[0]
        if user_to_show.id != ctx.author.id:
            user_roles = [
                role.name for role in sorted(ctx.author.roles, key=lambda x: int(x.position), reverse=True)
            ]
            if 'Minions' not in user_roles:
                await ctx.send(
                    "You do not have adequate permission to show another user's rank, incident will be reported"
                )
                return

        if not self.user_points[user_to_show.id].hidden:
            await ctx.send(
                "You are already visible" if user_to_show.id == ctx.author.id else
                f"User {user_to_show} is already visible"
            )
        else:
            await self.user_points[user_to_show.id].show_xp()
            await ctx.send(
                "You are now visible" if user_to_show.id == ctx.author.id else
                f"User {user_to_show} is now visible"
            )
