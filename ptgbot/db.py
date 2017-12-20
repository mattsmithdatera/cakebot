#! /usr/bin/env python

# Copyright (c) 2017, Thierry Carrez
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

import json
import os
import datetime


class PTGDataBase():

    BASE = {'tracks': [], 'slots': {}, 'now': {}, 'next': {}, 'colors': {},
            'location': {}, 'scheduled': {}, 'additional': {}}

    def __init__(self, filename, slots, scheduled, extrarooms):
        self.filename = filename
        if os.path.isfile(filename):
            with open(filename, 'r') as fp:
                self.data = json.load(fp)
        else:
            self.data = self.BASE
        self.data['slots'] = slots

        self.data['scheduled'] = scheduled
        # Add tracks mentioned in configuration that are not in track list
        for room, bookings in scheduled.items():
            for time, track in bookings.items():
                if track not in self.data['tracks']:
                    self.data['tracks'].append(track)

        # Rebuild 'additional' with rooms and slots from configuration, but
        # use saved data where the room/slot is preserved
        old_data = self.data['additional'].copy()
        self.data['additional'] = {}

        for room in extrarooms.keys():
            self.data['additional'][room] = {}
            for slot in extrarooms[room]:
                try:
                    self.data['additional'][room][slot] = old_data[room][slot]
                except KeyError:
                    self.data['additional'][room][slot] = ''

        # Save the data to disk
        self.save()

    def add_now(self, track, session):
        self.data['now'][track] = session
        if track in self.data['next']:
            del self.data['next'][track]
        self.save()

    def add_color(self, track, color):
        self.data['colors'][track] = color
        self.save()

    def add_location(self, track, location):
        if 'location' not in self.data:
            self.data['location'] = {}
        self.data['location'][track] = location
        self.save()

    def add_next(self, track, session):
        if track not in self.data['next']:
            self.data['next'][track] = []
        self.data['next'][track].append(session)
        self.save()

    def is_track_valid(self, track):
        return track in self.data['tracks']

    def list_tracks(self):
        return sorted(self.data['tracks'])

    def add_tracks(self, tracks):
        for track in tracks:
            if track not in self.data['tracks']:
                self.data['tracks'].append(track)
        self.save()

    def del_tracks(self, tracks):
        for track in tracks:
            if track in self.data['tracks']:
                self.data['tracks'].remove(track)
        self.save()

    def clean_tracks(self, tracks):
        for track in tracks:
            if track in self.data['now']:
                del self.data['now'][track]
            if track in self.data['next']:
                del self.data['next'][track]
        self.save()

    def wipe(self):
        self.data = self.BASE
        self.save()

    def save(self):
        timestamp = datetime.datetime.now()
        self.data['timestamp'] = '{:%Y-%m-%d %H:%M:%S}'.format(timestamp)
        self.data['tracks'] = sorted(self.data['tracks'])
        with open(self.filename, 'w') as fp:
            json.dump(self.data, fp)
