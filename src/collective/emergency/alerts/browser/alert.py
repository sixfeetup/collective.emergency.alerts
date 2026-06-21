from plone import api
from plone.registry.interfaces import IRegistry
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility

import datetime
import hashlib
import json
import time


class Alert(object):
    id = None
    _struct = {}

    def __init__(self, id):
        self._struct = {
            "title": "",
            "body": "",
            "start": "",
            "end": "",
            "level": "0",
            "is_active": "True",
            "url": "",
        }
        if id:
            registry = getUtility(IRegistry)
            alerts = registry[
                "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
            ]
            self.id = id
            if self.id in alerts:
                self._struct = alerts[self.id]
        else:
            self.id = hashlib.sha1(str(time.time()).encode("utf-8")).hexdigest()

    def save(self):
        registry = getUtility(IRegistry)
        alerts = registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ]
        if not alerts:
            alerts = {}
        alerts[self.id] = self._struct
        alerts[self.id]["body"] = alerts[self.id]["body"].replace("\r\n", "")
        alerts[self.id]["end"] = alerts[self.id]["end"] or "2050-12-25T13:12"
        alerts[self.id]["start"] = alerts[self.id]["start"] or "1999-12-25T13:12"
        registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ] = alerts

        # Force the save of a dictionary to be persistant
        registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ] = registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ]

    def delete(self):
        registry = getUtility(IRegistry)
        alerts = registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ]
        del alerts[self.id]
        registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ] = alerts

        # Force the save of a dictionary to be persistant
        registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ] = registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ]

    def set(self, name, value):
        self._struct[name] = value

    def get(self, name):
        return self._struct[name]

    # def _reset(self):
    #     registry = getUtility(IRegistry)
    #     alerts = registry['collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts']
    #     if not alerts:
    #         registry['collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts'] = {}
    #         # Force the save of a dictionary to be persistant
    #         registry['collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts'] = registry['collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts']


class AlertEdit(BrowserView):
    template = ViewPageTemplateFile("edit_alert.pt")
    alert = None
    error = False

    def __call__(self):
        self.alert = None  # default
        self.error = None  # default
        id = self.request.form.get("id", None)

        try:
            self.alert = Alert(id)
        except Exception as e:
            self.error = True

        if "form.widgets.submit" in self.request.form:
            self.alert.set(
                "title", self.request.form.get("form.widgets.title", "Missing title")
            )
            self.alert.set(
                "body",
                self.request.form.get(
                    "form.widgets.body", "No details available at this time"
                ),
            )

            self.alert.set("start", self.request.form.get("form.widgets.start", ""))
            self.alert.set("end", self.request.form.get("form.widgets.end", ""))
            self.alert.set(
                "url", self.portal.absolute_url() + "/alert?id=" + str(self.alert.id)
            )

            active = "False"
            if self.request.form.get("form.widgets.active", "off") == "on":
                active = "True"
            self.alert.set("is_active", active)

            self.alert.set("level", self.request.form.get("form.widgets.level", "0"))

            self.alert.save()
            return self.request.response.redirect(
                self.portal.absolute_url() + "/@@emergency_manager"
            )

        if "alert.state" in self.request.form:
            state = self.request.form.get("alert.state")
            if state == "False":
                self.alert.set("is_active", "True")
            else:
                self.alert.set("is_active", "False")
            self.alert.save()
            return self.request.response.redirect(
                self.portal.absolute_url() + "/@@emergency_manager"
            )

        if "alert.remove" in self.request.form:
            self.alert.delete()
            return self.request.response.redirect(
                self.portal.absolute_url() + "/@@emergency_manager"
            )

        return self.template()

    @property
    def portal(self):
        return api.portal.get()


def in_date_range(alert):
    """Returns True or False based on whether or not
    alert is within the set date range. Returns
    True when no dates are set.
    """
    now = datetime.datetime.now()
    alert_start = alert.get("start") or "1999-12-25T13:12"
    alert_end = alert.get("end") or "2050-12-25T13:12"
    start = datetime.datetime.strptime(alert_start, "%Y-%m-%dT%H:%M")
    end = datetime.datetime.strptime(alert_end, "%Y-%m-%dT%H:%M")
    return start <= now and now <= end


class AlertView(BrowserView):
    template = ViewPageTemplateFile("alert.pt")
    alert = None

    def __call__(self):

        self.alert = None  # default
        self.error = None  # default
        self.id = self.request.form.get("id", None)
        self.active_alerts = []
        self.inactive_alerts = []

        try:
            self.alert = Alert(self.id)
        except Exception:
            self.error = True

        if self.id:
            return self.template()

        registry = getUtility(IRegistry)
        registry_alerts = registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ]
        for alert in registry_alerts.values():
            if alert["is_active"] == "True" and in_date_range(alert):
                self.active_alerts.append(alert)
            else:
                self.inactive_alerts.append(alert)
        return self.template()


class AlertsBroadcaster(BrowserView):
    def __call__(self):
        data = []
        now = datetime.datetime.now()

        registry = getUtility(IRegistry)
        alerts = registry[
            "collective.emergency.alerts.browser.controlpanel.IEmergencyAlert.alerts"
        ]
        if alerts:
            for k, v in alerts.items():
                if v["is_active"] == "True":
                    start = self.dict_get(v, "start", "1999-12-25T13:12")
                    end = self.dict_get(v, "end", "2050-12-25T13:12")
                    try:
                        start = datetime.datetime.strptime(start, "%Y-%m-%dT%H:%M")
                        end = datetime.datetime.strptime(end, "%Y-%m-%dT%H:%M")
                    except ValueError:
                        # handle migrated data with different format
                        start = datetime.datetime.strptime(start, "%Y-%m-%d %H:%M")
                        end = datetime.datetime.strptime(end, "%Y-%m-%d %H:%M")
                    if start <= now and now <= end:
                        data.append(v)

        # Determine Format
        # self.request.response.setHeader('ETag', md5.new(str(data)).hexdigest())
        # self.request.response.setHeader('Cache-Control', 'max-age=60, s-maxage=60, public, must-revalidate')
        # self.request.response.setHeader('Vary', 'Accept-Encoding')
        self.request.response.setHeader("Content-Type", "application/json")
        self.request.response.setHeader("Access-Control-Allow-Origin", "*")
        return self.toJSON(data)

    def dict_get(self, v, key, default):
        if key in v:
            if not v[key]:
                return default
            return v[key]

    def toJSON(self, data):
        return json.dumps(data)

    def toJSONP(self, data):
        return "_EAS.loaded(" + self.toJSON(data) + ")"
