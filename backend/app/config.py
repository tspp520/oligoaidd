"""OligoLab application configuration (pydantic-settings)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "OligoLab"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 7130
    WORKERS: int = 4
    CORS_ORIGINS: str = "*"

    # LDAP 域账号
    LDAP_HOST: str = "10.1.1.56"
    LDAP_PORT: int = 389
    LDAP_BASE_DN: str = "DC=shangpharma,DC=com"
    LDAP_DOMAINS: str = "CP.shangpharma.com,CD-GW.shangpharma.com,CE.shangpharma.com"

    # 文献与知识库：md 文档主目录（每个文档一个同名子文件夹）
    LITERATURE_DOCS_DIR: str = "./backend/literature_docs"

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    AUTH_ENABLED: bool = True

    # PostgreSQL（独立库）
    PG_HOST: str = "127.0.0.1"
    PG_PORT: int = 5434
    PG_DB: str = "oligolab"
    PG_USER: str = "oligolab"
    PG_PASSWORD: str = ""
    PG_POOL_MIN: int = 2
    PG_POOL_MAX: int = 10

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def ldap_domain_list(self):
        return [d.strip() for d in self.LDAP_DOMAINS.split(",") if d.strip()]

    @property
    def pg_dsn(self) -> str:
        return f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = {"env_file": ".env", "env_prefix": "OLIGOLAB_"}


settings = Settings()
