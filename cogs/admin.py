import discord
from discord.ext import commands
from discord import app_commands
import json

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_data(self):
        try:
            with open("activity_data.json", "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_data(self, data):
        with open("activity_data.json", "w") as file:
            json.dump(data, file, indent=4)

    # Slash Command: Reset dữ liệu hoạt động
    @app_commands.command(name="reset", description="Reset toàn bộ dữ liệu hoạt động (chỉ Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset(self, interaction: discord.Interaction):
        self.save_data({})
        await interaction.response.send_message("🔄 **Dữ liệu hoạt động đã được reset!**", ephemeral=True)

    # Slash Command: Kiểm tra số ngày hoạt động của thành viên
    @app_commands.command(name="check", description="Xem số ngày hoạt động của thành viên")
    async def check(self, interaction: discord.Interaction, member: discord.Member):
        data = self.load_data()
        user_id = str(member.id)

        if user_id in data:
            days_active = data[user_id]["days_active"]
            await interaction.response.send_message(f"📊 **{member.name} đã hoạt động {days_active} ngày.**")
        else:
            await interaction.response.send_message(f"❌ **{member.name} chưa có dữ liệu hoạt động.**")

    # Slash Command: Chỉnh sửa số ngày hoạt động
    @app_commands.command(name="setdays", description="Chỉnh sửa số ngày hoạt động của thành viên (chỉ Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setdays(self, interaction: discord.Interaction, member: discord.Member, days: int):
        if days < 0:
            await interaction.response.send_message("❌ **Số ngày phải lớn hơn hoặc bằng 0.**", ephemeral=True)
            return

        data = self.load_data()
        user_id = str(member.id)

        if user_id not in data:
            data[user_id] = {"days_active": 0, "last_active_date": None}

        data[user_id]["days_active"] = days
        self.save_data(data)

        await interaction.response.send_message(f"✅ **Đã cập nhật số ngày hoạt động của {member.name} thành {days} ngày!**")

# Hàm setup để load cog vào bot chính
async def setup(bot):
    await bot.add_cog(Admin(bot))
