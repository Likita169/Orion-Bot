import discord
from discord.ext import commands, tasks
import json
from datetime import datetime

class Report(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activity_data = self.load_data()
        self.daily_report.start()  # Bắt đầu vòng lặp gửi báo cáo

    # Đọc dữ liệu từ file JSON
    def load_data(self):
        try:
            with open("activity_data.json", "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    # Gửi báo cáo hoạt động hàng ngày
    @tasks.loop(hours=24)
    async def daily_report(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        
        report_channel_id = config.get("REPORT_CHANNEL_ID")
        if not report_channel_id:
            print("❌ Không tìm thấy ID kênh báo cáo!")
            return

        channel = self.bot.get_channel(report_channel_id)
        if not channel:
            print("❌ Bot không tìm thấy kênh báo cáo trong server!")
            return

        today = datetime.now().strftime("%d/%m/%Y")
        report = f"📅 **Báo cáo hoạt động ngày {today}**\n\n"

        if not self.activity_data:
            report += "Không có ai hoạt động hôm nay! 💤"
        else:
            for user_id, data in self.activity_data.items():
                member = self.bot.get_user(int(user_id))
                if member:
                    report += f"**{member.name}**: {data['days_active']} ngày hoạt động 🏆\n"

        await channel.send(report)

    # Lệnh thủ công để gửi báo cáo (!report)
    @commands.command()
    async def report(self, ctx):
        await self.daily_report()

# Hàm setup để load cog vào bot chính
async def setup(bot):
    await bot.add_cog(Report(bot))
