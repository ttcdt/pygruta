#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   Calendar management

import datetime, re
import pygruta


def events_in_day(s_set, year, month, day):
    """ returns the events that happen through a day """

    s = "%04d%02d%02d" % (year, month, day)
    s_day = s + "000000"
    e_day = s + "235959"

    ret = []

    for s in s_set:
        s_story = s[2]
        e_story = s[4]

        # no end of story? assume the same day
        if e_story == "":
            e_story = s_story[0:8] + "235959"

        # in range?
        if s_story < e_day and e_story > s_day:
            ret.append(s)

    ret.reverse()

    return ret


def import_icalendar(gruta, fd):
    """ imports an iCalendar (.ics) file into the 'events' topic """

    in_vevent = False
    in_valarm = False

    # ensure topic exists
    if gruta.topic("events") == None:
        topic = gruta.new_topic({"id": "events",
                                "name": "Calendar Events", "internal": "1"})
        gruta.save_topic(topic)

    event_l = []

    for l in fd:
        l = l.replace("\n", "")

        if in_valarm:
            # ignore alarms by now
            if l == "END:VALARM":
                in_valarm = False

        elif in_vevent:
            if l == "BEGIN:VALARM":
                in_valarm = True

            elif l == "END:VEVENT":
                # create event
                s = {"date": ["", ""], "location": "", "description": ""}

                for ev in event_l:
                    # unescape things
                    ev = ev.replace("\\,", ",")
                    ev = ev.replace("\\n", "<br/>")

                    k, v = ev.split(":", 1)

                    if k == "UID":
                        s["reference"] = v
                    elif k == "SUMMARY":
                        s["title"] = v
                    elif k == "LOCATION":
                        s["location"] = v
                    elif k == "DTSTART;VALUE=DATE":
                        s["date"][0] = v
                    elif k == "DTEND;VALUE=DATE":
                        s["date"][1] = v
                    elif k == "DTSTART":
                        s["date"][0] = v
                    elif k == "DTEND":
                        s["date"][1] = v
                    elif k == "DESCRIPTION":
                        s["description"] = v

                for i in range(0, 2):
                    d = s["date"][i]

                    if len(d) == 8:
                        # date with no time
                        d += "000000"

                    elif d[-1] == "Z":
                        # UTC time: parse first
                        d1 = datetime.datetime(
                            int(d[0:4]),  int(d[4:6]), int(d[6:8]),
                            int(d[9:11]), int(d[11:13]), int(d[13:15]),
                            0, datetime.timezone.utc)

                        # convert to localtime
                        d2 = d1.astimezone()

                        # convert to gruta date
                        d = gruta.datetime_to_date(d2)

                    s["date"][i] = d

                # find the story
                id = gruta.md5(s["reference"])

                story = gruta.story("events", id)

                if story is None:
                    story = gruta.new_story({"topic_id": "events", "id": id})
                    op = "CREATE"
                else:
                    op = "UPDATE"

                gruta.story_defaults(story)

                content = "<h2>" + s["title"] + "</h2>\n"

                if s["description"]:
                    content += "<p>" + s["description"] + "</p>\n"

                if s["location"]:
                    u = s["location"].replace(" ", "%20")

                    content += "<p>"
                    content += "<a href=\"https://www.google.com/search?q=%s\">" % u
                    content += "&#x1f310; "
                    content += s["location"] + "</a></p>\n"
                    content += "</p>\n"

                story.set("date",      s["date"][0])
                story.set("udate",     s["date"][1])
                story.set("title",     s["title"])
                story.set("reference", s["reference"])
                story.set("content",   content)

                gruta.save_story(story)

                gruta.log("INFO", "Calendar: %s %s" % (op, s["title"]))

                in_vevent = False

            elif l[0] == " ":
                # broken line: add to previous one
                event_l[-1] += l[1:]

            else:
                event_l.append(l)

        else:
            if l == "BEGIN:VEVENT":
                in_vevent = True
                event_l = []


def export_icalendar(gruta):
    """ exports the "events" topic as an iCalendar (generator function) """

    header = [
        "BEGIN:VCALENDAR",
        "PRODID:-//triptico.com//Gruta Calendar//EN",
        "VERSION:2.0"
    ]

    # file header
    for l in header:
        yield l

    s_set = gruta.story_set(topics=["events"], private=True)

    for s in s_set:
        topic_id, id = s[0], s[1]

        story = gruta.story(topic_id, id)

        e = []

        # collect data
        body = pygruta.special_uris(gruta, story.get("body"))
        body = re.sub("<br/>", "\n", body)
        body = re.sub("<[^>]+>", "", body)

        if body != "" and body[0] == "\n":
            body = body[1:]

        if body != "" and body[-1] == "\n":
            body = body[0:-1]

        s_date = story.get("date")

        if s_date[8:14] == "000000":
            # date has no time: do not create as utc, because
            # it will jump to previous day
            s_date = gruta.date_to_datetime(s_date)
        else:
            s_date = gruta.date_to_datetime(s_date).astimezone(datetime.timezone.utc)

        e_date = story.get("udate")

        if e_date == "":
            # no end date:
            if s_date.hour == 0 and s_date.minute == 0:
                # start date has no time: set end date to tomorrow
                e_date = s_date + datetime.timedelta(days=1)
            else:
                # start date has time: set end date to 1 hour later
                e_date = s_date + datetime.timedelta(hours=1)
        else:
            if e_date[8:14] == "000000":
                e_date = gruta.date_to_datetime(e_date)
            else:
                e_date = gruta.date_to_datetime(e_date).astimezone(datetime.timezone.utc)

        c_date = story.get("ctime")
        if c_date == "":
            c_date = s_date
        else:
            c_date = gruta.date_to_datetime(c_date).astimezone(datetime.timezone.utc)

        m_date = story.get("mtime")
        if m_date == "":
            m_date = s_date
        else:
            m_date = gruta.date_to_datetime(m_date).astimezone(datetime.timezone.utc)

        # build the entry
        e.append("BEGIN:VEVENT")

        if s_date.hour + e_date.hour == 0 and s_date.minute + e_date.minute == 0:
            e.append("DTSTART;VALUE=DATE:" + s_date.strftime("%Y%m%d"))
            e.append("DTEND;VALUE=DATE:" + e_date.strftime("%Y%m%d"))
        else:
            e.append("DTSTART:" + s_date.strftime("%Y%m%dT%H%M%SZ"))
            e.append("DTEND:" + e_date.strftime("%Y%m%dT%H%M%SZ"))

#        e.append("DTSTAMP:" + m_date.strftime("%Y%m%dT%H%M%SZ"))
        e.append("CREATED:" + c_date.strftime("%Y%m%dT%H%M%SZ"))
        e.append("LAST-MODIFIED:" + m_date.strftime("%Y%m%dT%H%M%SZ"))
        e.append("UID:%s/%s@%s" % (topic_id, id, gruta.host_name))
        e.append("DESCRIPTION:" + body)
        e.append("SEQUENCE:%d" % int(story.get("revision")))
        e.append("SUMMARY:" + story.get("title"))
        e.append("END:VEVENT")

        for l in e:
            # escape things
            l = l.replace(",", "\\,")
            l = l.replace("\n", "\\n")

            # split line
            while l != " ":
                p, l = l[0:70], l[70:]

                yield p

                l = " " + l

    yield "END:VCALENDAR"


def get_handler(gruta, q_path, q_vars):
    """ calendar GET handler """

    status, body = 0, None

    if q_path == "/calendar/calendar.ics":
        status, body = 202, "\r\n".join(export_icalendar(gruta))

    return status, body, "text/calendar; charset=utf-8"
