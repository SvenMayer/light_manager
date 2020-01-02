#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import random
import requests
import threading
import time


RASPI_IP = "127.0.0.1"
DECONZ_API_KEY = ##DECONZ-API-KEY##
WEATHER_API_KEY = ##WEATHER-API-KEY##
WEATER_CITY_ID  = ##CITY-ID##
LOGFILE = os.path.splitext(__file__)[0] + ".log"

logging.basicConfig(filename=LOGFILE,
                    format="%(asctime)s %(levelname)s: %(message)s",
                    level=logging.INFO)
random.seed(time.time())


OFF_TIME = (
    (0, 22, 5),
    (1, 22, 5),
    (2, 22, 7),
    (3, 22, 5),
    (4, 22, 5),
    (5, 0, 0),
    (6, 0, 30),
    (6, 23, 28),
)



class scheduler(threading.Thread):
    DT_EPSILON = 0.1

    def __init__(self):
        super().__init__()
        self._queue = []
        self._cancel_flag = False
        self._queue_lock = threading.Lock()
        self._abort_event = threading.Event()
        self._data_available = threading.Event()
        logging.info("Scheduler initialized.")

    def add_event(self, time, evt, *args):
        logging.info("Event {0:s} scheduled for {1:.0f}s; arguments {2:s}".format(
                evt.__repr__(), time, args.__repr__()))
        self._data_available.clear()
        self._abort_event.set()
        self._queue_lock.acquire()
        self._queue.append((time, evt, args))
        self._queue.sort()
        self._queue_lock.release()
        self._data_available.set()
        logging.debug("Current queue: {0:s}".format(self._queue.__repr__()))

    def _pop_left(self):
        logging.debug("pop left called.")
        self._queue.pop(0)
        if len(self._queue) == 0:
            self._data_available.clear()
        else:
            self._data_available.set()
        logging.debug("pop left finished")
        logging.debug("Current queue: {0:s}".format(self._queue.__repr__()))

    def clear(self):
        self._data_available.clear()
        self._abort_event.set()
        self._queue_lock.acquire()
        self._queue = []
        self._queue_lock.release()

    def run(self):
        logging.info("Scheduler started.")
        while True:
            self._data_available.wait()
            if len(self._queue) == 0:
                break
            self._abort_event.clear()
            t = self._queue[0][0]
            dt = t - time.time()
            if dt < 0:
                dt = 0
            if self._abort_event.wait(dt):
                continue
            if t - time.time() <= self.DT_EPSILON:
                self._queue_lock.acquire()
                t, evt, args = self._queue.pop(0)
                self._queue_lock.release()
                try:
                    evt(*args)
                except Exception as e:
                    logging.error("An error occured when executing event: {0}".format(e))

    def stop(self):
        self.clear()
        self._data_available.set()
        logging.info("Scheduler terminated.")


class weather:
    API_KEY = WEATHER_API_KEY
    CITY_ID = WEATER_CITY_ID
    URL = "http://api.openweathermap.org/data/2.5/weather?id={id:s}&appid={apikey:s}"
    UPDATE_TIME = 30 * 60
    FALLBACK_SUNSET = 18 * 60 * 60

    def __init__(self):
        super().__init__()
        self._cloudcover = None
        self._sunset = None
        self._last_query = 0

    @property
    def clouds(self):
        self._check_for_update_weather()
        return self._cloudcover / 100.

    @property
    def sunset(self):
        self._check_for_update_weather()
        return self._sunset

    def _use_fallback(self):
        self._cloudcover = 0.
        today = time.localtime()
        self._sunset = time.time((
            today.tm_year, today.tm_mon, today.tm_mday, 0, 0, 0,
            today.tm_wday, today.tm_yday,
            today.tm_isdst)) + self.FALLBACK_SUNSET
        logging.info("Using fallback cloudcover {0:3.2f}, fallback sunset {1:.0f}s".format(
                self._cloudcover, self._sunset))

    def _check_for_update_weather(self):
        if (time.time() - self._last_query) < self.UPDATE_TIME:
            return
        logging.info("Requesting weather information.")
        res = requests.get(self.URL.format(
                id=self.CITY_ID, apikey=self.API_KEY))
        if not res.ok:
            logging.error("Cannot fetch weather information. Reason: {0:d}".format(
                    res.status_code))
#            raise Exception("Cannot fetch weather data")
            self._use_fallback()
        else:
            self._last_query = time.time()
            data = json.loads(res.text)
            self._sunset = data["sys"]["sunset"]
            self._cloudcover = data["clouds"]["all"]
            logging.info("Weather info: cloudcover {0:3.2f}, sunset {1:.0f}".format(
                    self._cloudcover, self._sunset))


class lights:
    OFF_TIMES = OFF_TIME
    SECONDS_FULL_COVER = 2. * 60. * 60.
    LOOP_REFRESH = 15 * 60.
    RANDOM_OFF_TIME = 30 * 60

    def __init__(self, weather, controller, scheduler):
        logging.info("Initialize \"lights\"")
        super().__init__()
        self._weather = weather
        self._controller = controller
        self._scheduler = scheduler

    def start(self):
        t_off = self._get_next_off_time()
        t_on = self._weather.sunset - self.SECONDS_FULL_COVER
        if t_on < time.time():
            t_on = time.time()
        if t_on > self._weather.sunset:
            t_on = self._get_next_day_check_on_time()
        self._scheduler.add_event(
            t_on, self._check_on_turn_on_if_on_time_current)
        self._scheduler.add_event(
            t_off, self._turn_off_and_schedule_new_off)

    def _get_lights_on_time(self):
        return (self._weather.sunset
                - self.SECONDS_FULL_COVER * self._weather.clouds)

    def _get_next_off_time(self):
        now = datetime.datetime.now()
        today = now.date()
        date = today
        off_times = []
        for i in range(7):
            off_times.extend([
                datetime.datetime(date.year, date.month, date.day,
                                  hour, minute)
                for day, hour, minute in self.OFF_TIMES
                if day == date.weekday()])
            date = date + datetime.timedelta(days=1)
        future_times = [itm for itm in off_times if (itm-now).days >= 0]
        future_times.sort()
        return (time.mktime(future_times[0].timetuple())
                + self.RANDOM_OFF_TIME * random.random())

    def _get_next_day_check_on_time(self):
        return (24 * 60 * 60
                + self._weather.sunset - self.SECONDS_FULL_COVER - 15*60)

    def _turn_off_and_schedule_new_off(self):
        logging.debug("_turn_off_and_schedule_new_off started.")
        self._controller.state = False
        t_nextoff = self._get_next_off_time()
        self._scheduler.add_event(
            t_nextoff, self._turn_off_and_schedule_new_off)
        logging.debug("_turn_off_and_schedule_new_off started.")

    def _check_on_turn_on_if_on_time_current(self):
        logging.debug("_check_on_turn_if_on_time_current started.")
        t_lightson = self._get_lights_on_time()
        now = time.time()
        t_refresh = now + self.LOOP_REFRESH
        if t_lightson <= now:
            self._controller.state = True
            t_check = self._get_next_day_check_on_time()
        elif t_lightson > t_refresh:
            t_check = t_refresh
        else:
            t_check = t_lightson
        self._scheduler.add_event(
            t_check, self._check_on_turn_on_if_on_time_current)
        logging.debug("_check_on_turn_if_on_time_current finished.")


class lights_api_controller:
    raspi_ip = RASPI_IP
    api_key = DECONZ_API_KEY

    def __init__(self, light_id):
        logging.info("Lights API started for id={0:d}".format(light_id))
        self._id = light_id

    @property
    def state(self):
        url = self._build_url("lights", str(self._id))
        res = requests.get(url)
        if not res.ok:
            logging.error(
                    "Cannot querry state of light {0:d}. Reason: {1:d}".format(
                            self._id, res.status_code))
#            raise Exception("Cannot connect")
        return json.loads(res.text)["state"]["on"]

    @state.setter
    def state(self, set_state):
        if not isinstance(set_state, bool):
            raise("State needs to be of type \"bool\"")
        return self.set_on(set_state)

    def set_on(self, on):
        logging.info("Sending command: \"Turn light {0:d} {1:s}\"".format(
                self._id, ("off", "on")[on]))
        url = self._build_url("lights", str(self._id), "state")
        for i in range(5):
            res = requests.put(url, json.dumps({"on": on}))
            if res.ok:
                break
        if not res.ok:
            logging.error(
                    "Cannot set state for light {0:d} to {1:d}. Reason: {2:d}".format(
                            self._id, on, res.status_code))

    def _build_url(self, *args):
        return "http://{ip:s}/api/{api_key:s}/{rest:s}".format(
                ip=self.raspi_ip, api_key=self.api_key, rest="/".join(args))


if __name__ == "__main__":
    logging.info("Program started!")
    sched = scheduler()
    sched.start()
    weath = weather()
    l = lights_api_controller(1)
    lts = lights(weath, l, sched)
    lts.start()
    sched.join()
