# BottleCanGowhere Bot

BottleCanGowhere is a Telegram bot designed to assist users with finding Reverse Vending Machines (RVMs) for recycling bottles and cans, reporting the status of RVMs, and setting reminders for recycling.

## Features

- **Find RVMs**: Locate the nearest RVMs based on your current location or a search query.
- **Report RVM Status**: Report the status of an RVM and get alternative nearby RVMs if the selected one is not working.
- **Set Reminders**: Set monthly reminders to recycle your bottles and cans.

## Prerequisites

- Python 3.7+
- Telegram Bot Token (You can get this from [BotFather](https://core.telegram.org/bots#botfather))
- Required Python packages (listed in `requirements.txt`)

## Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/koztkozt/BottleCanGowhere.git
    cd BottleCanGowhere
    ```
2. **Set up environment variables**:
    Create a `.env` file in the root directory and add your Telegram Bot Token:
    ```env
    BOT_TOKEN=your-telegram-bot-token
    ```

3. **Prepare the data**:
    Ensure you have a `data.csv` file in the root directory with the necessary RVM data.

## Running the Bot

To run the bot, execute the following command:
```sh
docker-compose up --build
```

## User Journey

### Start the Bot

1. **Start**: The user initiates the bot by sending the `/start` command. The bot greets the user and presents options to find RVMs, report RVM status, or set reminders.

### Finding RVMs

1. **Find RVMs**: The user selects the `/find` option.
2. **Share Location or Enter Query**: The bot asks the user to share their location or enter a location, building name, or postal code.
3. **Display Nearest RVMs**: The bot processes the input and displays the three nearest RVMs with details and directions.

### Reporting RVM Status

1. **Report RVM Status**: The user selects the `/report` option.
2. **Share Location**: The bot asks the user to share their current location.
3. **Select RVM**: The bot displays the three nearest RVMs and asks the user to select one.
4. **Report Status**: The user reports the status of the selected RVM.
5. **Confirmation and Alternatives**: The bot confirms the report and, if the RVM is not working, provides the status of the next two nearest RVMs.

### Setting Reminders

1. **Set Reminders**: The user selects the `/set` option.
2. **Choose Frequency**: The bot asks the user to choose the reminder frequency (currently only monthly is supported).
3. **Enter Day**: The user enters the day of the month for the reminder.
4. **Enter Time**: The user enters the time for the reminder in 24-hour format.
5. **Confirmation**: The bot confirms the reminder setup.

## Error Handling

If an error occurs, the bot logs the error and informs the user that an error occurred while processing their request.

## Exiting the Bot

To safely exit the bot and save the data, use `Ctrl+C` in the terminal where the bot is running. The bot will save the current state of the data to `data.csv`.
