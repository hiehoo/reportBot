from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ParseMode
import schedule
import time
from datetime import datetime
import pytz
import logging
from database import Database
from config import BOT_TOKEN, ADMIN_IDS, TIMEZONE, DEFAULT_REMINDER_TIME, DEFAULT_TOPIC_ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ReportBot:
    def __init__(self):
        self.updater = Updater(token=BOT_TOKEN, use_context=True)
        self.dp = self.updater.dispatcher
        self.db = Database()
        self.setup_handlers()
        self.setup_commands()

    def setup_commands(self):
        """Set up bot commands that appear in the menu"""
        commands = [
            ('start', 'Show bot information and help menu'),
            ('report', 'Submit your daily report'),
            ('status', 'Check who has reported today'),
            ('help', 'Show help information'),
        ]
        
        if ADMIN_IDS:
            commands.extend([
                ('trigger', 'Manually trigger reminder'),
                ('settime', 'Set daily reminder time (HH:MM)'),
                ('settopic', 'Set topic for reminders'),
            ])
        
        try:
            self.updater.bot.set_my_commands(commands)
        except Exception as e:
            logger.error(f"Failed to set commands: {str(e)}")

    def setup_handlers(self):
        self.dp.add_handler(CommandHandler("start", self.start_command))
        self.dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, self.handle_new_chat_members))
        self.dp.add_handler(CommandHandler("report", self.handle_report))
        self.dp.add_handler(CommandHandler("status", self.check_status))
        self.dp.add_handler(CommandHandler("trigger", self.manual_trigger, filters=Filters.user(user_id=ADMIN_IDS)))
        self.dp.add_handler(CommandHandler("settime", self.set_reminder_time, filters=Filters.user(user_id=ADMIN_IDS)))
        self.dp.add_handler(CommandHandler("settopic", self.set_topic, filters=Filters.user(user_id=ADMIN_IDS)))

    def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        welcome_message = (
            "👋 *Welcome to Daily Report Bot!*\n\n"
            "I'm here to help manage daily reports in your group.\n\n"
            "*Available Commands:*\n"
            "📝 /report - Submit your daily report\n"
            "📊 /status - Check who has reported today\n"
            "Daily reminders will be sent at 10:00 AM (GMT+7).\n"
            "Don't forget to submit your reports! 😊"
        )
        update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )

    def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command"""
        help_message = (
            "*📚 Daily Report Bot Help*\n\n"
            "*Basic Commands:*\n"
            "• /report <your_report> - Submit your daily report\n"
            "  Example: `/report Working on feature X`\n\n"
            "• /status - See who has reported today\n\n"
            "*How to use:*\n"
            "1. Wait for the daily reminder or use commands anytime\n"
            "2. Submit your report using the /report command\n"
            "3. Check submission status with /status\n\n"
            "*Report Format:*\n"
            "Simply type what you worked on after the /report command\n\n"
            "*Reminder Schedule:*\n"
            "• Weekdays: Regular daily report reminder\n"
            "• Weekends: Special weekend reminder\n"
        )

        if update.effective_user.id in ADMIN_IDS:
            help_message += (
                "\n*Admin Commands:*\n"
                "• /trigger - Manually send reminder\n"
                "• /settime <HH:MM> - Change reminder time\n"
                "  Example: `/settime 09:30`"
            )

        update.message.reply_text(
            help_message,
            parse_mode=ParseMode.MARKDOWN
        )

    def handle_new_chat_members(self, update: Update, context: CallbackContext):
        new_members = update.message.new_chat_members
        for member in new_members:
            if member.id == context.bot.id:
                chat_id = update.message.chat_id
                group_name = update.message.chat.title
                topic_id = update.message.message_thread_id or DEFAULT_TOPIC_ID
                
                logger.info(f"Bot added to group: {group_name} (ID: {chat_id}, Topic: {topic_id})")
                self.db.add_group(chat_id, group_name, topic_id, TIMEZONE)
                
                welcome_msg = "👋 Xin chào! Bot đã sẵn sàng gửi nhắc nhở report daily."
                context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=topic_id if topic_id != 0 else None,
                    text=welcome_msg
                )

    def handle_report(self, update: Update, context: CallbackContext):
        user = update.message.from_user
        chat_id = update.message.chat_id
        report_content = ' '.join(context.args)
        
        if not report_content:
            help_message = (
                "📝 *How to submit a report:*\n\n"
                "Use /report followed by your report content.\n"
                "*Example:*\n"
                "`/report Completed task A and working on task B`\n\n"
                "*Note:* Be clear and concise in your report."
            )
            update.message.reply_text(
                help_message,
                parse_mode=ParseMode.MARKDOWN
            )
            return

        if self.db.add_report(user.id, user.username, report_content, chat_id, TIMEZONE):
            update.message.reply_text(
                "✅ *Report submitted successfully!*\n"
                "Use /status to see all submissions.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.message.reply_text(
                "❌ Failed to submit report. Please try again.",
                parse_mode=ParseMode.MARKDOWN
            )

    def check_status(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        current_date = datetime.now(pytz.timezone(TIMEZONE)).date()
        
        reported_users = self.db.get_reported_users_with_reports(chat_id, current_date)
        
        message = "📊 *Today's Report Status:*\n\n"
        if reported_users:
            message += "*Reported:*\n"
            for username, report in reported_users:
                message += f"✅ @{username} \\- `{report}`\n"
        else:
            message += "No reports submitted yet today\\."
        
        update.message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN_V2
        )

    def manual_trigger(self, update: Update, context: CallbackContext):
        self.send_reminder(context)
        update.message.reply_text("✅ Manual reminder sent!")

    def set_reminder_time(self, update: Update, context: CallbackContext):
        if not context.args or len(context.args) != 1:
            update.message.reply_text("Please provide time in HH:MM format")
            return

        try:
            time_str = context.args[0]
            datetime.strptime(time_str, '%H:%M')
            schedule.clear()
            schedule.every().day.at(time_str).do(self.send_reminder, context)
            update.message.reply_text(f"⏰ Reminder time set to {time_str}")
        except ValueError:
            update.message.reply_text("❌ Invalid time format. Please use HH:MM")

    def set_topic(self, update: Update, context: CallbackContext):
        """Handle /settopic command"""
        if not context.args or len(context.args) != 1:
            update.message.reply_text(
                "Please provide the topic ID.\n"
                "Example: `/settopic 123`\n"
                "Use 0 for main group chat.",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        try:
            topic_id = int(context.args[0])
            chat_id = update.message.chat_id
            
            # Update the group's topic ID in the database
            self.db.add_group(chat_id, update.message.chat.title, topic_id)
            
            update.message.reply_text(
                f"✅ Reminder topic has been set to: {topic_id if topic_id != 0 else 'main chat'}",
                parse_mode=ParseMode.MARKDOWN
            )
        except ValueError:
            update.message.reply_text("❌ Invalid topic ID. Please provide a number.")

    def send_reminder(self, context: CallbackContext):
        groups = self.db.get_all_groups()
        current_time = datetime.now(pytz.timezone(TIMEZONE))
        is_weekend = current_time.weekday() >= 5

        if is_weekend:
            message = "🌅 Cuối tuần vui vẻ! Các em yêu ơi report daily nhé ❤️"
        else:
            message = "☀️ Các em yêu ơi report daily nhé"

        for group in groups:
            chat_id = group[0]
            topic_id = group[2] if len(group) > 2 else DEFAULT_TOPIC_ID
            
            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=topic_id if topic_id != 0 else None,
                    text=message,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to group {chat_id} topic {topic_id}: {str(e)}")

    def run(self):
        schedule.every().day.at(DEFAULT_REMINDER_TIME).do(self.send_reminder, self.updater)
        self.updater.start_polling()
        
        while True:
            schedule.run_pending()
            time.sleep(1) 