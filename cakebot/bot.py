#!/usr/bin/env python

# Copyright 2011, 2013 OpenStack Foundation
# Copyright 2012 Hewlett-Packard Development Company, L.P.
# Copyright 2018 Matt Smith (matthew.smith491@gmail.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import collections
import daemon
import io
import irc.bot
import json
import logging.config
import os
import time
import ssl
import sys

try:
    import daemon.pidlockfile as pid_file_module
except ImportError:
    # as of python-daemon 1.6 it doesn't bundle pidlockfile anymore
    # instead it depends on lockfile-0.9.1
    import daemon.pidfile as pid_file_module

# https://bitbucket.org/jaraco/irc/issue/34/
# irc-client-should-not-crash-on-failed
# ^ This is why pep8 is a bad idea.
irc.client.ServerConnection.buffer_class.errors = 'replace'
ANTI_FLOOD_SLEEP = 2
DOC_URL = 'https://github.com/mattsmithdatera/cakebot/blob/master/README.rst'


class CakeBot(irc.bot.SingleServerIRCBot):
    log = logging.getLogger("cakebot.bot")

    def __init__(self, nickname, password, server, port, channel):
        if port == 6697:
            factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            irc.bot.SingleServerIRCBot.__init__(self,
                                                [(server, port)],
                                                nickname, nickname,
                                                connect_factory=factory)
        else:
            irc.bot.SingleServerIRCBot.__init__(self,
                                                [(server, port)],
                                                nickname, nickname)
        self.nickname = nickname
        self.password = password
        self.channel = channel
        self.identify_msg_cap = False

    def on_nicknameinuse(self, c, e):
        self.log.debug("Nickname in use, releasing")
        c.nick(c.get_nickname() + "_")
        c.privmsg("nickserv", "identify %s " % self.password)
        c.privmsg("nickserv", "ghost %s %s" % (self.nickname, self.password))
        c.privmsg("nickserv", "release %s %s" % (self.nickname, self.password))
        time.sleep(ANTI_FLOOD_SLEEP)
        c.nick(self.nickname)

    def on_welcome(self, c, e):
        self.identify_msg_cap = False
        self.log.debug("Requesting identify-msg capability")
        c.cap('REQ', 'identify-msg')
        c.cap('END')
        if (self.password):
            self.log.debug("Identifying to nickserv")
            c.privmsg("nickserv", "identify %s " % self.password)
        self.log.info("Joining %s" % self.channel)
        c.join(self.channel)
        time.sleep(ANTI_FLOOD_SLEEP)

    def on_cap(self, c, e):
        self.log.debug("Received cap response %s" % repr(e.arguments))
        if e.arguments[0] == 'ACK' and 'identify-msg' in e.arguments[1]:
            self.log.debug("identify-msg cap acked")
            self.identify_msg_cap = True

    def usage(self, channel):
        self.send(channel, "Format is '#cakebot COMMAND [PARAMETERS]'")
        self.send(channel, "See doc at: " + DOC_URL)

    def send_test_list(self, channel):
        self.send(channel, "CakeBot Test Send")

    def on_pubmsg(self, c, e):
        if not self.identify_msg_cap:
            self.log.debug("Ignoring message because identify-msg "
                           "cap not enabled")
            return
        nick = e.source.split('!')[0]
        msg = e.arguments[0][1:]
        chan = e.target

        if msg.startswith('#'):
            if (False and not
                    (self.channels[chan].is_voiced(nick) or
                     self.channels[chan].is_oper(nick))):
                self.send(chan, "%s: Need voice to issue commands" % (nick,))
                return

            words = msg.split()
            if ((len(words) < 2) or
               (len(words) == 2 and words[1].lower() != 'clean')):
                self.send(chan, "%s: Incorrect number of arguments" % (nick,))
                self.usage(chan)
                return

            track = words[0][1:].lower()
            # if not self.data.is_track_valid(track):
            #     self.send(chan, "%s: unknown track '%s'" % (nick, track))
            #     self.send_track_list(chan)
            #     return

            # adverb = words[1].lower()
            # params = str.join(' ', words[2:])
            # if adverb in ['now', 'next', 'location']:
            #     if not self.data.get_track_room(track):
            #         self.send(chan, "%s: track '%s' is not scheduled today" %
            #                   (nick, track))
            #         return
            # if adverb == 'now':
            #     self.data.add_now(track, params)
            # elif adverb == 'next':
            #     self.data.add_next(track, params)
            # elif adverb == 'clean':
            #     self.data.clean_tracks([track])
            # elif adverb == 'color':
            #     self.data.add_color(track, params)
            # elif adverb == 'location':
            #     self.data.add_location(track, params)
            # elif adverb == 'book':
            #     room, timeslot = params.split('-')
            #     if self.data.is_slot_valid_and_empty(room, timeslot):
            #         self.data.book(track, room, timeslot)
            #     else:
            #         self.send(chan, "%s: invalid slot reference '%s'" %
            #                   (nick, params))
            if track == "test":
                self.send_test_list(chan)
            else:
                self.send(chan, "%s: unknown directive '%s'" % (nick, track))
                self.usage(chan)
                return

        if msg.startswith('~'):
            if not self.channels[chan].is_oper(nick):
                self.send(chan, "%s: Need op for admin commands" % (nick,))
                return
            words = msg.split()
            command = words[0][1:].lower()
            # if command == 'reload':
            #     self.data.reload()
            # elif command == 'unbook':
            #     params = str.join(' ', words[1:])
            #     room, timeslot = params.split('-')
            #     self.data.unbook(room, timeslot)
            # elif command == 'newday':
            #     self.data.new_day_cleanup()
            # elif command == 'requirevoice':
            #     self.data.require_voice()
            # elif command == 'alloweveryone':
            #     self.data.allow_everyone()
            # elif command == 'list':
            #     self.send_track_list(chan)
            # elif command in ('clean', 'add', 'del'):
            #     if len(words) < 2:
            #         self.send(
            #             chan, "this command takes one or more arguments")
            #         return
            #     getattr(self.data, command + '_tracks')(words[1:])
            if command == 'dickbutt':
                self.send_test_list(chan)
            else:
                self.send(chan, "%s: unknown command '%s'" % (nick, command))
                return

    def send(self, channel, msg):
        self.connection.privmsg(channel, msg)
        time.sleep(ANTI_FLOOD_SLEEP)


def start(configpath):

    with io.open(configpath, 'r') as fp:
        config = json.load(fp, object_pairs_hook=collections.OrderedDict)

    if 'log_config' in config:
        log_config = config['log_config']
        fp = os.path.expanduser(log_config)
        if not os.path.exists(fp):
            raise EnvironmentError(
                "Unable to read logging config file at %s" % fp)
        logging.config.fileConfig(fp)
    else:
        logging.basicConfig(level=logging.DEBUG,
                            handlers=[logging.StreamHandler(sys.stdout)])

    bot = CakeBot(config['irc_nick'],
                  config.get('irc_pass', ''),
                  config['irc_server'],
                  config['irc_port'],
                  config['irc_channel'])
    bot.start()


def main():
    parser = argparse.ArgumentParser(description='PTG bot.')
    parser.add_argument('configfile', help='specify the config file')
    parser.add_argument('-d', dest='nodaemon', action='store_true',
                        help='do not run as a daemon')
    args = parser.parse_args()

    if not args.nodaemon:
        pid = pid_file_module.TimeoutPIDLockFile(
            "/var/run/cakebot/cakebot.pid", 10)
        with daemon.DaemonContext(pidfile=pid):
            start(args.configfile)
    start(args.configfile)


if __name__ == "__main__":
    main()
