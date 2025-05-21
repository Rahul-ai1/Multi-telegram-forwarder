#!/bin/bash

# Check if .env file exists, if not create one from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit the .env file if needed before running the bot again."
fi

# Run the bot
echo "Starting the Telegram forwarder bot..."
python telegram_forwarder.py
