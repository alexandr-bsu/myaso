from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
import os
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()


class SupabaseSettings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class OpenRouterSettings(BaseSettings):
    # base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str
    model_id: str
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class LangFuseSettings(BaseSettings):
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AlibabaSettings(BaseSettings):
    base_alibaba_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    alibaba_key: str = ""
    embedding_model_id: str = "text-embedding-v4"
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Fallback to environment variables if not loaded from .env
        if not self.base_alibaba_url or self.base_alibaba_url == "":
            self.base_alibaba_url = os.getenv(
                "BASE_ALIBABA_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            )

        if not self.alibaba_key or self.alibaba_key == "":
            self.alibaba_key = os.getenv("ALIBABA_KEY", "")

        if not self.embedding_model_id or self.embedding_model_id == "":
            self.embedding_model_id = os.getenv(
                "EMBEDDING_MODEL_ID", "text-embedding-v4"
            )

        print(f"AlibabaSettings loaded - base_url: {self.base_alibaba_url}")
        print(
            f"AlibabaSettings loaded - api_key: {self.alibaba_key[:10] if self.alibaba_key else 'None'}..."
        )


class Settings(BaseModel):
    supabase: SupabaseSettings = SupabaseSettings()
    openrouter: OpenRouterSettings = OpenRouterSettings()
    alibaba: AlibabaSettings = AlibabaSettings()
    langfuse: LangFuseSettings = LangFuseSettings()


# Debug environment variables
print("=== Environment Variables Debug ===")
print(f"BASE_ALIBABA_URL from env: {os.getenv('BASE_ALIBABA_URL')}")
print(f"ALIBABA_KEY from env: {os.getenv('ALIBABA_KEY', 'Not found')[:10]}...")
print("===================================")

settings = Settings()
