from lutris import settings
from lutris.database import sql
from lutris.util.log import logger


class ServiceGameCollection:
    @classmethod
    def get_service_games(cls, searches=None, filters=None, excludes=None, sorts=None):
        return sql.filtered_query(
            settings.DB_PATH, "service_games", searches=searches, filters=filters, excludes=excludes, sorts=sorts
        )

    @classmethod
    def get_for_service(cls, service):
        if not service:
            raise ValueError("No service provided")
        return sql.filtered_query(settings.DB_PATH, "service_games", filters={"service": service})

    @classmethod
    def get_game(cls, service, value, field="appid"):
        """Return a single"""
        if not service:
            raise ValueError("No service provided")
        if not value:
            raise ValueError("No value provided")
        results = sql.filtered_query(settings.DB_PATH, "service_games", filters={"service": service, field: value})
        if not results:
            return
        if len(results) > 1:
            logger.warning("More than one game found for %s %s on %s", field, value, service)
        return results[0]
