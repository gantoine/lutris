"""Manage RomM libraries"""

import concurrent.futures
import json
import os
from gettext import gettext as _

from gi.repository import Gtk

from lutris import settings
from lutris.exceptions import UnavailableGameError
from lutris.gui.dialogs import InputDialog
from lutris.installer import AUTO_ELF_EXE, AUTO_WIN32_EXE
from lutris.installer.installer_file import InstallerFile
from lutris.services.base import SERVICE_LOGIN, OnlineService
from lutris.services.service_game import ServiceGame
from lutris.services.service_media import ServiceMedia
from lutris.util import linux
from lutris.util.http import HTTPError, Request
from lutris.util.log import logger


class RommIcon(ServiceMedia):
    """Romm icon"""

    service = "romm"
    size = (70, 70)
    dest_path = os.path.join(settings.CACHE_DIR, "romm/icons")
    file_patterns = ["%s.png"]
    api_field = "icon"


class RommSmallIcon(RommIcon):
    size = (35, 35)


class RommBigIcon(RommIcon):
    size = (105, 105)


class RommGame(ServiceGame):
    """Service game for Romm games"""

    service = "romm"

    @classmethod
    def new_from_romm(cls, romm_game):
        """Converts a game from the API to a service game usable by Lutris"""
        service_game = RommGame()
        service_game.appid = romm_game["id"]
        service_game.slug = romm_game["slug"]
        service_game.name = romm_game["name"]
        service_game.details = json.dumps(romm_game)
        return service_game


class RommService(OnlineService):
    """Service for Romm"""

    id = "romm"
    _matcher = "romm"
    name = _("Romm")
    icon = "romm"
    online = True
    drm_free = True
    runner = "libretro"
    medias = {"small_icon": RommSmallIcon, "icon": RommIcon, "big_icon": RommBigIcon}
    default_format = "icon"

    cookies_path = os.path.join(settings.CACHE_DIR, "romm/cookies")
    cache_path = os.path.join(settings.CACHE_DIR, "romm/library/")
    config_path = os.path.join(settings.CONFIG_DIR, "romm/config.json")

    def __init__(self):
        super().__init__()

        # Check the config file for the RomM host
        if os.path.exists(self.config_path):
            with open(self.config_path) as config_file:
                config = json.load(config_file)
                self.host_url = config["host"]
                self.redirect_uri = self.host_url + "/"

    @property
    def login_url(self):
        """Return the login URL"""
        return self.host_url + "/login?next=/"

    @property
    def api_url(self):
        """Return the API URL"""
        return self.host_url + "/api"

    def configure(self, parent=None):
        """Configure the RomM service"""
        config_dialog = InputDialog({
            "parent": parent,
            "title": _("RomM Host"),
            "question": _("Enter the RomM host URL WITHOUT a trailing slash"),
            "initial_value": "https://demo.romm.app",
        })

        result = config_dialog.run()
        if result != Gtk.ResponseType.OK:
            config_dialog.destroy()
            return

        new_host = config_dialog.user_value
        config_dialog.destroy()

        # Remove the trailing slash if it exists
        if new_host.endswith("/"):
            new_host = new_host[:-1]
        self.host_url = new_host

        # Store the new host in the config file
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as config_file:
            json.dump({"host": new_host}, config_file)

    def login(self, parent=None):
        """Connect to RomM"""
        if not self.host_url:
            self.configure(parent)

        super().login(parent)

    def login_callback(self, url):
        """Called after the user has logged in successfully"""
        SERVICE_LOGIN.fire(self)

    def is_connected(self):
        """This doesn't actually check if the authentication
        is valid like the GOG service does.
        """
        return self.is_authenticated()

    def load(self):
        """Load the user's Romm library"""
        try:
            library = self.get_library()
        except ValueError as ex:
            raise RuntimeError("Failed to get Romm library. Try logging out and back-in.") from ex

        romm_games = []
        seen = set()
        for game in library:
            if game["name"] in seen:
                continue
            romm_games.append(RommGame.new_from_romm(game))
            seen.add(game["name"])
        for game in romm_games:
            game.save()
        return romm_games

    def make_api_request(self, url):
        """Make an authenticated request to the Romm API"""
        request = Request(url, cookies=self.load_cookies())
        try:
            request.get()
        except HTTPError:
            logger.error("Failed to request %s", url)
            return
        return request.json

    def get_library(self):
        """Return the games from the user's library"""
        url = f"{self.api_url}/roms?order_by=name&order_dir=asc&limit=250"
        return self.make_api_request(url)

    def get_installer_files(self, installer, installer_file_id, _selected_extras):
        pass

    def generate_installer(self, db_game):
        details = json.loads(db_game["details"])

    def get_installed_runner_name(self, db_game):
        return self.runner
