# -*- coding: utf-8 -*-
# Copyright (c) 2024 Manuel Schneider
#
# https://wiki.archlinux.org/title/Aurweb_RPC_interface
# https://aur.archlinux.org/rpc/swagger
# https://aur.archlinux.org/rpc/openapi.json
#

import json
from datetime import datetime
from pathlib import Path
from shutil import which
from time import sleep
from urllib import request, parse

from albert import *

md_iid = "5.0"
md_version = "2.1.1"
md_name = "AUR"
md_description = "Query and install AUR packages"
md_license = "MIT"
md_url = "https://github.com/albertlauncher/albert-plugin-python-aur"
md_readme_url = "https://github.com/albertlauncher/albert-plugin-python-aur/blob/main/README.md"
md_authors = ["@ManuelSchneid3r"]
md_maintainers = ["@mparati31"]


class Plugin(PluginInstance, GeneratorQueryHandler):

    aur_url = "https://aur.archlinux.org/packages/"
    baseurl = 'https://aur.archlinux.org/rpc/'

    def __init__(self):
        PluginInstance.__init__(self)
        GeneratorQueryHandler.__init__(self)

        if which("yaourt"):
            self.install_cmdline = "yaourt -S aur/%s"
        elif which("pacaur"):
            self.install_cmdline = "pacaur -S aur/%s"
        elif which("yay"):
            self.install_cmdline = "yay -S aur/%s"
        elif which("paru"):
            self.install_cmdline = "paru -S aur/%s"
        else:
            info("No supported AUR helper found.")
            self.install_cmdline = None

    def defaultTrigger(self):
        return 'aur '

    @staticmethod
    def icon():
        return makeImageIcon(Path(__file__).parent / "arch.svg")

    @staticmethod
    def packageIcon():
        return makeComposedIcon(Plugin.icon(), makeGraphemeIcon("📦"))

    def emptyQueryItem(self):
        return StandardItem(
            id=self.id(),
            text=self.name(),
            subtext="Enter a query to search the AUR",
            icon_factory=Plugin.packageIcon,
            actions=[Action("open-aur", "Open AUR packages website", lambda: openUrl(self.aur_url))]
        )

    def errorItem(self, msg: str):
        return StandardItem(
            id=self.id(),
            text="Error",
            subtext=msg,
            icon_factory=lambda: makeComposedIcon(Plugin.icon(), makeGraphemeIcon("⚠️"))
        )

    def items(self, ctx):
        for _ in range(50):
            sleep(0.01)
            if not ctx.isValid:
                return

        query = ctx.query.strip()

        if not query:
            yield [self.emptyQueryItem()]
            return

        params = {
            'v': '5',
            'type': 'search',
            'by': 'name',
            'arg': query
        }
        url = "%s?%s" % (self.baseurl, parse.urlencode(params))
        req = request.Request(url)

        with request.urlopen(req) as response:
            data = json.loads(response.read().decode())

        if data['type'] == "error":
            yield [self.errorItem(data['error'])]
        else:
            results = []
            results_json = data['results']
            results_json.sort(key=lambda i: i['Name'])
            results_json.sort(key=lambda i: len(i['Name']))

            for entry in results_json:
                name = entry['Name']
                item = StandardItem(
                    id=self.id(),
                    icon_factory=Plugin.packageIcon,
                    text=f"{entry['Name']} {entry['Version']}"
                )

                subtext = f"⭐{entry['NumVotes']}"
                if entry['Maintainer'] is None:
                    subtext += ', Unmaintained!'
                if entry['OutOfDate']:
                    subtext += ', Out of date: %s' % datetime.fromtimestamp(entry['OutOfDate']).strftime("%F")
                if entry['Description']:
                    subtext += ', %s' % entry['Description']
                item.subtext = subtext

                actions = []
                if self.install_cmdline:
                    pacman = self.install_cmdline.split(" ", 1)[0]
                    actions.append(Action(
                        id="inst",
                        text="Install using %s" % pacman,
                        callable=lambda n=name: runTerminal(
                            script=self.install_cmdline % n + " ; exec $SHELL"
                        )
                    ))
                    actions.append(Action(
                        id="instnc",
                        text="Install using %s (noconfirm)" % pacman,
                        callable=lambda n=name: runTerminal(
                            script=self.install_cmdline % n + " --noconfirm ; exec $SHELL"
                        )
                    ))

                actions.append(Action("open-aursite", "Open AUR website",
                                      lambda n=name: openUrl(f"{self.aur_url}{n}/")))

                if entry['URL']:
                    actions.append(Action("open-website", "Open project website",
                                          lambda u=entry['URL']: openUrl(u)))

                item.actions = actions
                results.append(item)

            yield results
