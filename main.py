import logging
import os
import sys
import signal
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv
import httpx
import urllib.parse

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Define states for the conversations
(
    FIND_RVM_LOCATION, REPORT_LOCATION, REPORT_RVM, REPORT_STATUS, 
    REMINDER_FREQ, REMINDER_DAY, REMINDER_TIME
) = range(7)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about their choice."""
    reply_keyboard = [["/find"], ["/report"], ["/set"]]
    await update.message.reply_text(
        "<b>Welcome to BottleCanGowhere!</b>\n\n"
        "I'm here to assist you with Bottles & Cans Recycling. How can I help you today?\n"
        "/find Find Reverse Vending Machines (RVMs)\n"
        "/report Report RVM Status\n"
        "/set Set Reminders\n"
        "/about About\n"
        "/cancel Cancel",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    context.user_data.clear()
    return ConversationHandler.END
    
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provides information about the Recycle N Save initiative."""
    await update.message.reply_text(
        "Recycle N Save is a joint initiative by F&N and NEA to place Smart Reverse Vending Machines across Singapore "
        "to encourage recycling of used plastic drink bottles and aluminium drink cans amongst Singaporeans.\n"
        "https://recyclensave.sg/\n"
        "Singapore, 21 March 2023 – The National Environment Agency (NEA) has announced details of the beverage container return scheme (Scheme)."
        "Under the Scheme, all pre-packaged beverages in plastic bottles and metal cans ranging from 150 millilitres to 3 litres "
        "will have a refundable deposit of 10 cents. This deposit will be fully refunded when empty beverage containers are returned "
        "at designated return points.\n"
        "https://www.nea.gov.sg/media/news/news/index/the-beverage-container-return-scheme-highlights-singapore-s-commitment-to-tackle-packaging-waste"
    )

async def find_rvm_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the find RVM conversation and asks for the user's location or postal code."""
    markup = ReplyKeyboardMarkup(
        [[KeyboardButton("Share Location", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text(
        "To help you find the nearest RVMs, please:\n"
        "- Share your location or\n"
        "- Type the location, building name, or postal code.",
        reply_markup=markup
    )
    return FIND_RVM_LOCATION

async def find_rvm_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's location or search query and presents the nearest RVMs."""
    if update.message.location:
        curr_latitude, curr_longitude = update.message.location.latitude, update.message.location.longitude
    else:
        query = update.message.text.strip()
        try:
            curr_latitude, curr_longitude = await get_lat_long_from_query(query)
        except ValueError:
            await update.message.reply_text("Please try again with a valid location, building name, or postal code.")
            return FIND_RVM_LOCATION

    await find_nearest_rvms(update, context, curr_latitude, curr_longitude)
    context.user_data.clear()
    return ConversationHandler.END

async def get_lat_long_from_query(query: str) -> tuple:
    """Fetches latitude and longitude from a location, building, or postal code using OneMap API."""
    if not query.replace(" ", "").isalnum():
        raise ValueError("Invalid query: Only alphanumeric characters and spaces are allowed.")
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={encoded_query}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    data = response.json()
    if data['found'] > 0:
        return float(data['results'][0]['LATITUDE']), float(data['results'][0]['LONGITUDE'])
    else:
        raise ValueError("Invalid query or no results found")
        
async def find_nearest_rvms(update: Update, context: ContextTypes.DEFAULT_TYPE, curr_latitude: float, curr_longitude: float) -> None:
    """Finds the nearest RVMs based on the provided latitude and longitude."""
    directions_base_url = 'https://www.google.com/maps/dir/?api=1&destination='

    df = context.bot_data['df']
    df_copy = df.copy()
    df_copy['distances'] = df_copy.apply(
        lambda x: distance(x['Longitude'], x['Latitude'], curr_longitude, curr_latitude), axis=1
    )
    result_df = df_copy.sort_values('distances').iloc[0:3]

    response = "Here are the 3 nearest RVMs:\n"
    for _, row in result_df.iterrows():
        status_emoji = "🟢" if row['Status'] == "Working" else "🔴"
        nearby_bins = f'<b>[Test Feature] Nearby Bins:</b> {row["Nearby"]}' if row["Nearby"] not in ["None", None, float('nan')] else ""
        response += (
            f'{status_emoji} <b><u>{row["Name"]}</u></b> ({row["distances"]:.0f} meters) \n'
            f'{row["Address"]} \n'
            f'{row["Description"]} \n'
            f'<b>Hours:</b> {row["Hours"]} \n'
            f'<b>Status:</b> {row["Status"]} \n'
            f'{nearby_bins} \n'
            f'<b>Get Directions</b>: {directions_base_url}{row["Latitude"]},{row["Longitude"]} \n\n'
        )
    await update.message.reply_text(
        response, parse_mode='HTML', disable_web_page_preview=True,
        reply_markup=ReplyKeyboardRemove()
    )

async def report_rvm_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the report RVM conversation and asks for the user's location."""
    markup = ReplyKeyboardMarkup(
        [[KeyboardButton("Share Location", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True
    )
    await update.message.reply_text(
        "Sure, let's report the status of the RVM. First, I need to know your location. Can you please share your current location?",
        reply_markup=markup
    )
    return REPORT_LOCATION

async def report_rvm_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's location and presents the nearest RVMs."""
    curr_latitude, curr_longitude = update.message.location.latitude, update.message.location.longitude
    directions_base_url = 'https://www.google.com/maps/dir/?api=1&destination='

    df = context.bot_data['df']
    df_copy = df.copy()
    df_copy['distances'] = df_copy.apply(
        lambda x: distance(x['Longitude'], x['Latitude'], curr_longitude, curr_latitude), axis=1
    )
    result_df = df_copy.sort_values('distances').iloc[0:3]

    context.user_data['nearest_rvms'] = result_df

    response = "Thanks! Based on your location, here are the 3 nearest RVMs.\n"
    reply_keyboard = [[row['Name']] for _, row in result_df.iterrows()]
    response += "\nWhich RVM would you like to report on?"
    await update.message.reply_text(
        response, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return REPORT_RVM

async def report_rvm_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's RVM choice and asks for the status."""
    user_choice = update.message.text
    context.user_data['selected_rvm'] = user_choice
    rvm_name = context.user_data['nearest_rvms'].loc[
        context.user_data['nearest_rvms']['Name'] == user_choice, 'Name'
    ].values[0]
    reply_keyboard = [["Working", "Full"], ["Out of Order", "Other Issues"]]
    await update.message.reply_text(
        f"You've selected the RVM at {rvm_name}. What's the current status?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return REPORT_STATUS

async def report_rvm_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's status report and confirms the report."""
    user_choice = update.message.text
    context.user_data['rvm_status'] = user_choice
    rvm_name = context.user_data['nearest_rvms'].loc[
        context.user_data['nearest_rvms']['Name'] == context.user_data['selected_rvm'], 'Name'
    ].values[0]
    context.bot_data['df'].loc[context.bot_data['df']['Name'] == rvm_name, 'Status'] = user_choice

    response = f"Thank you for letting us know! The RVM at <u><b>{rvm_name}</b></u> is currently <u><b>{user_choice}</b></u>."
    
    if user_choice.lower() != "working":
        # Get the alternative 2 locations
        selected_rvm_index = context.user_data['nearest_rvms'].index[
            context.user_data['nearest_rvms']['Name'] == context.user_data['selected_rvm']
        ][0]
        alternative_rvms = context.user_data['nearest_rvms'].drop(selected_rvm_index).iloc[0:2]

        response += "\n\nHere are the statuses of the alternative 2 nearest RVMs:\n"
        directions_base_url = 'https://www.google.com/maps/dir/?api=1&destination='
        for _, row in alternative_rvms.iterrows():
            status_emoji = "🟢" if row['Status'] == "Working" else "🔴"
            nearby_bins = f'<b>[Test Feature] Nearby Bins:</b> {row["Nearby"]}' if row["Nearby"] != "None" else ""
            response += (
                f'{status_emoji} <b><u>{row["Name"]}</u></b> ({row["distances"]:.0f} meters) \n'
                f'{row["Address"]} \n'
                f'{row["Description"]} \n'
                f'<b>Hours:</b> {row["Hours"]} \n'
                f'<b>Status:</b> {row["Status"]} \n'
                f'{nearby_bins} \n'
                f'<b>Get Directions</b>: {directions_base_url}{row["Latitude"]},{row["Longitude"]} \n\n'
            )

    await update.message.reply_text(response, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML', disable_web_page_preview=True)
    context.user_data.clear()
    return ConversationHandler.END

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the set reminder conversation."""
    reply_keyboard = [["Monthly"]]
    await update.message.reply_text(
        "Great! Let's set up a reminder for you. How often would you like to be reminded to recycle your bottles and cans?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return REMINDER_FREQ

async def reminder_freq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's reminder frequency choice."""
    user_choice = update.message.text
    context.user_data['reminder_freq'] = user_choice

    if user_choice == "Monthly":
        await update.message.reply_text(
            "Okay, you've chosen a monthly reminder. Please enter the day of the month (1-31) that works best for you:"
        )
        return REMINDER_DAY
    else:
        await update.message.reply_text(
            "Currently, only monthly reminders are supported. Ending the conversation."
        )
        return ConversationHandler.END

async def reminder_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's reminder day choice."""
    day = update.message.text
    if not validate_reminder_day(day):
        await update.message.reply_text("Invalid day. Please enter a valid day of the month (1-31).")
        return REMINDER_DAY
    context.user_data['reminder_day'] = day
    await update.message.reply_text("What time would you like to receive the reminder? (e.g. 1030, 2230)")
    return REMINDER_TIME

async def reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the user's reminder time choice."""
    time = update.message.text
    if not validate_reminder_time(time):
        await update.message.reply_text("Invalid time. Please enter a valid time in 24-hour format (e.g. 1030, 2230).")
        return REMINDER_TIME
    context.user_data['reminder_time'] = time

    reminder_freq = context.user_data['reminder_freq']
    reminder_day = context.user_data['reminder_day']
    reminder_time = context.user_data['reminder_time']

    await update.message.reply_text(
        f"Perfect! Your reminder is all set. Every month on day {reminder_day} at {reminder_time}, you'll receive this message:\n"
        f"\"It's time to recycle! Don't forget to bring your bottles and cans to the nearest RVM.\""
    )
    context.user_data.clear()
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles unknown commands."""
    await update.message.reply_text("Welcome! Please use /start to begin.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    await update.message.reply_text("An error occurred while processing your request. Please try again later.")

def distance(lon1, lat1, lon2, lat2):
    """Calculates the distance between two points on the Earth using the haversine formula."""
    R = 6371000  # radius of the Earth in meters

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

def validate_reminder_day(day: str) -> bool:
    """Validates the reminder day input."""
    return day.isdigit() and 1 <= int(day) <= 31

def validate_reminder_time(time: str) -> bool:
    """Validates the reminder time input."""
    return time.isdigit() and len(time) == 4 and 0 <= int(time[:2]) < 24 and 0 <= int(time[2:]) < 60

def signal_handler(sig, frame):
    """Handles the signal for saving data and exiting."""
    print('Saving data and exiting...')
    save_dataframe(application.bot_data['df'])
    sys.exit(0)

def save_dataframe(df):
    """Saves the DataFrame to a CSV file."""
    df.to_csv('data.csv', index=False)
    print("Data saved to data.csv")

def main() -> None:
    """Main function to run the bot."""
    global application
    df = pd.read_csv('data.csv')
    load_dotenv()
    TOKEN = os.getenv('BOT_TOKEN')
    if not TOKEN:
        raise Exception('Bot token is not defined')

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Store the DataFrame in the bot_data
    application.bot_data['df'] = df

    find_rvm_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("find", find_rvm_start)],
        states={
            FIND_RVM_LOCATION: [
                MessageHandler(filters.LOCATION | filters.TEXT & ~filters.COMMAND, find_rvm_location)
            ],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel)],
        allow_reentry=True
    )
    # Add report RVM conversation handler
    report_rvm_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("report", report_rvm_start)],
        states={
            REPORT_LOCATION: [MessageHandler(filters.LOCATION, report_rvm_location)],
            REPORT_RVM: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_rvm_choice)],
            REPORT_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_rvm_status)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel)],
        allow_reentry=True
    )
    # Add reminder conversation handler
    reminder_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set", set_reminder)],
        states={
            REMINDER_FREQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_freq)],
            REMINDER_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_day)],
            REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reminder_time)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel)],
        allow_reentry=True
    )

    application.add_handler(CommandHandler("start", start), 1)
    application.add_handler(CommandHandler("about", about), 1)
    application.add_handler(find_rvm_conv_handler, 2)
    application.add_handler(report_rvm_conv_handler, 3)
    application.add_handler(reminder_conv_handler, 4)
    application.add_error_handler(error_handler)

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run the bot until the user presses Ctrl-C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Save the data when the program exits
        save_dataframe(application.bot_data['df'])

if __name__ == '__main__':
    main()