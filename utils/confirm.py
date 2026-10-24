# utils/confirm.py
import discord


class ConfirmView(discord.ui.View):
    """Confirm / Cancel buttons that only the command author can press."""
    def __init__(self, user_id: int, on_confirm, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.on_confirm = on_confirm      # async function(interaction)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Working...", view=None)
        await self.on_confirm(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="Cancelled.", view=None)
