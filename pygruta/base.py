#
#   pygruta CMS
#   ttcdt <dev@triptico.com>
#
#   This software is released into the public domain.
#

#   base classes

import datetime, re, hashlib, time, os
import pygruta
import pygruta.cache
import pygruta.http

import pygruta.html as html
import pygruta.xml as xml
import pygruta.text as text
import pygruta.activitypub as activitypub
import pygruta.calendar as calendar

class O:
    # a very basic class for objects
    # with a limited set of fields
    def __init__(self, fields, data={}):
        self.fields = fields
        self.data   = {}

        self.fill(data)

    def fill(self, data):
        if data is None:
            self = None
        else:
            for f, v in data.items():
                self.set(f, v)

        return self

    def get(self, field):
        if field in self.fields:
            v = self.data.get(field)

            if v is None:
                v = ""

            return v
        else:
            raise KeyError(field)

    def set(self, field, value):
        if field in self.fields:
            self.data[field] = value
        else:
            raise KeyError(field)

# Gruta Data

class Topic(O):
    def __init__(self, data={}):
        super().__init__(fields=[
            "id", "name", "editors", "max_stories",
            "internal", "description"
        ], data=data)

class Story(O):
    def __init__(self, data={}):
        super().__init__(fields=[
            "id", "topic_id", "title", "date", "date2", "userid",
            "format", "hits", "toc", "has_comments",
            "full_story", "content", "description", "abstract",
            "body", "image", "tags", "udate", "redir", "lang",
            "reference", "revision", "ctime", "mtime", "context"
        ], data=data)

class User(O):
    def __init__(self, data={}):
        super().__init__(fields=[
            "id", "username", "email", "password", "can_upload",
            "is_admin", "xdate", "bio", "avatar", "url",
            "privkey", "pubkey"
        ], data=data)

class Follower(O):
    def __init__(self, data={}):
        super().__init__(fields=[
            "id", "user_id", "context", "date", "network",
            "ldate", "failures", "disabled"
        ], data=data)


# Gruta source base object

class Gruta:
    def __init__(self):
        # store the host_name
        self.host_name = self.template("cfg_host_name")

        # not a logged user by default
        self.logged_user = ""

        # empty url_prefix
        self.url_prefix = ""

        # debug flag (if 0, log messages of DEBUG category don't show)
        self.debug = 0

        self.html_cache = pygruta.cache.Cache()
        self.page_cache = pygruta.cache.Cache()

        # timed flush information
        self.timed_flush_max  = 24 * 60 * 60
        self.timed_flush_last = time.time()

    def flush(self):
        """ flushes possible pending data in memory """
        self._flush()
        self.log("INFO", "FLUSH")

    def timed_flush(self):
        """ flushes if the counter timeouts """
        t = time.time()
        r = self.timed_flush_max - (t - self.timed_flush_last)

        if r < 0:
            self.flush()
            self.timed_flush_last = t

        return r

    def close(self):
        self._close()


    def clear_caches(self):
        """ clears internal caches, if needed """

        self.html_cache.clear()
        self.page_cache.clear()


    # helping functions

    def is_subset_of(self, subset, superset):
        cnt = 0
    
        for e in subset:
            # if e starts with !, it's an element
            # that must *not* be in the superset
            if e[0] == "!":
                if e[1:] in superset:
                    cnt = 0
                    break
                else:
                    cnt += 1
            elif e in superset:
                cnt += 1
    
        return bool(cnt and cnt == len(subset))
    

    # date processing

    def wday_name(self, day):
    # FIXME: these don't belong here
        return "LMXJVSD"[day]

    def month_name(self, month):
    # FIXME: these don't belong here
        return ["enero", "febrero", "marzo",
               "abril", "mayo", "junio",
               "julio", "agosto", "septiembre",
               "octubre", "noviembre", "diciembre"][month]

    def datetime_to_date(self, datetime):
        return datetime.strftime("%Y%m%d%H%M%S")

    def date_to_datetime(self, date):
        return datetime.datetime(int(date[0:4]),
            int(date[4:6]), int(date[6:8]),
            int(date[8:10]), int(date[10:12]),
            int(date[12:14]))

    def date_format(self, date, format):
        dt = self.date_to_datetime(date)

        # FIXME: move elsewhere
        if self.template("cfg_lang") == "es":
            format = format.replace("%B", self.month_name(dt.month - 1))

        return dt.strftime(format)

    def today(self):
        return self.datetime_to_date(datetime.datetime.now())

    def today_utc(self):
        return self.datetime_to_date(datetime.datetime.utcnow())

    def md5(self, string):
        m = hashlib.md5()
        m.update(string.encode())
        return m.hexdigest()


    # logging

    def log(self, category, string):

        # DEBUG messages are only shown is self.debug is True
        if category == "DEBUG" and self.debug == 0:
            return

        # build message
        s = pygruta.log_str(category, string)

        # get log file (i.e. /home/angel/log/pygruta-triptico-%Y%m%d.log)
        lf = self.template("cfg_log_file")

        if lf != "":
            # lf can be strftime()-tagged
            lf = datetime.datetime.now().strftime(lf)

            try:
                with open(lf, "a") as f:
                    f.write(s + "\n")
            except:
                pass

        # if stdout is a tty, also print there
        if os.isatty(1):
            print(s, flush=True)


    def valid_id(self, id):
        """ tests if an id is valid """

        return bool(re.match("^[A-Za-z0-9_-]+$", id))


    # topics

    def topic(self, id):
        """ opens an existent topic """

        if self.valid_id(id):
            topic = Topic({"id": id})
            topic = self._load_topic(topic)
        else:
            topic = None

        return topic


    def new_topic(self, o={}):
        """ creates a new topic """

        return Topic(o)


    def save_topic(self, topic):
        """ saves a topic """

        if self.valid_id(topic.get("id")):
            topic = self._save_topic(topic)
        else:
            topic = None

        return topic


    # stories

    def story(self, topic_id, id):
        """ opens an existent story """

        if self.valid_id(topic_id) and self.valid_id(id):
            story = Story({"topic_id": topic_id, "id": id})
            story = self._load_story(story)
        else:
            story = None

        return story


    def new_story(self, o={}):
        """ creates a new story """

        return Story(o)


    def story_new_id(self, story):
        """ creates an automatic id for a story """

        if story.get("title"):
            # create a 'slug' for the title
            id = pygruta.slugify(story.get("title"))

        else:
            # pick one from date
            id = "i%x" % int(self.today()[2:])

        seq = 1

        # search now if there is already a story with that id
        while True:
            if self.story(story.get("topic_id"), id) is None:
                break
            else:
                # strip (possible) -NNN at the end
                id = re.sub("-[0-9]+$", "", id)
                seq += 1
                id += "-%d" % seq

        story.set("id", id)


    def story_defaults(self, story):
        """ fills the default fields of a story """

        # no date? set it to today
        if story.get("date") == "":
            story.set("date", self.today())

        # no format? set default
        if story.get("format") == "":
            story.set("format", self.template("cfg_default_format") or "raw_html")

        # no full_story? set default
        if story.get("full_story") == "":
            story.set("full_story", self.template("cfg_full_story") or "0")

        # no revision? set default
        if story.get("revision") == "":
            story.set("revision", "0")

        # no user? set to the most reasonable value
        if story.get("userid") == "":
            story.set("userid", self.logged_user or self.template("cfg_main_user") or "admin")

        return story


    def save_story(self, story):
        """ saves a story """

        topic_id = story.get("topic_id")

        if self.topic(topic_id) is not None:
            # render the story (title field can now be set)
            self.render(story)

            # no id? create one
            if story.get("id") == "":
                self.story_new_id(story)

            if self.valid_id(story.get("id")):
                # fill the story defaults in case they are not set
                self.story_defaults(story)

                today = self.today()

                # no ctime?
                if story.get("ctime") == "":
                    date = story.get("date")
                    story.set("ctime", today if today < date else date);

                # set mtime
                story.set("mtime", today)

                # increment revision
                story.set("revision", str(int(story.get("revision")) + 1))

                # do the real save
                story = self._save_story(story)

            else:
                story = None

        else:
            story = None

        return story


    def delete_story(self, story):
        """ deletes a story """

        return self._delete_story(story)


    # USERS

    def user(self, id):
        """ returns an existent user """

        if self.valid_id(id):
            user = User({"id": id})
            user = self._load_user(user)
        else:
            user = None

        return user

    def new_user(self, o={}):
        """ creates a new user """

        return User(o)

    def save_user(self, user):
        """ saves a user """

        if self.valid_id(user.get("id")):
            user = self._save_user(user)
        else:
            user = None

        return user


    # FOLLOWERS

    def follower(self, user_id, id):
        t = Follower({"id": id, "user_id": user_id})
        return self._load_follower(t)

    def new_follower(self, o):
        return Follower(o)

    def save_follower(self, follower):
        if follower.get("user_id") == "":
            raise KeyError("user_id")

        if follower.get("id") == "":
            raise KeyError("id")

        return self._save_follower(follower)


    # IMAGES

    def valid_image_id(self, id):
        return not(bool("/" in id))

    def image_mime_type(self, id):
        mt = None

        if re.search(r"\.jpe?g$", id):
            mt = "image/jpeg"
        elif id.endswith(".gif"):
            mt = "image/gif"
        elif id.endswith(".png"):
            mt = "image/png"
        elif id.endswith(".ico"):
            mt = "image/x-icon"

        return mt


    # SHORTENED URLS

    def shorten_url(self, l_url):

        i = 1
        f = False
        s = None

        t = self.topic("s")

        if t is None:
            # topic doesn't exist? create it and start from 1
            t = self.new_topic({"id": "s", "name": "Shortened URLs"})
            self.save_topic(t)

            # create an index story that is itself a redirect to index
            s = self.new_story({
                "topic_id": "s",
                "id":       "index",
                "content":  "&nbsp;",
                "redir":    self.aurl(),
                "title":    self.aurl(),
                "date":     "19000101000000"
                }
            )

            self.save_story(s)

        else:
            # find a story that redirs to l_url
            for id in self.stories("s"):
                s = self.story("s", id)

                if s.get("redir") == l_url:
                    f = True
                    break

                i += 1

        if not f:
            # not found: create new story
            s = self.new_story({
                "topic_id": "s",
                "id":       "%x" % i,
                "content":  "&nbsp;",
                "redir":    l_url,
                "title":    l_url
                }
            )

            self.save_story(s)

        return self.aurl(s)


    # others

    def url(self, object=None, prefix=None, absolute=False):
        """ Returns a gruta URL depending on object """

        base_url = "https://" + self.host_name

        if absolute:
            s = base_url
        else:
            s = ""

        s += self.url_prefix

        if isinstance(object, Story):
            s += "/%s/%s.html" % (object.get("topic_id"), object.get("id"))

        elif isinstance(object, Topic):
            s += "/%s/index.html" % object.get("id")

        elif isinstance(object, User):
            s += "/user/%s.html" % object.get("id")

        elif isinstance(object, str):
            if prefix is not None:
                if prefix[0] != "/":
                    s += "/"

                s += prefix

            if object[0] != "/":
                s += "/"

            s += object

        else:
            s += "/"

        # fix base_url repetitions
        if s.startswith(base_url + "/" + base_url):
            s = s[len(base_url) + 1:]

        return s

    def aurl(self, object=None, prefix=None):
        """ Returns a gruta URL depending on object """

        return self.url(object, prefix, absolute=True)


    def render(self, story):
        # renders the story depending on format
        content = story.get("content")
        format  = story.get("format")

        title    = story.get("title")
        body     = ""
        abstract = ""

        if format == "text":
            # content is verbatim text

            if title == "":
                # pick title from first line
                title = content.split("\n")[0]
                title = title.replace("\n", "")

            # fix problematic chars
            content = re.sub("&", "&amp;", content)
            content = re.sub("<", "&lt;", content)
            content = re.sub(">", "&gt;", content)

            # wrap body as preformatted
            body = "<pre>\n" + content + "</pre>\n"
            abstract = body

        else:
            # grutatxt, html and raw_html are similar

            if format == "grutatxt":
                grutatxt = self.template("cfg_grutatxt_path")

                if grutatxt == "":
                    grutatxt = "/usr/local/bin/grutatxt -f 1 -dl -nb"

                cmd = grutatxt.split(" ")

                # save content to a temporary file
                import tempfile
                f = tempfile.TemporaryFile()
                f.write(content.encode("utf-8"))
                f.seek(0)

                # pipe through grutatxt
                import subprocess
                try:
                    p = subprocess.Popen(cmd, stdin=f, stdout=subprocess.PIPE)
                    content = p.stdout.read().decode("utf-8")
                except:
                    content = ""

            if title == "":
                # get title
                x = re.search("<\s*h1[^>]*>[^<]*<\s*/h1[^>]*>",
                    content, flags=re.IGNORECASE)
                if x is None:
                    x = re.search("<\s*h2[^>]*>[^<]*<\s*/h2[^>]*>",
                        content, flags=re.IGNORECASE)

                if x is not None:
                    title = re.sub("<[^>]+>", "", x.group(0))

            # strip unacceptable tag sets
            content = re.sub(r"<\s*head[^>]*>.*<\s*/head[^>]*>", "",
                content, flags=re.IGNORECASE)

            # strip unacceptable tags
            bad_tags = "|".join([
                "style", "html", "!doctype", "body", "meta", "link"
                ])

            content = re.sub(r"<\s*/?(" + bad_tags + ")[^>]*>", "",
                        content, flags=re.IGNORECASE)

            # is there a spaceship in the content?
            if "<->" in content:
                abstract = content.split("<->")[0]
                content  = content.replace("<->", "")

            if abstract == "" or story.get("full_story") == "1":
                abstract = content

            body = content

        # clean the title
        title = title.replace("\n", " ")
        title = re.sub("%", "&#37;", title)
        title = re.sub("^\s+", "", title)
        title = re.sub("\s+$", "", title)

        # strip the title
        body     = re.sub("<h2.*>[^<]+</h2>", "", body)
        abstract = re.sub("<h2.*>[^<]+</h2>", "", abstract)

        story.set("title",    title)
        story.set("body",     body)
        story.set("abstract", abstract)

        # find an image in the body
        x = re.search("(img|thumb)://([\w0-9_\.-]+)", body)

        if x is not None:
            story.set("image", "/img/" + x.group(2))


    def notify(self, message):
        """ sends a notification """

        bot     = self.template("cfg_telegram_notify_bot")
        chat_id = self.template("cfg_telegram_notify_chat_id")

        if bot and chat_id:
            # notify via Telegram
            status, body = pygruta.http.request("POST",
                "https://api.telegram.org/bot" + bot + "/sendMessage",
                fields={
                    "chat_id": chat_id,
                    "text":    message
                })

        # print it
        self.log("INFO", "NOTIFY %s" % message)


    def feed(self):
        """ returns the story_set for the feed """

        rss_num    = int(self.template("cfg_rss_num"))
        rss_topics = self.template("cfg_rss_topics").split(":")

        return self.story_set(topics=rss_topics, num=rss_num)


    # TAGS

    def tags(self, private=False, test=False):
        """ returns a dict of tag -> [[topic_id, id]] """
        c = {}

        for s in self.story_set(private=private):
            for t in s[3]:
                l = c.get(t)
                if not l:
                    l = c[t] = []

                l.append([s[0], s[1]])

                # if test is set, only check that there is at least 1 tag
                if test:
                    break

        return c


    def create(self, uid=None, topic_id=None):
        """ creates a new Gruta site """

        self._create()

        if topic_id is None:
            topic_id = ""

        if uid is None:
            uid = "admin"

        topics = [ topic_id ]
        topics_str = ":".join(topics)

        default_templates = {
            "cfg_site_name":        "Welcome to Pygruta",
            "cfg_slogan":           "A newly created Pygruta site",
            "cfg_index_topics":     topics_str,
            "cfg_rss_topics":       topics_str,
            "cfg_main_menu_topics": topics_str,
            "cfg_index_num":        "10",
            "cfg_rss_num":          "10",
            "cfg_topic_num":        "10",
            "cfg_copyright":        "",
            "cfg_main_user":        uid,
            "cfg_host_name":        "FILLME",
            "css_compact":          "body { max-width: 50em; margin: auto; font-family: 'Courier New', monospace; padding: 1em }\n" +
                                    "#subtitle { color: #a0a0a0 }\n" +
                                    "blockquote { margin: 0 20px; padding: 0 20px; border-left: 6px solid #efefef; font-style: italic }\n" +
                                    ".right { float: right; margin: 0.5em; padding: 1em; padding-top: 0 }\n" +
                                    ".left { float: left; margin: 0.5em; padding: 1em }\n" +
                                    ".center { display: flex; justify-content: center; align-items: center }\n" +
                                    ".hidden { display: none }\n" +
                                    ".categories { clear: both }\n" +
                                    ".dt-published, .p-author { color: #a0a0a0 }\n" +
                                    "#main nav .prev { float: right }\n" +
                                    "footer { clear: both }\n" +
                                    ".h-card { clear: both }\n" +
                                    "img { max-width: 100% }",
            "css_calendar":         "html, body { height: 100%; margin: 0; font-family: arial }\n" +
                                    ".calendar { width: 100%; height: 100%; margin: 0; padding: 0; font-size: 9pt }\n" +
                                    ".month-name { font-size: 280%; position: fixed; z-index: -1;\n" +
                                    "  width: 50%; height: 10%; text-align: center; top: 40%; left: 25%; }\n" +
                                    ".month { height: 100%; margin: 0; padding: 0; }\n" +
                                    ".box { box-sizing: border-box; float: left; overflow: hidden; opacity: 0.9;\n" +
                                    "  border-right: 1px solid #dddddd; border-bottom: 1px solid #dddddd;\n" +
                                    "  width: 14.28%; height: 16.66%; background: #f0f0f0 }\n" +
                                    ".day { width: 14.28%; height: 16.66%; margin: 0; padding: 0; float: left; }\n" +
                                    ".day-label { text-align: center; margin: 3px; }\n" +
                                    ".this-month { background: white }\n" +
                                    ".today { background: #1982d1; color: white; border-radius: 4px }\n" +
                                    ".day-content { white-space: nowrap }\n" +
                                    ".button { text-align: center; font-size: 300%; }\n" +
                                    "a { color: black }"
        }

        user_data = {
            "id":       uid,
            "username": uid,
            "email":    uid + "@localhost"
        }

        for (id, content) in default_templates.items():
            if self.template(id) == "":
                self.save_template(id, content)

        for t in topics:
            topic = self.new_topic({"id": t, "name": t})
            self.save_topic(topic)

        if len(list(self.users())) == 0:
            user = self.new_user(user_data)
            self.save_user(user)


    def copy(self, org):
        """ copies the org source into this db """

        self._create()

        for topic_id in org.topics(private=True):
            topic = org.topic(topic_id)

            org.log("DEBUG", "Create: topic '%s'" % topic_id)
            self.save_topic(topic)

            for id in org.stories(topic_id):
                story = org.story(topic_id, id)

                org.log("DEBUG", "Create: story '%s/%s'" % (topic_id, id))
                self.save_story(story)

        for id in org.users():
            user = org.user(id)

            org.log("DEBUG", "Create: user '%s'" % id)
            self.save_user(user)

            for fwid in org.followers(id):
                follower = org.follower(id, fwid)

                org.log("DEBUG", "Create: follower '%s/%s'" % (id, fwid))
                self.save_follower(follower)

        for id in org.templates():
            content = org.template(id)

            org.log("DEBUG", "Create: template '%s'" % id)
            self.save_template(id, content)

        for id in org.images():
            content = org.image(id)

            org.log("DEBUG", "Create: image '%s'" % id)
            self.save_image(id, content)


    def get_handler(self, q_path, q_vars={}):
        """ global GET handler """

        status, body, ctype = 0, None, None

        # cascade all the handler

        self.log("DEBUG", "get_handler: %s" % q_path)

        if status == 0:
            # calendar before html
            status, body, ctype = calendar.get_handler(self, q_path, q_vars)

        if status == 0:
            status, body, ctype = html.get_handler(self, q_path, q_vars)

        if status == 0:
            status, body, ctype = xml.get_handler(self, q_path, q_vars)

        if status == 0:
            status, body, ctype = text.get_handler(self, q_path, q_vars)

        if status == 0:
            status, body, ctype = activitypub.get_handler(self, q_path, q_vars)

        if status == 0:
            status, body, ctype = activitypub.webfinger_get_handler(
                                self, q_path, q_vars)


        return status, body, ctype
