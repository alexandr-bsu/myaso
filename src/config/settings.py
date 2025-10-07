from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class SupabaseSettings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class OpenRouterSettings(BaseSettings):
    base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    openrouter_api_key: str
    model_id: str
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class LangFuseSettings(BaseSettings):
    langfuse_public_key: str 
    langfuse_secret_key: str
    langfuse_host: str 
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

class Settings(BaseModel):
    supabase: SupabaseSettings = SupabaseSettings()
    openrouter: OpenRouterSettings = OpenRouterSettings()
    langfuse: LangFuseSettings = LangFuseSettings()

settings = Settings() 