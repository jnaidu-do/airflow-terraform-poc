from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    AIRFLOW_API_URL: str = "http://airflow-webserver:8080/api/v1"
    AIRFLOW_USERNAME: str = "admin"
    AIRFLOW_PASSWORD: str = "admin"
    AIRFLOW_DAG_ID: str = "terraform_dag"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = ""
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 