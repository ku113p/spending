# Gemini Code Understanding

## Project Overview

This project is a Telegram bot for managing receipts. It allows users to upload receipt images, from which the bot extracts information using an AI-powered pipeline. The extracted data is then stored in a MongoDB database, and users can interact with the bot to view, manage, and export their receipt data.

The project is built with Python and utilizes several key technologies:

*   **Telegram Bot:** The bot is built using the `python-telegram-bot` library.
*   **AI Pipeline:** The receipt processing pipeline is built with `langgraph` and `langchain`, which suggests a multi-step process involving OCR, data extraction, and user interaction for verification.
*   **Database:** MongoDB is used to store receipt information, with `pymongo` as the driver.
*   **Caching:** Redis is used for caching, likely for storing session data or intermediate pipeline results.
*   **Dependency Management:** The project uses uv for managing Python dependencies.
*   **Containerization:** Docker and Docker Compose are used to manage the project's services, including MongoDB, Mongo Express, and Redis.

## Building and Running

### 1. Start the Services

The project uses Docker Compose to run its services. To start the services, run the following command:

```bash
docker-compose up -d
```

This will start the following services:

*   `mongo`: A MongoDB instance.
*   `mongo-express`: A web-based interface for MongoDB.
*   `redis`: A Redis instance.

### 2. Install Dependencies

The project uses uv to manage its dependencies. To install the dependencies, run the following command in the `spending` directory:

```bash
uv pip install -e .
```

### 3. Run the Bot

To run the bot, execute the following command in the `spending` directory:

```bash
uv run python main.py
```

This will start the Telegram bot, which will then be able to receive and process messages.

### 4. Run Jupyter Lab

The project also includes a Jupyter Lab environment for interactive development and data analysis. To start Jupyter Lab, run the following command in the `spending` directory:

```bash
uv run jupyter lab
```

## AI Pipeline

The core of this project is the AI pipeline that processes receipt images. The pipeline is built using `langgraph` and is defined in the `spending/graphs/pipelines/` directory. It is a state machine that orchestrates a series of sub-graphs to perform the following steps:

1.  **`full_pipeline`**: This is the main pipeline that orchestrates the entire receipt processing workflow.

2.  **`image_to_normailized_receipt`**: This sub-graph takes an image file path and returns a normalized receipt. It consists of two nodes:
    *   **`photo_to_receipt`**: This node uses an OpenAI vision model to extract the raw text from the receipt image.
    *   **`receipt_normalize`**: This node uses an AI agent to normalize the raw text into a structured format, including a list of products, prices, and the shop's name.

3.  **Duplicate Check**: The `full_pipeline` calculates a hash of the image and checks if a receipt with the same hash already exists in the database.

4.  **User Interaction**: If the receipt is new, it's saved to the database, and the user is asked to review the extracted data. If the receipt already exists, the user is asked how to proceed (overwrite, review, or do nothing).

5.  **`correct_receipt`**: If the user requests corrections, this sub-graph is invoked. It uses an AI agent to update the receipt data based on the user's feedback.

## Development Conventions

*   **Dependency Management:** Dependencies are managed with uv and are listed in the `pyproject.toml` file.
*   **Modular Structure:** The code is organized into modules with clear responsibilities, such as `bot`, `db`, `graphs`, and `exports`.
*   **AI Pipelines:** The use of `langgraph` suggests that AI-powered workflows are defined as state machines, which allows for a clear and maintainable implementation of complex processes.
*   **Database Abstraction:** Database interactions are abstracted through a set of "operations" defined in the `db` module, which provides a consistent interface for interacting with the database.
*   **Configuration:** The project uses a `config.py` file to manage configuration settings, which is a good practice for separating configuration from code.
*   **Containerization:** The use of Docker and Docker Compose for managing services is a good practice for ensuring a consistent and reproducible development environment.
