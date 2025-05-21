# Telegram Channel Forwarder Guide

## Overview
This project is a Telegram channel message forwarder that monitors a source channel for new messages, processes them by removing any links, adds a custom referral link, and forwards the modified messages to a target channel. It's built using the Telethon Python library for interacting with the Telegram API.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system follows a simple event-driven architecture:
1. A Telegram client connects to the Telegram API using provided credentials
2. The client listens for new messages in a source channel
3. When a new message is detected, it processes the message (removing links, adding referral)
4. The modified message is then forwarded to a target channel

The architecture is lightweight and stateless, with all configuration managed through environment variables.

## Key Components

### telegram_forwarder.py
The main script responsible for:
- Connecting to the Telegram API
- Monitoring the source channel
- Processing messages (removing links, adding referral links)
- Forwarding processed messages to the target channel

This file implements event handlers for Telegram messages and includes error handling for common issues like rate limiting and permission errors.

### start.sh
A shell script that:
- Checks for required dependencies
- Installs necessary Python packages
- Creates a .env file from .env.example if one doesn't exist
- Launches the main telegram_forwarder.py script

This script serves as the entry point for the application and handles basic setup.

### Environment Configuration
The application uses environment variables for configuration, with a sample provided in .env.example:
- Telegram API credentials (API_ID, API_HASH, BOT_TOKEN)
- Channel information (SOURCE_CHANNEL, TARGET_CHANNEL)
- Referral link (REFERRAL_LINK)

## Data Flow
1. **Input**: New messages posted in the source Telegram channel
2. **Processing**:
   - Message text is extracted
   - URLs are removed using regex pattern matching
   - Referral link is appended to the message
3. **Output**: Processed message is forwarded to the target channel

There is no persistent data storage in this application. All operations happen in memory.

## External Dependencies
The application relies on the following external dependencies:
- **Telethon** (>=1.40.0): Python library for interacting with Telegram's API
- **Python dotenv** (implied from the deployment configuration): For loading environment variables

These dependencies are managed through pip and the package requirements are defined in pyproject.toml.

## Deployment Strategy
The application is designed to be deployed in a Replit environment:
1. The .replit file defines the project configuration for Replit
2. The deployment runs the start.sh script, which:
   - Installs required dependencies
   - Sets up environment variables
   - Starts the Telegram forwarder

The application is designed to run as a long-lived process that continuously monitors the source channel and forwards messages.

## Implementation Notes
- The message processing includes regex-based link removal
- Error handling is implemented for network issues and rate limiting
- The application properly handles both text messages and media
- The code is structured to allow for easy modification of the source/target channels and referral link

## Development Guidelines
When modifying the code:
1. Always test changes with a test channel before using production channels
2. Be aware of Telegram's rate limits to avoid triggering anti-spam measures
3. Keep API credentials secure and never commit them to the repository
4. Make sure error handling is robust, especially for network or permission issues