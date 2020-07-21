#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   HTML generator

import time, re, datetime
import lxml.html

import pygruta
import pygruta.calendar

def links_in_content(content):
    """ Returns all links inside content """

    try:
        htmldoc = lxml.html.document_fromstring(content)
    except:
        htmldoc = None

    if htmldoc is not None:
        for l in htmldoc.iterlinks():
            yield l


def header(gruta, nav_headers="", title="", onload="", image=""):
    """ standard page header """

    head, state, context = gruta.html_cache.get("h-head")

    if not head:
        head = "<!doctype html>\n<html>\n<head>\n"
        head += "<style type=\"text/css\">%s</style>\n" % gruta.template("css_compact")
        head += "<link rel=\"alternate\" type=\"application/atom+xml\" title=\"ATOM\" href=\"%s\" />\n" % gruta.url("atom.xml")
        head += "<link rel=\"alternate\" type=\"application/rss+xml\" title=\"RSS\" href=\"%s\" />\n" % gruta.url("rss.xml")
        head += "<link rel=\"shortcut icon\" href=\"%s\"/>\n" % gruta.template("cfg_favicon_url")

        wm_hook = gruta.template("cfg_webmention_hook")

        if wm_hook == "":
            wm_hook = gruta.aurl("webmention/")

        if wm_hook[0:8] == "https://":
            head += "<link rel=\"webmention\" href=\"%s\"/>\n" % wm_hook

        head += "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"/>\n"
        head += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
        head += "<meta name=\"generator\" content=\"pygruta\"/>\n"

        gruta.html_cache.put("h-head", head)

    header, state, context = gruta.html_cache.get("h-header")

    if not header:
        header = "<body onLoad=\"{onload}\">\n"
        header += "<header>\n"
        header += "<h1 id=\"title\"><a href=\"%s\">%s</a></h1>\n" % (
            gruta.url(), gruta.template("cfg_site_name"))

        header += "<h2 id=\"subtitle\">%s</h2>\n" % gruta.template("cfg_slogan")

        # navigation menu
        nav = ""

        for t in gruta.template("cfg_main_menu_topics").split(":"):
            topic = gruta.topic(t)

            if topic:
                nav += "<li><a href=\"%s\">%s</a></li>\n" % (
                    gruta.url(topic), topic.get("name"))

        # only generate a Tags link if there are any
        if len(gruta.tags(test=True)) > 0:
            nav += "<li><a href=\"%s\">Tags</a></li>\n" % gruta.url("tag/")

        # don't generate an empty nav
        if nav != "":
            header += "<nav id=\"menu\">\n<ul>\n" + nav + "</ul>\n</nav>\n"

        header += "</header>\n"

        t = gruta.template("sidebar")

        if t != "":
            header += "<div id=\"sidebar\">\n" + t + "</div>\n"

        t = gruta.template("banner")

        if t != "":
            header += "<div id=\"banner\">\n" + t + "</div>\n"

        header += "<section id=\"main\">\n"

        gruta.html_cache.put("h-header", header)

    s = head
    s += "<title>%s: %s</title>\n" % (gruta.template("cfg_site_name"), title)

    s += gruta.template("additional_headers") + nav_headers

    # if there is an image URL, add it to headers
    if image != "":
        s += "<meta property=\"og:image\" content=\"%s\"/>\n" % gruta.aurl(image)

    s += header.format(title=title, onload=onload)

    return s


def footer(gruta):
    """ standard page footer """

    s, state, context = gruta.html_cache.get("h-footer")

    if not s:
        s = "</section>\n"
        s += "<footer id=\"footer\">\n"
        s += gruta.template("cfg_copyright") + "\n"
        s +="</footer>\n</body>\n</html>\n"

        gruta.html_cache.put("h-footer", s)

    return s


def article(gruta, story, content):
    """ article HTML block """

    topic_id = story.get("topic_id")
    id       = story.get("id")

    i = "h-%s/%s" % (topic_id, id)
    art, state, context = gruta.html_cache.get(i)

    if art is None:
        art = []

        # article title
        s = "<h2 class=\"p-name u-url\">"
        s += "<a href=\"%s\">%s</a>" % (gruta.url(story), story.get("title"))

        # add a link to edit the story if a user is logged in
        if gruta.logged_user:
            s += " <a href=\"%s\">&nbsp;&#x270E;&nbsp;</a>\n" % (
                gruta.url("/admin/story/%s/%s" % (topic_id, id)))

        s += "</h2>\n"

        s += "<p>"

        # build date
        dt = story.get("date")
        if dt[0:4] != "1900":
            try:
                df = gruta.template("cfg_date_format") or "%Y-%m-%d"

                d1 = gruta.date_format(dt, "%Y-%m-%d %H:%M:%S")
                d2 = gruta.date_format(dt, df)

                s += "<time class=\"dt-published\" datetime=\"%s\">%s</time>\n" % (
                    d1, d2)
            except:
                gruta.log("WARN", "Article: bad date for " + topic_id + "/" + id)

        # add author
        user = gruta.user(story.get("userid"))

        if user is not None:
            s += " <a rel=\"author\" class=\"p-author h-card\" href=\"%s\">%s</a>" % (
                gruta.url(user), user.get("username"))

        s += "<p>\n"

        # main e-content with %s anchor for body or abstract
        s += "<div class=\"e-content\">\n"

        art.append(s)

        # second part
        s = "</div>\n"

        # categories (tags)
        cat = ""

        # only generate a topic category if there is more than one topic
        if len(list(gruta.topics())) > 1:
            topic = gruta.topic(topic_id)
            cat += "<li><a class=\"p-category\" href=\"%s\">%s</a></li>\n" % (
                gruta.url(topic), topic.get("name").lower())

        for t in story.get("tags"):
            cat += "<li><a class=\"p-category\" href=\"%s\">%s</a></li>\n" % (
                gruta.url(t + ".html", "tag"), t)

        if cat != "":
            s += "<ul class=\"categories\">\n" + cat + "</ul>\n"

        art.append(s)

        # if no body, save the story triggering a rendering
        if story.get("body") == "" or story.get("abstract") == "":
            gruta.log("INFO", "Render: %s" % gruta.url(story))
            gruta.save_story(story)

        gruta.html_cache.put(i, art)

    return art[0] + content + art[1]


def story(gruta, story):
    """ story page """

    # get the article block
    art_block = article(gruta, story, story.get("body"))

    # build the page
    onload = story.get("redir")

    if onload:
        onload = "window.location.replace('%s');" % onload

    page = header(gruta, title=story.get("title"), onload=onload,
        image=story.get("image"))

    page += "<article id=\"%s/%s\" class=\"h-entry\" lang=\"%s\">\n" % (
        story.get("topic_id"), story.get("id"), story.get("lang"))

    page += art_block

    page += "</article>\n"

    page += footer(gruta)

    return pygruta.special_uris(gruta, page)


def user(gruta, u):
    """ user page """

    page = header(gruta, title=u.get("username"))

    page += "h-card://%s" % u.get("id")

    page += footer(gruta)

    return pygruta.special_uris(gruta, page)


def tag(gruta, tag=None, s_set=None):
    """ tag page """

    if tag is not None:

        page = header(gruta, title=tag)

        page += "<h2>%s:</h2>" % tag
        page += "<ul>\n"

        for s in s_set:
            story = gruta.story(s[0], s[1])

            page += "<li><a href=\"%s\">%s</a></li>\n" % (
                gruta.url(story), story.get("title"))

        page += "</ul>\n"
        page += footer(gruta)

    else:

        # no tag: generate the index of tags
        tags = gruta.tags()
        tidx = list(tags.keys())
        tidx.sort()

        page = header(gruta, title="Tags")
        page += "<h2>Tags</h2>\n"
        page += "<ul>\n"

        for tag in tidx:
            page += "<li><a href=\"%s\">%s (%d)</a></li>\n" % (
                gruta.url(tag + ".html", "tag"), tag, len(tags[tag]))

        page += "</ul>\n"
        page += footer(gruta)

    return pygruta.special_uris(gruta, page)


def nav_links(gruta, s_set, offset, page, prefix=None):
    """ gets navigation links for header and footer """

    if offset:
        if offset == page:
            prev = "index"
        else:
            prev = "~%d" % (offset - page)
    else:
        prev = ""

    if len(s_set) > page:
        next = "~%d" % (offset + page)
    else:
        next = ""

    h_nav = ""
    f_nav = ""

    if next:
        next = gruta.url(next + ".html", prefix)
        h_nav += "<link rel=\"next\" href=\"%s\"/>\n" % next
        f_nav += "<a href=\"%s\" class=\"next\">«</a>\n" % next

    if prev:
        prev = gruta.url(prev + ".html", prefix)
        h_nav += "<link rel=\"prev\" href=\"%s\"/>\n" % prev
        f_nav += "<a href=\"%s\" class=\"prev\">»</a>\n" % prev

    return (h_nav, f_nav)


def paged_index(gruta, s_set, offset, num, title, prefix=None):
    """ a paged index of stories """

    h_nav, f_nav = nav_links(gruta, s_set, offset, num, prefix)

    page = header(gruta, nav_headers=h_nav, title=title)

    for s in s_set[0:num]:
        story   = gruta.story(s[0], s[1])
        content = story.get("abstract")

        # if abstract is different from the body,
        # add a link to the full story
        if content != story.get("body"):
            content += "<p>story://%s/%s (&#128279; ...)</p>" % (s[0], s[1])

        page += "<div id=\"%s/%s\" lang=\"%s\">\n" % (s[0], s[1], story.get("lang"))

        page += article(gruta, story, content)

        page += "</div>\n"

    page += "<div class=\"index-footer\">\n"

    page += "<nav>\n<p>\n%s</p>\n</nav>\n" % f_nav

    page += "</div>\n"

    page += footer(gruta)

    return pygruta.special_uris(gruta, page)


# calendars

def calendar_month(gruta, year=None, month=None, topics=None, private=True):
    """ Generates a full month calendar """

    # get all stories
    s_set = list(gruta.story_set(topics=topics, private=private))

    today = datetime.datetime.now()

    # no date given? current month
    if year is None:
        year = today.year
    if month is None or month < 1 or month > 12:
        month = today.month

    # get day 1 of the month
    day_1 = datetime.date(year, month, 1)

    # create a delta time to find first Monday
    delta = datetime.timedelta(days=day_1.weekday())

    # calculate start date
    s_date = day_1 - delta
    date   = s_date

    page = "<!doctype html>\n<html>\n<head>\n\n<style>\n"
    page += gruta.template("css_calendar")
    page += "</style>\n"
    page += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
    page += "<link rel=\"shortcut icon\" href=\"%s\"/>\n" % gruta.template("cfg_favicon_url")
    page += "<title>Calendar - %s</title>\n" % gruta.template("cfg_site_name")
    page += "</head>\n"
    page += "<body>\n"
    page += "<div class=\"calendar\">\n"

    page += "<div class=\"month-name\">\n"
    page += gruta.month_name(month - 1) + " " + str(year) + "\n"
    page += "</div>\n"
    page += "<div class=\"month\">\n"

    # iterate for 39 days
    for d in range(0, 39):
        # calculate month class
        m_class = "box day"

        if date.month == month:
            m_class += " this-month"

        # calculate day class
        d_class = "day-label"

        if date.year == today.year and date.month == today.month and date.day == today.day:
            d_class += " today"

        # calculate day label
        d_label = gruta.wday_name(date.weekday()) + " " + str(date.day)

        # generate day
        url = gruta.url("/calendar/%s/%s/%s" % (date.year, date.month, date.day))
        page += "<a href=\"" + url + "\">\n"
        page += "<div class=\"" + m_class + "\">\n"
        page += "<div class=\"" + d_class + "\">" + d_label + "</div>\n"
        page += "<div class=\"day-content\">\n"

        # get stories for this day
        s_sset = pygruta.calendar.events_in_day(s_set, date.year, date.month, date.day)

        for s in s_sset:
            story = gruta.story(s[0], s[1])
            c     = story.get("title")

            # if the event continues next day, show it
            if s[4] > "%04d%02d%02d239999" % (date.year, date.month, date.day):
                c += "·" * 80
            else:
                # add hour if it's not 00:00
                hm = gruta.date_format(s[2], "%H:%M")

                if hm != "00:00":
                    c= hm + " " + c

            page += c + "<br/>\n"

        page += "</div>\n"
        page += "</div>\n"
        page += "</a>\n"

        date += datetime.timedelta(days=1)

    # prev month button
    w_month = s_date - datetime.timedelta(days=15)
    url     = gruta.url("/calendar/%s/%s/" % (w_month.year, w_month.month))
    page += "<a href=\"" + url + "\">\n"
    page += "<div class=\"box\">\n"
    page += "<div class=\"button\">«</div>\n"
    page += "</div>\n"
    page += "</a>\n"

    # today button
    url = gruta.url("/calendar/")
    page += "<a href=\"" + url + "\">\n"
    page += "<div class=\"box\">\n"
    page += "<div class=\"button\">&bull;</div>\n"
    page += "</div>\n"
    page += "</a>\n"

    # next month button
    url = gruta.url("/calendar/%s/%s/" % (date.year, date.month))
    page += "<a href=\"" + url + "\">\n"
    page += "<div class=\"box\">\n"
    page += "<div class=\"button\">»</div>\n"
    page += "</div>\n"
    page += "</a>\n"

    page += "</div>\n</div>\n</body>\n</html>\n"

    return page


def calendar_day(gruta, year, month, day, topics=None, private=True):
    """ Generates a day calendar """

    try:
        date = datetime.date(year, month, day)
    except:
        date = None

    if date is not None:
        page = "<!doctype html>\n<html>\n<head>\n\n<style>\n"
        page += gruta.template("css_calendar")
        page += "</style>\n"
        page += "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
        page += "<link rel=\"shortcut icon\" href=\"%s\"/>\n" % gruta.template("cfg_favicon_url")
        page += "<title>Calendar - %s</title>\n" % gruta.template("cfg_site_name")
        page += "</head>\n"
        page += "<body>\n"
        page += "<div class=\"calendar-day\" style=\"font-size: 11pt; margin: auto;\">\n"

        yest  = date - datetime.timedelta(days=1)
        tomo  = date + datetime.timedelta(days=1)

        page += "<h1>"

#        page += "<a href=\"%s\">&nbsp;«&nbsp;</a>" % gruta.url("/calendar/%d/%d/%d" % (
#            yest.year, yest.month, yest.day))

#        page += " &nbsp; "

        page += "<a href=\"%s\">" % gruta.url("/calendar/%d/%d/" % (year, month))
        page += "%d %s %d" % (day, gruta.month_name(month - 1), year)
        page += "</a>"

#        page += " &nbsp; "

#        page += "<a href=\"%s\">&nbsp;»&nbsp;</a>" % gruta.url("/calendar/%d/%d/%d" % (
#            tomo.year, tomo.month, tomo.day))

        page += "</h1>\n"

        # get all stories
        s_set = list(gruta.story_set(topics=topics, private=private))

        # add link to create a new entry
        page += "<h2>"
        page += "<a href=\"%s\">&nbsp;+&nbsp;</a>" % (
            gruta.url("/admin/story/events/?date=%04d%02d%02d000000" % (year, month, day)))
        page += "</h2>"

        # get stories for this day
        s_sset = pygruta.calendar.events_in_day(s_set, year, month, day)

        for s in s_sset:
            story = gruta.story(s[0], s[1])
            hm    = gruta.date_format(story.get("date"), "%H:%M")

            page += "<h2>"

            if hm != "00:00":
                page += hm + " "

            page += story.get("title")

            page += " <a href=\"%s\">&nbsp;&#x270E;&nbsp;</a>" % (
                gruta.url("/admin/story/%s/%s" % (story.get("topic_id"), story.get("id"))))

            page += "</h2>\n"
            page += pygruta.special_uris(gruta, story.get("abstract"))

        page += "</div>\n</div>\n</body>\n</html>\n"

    else:
        # invalid date
        page = None

    return page


# main admin page

def admin(gruta):

    page = header(gruta, title="Admin")

    page += "<h2>Admin</h2>\n"

    page += "<h3>Future Stories</h3>\n"

    page += "<ul>\n"

    s_set = gruta.story_set(d_from=gruta.today(), private=True)

    df = gruta.template("cfg_date_format") or "%Y-%m-%d"

    for s in s_set:
        topic_id, id = s[0], s[1]
        story = gruta.story(topic_id, id)

        page += "<li>%s - " % gruta.date_format(s[2], df)

        page += "<a href=\"%s\">%s</a>" % (gruta.url(story), story.get("title"))
        page += " <a href=\"%s\">&nbsp;&#x270E;&nbsp;</a>" % (
                    gruta.url("/admin/story/%s/%s" % (topic_id, id)))

        page += "</li>\n"

    page += "</ul>\n"

    page += "<h3>Topics</h3>\n"

    page += "<ul>\n"

    for t in sorted(list(gruta.topics(private=True))):
        topic = gruta.topic(t)
        page += "<li><a href=\"%s\">%s</a>" % (gruta.url(topic), topic.get("name"))
        page += " <a href=\"%s\">&nbsp;&#x270E;&nbsp;</a>" % (
                    gruta.url("/admin/topic/%s" % t))

        page += "</li>\n"

    page += "</ul>\n"

    page += footer(gruta)

    return page


# admin: stories

def edit_story(gruta, story, q_vars):
    """ generates an edit story page """

    # iterate q_vars and use it to fill empty story fields
    for k, v in q_vars.items():
        if k in story.fields and story.get(k) == "":
            story.set(k, v[0])

    page = header(gruta, title="Edit Story")

    page += "<h2>Edit Story</h2>\n"

    page += "<form method=\"post\" action=\"%s\">\n" % gruta.url("/admin/story/")

    page += "<p><input type=\"submit\" class=\"button\" value=\"OK\"></p>\n"

    topic_id = story.get("topic_id")

    page += "<p>Id:<br/>\n"

    page += "<select name=\"topic_id\">\n"

    for t in gruta.topics(private=True):
        page += "<option value=\"%s\"" % t

        if t == topic_id:
            page += " selected"
        else:
            page += " disabled"

        page += ">%s</option>\n" % t

    page += "</select>\n"

    page += " / "

    id = story.get("id")

    if id == "":
        page += "<input type=\"text\" size=\"40\" name=\"id\" value=\"%s\"/>\n" % id
    else:
        page += "<input type=\"text\" size=\"40\" name=\"id\" value=\"%s\" readonly/>\n" % id

    page += "</p>\n"

    date = story.get("date")
    page += "<p>Start date (empty, now):<br/>\n"
    page += "D: <input type=\"text\" size=\"2\" name=\"s_day\" value=\"%s\"/>\n" % date[6:8]
    page += "M: <input type=\"text\" size=\"2\" name=\"s_month\" value=\"%s\"/>\n" % date[4:6]
    page += "Y: <input type=\"text\" size=\"4\" name=\"s_year\" value=\"%s\"/>\n" % date[0:4]
    page += "H: <input type=\"text\" size=\"2\" name=\"s_hour\" value=\"%s\"/>\n" % date[8:10]
    page += "M: <input type=\"text\" size=\"2\" name=\"s_min\" value=\"%s\"/>\n" % date[10:12]
    page += "S: <input type=\"text\" size=\"2\" name=\"s_sec\" value=\"%s\"/>\n" % date[12:14]
    page += "</p>\n"

    date = story.get("udate")
    page += "<p>End date (empty, never):<br/>\n"
    page += "D: <input type=\"text\" size=\"2\" name=\"u_day\" value=\"%s\"/>\n" % date[6:8]
    page += "M: <input type=\"text\" size=\"2\" name=\"u_month\" value=\"%s\"/>\n" % date[4:6]
    page += "Y: <input type=\"text\" size=\"4\" name=\"u_year\" value=\"%s\"/>\n" % date[0:4]
    page += "H: <input type=\"text\" size=\"2\" name=\"u_hour\" value=\"%s\"/>\n" % date[8:10]
    page += "M: <input type=\"text\" size=\"2\" name=\"u_min\" value=\"%s\"/>\n" % date[10:12]
    page += "S: <input type=\"text\" size=\"2\" name=\"u_sec\" value=\"%s\"/>\n" % date[12:14]
    page += "</p>\n"

    format = story.get("format") or gruta.template("cfg_default_format")
    page += "<p>Format:<br/>\n"
    if format == "grutatxt":
        page += "<input type=\"radio\" name=\"format\" value=\"grutatxt\" checked> grutatxt"
        page += "<input type=\"radio\" name=\"format\" value=\"raw_html\"> raw_html"
    else:
        page += "<input type=\"radio\" name=\"format\" value=\"grutatxt\"> grutatxt"
        page += "<input type=\"radio\" name=\"format\" value=\"raw_html\" checked> raw_html"

    page += "</p>\n"

    page += "<p>Full story in indexes:<br/>\n"
    page += "<input type=\"checkbox\" name=\"full_story\""

    if id == "":
        full_story = gruta.template("cfg_full_story")
    else:
        full_story = story.get("full_story")

    if full_story == "1":
        page += " checked"

    page += "/></p>\n"

    page += "<p>Language (en, es, fr...):<br/>\n"
    page += "<input type=\"text\" size=\"2\" name=\"lang\" value=\"%s\"/>" % story.get("lang")
    page += "</p>\n"

    page += "<p>Title:</br>\n"
    page += "<input type=\"text\" size=\"60\" name=\"title\" value=\"%s\"/>\n" % story.get("title")
    page += "</p>\n"

    page += "<p>Content:<br/>\n"
    page += "<textarea name=\"content\" cols=\"80\" rows=\"30\" "
    page += "onkeyup=\"javascript:count_and_preview();\" wrap=\"virtual\""
    page += ">%s</textarea></p>\n" % story.get("content")

    page += "<p>Tags (comma separated):</br>\n"
    s_tags = ",".join(story.get("tags"))
    page += "<input type=\"text\" size=\"45\" name=\"tags\" value=\"%s\"/>\n" % s_tags
    page += "</p>\n"

    page += "<p>Redirect to (URL):</br>\n"
    page += "<input type=\"text\" size=\"45\" name=\"redir\" value=\"%s\"/>\n" % story.get("redir")
    page += "</p>\n"

    page += "<p>Reference or In Reply To (URL):</br>\n"
    page += "<input type=\"text\" size=\"45\" name=\"reference\" value=\"%s\"/>\n" % story.get("reference")
    page += "</p>\n"

#    page += "<p>Preview:<br/>\n"
#    page += "<div id=\"preview\" style=\"border: solid 1px;\"></div>\n"
#    page += "</p>"

    page += "<input type=\"hidden\" name=\"method\" value=\"post\">\n"

    page += "<p><input type=\"submit\" class=\"button\" value=\"OK\"></p>\n"
    page += "</form>\n"

    page += "<form method=\"post\" "
    page += "onsubmit=\"return confirm('Are you sure you want to delete this story?');\" "
    page += "action=\"%s\">\n" % gruta.url("/admin/story/")
    page += "<input type=\"hidden\" name=\"topic_id\" value=\"%s\">\n" % topic_id
    page += "<input type=\"hidden\" name=\"id\" value=\"%s\">\n" % id
    page += "<input type=\"hidden\" name=\"method\" value=\"delete\">\n"
    page += "<input type=\"submit\" class=\"button\" value=\"DELETE\">\n"
    page += "</form>\n"

    page += footer(gruta)

    return page


def post_story(gruta, p_data):
    """ posts a story """

    page = header(gruta, title="Post Story")

    # post data fields
    p_fields = [
        "topic_id", "id", "tags", "format", "lang", "content",
        "s_year", "s_month", "s_day", "s_hour", "s_min", "s_sec",
        "u_year", "u_month", "u_day", "u_hour", "u_min", "u_sec",
        "full_story", "redir", "title", "reference"
    ]

    s_data = {}

    # transfer post data
    for f in p_fields:
        try:
            v = p_data[f][0]
        except:
            v = ""

        s_data[f] = v

    if gruta.topic(s_data["topic_id"]):
        story = gruta.story(s_data["topic_id"], s_data["id"])

        if story is None:
            story = gruta.new_story({"topic_id": s_data["topic_id"], "id": s_data["id"]})

        gruta.story_defaults(story)

        today = gruta.today()

        # build s_date
        year  = s_data["s_year"]
        month = s_data["s_month"]
        day   = s_data["s_day"]
        hour  = s_data["s_hour"]
        min   = s_data["s_min"]
        sec   = s_data["s_sec"]

        # date component missing? get today
        if year == "" or month == "" or day == "":
            s_date = today
        else:
            s_date = year + month + day

            # hour component missing? set to 00:00:00
            if hour == "" or min == "" or sec == "":
                s_date += "000000"
            else:
                s_date += hour + min + sec

        # build u_date
        year  = s_data["u_year"]
        month = s_data["u_month"]
        day   = s_data["u_day"]
        hour  = s_data["u_hour"]
        min   = s_data["u_min"]
        sec   = s_data["u_sec"] or "00"

        if hour == "" or min == "":
            if year == "" or month == "" or day == "":
                # no date nor time: empty
                u_date = ""
            else:
                # date but no time: time 000000
                u_date = year + month + day + "000000"
        else:
            if year == "" or month == "" or day == "":
                # no date but time: story date at time
                u_date = s_date[0:8]
            else:
                # full date
                u_date = year + month + day

            u_date += hour + min + sec

        # assign
        story.set("topic_id",   s_data["topic_id"])
        story.set("id",         s_data["id"])
        story.set("date",       s_date)
        story.set("udate",      u_date)
        story.set("format",     s_data["format"])
        story.set("lang",       s_data["lang"])
        story.set("redir",      s_data["redir"])
        story.set("title",      s_data["title"])
        story.set("content",    s_data["content"].replace("\r", ""))
        story.set("full_story", "1" if s_data["full_story"] == "on" else "0")
        story.set("reference",  s_data["reference"])

        # ensure the list is empty and not [""]
        if s_data["tags"] == "":
            t = []
        else:
            t = s_data["tags"].replace(", ", ",").split(",")

        story.set("tags", t)

        gruta.save_story(story)

        # url to keep on editing
        edit_url = gruta.url("/admin/story/%s/%s" % (
            story.get("topic_id"), story.get("id")))

        page += "<p><a href=\"%s\">Continue editing</a>\n" % edit_url

        page += "<h2>%s</h2>\n" % story.get("title")
        page += pygruta.special_uris(gruta, story.get("body"))

        page += "<p><a href=\"%s\">Continue editing</a>\n" % edit_url

    else:
        page += "<h2>ERROR</h2><p>Bad topic_id.</p>"

    page += footer(gruta)

    return page


def delete_story(gruta, p_data):
    """ deletes a story """

    page = header(gruta, title="Delete Story")

    story = gruta.story(p_data["topic_id"][0], p_data["id"][0])

    if story is not None:
        gruta.delete_story(story)
        page += "<h2>Deleted</h2>"

    else:
        page += "<h2>ERROR</h2><p>Bad story.</p>"

    page += footer(gruta)

    return page


# admin:topic

def edit_topic(gruta, topic):

    page = header(gruta, title="Edit Topic")

    page += "<h2>%s</h2>\n" % topic.get("name")

    page += "<h3>Future Stories</h3>\n"

    # list of future stories on this topic
    s_set = gruta.story_set(topics=[topic.get("id")], d_from=gruta.today(), private=True)

    page += "<ul>\n"

    page += "<li><a href=\"%s\">[+]</a></li>\n" % (
        gruta.url("/admin/story/%s/" % topic.get("id")))

    df = gruta.template("cfg_date_format") or "%Y-%m-%d"

    for s in s_set:
        topic_id, id = s[0], s[1]
        story = gruta.story(topic_id, id)

        page += "<li>%s - " % gruta.date_format(s[2], df)

        page += "<a href=\"%s\">%s</a>" % (gruta.url(story), story.get("title"))
        page += " <a href=\"%s\">&nbsp;&#x270E;&nbsp;</a>" % (
                    gruta.url("/admin/story/%s/%s" % (topic_id, id)))

        page += "</li>\n"

    page += "</ul>\n"

    page += "<h3>Edit Topic</h3>\n"

    page += "<form method=\"post\" action=\"%s\">\n" % gruta.url("/admin/topic/")

    page += "<input type=\"hidden\" name=\"id\" value=\"%s\"/>\n" % topic.get("id")

    page += "<p>Name:<br/>\n"
    page += "<input type=\"text\" size=\"60\" name=\"name\" value=\"%s\"/>\n" % topic.get("name")
    page += "</p>\n"

    page += "<p>Description:<br/>\n"
    page += "<input type=\"text\" size=\"80\" name=\"description\" value=\"%s\"/>\n" % topic.get("description")
    page += "</p>\n"

    page += "<p>Internal:<br/>\n"
    page += "<input type=\"checkbox\" name=\"internal\""

    if topic.get("internal") == "1":
        page += " checked"

    page += "/>\n</p>\n"

    page += "<p>Editors:<br/>\n"
    page += "<input type=\"text\" size=\"40\" name=\"editors\" value=\"%s\"/>\n" % topic.get("editors")
    page += "</p>\n"

    page += "<input type=\"hidden\" name=\"method\" value=\"post\">\n"

    page += "<p><input type=\"submit\" class=\"button\" value=\"OK\"></p>\n"
    page += "</form>\n"

    page += footer(gruta)

    return page


def post_topic(gruta, p_data):
    """ posts a topic """

    page = header(gruta, title="Post Topic")

    id = p_data["id"][0]

    topic = gruta.topic(id)

    if topic is not None:
        page += "<h2>" + p_data["id"][0] + "</h2>\n"

        for f in ("name", "description", "internal", "editors"):
            try:
                v = p_data[f][0]
            except:
                v = ""

            if f == "internal":
                v = "1" if v == "on" else "0"

            topic.set(f, v)

        gruta.save_topic(topic)

        page += "<h2>OK</h2>\n"

    else:
        page += "<h2>ERROR</h2><p>Bad topic_id.</p>"

    return page


# handler

def get_handler(gruta, q_path, q_vars):
    """ HTML get handler """

    status, body, ctype = 0, None, "text/html; charset=utf-8"

    if q_path == "/" or q_path == "/index.html":
        # INDEX

        # do info/index exist?
        story_o = gruta.story("info", "index")

        if story_o is not None:

            body = header(gruta, title=gruta.template("cfg_slogan"),
                image=story_o.get("image"))

            body += story_o.get("body")
            body += footer(gruta)

            status, body = 200, pygruta.special_uris(gruta, body)

        else:
            offset   = 0
            num      = int(gruta.template("cfg_index_num"))
            i_topics = gruta.template("cfg_index_topics").split(":")
            title    = gruta.template("cfg_slogan")
            s_set    = list(gruta.story_set(topics=i_topics, offset=offset, num=num + 1))

            status, body = 200, paged_index(gruta, s_set, offset, num, title)


    elif re.search("^/s/[0-9a-f]+", q_path):
        # SHORT URL

        body = gruta.unshorten_url(q_path)

        if body != "":
            status = 303 # redirect to body
        else:
            status = 404


    elif re.search("^/~\d+\.html$", q_path):
        # INDEX with offset

        s        = q_path.replace(".html", "")[2:]
        offset   = int(s)
        num      = int(gruta.template("cfg_index_num"))
        i_topics = gruta.template("cfg_index_topics").split(":")
        title    = gruta.template("cfg_slogan")
        s_set    = list(gruta.story_set(topics=i_topics, offset=offset, num=num + 1))

        if len(s_set):
            status, body = 200, paged_index(gruta, s_set, offset, num, title)


    elif re.search("^/img/.+$", q_path):
        # Images
        id = q_path.split("/")[-1]

        body = gruta.image(id)

        if body is not None:
            status, ctype = 200, gruta.image_mime_type(id)
        else:
            status = 404


    elif q_path == "/tag/" or q_path == "/tag/index.html":
        # TAG list

        status, body = 200, tag(gruta)


    elif re.search("^/tag/.+\.html$", q_path):
        # TAG

        s          = q_path.replace(".html", "")[1:]
        dummy, t   = s.split("/")
        s_set      = list(gruta.story_set(tags=[t]))

        if len(s_set):
            status, body = 200, tag(gruta, t, s_set)
        else:
            status = 404


    elif re.search("^/user/.+\.html$", q_path):
        # USER

        s        = q_path.replace(".html", "")[1:]
        dummy, u = s.split("/")
 
        user_o = gruta.user(u)

        if user_o is not None:
            status, body = 200, user(gruta, user_o)
        else:
            status = 404


    elif re.search("^/calendar/.*", q_path):
        # CALENDAR

        a = q_path[1:].split("/")

        # get year
        if len(a) == 4:
            year  = int(a[1])
            month = int(a[2])
            day   = int(a[3] or "0")
        else:
            year  = None
            month = None
            day   = 0

        # get topic list for the calendar
        topics = gruta.template("cfg_calendar_topics")

        if topics == "":
            topics = None
        else:
            topics = topics.split(":")

        if day == 0:
            body = calendar_month(gruta, year, month, topics)
        else:
            body = calendar_day(gruta, year, month, day, topics)

        if body is not None:
            # "202 Accepted" to avoid being cached
            status = 202


    elif re.search("^/admin/story/.+", q_path):
        # EDIT_STORY

        l = q_path[1:].split("/")

        # id is optional for new stories
        if len(l) == 4:
            topic_id, id = l[2], l[3]
        else:
            topic_id, id = l[2], ""

        topic = gruta.topic(topic_id)

        if topic is not None:
            story_o = gruta.story(topic_id, id)

            if story_o is None:
                story_o = gruta.new_story({"topic_id": topic_id, "id": id})

            status, body = 202, edit_story(gruta, story_o, q_vars)

        else:
            status = 404


    elif re.search("^/admin/topic/.+", q_path):
        # EDIT_TOPIC

        l = q_path[1:].split("/")

        if len(l) == 3:
            topic_id = l[2]

            topic = gruta.topic(topic_id)

            if topic is not None:
                status, body = 202, edit_topic(gruta, topic)
            else:
                status = 404
        else:
            status = 404


    elif re.search("^/admin/?$", q_path):
        # ADMIN

        status, body = 202, admin(gruta)


    elif re.search("^/[^/]+/(index\.html)?$", q_path) or re.search("^/[^/]+/~\d+\.html$", q_path):
        # TOPIC, with or without offset

        s     = q_path.replace(".html", "")[1:]
        id, o = s.split("/")

        if o.startswith("~"):
            o = o.replace("~", "")
        else:
            o = "0"

        topic = gruta.topic(id)

        if topic is not None and (gruta.logged_user or topic.get("internal") != "1"):
            # visible topic

            private = True if gruta.logged_user else False

            offset = int(o)

            # first page? test if there is an index story
            if offset == 0:
                story_o = gruta.story(id, "index")
            else:
                story_o = None

            if story_o is not None:
                status, body = 200, story(gruta, story_o)
            else:
                num    = int(gruta.template("cfg_topic_num"))
                title  = topic.get("name")

                # as private can be set to True because there is a logged user,
                # set d_to to today to avoid showing future stories
                s_set  = list(gruta.story_set(topics=[id],
                    offset=offset, num=num + 1, private=private, d_to=gruta.today()))

                if len(s_set):
                    status, body = 200, paged_index(gruta, s_set, offset, num, title, id)
                else:
                    status = 404
        else:
            status = 404


    elif re.search("^/[^/]+/.+\.html$", q_path):
        # STORY

        s            = q_path.replace(".html", "")[1:]
        topic_id, id = s.split("/")
        topic        = gruta.topic(topic_id)

        if topic is not None and topic.get("internal") != "1":
            story_o = gruta.story(topic_id, id)

            if story_o is not None:
                status, body = 200, story(gruta, story_o)
            else:
                status = 404
        else:
            status = 404


    return status, body, ctype


def post_handler(gruta, q_path, q_vars, p_data):
    """ HTML post handler """

    status, body, ctype = 404, "<h1>404 Not Found</h1>", "text/html; charset=utf-8"

    if q_path == "/admin/story/":
        if p_data["method"][0] == "delete":
            status, body = 202, delete_story(gruta, p_data)
        else:
            status, body = 202, post_story(gruta, p_data)

    if q_path == "/admin/topic/":
        status, body = 202, post_topic(gruta, p_data)

    return (status, body, ctype)
