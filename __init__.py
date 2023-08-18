import discord
from discord._types import ClientT
from discord.ext import commands
from discord import app_commands, Interaction
from psycopg2.extensions import connection, cursor

import breadcord
from data.modules.nebulus_manager.BaseCog import BaseModule


class TagEditorView(discord.ui.Modal, title="Tag editor"):
    content = discord.ui.TextInput(label="Tag content", style=discord.TextStyle.paragraph)

    def __init__(self, bot: breadcord.Bot, conn: connection, cur: cursor, server_id: int, tag: str):
        super().__init__()

        self.bot = bot
        self.conn = conn
        self.cur = cur
        self.server_id = server_id
        self.tag = tag

        self.cur.execute(
            "SELECT tag_content FROM tags WHERE server_id = %s and tag_name = %s",
            (self.server_id, self.tag)
        )

        self.exists = False
        res = self.cur.fetchall()

        if res:
            self.content.default = res[0][0]
            self.exists = True

    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        if self.exists:
            self.cur.execute(
                "UPDATE tags "
                "SET tag_content = %s "
                "WHERE server_id = %s AND tag_name = %s",
                (self.content.value, interaction.guild.id, self.tag)
            )
            await interaction.response.send_message(f"`{self.tag}` Updated!")
        else:
            self.cur.execute(
                "INSERT INTO tags(server_id, tag_name, tag_content) VALUES (%s, %s, %s)",
                (self.server_id, self.tag, self.content.value)
            )
            await interaction.response.send_message(f"`{self.tag}` Updated!")
        self.conn.commit()


class NebulusTags(
    BaseModule,
    commands.GroupCog,
    group_name="tag",
    group_description="Customise your Nebulus experience"
):
    def __init__(self, module_id: str, /):
        super().__init__(module_id)

        # TODO: This is a temporary way of getting a module. This will be changed once Breadcord is fixed.
        self.connection: connection = self.bot.cogs.get("NebulusManager").connection
        self.cursor: cursor = self.connection.cursor()

        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS tags ("
            "    server_id  bigint NOT NULL,"
            "    tag_name    text NOT NULL,"
            "    tag_content text NOT NULL,"
            "    PRIMARY KEY (server_id)"
            ");"
        )
        self.connection.commit()

    @app_commands.command()
    @app_commands.default_permissions(manage_messages=True)
    async def set(self, interaction: Interaction, tag: str):
        await interaction.response.send_modal(TagEditorView(self.bot, self.connection, self.cursor, interaction.guild.id, tag))

    @app_commands.command()
    async def get(self, interaction: Interaction, tag: str):
        self.cursor.execute(
            "SELECT tag_content FROM tags WHERE server_id = %s and tag_name = %s",
            (interaction.guild.id, tag)
        )

        res = self.cursor.fetchall()

        if res:
            await interaction.response.send_message(res[0][0])
        else:
            await interaction.response.send_message(f"Cannot find tag named `{tag}`", ephemeral=True)


async def setup(bot: breadcord.Bot):
    await bot.add_cog(NebulusTags("nebulus_tags"))
