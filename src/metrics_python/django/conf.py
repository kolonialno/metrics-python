from django.conf import settings as django_settings


class Settings:
    @property
    def OBSERVE_DUBLICATE_QUERIES(self) -> bool:
        return bool(
            getattr(
                django_settings,
                "METRICS_PYTHON_OBSERVE_DUBLICATE_QUERIES",
                False,
            )
        )

    @property
    def PRINT_DUPLICATE_QUERIES(self) -> bool:
        return bool(
            getattr(
                django_settings,
                "METRICS_PYTHON_PRINT_DUPLICATE_QUERIES",
                False,
            )
        )


settings = Settings()
