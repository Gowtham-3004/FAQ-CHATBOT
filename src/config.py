from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Gemini
    gemini_api_key: str

    # MongoDB
    mongodb_uri: str
    mongodb_db: str = "faq_chatbot"
    mongodb_collection: str = "faqs"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
